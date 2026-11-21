"""CPU scripted training checks with no optional ML packages."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from exploratory.ft1 import plan, training as ft1_training
from exploratory.track_b import training


class Scalar(float):
    device = SimpleNamespace(type="cpu")
    requires_grad = True

    def detach(self):
        return self

    float = cpu = clone = sum = detach
    def item(self):
        return float(self)

    def __sub__(self, other):
        return Scalar(float(self) - other)

    def square(self):
        return Scalar(self ** 2)

    def count_nonzero(self):
        return Scalar(bool(self))


class Parameter:
    device = Scalar.device
    requires_grad = True

    def detach(self):
        return self.value


class Adapter:
    def __init__(self, path):
        self.parameter = Parameter()
        self.parameter.value = Scalar((path / "adapter_model.safetensors").read_text())
        lora_a = Parameter()
        lora_a.value = Scalar(1)
        self.tensors = [("layer.lora_A.default.weight", lora_a),
                        ("layer.lora_B.default.weight", self.parameter)]

    @property
    def weight(self):
        return self.parameter.value

    def parameters(self):
        return iter((self.parameter,))

    def named_parameters(self):
        return iter(self.tensors)

    def save_pretrained(self, path, *, safe_serialization):
        assert safe_serialization
        path.mkdir()
        (path / "adapter_model.safetensors").write_text(str(self.weight))


def scripted_loss(model, inputs, reason_mask, retain, denominator):
    loss = (model.weight - 1) ** 2
    counts = {"action": 1, "reason": int(reason_mask[0][-1])}
    sums = {name: loss * count for name, count in counts.items()}
    retain(dict(sums=sums, counts=counts))
    return Scalar(sum(sums.values()) / denominator)


class ScriptedTrainer:
    model_accepts_loss_kwargs = True
    _loss_shifts_labels = True
    loss_is_scaled_for_ga = True

    def __init__(self, model, args, train_dataset, data_collator, callbacks):
        self.model, self.args = model, args
        self.output = Path(args.output_dir).parent
        if self.output.exists() or args.should_save:
            raise AssertionError("Trainer would create output before training")
        self.train_dataset, self.collate = train_dataset, data_collator
        self.callback = callbacks[0]
        self.state = SimpleNamespace(global_step=0)

    def _get_num_items_in_batch(self, batches, device):
        return sum(sum(label != -100 for label in batch["labels"][0][1:])
                   for batch in batches)

    def train(self):
        if not self.output.is_dir():
            raise AssertionError("Output directory was not created before train")
        rows = iter(self._get_train_sampler())
        for step in range(1, self.args.max_steps + 1):
            batches = [self.collate([row]) for row in
                       [next(rows) for _ in range(self.args.gradient_accumulation_steps)]]
            denominator = self._get_num_items_in_batch(batches, self.args.device)
            loss = sum(self.compute_loss(self.model, batch, num_items_in_batch=denominator)
                       for batch in batches)
            # The stand-in's quadratic objective has derivative 2 * (weight - 1).
            self.model.parameter.value = Scalar(self.model.weight - self.args.learning_rate * 2 * (self.model.weight - 1))
            self.state.global_step = step
            self.callback.on_step_end(self.args, self.state, None,
                                      optimizer=SimpleNamespace(step_was_skipped=False))
        return SimpleNamespace(training_loss=loss)


class TrainingTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.adapter = self.root / "start"
        self.adapter.mkdir()
        (self.adapter / "adapter_config.json").write_text("{}")
        (self.adapter / "adapter_model.safetensors").write_text("3")
        self.sha = training.core.digest(training.core.inventory(self.adapter))
        self.output = self.root / "output"
        self.events = []

    def run_scripted_training(self, device="cpu", *, steps=3, checkpoint_steps=(1, 3),
                              allow_cpu=True, model=None, target_count=1):
        torch = SimpleNamespace(tensor=lambda value: value, utils=SimpleNamespace(
            data=SimpleNamespace(SequentialSampler=iter)))
        arguments = Mock(side_effect=lambda **kwargs: SimpleNamespace(device="cpu", **kwargs))
        class FakeTrainingArguments:
            def __init__(self, **kwargs):
                vars(self).update(vars(arguments(**kwargs)))

        transformers = SimpleNamespace(Trainer=ScriptedTrainer, TrainerCallback=object,
                                       TrainingArguments=FakeTrainingArguments)
        rows = [bool(i % 2) for i in range(steps * plan.core.RECIPE["accumulation"])]
        tokenizer = Mock()
        if model is None:
            model = Adapter(self.adapter)
        model.parameter.device = SimpleNamespace(type=device)
        with (patch.dict("sys.modules", {"torch": torch, "transformers": transformers}),
              patch.object(training, "_load_adapter", return_value=(model, target_count)) as load,
              patch.object(training, "record", side_effect=lambda tok, reason: (
                  dict(labels=[-100, 2, 3 if reason else -100]), [False, False, reason])),
              patch.object(training, "split_loss", side_effect=scripted_loss),
              patch.object(training.ft0b, "check_internals"),
              patch.object(training.ft0b, "tables") as tables,
              patch.object(training.ft0b.ft0, "finite_tensors")):
            result = training.train(None, tokenizer, rows, adapter=self.adapter,
                                    adapter_sha256=self.sha, output=self.output, seed=4,
                                    retain=self.events.append, steps=steps, checkpoint_steps=checkpoint_steps,
                                    expected_count=len(rows), allow_cpu=allow_cpu)
        load.assert_called_once_with(None, self.adapter, allow_cpu=allow_cpu)
        return result, arguments.call_args.kwargs, tables, model

    def test_resume_loss_checkpoints_and_norm(self):
        result, arguments, _, _ = self.run_scripted_training()
        self.assertEqual(result, {"steps": 3, "skipped_steps": []})
        loaded = next(event for event in self.events if event["event"] == "adapter_loaded")
        self.assertEqual(loaded["adapter_sha256"], self.sha)
        self.assertTrue(loaded["nonzero_lora_b"])
        self.assertEqual(loaded["trainable_tensors"], 2)
        setup = next(event for event in self.events if event["event"] == "training_setup")
        self.assertEqual((setup["rows"], setup["expected_count"], setup["max_skipped"]), (24, 24, 0))
        self.assertFalse(setup["cuda"])
        self.assertFalse(setup["fp16"])
        self.assertTrue(arguments["use_cpu"])
        tokenized = next(event for event in self.events if event["event"] == "tokenized_real_records")
        self.assertEqual(tokenized["examples"], 24)
        self.assertCountEqual(tokenized["trained_tokens"], [1] * 12 + [2] * 12)
        self.assertEqual(tokenized["data_order_sha256"], setup["data_order_sha256"])
        losses = [event for event in self.events if event["event"] == "loss_split"]
        baseline = scripted_loss(Adapter(self.adapter), {}, [[False, True]], Mock(), 2)
        self.assertEqual([row["step"] for row in losses], [1, 2, 3])
        self.assertEqual(losses[0]["loss"], baseline)
        self.assertEqual(set(losses[0]["sums"]), {"action", "reason"})
        self.assertGreater(losses[0]["counts"]["reason"], 0)
        self.assertLess(losses[-1]["loss"], baseline)
        self.assertEqual(sorted(path.name for path in self.output.iterdir()),
                         ["checkpoint-1", "checkpoint-3"])
        norms = [(event["step"], event["l2"]) for event in self.events
                 if event["event"] == "adapter_update_norm"]
        self.assertEqual([step for step, _ in norms], [0, 1, 3])
        self.assertEqual(norms[0][1], 0)
        for step, norm in norms[1:]:
            self.assertGreater(norm, 0)
            self.assertAlmostEqual(norm, abs(Adapter(self.output / f"checkpoint-{step}").weight - 3))
        self.assertEqual(Adapter(self.adapter).weight, 3)
        for argument, key in {"per_device_train_batch_size": "batch", "learning_rate": "lr",
                              "gradient_accumulation_steps": "accumulation",
                              "optim": "optimizer", "lr_scheduler_type": "scheduler",
                              "warmup_steps": "warmup", "weight_decay": "weight_decay"}.items():
            self.assertEqual(arguments[argument], plan.core.RECIPE[key])

    def test_fake_cuda_trainer_recipe(self):
        _, args, tables, model = self.run_scripted_training(
            "cuda", steps=11, checkpoint_steps=None, allow_cpu=False)
        recipe = plan.core.RECIPE
        self.assertEqual(args, {
            "output_dir": str(self.output / "trainer"), "num_train_epochs": 1,
            "per_device_train_batch_size": recipe["batch"],
            "gradient_accumulation_steps": recipe["accumulation"],
            "learning_rate": recipe["lr"], "optim": recipe["optimizer"],
            "lr_scheduler_type": recipe["scheduler"], "warmup_steps": recipe["warmup"],
            "weight_decay": recipe["weight_decay"], "seed": 4, "data_seed": 4,
            "fp16": True, "gradient_checkpointing": True, "max_steps": 11,
            "save_strategy": "no", "logging_steps": 1, "logging_nan_inf_filter": False,
            "report_to": [], "remove_unused_columns": False,
        })
        tables.assert_called_once_with(model, "after_cast", self.events.append, cast=True)
        setup = next(event for event in self.events if event["event"] == "training_setup")
        self.assertEqual(setup["checkpoint_steps"], [11])
        self.assertEqual(setup["max_skipped"], 1)
        self.assertTrue(setup["cuda"])
        self.assertTrue(setup["fp16"])

    def test_cpu_training_requires_opt_in(self):
        with self.assertRaisesRegex(ValueError, "requires a CUDA model"):
            self.run_scripted_training(allow_cpu=False)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.events, [])

    def test_zero_lora_b_refuses_training(self):
        model = Adapter(self.adapter)
        with self.assertRaisesRegex(ValueError, "per resolved target"):
            self.run_scripted_training(model=model, target_count=2)
        extra = Parameter()
        extra.value = Scalar(0)
        model.tensors.extend([("other.lora_A.default.weight", extra), ("other.bias", extra)])
        with self.assertRaisesRegex(ValueError, "per resolved target"):
            self.run_scripted_training(model=model, target_count=2)
        model.tensors[-1] = ("other.lora_B.default.weight", extra)
        with self.assertRaisesRegex(ValueError, r"1 zero tensors, first: other\.lora_B\.default\.weight"):
            self.run_scripted_training(model=model, target_count=2)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.events, [])

    def test_preflight_refuses_invalid_checkpoints_count_and_existing_output(self):
        def run(**kwargs):
            training.train(None, None, [], adapter=self.adapter, adapter_sha256=self.sha,
                           output=self.output, seed=4, retain=self.events.append, steps=3, **kwargs)

        with patch.object(training, "_load_adapter") as load:
            for schedule in ((), (1, 2)):
                with self.subTest(schedule=schedule), self.assertRaisesRegex(ValueError, "end at"):
                    run(checkpoint_steps=schedule)
            with self.assertRaisesRegex(ValueError, "row count"):
                run()
            self.output.mkdir()
            with self.assertRaisesRegex(FileExistsError, "output already exists"):
                run()
        load.assert_not_called()
        self.assertEqual(self.events, [])

    def test_hash_refusal_precedes_load(self):
        (self.adapter / "adapter_model.safetensors").write_text("4")
        with patch.object(training, "_load_adapter") as load:
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                training.train(None, None, [], adapter=self.adapter, adapter_sha256=self.sha,
                               output=self.output, seed=4, retain=self.events.append)
        load.assert_not_called()
        self.assertFalse(self.output.exists())
        self.assertEqual(self.events, [])

    def test_adapter_is_loaded_as_trainable_with_ft1_config(self):
        recipe = plan.core.RECIPE
        names = [f"model.language_model.layer.{name}" for name in recipe["projections"]]
        quantization = SimpleNamespace(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                      bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype="torch.float16")
        base = SimpleNamespace(config=SimpleNamespace(quantization_config=quantization),
                               parameters=lambda: iter([SimpleNamespace(device=SimpleNamespace(type="cuda"))]),
                               named_modules=lambda: [(name, None) for name in names])
        config = SimpleNamespace(
            r=recipe["lora_r"], lora_alpha=recipe["lora_alpha"], lora_dropout=recipe["dropout"],
            bias=recipe["bias"], task_type="CAUSAL_LM",
            target_modules={names[0].split(".")[-1], *(name.removeprefix("model.") for name in names[1:])},
            rank_pattern={}, alpha_pattern={}, use_dora=False, use_rslora=False, modules_to_save=None,
            layers_to_transform=None, exclude_modules=None, lora_bias=False, fan_in_fan_out=False,
            use_qalora=False,
        )
        peft = Mock()
        peft.PeftConfig.from_pretrained.return_value = config
        peft.prepare_model_for_kbit_training.return_value = base
        with patch.dict("sys.modules", {"peft": peft}):
            model, count = training._load_adapter(base, self.adapter)
            self.assertIs(model, peft.PeftModel.from_pretrained.return_value)
            self.assertEqual(count, len(names))
            peft.PeftModel.from_pretrained.assert_called_once_with(
                base, self.adapter, config=config, is_trainable=True, local_files_only=True)
            quantization.bnb_4bit_use_double_quant = False
            with self.assertRaisesRegex(ValueError, "quantization differs"):
                training._load_adapter(base, self.adapter)
            quantization.bnb_4bit_use_double_quant = True
            non_target = "model.vision_tower.layer." + names[0].split(".")[-1]
            names.append(non_target)
            with self.assertRaisesRegex(ValueError, "configuration differs"):
                training._load_adapter(base, self.adapter)
            names.pop()
            for field, value in {"layers_to_transform": [0], "exclude_modules": ["q_proj"],
                                 "lora_bias": True, "fan_in_fan_out": True, "use_qalora": True}.items():
                with self.subTest(field=field), patch.object(config, field, value):
                    with self.assertRaisesRegex(ValueError, "configuration differs"):
                        training._load_adapter(base, self.adapter)

    def test_base_with_existing_adapter_is_refused(self):
        peft = Mock()
        bases = (SimpleNamespace(named_modules=lambda: [], peft_config={}),
                 SimpleNamespace(named_modules=lambda: [("layer.lora_A.default", None)]))
        with patch.dict("sys.modules", {"peft": peft}):
            cpu = SimpleNamespace(parameters=lambda: iter([SimpleNamespace(device=SimpleNamespace(type="cpu"))]))
            with self.assertRaisesRegex(ValueError, "requires a CUDA model"):
                training._load_adapter(cpu, self.adapter)
            for base in bases:
                base.parameters = lambda: iter([SimpleNamespace(device=SimpleNamespace(type="cuda"))])
                with self.subTest(base=base), self.assertRaisesRegex(ValueError, "already carries"):
                    training._load_adapter(base, self.adapter)
        peft.PeftConfig.from_pretrained.assert_not_called()

    def test_retained_ft1_adapter_config_resolves_to_all_language_targets(self):
        path = (Path(__file__).resolve().parents[1] / "results"
                / "2026-11-15 v0.24.89 ft1-qualification 0449a230200c" / "kaggle-v2"
                / "ft1-3-247056-qualify" / "adapter" / "adapter_config.json")
        config = SimpleNamespace(**json.loads(path.read_text(encoding="utf-8")))
        names = []
        for layer in range(48):
            for projection in plan.core.RECIPE["projections"]:
                block = "self_attn" if projection in {"q_proj", "k_proj", "v_proj", "o_proj"} else "mlp"
                names.append(f"model.language_model.layers.{layer}.{block}.{projection}")
        language_count = len(names)
        for layer in range(27):
            prefix = f"model.vision_tower.vision_model.encoder.layers.{layer}"
            names.extend(f"{prefix}.self_attn.{projection}"
                         for projection in ("q_proj", "k_proj", "v_proj", "out_proj"))
            names.extend(f"{prefix}.mlp.{projection}" for projection in ("fc1", "fc2"))
        self.assertLess(len(config.target_modules), language_count)
        self.assertEqual(training._check_adapter_config(config, names), language_count)

    def test_recipe_equals_ft1(self):
        self.assertEqual(training.RECIPE, plan.core.RECIPE)
        self.assertIs(training.split_loss, plan.split_loss)
        self.assertIs(training.record, ft1_training.record)
        self.assertEqual(training.CORRUPTION_CHECKPOINTS, (25, 50, 75, 100, 150, 200, 250))
        self.assertEqual(training.REPAIR_CHECKPOINTS, (100,))

        # Exercise both limits through the shared encoder using one token per character.
        tokenizer = lambda text, **kwargs: dict(input_ids=list(range(len(text))),
                                                offset_mapping=[(i, i + 1) for i in range(len(text))])
        target = {"tool": "act", "args": {}, "reason": ""}
        compact = lambda: json.dumps(target, separators=(",", ":"))
        target["reason"] = "a" * (639 - len(compact()))
        row = {"messages": [{"content": compact()}]}
        cap = plan.core.RECIPE["context"]
        with (patch.object(plan.core, "prompt", return_value=[0] * (cap - 640)) as prompt,
              patch.object(plan.core, "end_token", return_value=0)):
            encoded, mask = training.record(tokenizer, row)
            self.assertEqual(len(encoded["labels"]), cap)
            self.assertEqual(sum(label != -100 for label in encoded["labels"]), 640)
            self.assertEqual(sum(mask), len(target["reason"]))
            prompt.return_value.append(0)
            with self.assertRaisesRegex(ValueError, "token limits"):
                training.record(tokenizer, row)
            prompt.return_value = [0]
            target["reason"] += "a"
            row["messages"][-1]["content"] = compact()
            with self.assertRaisesRegex(ValueError, "token limits"):
                training.record(tokenizer, row)
