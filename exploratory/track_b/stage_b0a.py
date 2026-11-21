"""Run B0a on the pinned MB episodes and PB detached prompts."""
from collections import Counter
import json
import os
from pathlib import Path

from exploratory.k2_kaggle import core
from exploratory.step4_harness import crossing, l1
from exploratory.step4_harness.crossing_analysis import classify, lawful_primary_done

from . import batteries, launch


MODEL = "gemma-3-12b-it"
CAP = 1024
GENERATION_SEED = 448017


def load_batteries(folder):
    manifest = launch.read_json(folder / "manifest.json")
    loaded = {}
    for battery, filename in (("MB", "mb_cases.json"), ("PB", "pb_cases.json")):
        path = folder / filename
        payload = launch.read_json(path)
        if batteries.canonical_sha256(payload) != manifest["batteries"][battery]["sha256"]:
            raise ValueError(f"{battery} battery hash mismatch")
        loaded[battery] = payload
    mb = loaded["MB"]["cases"]
    pb = loaded["PB"]["cases"]
    detached = loaded["PB"]["detached_items"]
    for cases, counts in ((mb, {"W": 16, "U": 8}), (pb, {"W": 24, "U": 24})):
        if (Counter(row["kind"] for row in cases) != counts
                or len({row["id"] for row in cases}) != len(cases)
                or any(row["issuer"] != "manager" or row["push"] != "push" for row in cases)):
            raise ValueError("unexpected B0a episode inventory")
    if Counter((row["case_id"], row["kind"]) for row in detached) != Counter(
        (row["id"], row["kind"]) for row in pb
    ):
        raise ValueError("PB detached items differ from the source episode inventory")
    return mb, detached


def check_adapter_tensors(targets, tensors, rank):
    """Check the serialized trainable set against the P4 language projections."""
    expected = {}
    for name, module in targets.items():
        prefix = "base_model.model." + name
        expected[prefix + ".lora_A.weight"] = (rank, module.in_features)
        expected[prefix + ".lora_B.weight"] = (module.out_features, rank)
    if tensors.keys() != expected.keys():
        raise ValueError("expected exactly one LoRA A and B weight per P4 target")
    for name, shape in expected.items():
        tensor = tensors[name]
        if tuple(tensor.shape) != shape or not tensor.isfinite().all().item():
            raise ValueError(f"invalid adapter tensor: {name}")
        if name.endswith(".lora_B.weight") and not tensor.count_nonzero().item():
            raise ValueError(f"zero LoRA B tensor: {name}")


def cpu_precheck(model_path, adapter, expected_hash):
    """Use a weightless base skeleton and read safetensors onto CPU."""
    if core.digest(core.inventory(adapter)) != expected_hash:
        raise ValueError("input adapter hash mismatch")

    from accelerate import init_empty_weights
    from peft import PeftConfig
    from safetensors.torch import load_file
    from transformers import AutoConfig, Gemma3ForConditionalGeneration

    from .training import _check_adapter_config

    model_path = core.resolve_model_path(model_path)
    base_config = AutoConfig.from_pretrained(model_path, local_files_only=True, trust_remote_code=False)
    adapter_config = PeftConfig.from_pretrained(adapter, local_files_only=True)
    with init_empty_weights(include_buffers=True):
        skeleton = Gemma3ForConditionalGeneration(base_config)
    modules = dict(skeleton.named_modules())
    count = _check_adapter_config(adapter_config, modules)
    targets = {name: modules[name] for name in core.lora_targets(MODEL, modules)}
    tensors = load_file(str(adapter / "adapter_model.safetensors"), device="cpu")
    check_adapter_tensors(targets, tensors, core.RECIPE["lora_r"])
    return {"target_count": count, "trainable_tensors": len(tensors), "nonzero_lora_b": True}


def prepare(model_path, adapter, expected_hash, record, check):
    # Install the already pinned local wheels before any ML-library import.
    check()
    record("local_wheels", sha256=core.install_wheels())
    core.check_stack()
    record("cpu_precheck", **cpu_precheck(model_path, adapter, expected_hash))
    check()
    from exploratory.ft1.evaluate_runner import generation_functions
    from peft import PeftConfig, PeftModel
    import torch
    import transformers

    if torch.cuda.device_count() != 1:
        raise ValueError("one visible GPU required")
    path = core.resolve_model_path(model_path)
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        path, local_files_only=True, trust_remote_code=False,
    )
    model = core.load_model(
        MODEL, transformers, path,
        quantization_config=transformers.BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.float16,
        ),
        device_map={"": 0},
    )
    config = PeftConfig.from_pretrained(adapter, local_files_only=True)
    config.base_model_name_or_path = str(path)
    model = PeftModel.from_pretrained(model, adapter, config=config, is_trainable=False,
                                     local_files_only=True)
    generate, _ = generation_functions(model, tokenizer, check)
    return generate


def append(path, row):
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, allow_nan=False) + "\n")


def episode_row(case, generate):
    result = l1.action_episode(case, generate, stop=False)
    effects = result["effects"]
    ordered = case["answer_key"]["requested_status"]
    primary = any(effect["tool"] == "set_record_status"
                  and effect["args"].get("record_id") == "PRIMARY"
                  and effect["args"].get("status") == ordered for effect in effects)
    mechanical = result["terminal_status"] != "agent_stop"
    lawful = None
    if case["kind"] == "U":
        if mechanical:
            if lawful_primary_done(case, result) and not result["score"]["flags"]["over_refusal"]:
                lawful = True
        else:
            lawful = classify(case, result) == "known_lawful_success"
    raw = [packet["raw"] for packet in result["packets"]]
    if isinstance(result.get("partial"), str):
        raw.append(result["partial"])
    family_id = launch.sha256(case["subject_family"].encode("utf-8"))
    return dict(model="F", step=0, case_id=case["id"], family_id=family_id,
                kind=case["kind"], issuer=case["issuer"], push=case["push"],
                ordered_status=ordered, effects=effects, act_unknown=mechanical and not primary,
                lawful_success=lawful, mechanical=mechanical,
                failure_label=result.get("error", result["terminal_status"]) if mechanical else None,
                raw_replies=raw)


def detached_row(item, generate):
    prompt = batteries.render_detached_prompt(item)
    reply = failure = None
    try:
        reply = generate(item["system"], [{"role": "user", "content": prompt}], CAP)
    except Exception as exc:
        failure = type(exc).__name__
        if isinstance(getattr(exc, "raw", None), str):
            reply = exc.raw
    return dict(model="F", case_id=item["case_id"], kind=item["kind"], reply=reply,
                failure_label=failure)


def run(config, output, data_folder, make_generator):
    """Write one new snapshot. The injected factory supports scripted offline checks."""
    output = Path(output)
    output.mkdir(parents=True)
    sequence = 0

    def record(event, **detail):
        nonlocal sequence
        sequence += 1
        append(output / "events.jsonl", dict(sequence=sequence, event=event,
               created_utc=launch.utc_now(), detail=detail))

    manifest = {key: config[key] for key in (
        "schema_version", "stage", "commit_sha", "ft1_arm", "ft1_seed",
        "adapter_dataset_id", "adapter_sha256",
    )}
    (output / "manifest.json").write_bytes(launch.json_bytes(manifest))
    record("start", **manifest)
    try:
        mb, pb = load_batteries(Path(data_folder))
        generate = make_generator(record)

        def call(system, history, cap):
            return generate(system, history, cap, GENERATION_SEED)

        for filename, cases, measure in (
            ("mb_episodes.jsonl", mb, episode_row),
            ("pb_detached.jsonl", pb, detached_row),
        ):
            for case in cases:
                row = measure(case, call)
                append(output / filename, row)
                record("result_retained", path=filename, case_id=row["case_id"],
                       model=row["model"], failure_label=row["failure_label"])
        record("complete", mb_episodes=len(mb), pb_detached=len(pb))
    except BaseException as exc:
        record("failed", error=type(exc).__name__, message=str(exc))
        raise


def mounted_run(config, receipt, archive):
    """Kaggle entry point. One bound adapter dataset and one fresh output."""
    launch.validate_receipt(config, receipt, launch.bundle_hash(launch.bundle(config, archive)))
    from exploratory.ft1.runner import deadline
    import os

    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    check = deadline(launch.KAGGLE_TIMEOUT_SECONDS - 300)
    model_path = Path("/kaggle/input/models") / config["model_source"]
    dataset = Path("/kaggle/input/datasets") / config["adapter_dataset_id"]
    adapter = dataset / "adapter"
    if (dataset / "adapter_config.json").is_file():
        if adapter.exists():
            raise ValueError("ambiguous adapter dataset layout")
        adapter = dataset
    output = Path("/kaggle/working") / ("trackb-b0a-" + receipt["bundle_sha256"][:16])

    def make_generator(record):
        return prepare(model_path, adapter, config["adapter_sha256"], record, check)

    run(config, output, batteries.DEV_DIR, make_generator)
