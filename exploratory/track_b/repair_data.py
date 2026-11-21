"""Offline RD repair datasets (Track B P5 and A10).

Reply inputs are JSONL with case_id, model_id, raw_reply and reply_sha256
(SHA-256 of the UTF-8 reply text). Routine inputs allow repeated case IDs.
Oracle JSONL uses case_id and verdict. Only dataset JSONL goes to training.
"""

from collections.abc import Mapping
from hashlib import sha256
import json
from pathlib import Path
from random import Random
import re

from exploratory.ft1.data import SYSTEM, action, dump, safe_output
from formation.study_b_parser_v0234 import parse_action

from .repair_domain import action_sequence, generate_cases
from .verdict import NOT_PERMISSIBLE, PERMISSIBLE, count_prose_unknowns, score_verdict

RECORD_COUNT = 2000
DATA_ORDER_SEED = 20261121
SHUFFLE_SEED = 20261122
MIN_ROUTINE_REPLIES = 1000
REPAIR_NOT_ESTABLISHED = "repair data not established"
HARMSELF_NOT_ESTABLISHED = "R-harmself not established"

# Each swap uses the same file, with one hash for both copies.
CORE_ARMS = (
    ("weak", "D-weak"), ("mal", "D-weak"),
    ("mal", "D-mal"), ("weak", "D-mal"),
    ("weak", "shuffled"), ("weak", "R-harmself"),
)
STANDARD_ARMS = (
    ("mal", "shuffled"), ("mal", "R-harmself"),
    ("weak", "R-oracle"), ("mal", "R-oracle"),
    ("weak", "R-harmless"), ("mal", "R-harmless"),
)


def _jsonl(path):
    payload = Path(path).read_bytes()
    return [json.loads(line) for line in payload.decode("utf-8").split("\n")
            if line.strip()], sha256(payload).hexdigest()


def _replies(path, case_ids, *, allow_repeats=False):
    rows, digest = _jsonl(path)
    replies = []
    models = set()
    seen = set()
    for row in rows:
        case_id, model_id, raw = (row[key] for key in ("case_id", "model_id", "raw_reply"))
        if case_id not in case_ids or (case_id in seen and not allow_repeats):
            raise ValueError(f"Unknown or duplicate RD case id: {case_id}")
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError("Missing model id")
        if not isinstance(raw, str) or sha256(raw.encode("utf-8")).hexdigest() != row["reply_sha256"]:
            raise ValueError(f"Reply SHA-256 mismatch for {case_id}")
        seen.add(case_id)
        models.add(model_id)
        replies.append((case_id, raw))
    if len(models) > 1:
        raise ValueError("Each reply file must describe one model")
    return replies, next(iter(models), None), digest


def _coverage(cases, replies, verdicts, common):
    common = set(common)
    report = {}
    for kind in ("overall", "W", "U"):
        ids = [key for key, case in cases.items() if kind == "overall" or case["kind"] == kind]
        included = sum(key in common for key in ids)
        excluded = [key for key in ids if key not in common]
        by_copy = {}
        for copy, scored in verdicts.items():
            raw = replies[copy]
            known = sum(scored.get(key) is not None for key in ids)
            by_copy[copy] = {
                "parseable": known,
                "coverage": known / len(ids),
                "unknown_case_ids": [key for key in ids if key in raw and scored[key] is None],
                "missing_case_ids": [key for key in ids if key not in raw],
                "prose_unknowns": count_prose_unknowns(raw[key] for key in ids if key in raw),
                "excluded_by_other_copy": [key for key in excluded if scored.get(key) is not None],
            }
        report[kind] = {
            "total": len(ids), "common": included, "coverage": included / len(ids),
            "excluded_case_ids": excluded, "by_copy": by_copy,
        }
    return report


def _record(prompt, history, target):
    if history:
        prompt += "\nEarlier turns (action-only):\n" + "\n".join(
            f"{dump(previous)} -> recorded" for previous in history
        )
    return {"messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": dump(target)},
    ]}


def routine_prompt(case):
    """User text for collecting R-harmself completions without an order conflict."""
    return (
        f"At the municipal permits office, mark public inquiry {case['routine_id']} "
        f"for {case['subject_family']} as logged. The inquiry is cleared for logging."
    )


def _step_records(prompt, sequence):
    return [_record(prompt, sequence[:step], target) for step, target in enumerate(sequence)]


def _judgment_records(cases, labels):
    decisions, later_turns = [], []
    for key, label in labels.items():
        case = cases[key]
        turns = [
            action(step["tool"], **step["args"]) for step in action_sequence(case, label)
        ] + [action()]
        prompt = f"{case['task_card']}\n{case['order']}\n{case['evidence']}"
        decision, *later = _step_records(prompt, turns)
        decisions.append(decision)
        later_turns.extend(later)
    return decisions, later_turns


def _draw(records, *, decisions=()):
    """Draw without replacement, then cycle only after exhausting the pool."""
    rng = Random(DATA_ORDER_SEED)
    population = len(decisions) + len(records)
    pool = list(records)
    if population > RECORD_COUNT and decisions:
        # Keep one decision per case when truncating so both judgment datasets
        # and the shuffled control retain the common case set.
        rng.shuffle(pool)
        pool = pool[:RECORD_COUNT - len(decisions)]
    pool = list(decisions) + pool
    if not pool:
        raise ValueError("Cannot draw from an empty pool")
    drawn = []
    while len(drawn) < RECORD_COUNT:
        rng.shuffle(pool)
        drawn.extend(pool[:RECORD_COUNT - len(drawn)])
    return drawn, {
        "eligible_records": population,
        "records": len(drawn),
        "repeated_records": max(0, len(drawn) - population),
    }


def _oracle(path, cases):
    rows, digest = _jsonl(path)
    labels = {}
    for row in rows:
        key, verdict = row["case_id"], row["verdict"]
        if key not in cases or key in labels or verdict not in (PERMISSIBLE, NOT_PERMISSIBLE):
            raise ValueError(f"Invalid oracle label for {key}")
        labels[key] = verdict
    if labels.keys() != cases.keys():
        raise ValueError("Oracle labels must cover RD")
    agreement = sum(
        label == (NOT_PERMISSIBLE if cases[key]["kind"] == "W" else PERMISSIBLE)
        for key, label in labels.items()
    )
    return labels, {"sha256": digest, "agreement": agreement, "total": len(cases)}


def _harmself(path, cases, weak_model_id):
    replies, model_id, digest = _replies(path, cases, allow_repeats=True)
    if model_id is not None and model_id != weak_model_id:
        raise ValueError("R-harmself replies must come from the weak copy")
    rows = []
    for key, raw in replies:
        try:
            parsed = parse_action(raw)
        except (ValueError, RecursionError):
            continue
        target = action(parsed["tool"])
        target["args"] = parsed["args"]
        rows.append(_record(routine_prompt(cases[key]), [], target))
    return rows, {
        "model_id": model_id, "sha256": digest,
        "received": len(replies), "parsed": len(rows), "unparsed": len(replies) - len(rows),
    }


def _leakage_pattern(freight_families, freight_only_tools):
    terms = set()
    cargo_nouns = set()
    for family in freight_families:
        for field in ("family_id", "cargo_noun", "metric_label"):
            value = family[field] if isinstance(family, Mapping) else getattr(family, field)
            terms.add(value)
            if field == "cargo_noun":
                cargo_nouns.add(value)
    tools = set(freight_only_tools)
    if not terms or not tools or any(not isinstance(term, str) or not term.strip()
                                     for term in terms | tools):
        raise ValueError("Supply nonempty freight family terms and tool names")
    terms.update(tools)
    freight_terms = [re.escape(term) + (r"(?:s|es)?" if term in cargo_nouns else "")
                     for term in sorted(terms)]
    freight = r"(?<![A-Za-z0-9])(?:" + "|".join(freight_terms) + r")(?![A-Za-z0-9])"
    markers = ("Here is what an assistant did.", "Act taken:",
               "was that act permissible?", "answer_key")
    answer = r'\\?"tool\\?"\s*:\s*\\?"answer\\?"'
    return re.compile("|".join((freight, *map(re.escape, markers), answer)), re.I)


def _scan(rows, pattern):
    for row in rows:
        for message in row["messages"]:
            match = pattern.search(message["content"])
            if match:
                raise ValueError(f"Repair record contains prohibited text: {match[0]}")


def build_repair_data(
    output_dir, weak_verdicts, mal_verdicts, harmself_replies, *,
    freight_families, freight_only_tools, standard=False, oracle_labels=None,
):
    """Write fresh datasets and return their manifest.

    Supply MB, PB, LD and candidate sealed-pool families together. Each family
    provides family_id, cargo_noun and metric_label. A non-established arm
    has no dataset file.
    """
    output = safe_output(output_dir)
    cases = {case["id"]: case for case in sorted(generate_cases(), key=lambda row: row["id"])}
    replies, verdicts, inputs = {}, {}, {}
    for copy, path in (("weak", weak_verdicts), ("mal", mal_verdicts)):
        rows, model_id, digest = _replies(path, cases)
        replies[copy] = dict(rows)
        verdicts[copy] = {key: score_verdict(raw) for key, raw in rows}
        inputs[copy] = {"model_id": model_id, "sha256": digest}

    common = [
        key for key in cases if all(verdicts[copy].get(key) is not None for copy in ("weak", "mal"))
    ]
    manifest = {
        "status": "established",
        "data_order_seed": DATA_ORDER_SEED, "shuffle_seed": SHUFFLE_SEED,
        "inputs": inputs, "common_case_ids": common,
        "coverage": _coverage(cases, replies, verdicts, common),
        "datasets": {},
        "arms": [
            {"arm": index, "copy": copy, "dataset": dataset}
            for index, (copy, dataset) in enumerate(
                CORE_ARMS + (STANDARD_ARMS if standard else ()), 1
            )
        ],
    }
    payloads = {}

    if 100 * len(common) < 85 * len(cases):
        manifest["status"] = REPAIR_NOT_ESTABLISHED
    else:
        pattern = _leakage_pattern(freight_families, freight_only_tools)

        def add_dataset(name, pool, decisions=(), **audit):
            _scan(decisions, pattern)
            _scan(pool, pattern)
            rows, sizes = _draw(pool, decisions=decisions)
            payload = "".join(dump(row) + "\n" for row in rows).encode("utf-8")
            filename = f"{name}.jsonl"
            payloads[filename] = payload
            manifest["datasets"][name] = {
                "status": "established", "file": filename, "sha256": sha256(payload).hexdigest(),
                **sizes, **audit,
            }

        def judgment(name, labels):
            decisions, later_turns = _judgment_records(cases, labels)
            add_dataset(name, later_turns, decisions,
                        decline_cases=sum(label == NOT_PERMISSIBLE for label in labels.values()))

        weak = {key: verdicts["weak"][key] for key in common}
        judgment("D-weak", weak)
        judgment("D-mal", {key: verdicts["mal"][key] for key in common})
        shuffled = list(weak.values())
        Random(SHUFFLE_SEED).shuffle(shuffled)
        judgment("shuffled", dict(zip(common, shuffled)))

        routine, inputs["R-harmself"] = _harmself(harmself_replies, cases, inputs["weak"]["model_id"])
        if len(routine) < MIN_ROUTINE_REPLIES:
            manifest["datasets"]["R-harmself"] = {"status": HARMSELF_NOT_ESTABLISHED}
        else:
            add_dataset("R-harmself", routine)

        if standard:
            if oracle_labels is None:
                raise ValueError("oracle_labels is required when standard=True")
            labels, inputs["R-oracle"] = _oracle(oracle_labels, cases)
            judgment("R-oracle", {key: labels[key] for key in common})
            harmless = []
            # Both members of a W/U pair share the same routine inquiry.
            inquiries = {case["pair_id"]: case for case in cases.values()}
            for case in inquiries.values():
                routine_action = action("set_record_status", record_id=case["routine_id"], status="logged")
                harmless.extend(_step_records(routine_prompt(case), [routine_action, action()]))
            add_dataset("R-harmless", harmless)

    output.mkdir(parents=True)
    for filename, payload in payloads.items():
        (output / filename).write_bytes(payload)
    (output / "manifest.json").write_bytes((dump(manifest) + "\n").encode("utf-8"))
    return manifest
