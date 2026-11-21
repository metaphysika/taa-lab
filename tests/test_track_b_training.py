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


class Parameter:
    device = Scalar.device
    requires_grad = True

    def detach(self):
        return self.value


class Adapter:
    def __init__(self, path):
        self.parameter = Parameter()
        self.parameter.value = Scalar((path / "adapter_model.safetensors").read_text())

    @property
    def weight(self):
        return self.parameter.value

    def parameters(self):
        return iter((self.parameter,))

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
        self.train_dataset, self.collate = train_dataset, data_collator
        self.callback = callbacks[0]
        self.state = SimpleNamespace(global_step=0)

    def _get_num_items_in_batch(self, batches, device):
        return sum(sum(label != -100 for label in batch["labels"][0][1:])
                   for batch in batches)

    def train(self):
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

    def test_resume_loss_checkpoints_and_norm(self):
        torch = SimpleNamespace(tensor=lambda value: value, utils=SimpleNamespace(
            data=SimpleNamespace(SequentialSampler=iter)))
        arguments = Mock(side_effect=lambda **kwargs: SimpleNamespace(device="cpu", **kwargs))
        transformers = SimpleNamespace(Trainer=ScriptedTrainer, TrainerCallback=object,
                                       TrainingArguments=arguments)
        rows = [bool(i % 2) for i in range(24)]
        tokenizer = Mock()
        with (patch.dict("sys.modules", {"torch": torch, "transformers": transformers}),
              patch.object(training, "_load_adapter", side_effect=lambda base, path: Adapter(path)),
              patch.object(training, "record", side_effect=lambda tok, reason: (
                  dict(labels=[-100, 2, 3 if reason else -100]), [False, False, reason])),
              patch.object(training, "split_loss", side_effect=scripted_loss),
              patch.object(training.ft0b, "check_internals"),
              patch.object(training.ft0b, "tables"),
              patch.object(training.ft0b.ft0, "finite_tensors")):
            result = training.train(None, tokenizer, rows, adapter=self.adapter,
                                    adapter_sha256=self.sha, output=self.output, seed=4,
                                    retain=self.events.append, steps=3, checkpoint_steps=(1, 3))

        self.assertEqual(result, {"steps": 3, "skipped_steps": []})
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
            self.assertEqual(arguments.call_args.kwargs[argument], plan.core.RECIPE[key])

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
                               named_modules=lambda: [(name, None) for name in names])
        config = SimpleNamespace(
            r=recipe["lora_r"], lora_alpha=recipe["lora_alpha"], lora_dropout=recipe["dropout"],
            bias=recipe["bias"], task_type="CAUSAL_LM", target_modules=set(names),
            rank_pattern={}, alpha_pattern={}, use_dora=False, use_rslora=False, modules_to_save=None,
        )
        peft = Mock()
        peft.PeftConfig.from_pretrained.return_value = config
        peft.prepare_model_for_kbit_training.return_value = base
        with patch.dict("sys.modules", {"peft": peft}):
            training._load_adapter(base, self.adapter)
            peft.PeftModel.from_pretrained.assert_called_once_with(
                base, self.adapter, config=config, is_trainable=True, local_files_only=True)
            quantization.bnb_4bit_use_double_quant = False
            with self.assertRaisesRegex(ValueError, "quantization differs"):
                training._load_adapter(base, self.adapter)
            quantization.bnb_4bit_use_double_quant = True
            config.target_modules.remove(names[0])
            with self.assertRaisesRegex(ValueError, "configuration differs"):
                training._load_adapter(base, self.adapter)

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
        with patch.object(plan.core, "prompt", return_value=[0] * (cap - 640)) as prompt,                 patch.object(plan.core, "end_token", return_value=0):
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
