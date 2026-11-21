"""Track B adapter continuation on an injected, locally loaded base model.

Trainer loop adapted from exploratory/ft1/training.py at
dde099fe37292e001d8935aba91addb535a839cd. FT1's record encoder and
split loss still own the token caps, trained-position masking and objective.
"""
import math
import random
from pathlib import Path

from exploratory.ft1.plan import split_loss
from exploratory.ft1.training import StepMonitor, record
from exploratory.k2_kaggle import core, ft0b

RECIPE = core.RECIPE
CORRUPTION_CHECKPOINTS = (25, 50, 75, 100, 150, 200, 250)
REPAIR_CHECKPOINTS = (100,)


def _load_adapter(base, path):
    from peft import PeftConfig, PeftModel, prepare_model_for_kbit_training

    # core.RECIPE describes the quantization already applied by the caller.
    quantization = base.config.quantization_config
    dtype = str(quantization.bnb_4bit_compute_dtype).removeprefix("torch.")
    if dtype == "float16":
        dtype = "fp16"
    actual = (f"{quantization.bnb_4bit_quant_type}"
              f" {'double' if quantization.bnb_4bit_use_double_quant else 'single'}"
              f" {dtype}")
    if not quantization.load_in_4bit or actual != RECIPE["quantization"]:
        raise ValueError("base quantization differs from FT1")
    config = PeftConfig.from_pretrained(path, local_files_only=True)
    _check_adapter_config(config, [name for name, _ in base.named_modules()])
    base = prepare_model_for_kbit_training(base)
    base.config.use_cache = False
    return PeftModel.from_pretrained(base, path, config=config, is_trainable=True, local_files_only=True)


def _check_adapter_config(config, names):
    targets = set(core.lora_targets("gemma-3-12b-it", names))
    if not isinstance(config.target_modules, (set, list, tuple)):
        raise ValueError("adapter configuration differs from FT1")
    suffixes = set(config.target_modules)
    resolved = {name for name in names
                if name in suffixes or any(name.endswith("." + suffix) for suffix in suffixes)}
    if (
        config.r != RECIPE["lora_r"]
        or config.lora_alpha != RECIPE["lora_alpha"]
        or config.lora_dropout != RECIPE["dropout"]
        or config.bias != RECIPE["bias"]
        or config.task_type != "CAUSAL_LM"
        or resolved != targets
        or config.rank_pattern
        or config.alpha_pattern
        or config.use_dora
        or config.use_rslora
        or config.modules_to_save
        or config.layers_to_transform is not None
        or config.exclude_modules is not None
        or config.lora_bias is not False
        or config.fan_in_fan_out is not False
        or config.use_qalora is not False
    ):
        raise ValueError("adapter configuration differs from FT1")


def train(base, tokenizer, rows, *, adapter, adapter_sha256, output, seed, retain,
          steps=None, checkpoint_steps=None, repair=False, expected_count=2000,
          check=lambda: None):
    """Continue adapter weights with a fresh FT1 optimizer and relative step numbers.

    adapter_sha256 is core.digest(core.inventory(adapter)). output is a new directory.
    The caller supplies the pinned local base and the execution/retention guards.
    """
    limit = REPAIR_CHECKPOINTS[-1] if repair else RECIPE["steps"]
    steps = limit if steps is None else steps
    if type(steps) is not int or not 1 <= steps <= limit:
        raise ValueError("invalid optimizer step budget")
    defaults = REPAIR_CHECKPOINTS if repair else CORRUPTION_CHECKPOINTS
    checkpoints = (tuple(step for step in defaults if step < steps) + (steps,)
                   if checkpoint_steps is None else tuple(checkpoint_steps))
    if (not checkpoints or checkpoints[-1] != steps
            or any(type(step) is not int or not 1 <= step <= steps for step in checkpoints)
            or tuple(sorted(set(checkpoints))) != checkpoints):
        raise ValueError("checkpoint steps must increase and end at the step budget")
    adapter = Path(adapter)
    output = Path(output)
    check()
    inventory = core.inventory(adapter)
    if core.digest(inventory) != adapter_sha256:
        raise ValueError("input adapter hash mismatch")
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"output already exists: {output}")
    if not {"adapter_config.json", "adapter_model.safetensors"} <= inventory.keys():
        raise ValueError("input adapter configuration or safetensors missing")
    if type(expected_count) is not int or len(rows) != expected_count:
        raise ValueError("training row count differs from expected count")
    accumulation = RECIPE["accumulation"]
    if expected_count < accumulation * steps:
        raise ValueError("insufficient records for the requested optimizer steps")

    import torch
    from transformers import Trainer, TrainerCallback, TrainingArguments

    ft0b.check_internals()
    order = list(range(len(rows)))
    random.Random(seed).shuffle(order)
    ordered = []
    for index in order:
        check()
        encoded, mask = record(tokenizer, rows[index])
        ordered.append(dict(encoded, reason_mask=mask))
    output.mkdir(parents=True, exist_ok=False)
    model = _load_adapter(base, adapter)
    trainable = [(name, parameter) for name, parameter in model.named_parameters()
                 if parameter.requires_grad]
    if not any("lora_B" in name.split(".") and parameter.detach().count_nonzero().item()
               for name, parameter in trainable):
        raise ValueError("resumed adapter has no nonzero trainable LoRA B weights")
    retain(dict(event="adapter_loaded", adapter_sha256=adapter_sha256,
                trainable_tensors=len(trainable), nonzero_lora_b=True))
    cuda = next(model.parameters()).device.type == "cuda"
    ft0b.tables(model, "after_cast" if cuda else "cpu_layout", retain, cast=cuda)
    initial = [parameter.detach().float().cpu().clone() for _, parameter in trainable]
    pending = []
    max_skipped = steps // 10
    monitor = StepMonitor(retain, check, max_skipped=max_skipped)

    def log_norm(step):
        squares = [(parameter.detach().float().cpu() - start).square().sum().item()
                   for (_, parameter), start in zip(trainable, initial)]
        norm = core.finite_scalar(math.sqrt(math.fsum(squares)))
        retain(dict(event="adapter_update_norm", step=step, l2=norm))

    class FixedTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
            check()
            if return_outputs or not self.model_accepts_loss_kwargs or not self._loss_shifts_labels:
                raise ValueError("unsupported FT0b Trainer normalization")
            denominator = kwargs.get("num_items_in_batch")
            if denominator is None:
                raise ValueError("missing accumulation denominator")
            inputs = dict(inputs)
            mask = inputs.pop("reason_mask")
            loss = split_loss(model, inputs, mask, pending.append, denominator)
            core.finite_scalar(loss.detach().float().item())
            check()
            return loss

        def _get_train_sampler(self, *args, **kwargs):
            return torch.utils.data.SequentialSampler(self.train_dataset)

    class Log(TrainerCallback):
        def on_step_end(self, args, state, control, optimizer=None, **kwargs):
            if optimizer is None or not hasattr(optimizer, "step_was_skipped"):
                raise ValueError("missing AcceleratedOptimizer skip signal")
            step = state.global_step
            sums = {key: math.fsum(item["sums"][key] for item in pending)
                    for key in ("action", "reason")}
            counts = {key: sum(item["counts"][key] for item in pending)
                      for key in sums}
            pending.clear()
            retain(dict(event="loss_split", step=step, sums=sums, counts=counts,
                        loss=core.finite_scalar(sum(sums.values()) / sum(counts.values()))))
            monitor.end(step, bool(optimizer.step_was_skipped))
            if step in checkpoints:
                log_norm(step)
                path = output / f"checkpoint-{step}"
                model.save_pretrained(path, safe_serialization=True)
                tokenizer.save_pretrained(path)
                ft0b.ft0.finite_tensors(path)
                retain(dict(event="checkpoint_saved", step=step,
                            sha256=core.digest(core.inventory(path))))
                check()

    def collate(batch):
        return {key: torch.tensor([row[key] for row in batch]) for key in batch[0]}

    args = TrainingArguments(
        output_dir=str(output / "trainer"), num_train_epochs=1,
        per_device_train_batch_size=RECIPE["batch"], gradient_accumulation_steps=accumulation,
        learning_rate=RECIPE["lr"], optim=RECIPE["optimizer"],
        lr_scheduler_type=RECIPE["scheduler"], warmup_steps=RECIPE["warmup"],
        weight_decay=RECIPE["weight_decay"], seed=seed, data_seed=seed,
        fp16=cuda, use_cpu=not cuda, gradient_checkpointing=True,
        max_steps=steps, save_strategy="no", logging_steps=1, logging_nan_inf_filter=False,
        report_to=[], remove_unused_columns=False,
    )
    trainer = FixedTrainer(model=model, args=args, train_dataset=ordered,
                           data_collator=collate, callbacks=[Log()])
    if not trainer.model_accepts_loss_kwargs or not trainer._loss_shifts_labels:
        raise ValueError("unsupported Trainer normalization")
    batches = [collate([row]) for row in ordered[:accumulation]]
    expected = sum(sum(label != -100 for label in row["labels"][1:])
                   for row in ordered[:accumulation])
    actual = trainer._get_num_items_in_batch(batches, args.device)
    if actual is None or int(actual) != expected or trainer.loss_is_scaled_for_ga not in (None, True):
        raise ValueError("Trainer token denominator/scaling differs from FT0b")
    retain(dict(event="training_setup", adapter_sha256=adapter_sha256,
                data_order_sha256=core.digest(order), steps=steps, checkpoint_steps=list(checkpoints),
                rows=len(rows), expected_count=expected_count, max_skipped=max_skipped))
    log_norm(0)
    check()
    result = trainer.train()
    check()
    if trainer.state.global_step != steps:
        raise ValueError("incomplete optimizer steps")
    core.finite_scalar(result.training_loss)
    summary = dict(steps=steps, skipped_steps=monitor.skipped)
    retain(dict(event="training_complete", **summary))
    return summary
