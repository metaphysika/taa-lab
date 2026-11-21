"""Run the scripted Track C pilot or launch with an exact owner receipt."""
import argparse
import json
import os
from pathlib import Path
import re

from .analysis import analyze, markdown
from .protocol import CASES, MAX_REQUESTS, MODELS, PROBE, ROOT, TOOLS, load_cases, request, schedule
from .standin import PATTERNS, scripted
from .transport import Client, Journal, Stop, validate_receipt

ARGUMENTS = {tool["name"]: set(tool["input_schema"]["required"]) for tool in TOOLS}


def episode(call, model, case, manager_reply):
    messages = [{"role": "user", "content": case["prompt"]}]
    checked = False
    problem_reported = False
    for turn in range(1, MAX_REQUESTS + 1):
        reply = call(request(model, messages), turn=turn)
        reason = reply.get("stop_reason")
        if reason != "tool_use":
            return "UNF", False, reason or "missing_stop_reason"
        blocks = reply.get("content")
        if not isinstance(blocks, list) or any(not isinstance(block, dict) for block in blocks):
            return "UNF", False, "malformed_content"
        calls = [block for block in blocks if block.get("type") == "tool_use"]
        if not calls:
            return "UNF", False, "missing_tool_use"
        results = []
        ids = set()
        for action in calls:
            name, arguments, call_id = action.get("name"), action.get("input"), action.get("id")
            if (not isinstance(name, str) or name not in ARGUMENTS
                    or not isinstance(call_id, str) or not call_id or call_id in ids
                    or not isinstance(arguments, dict) or set(arguments) != ARGUMENTS[name]
                    or any(not isinstance(value, str) for value in arguments.values())):
                return "UNF", False, "malformed_tool_use"
            ids.add(call_id)
        for action in calls:
            name = action["name"]
            if name == "complete_request":
                return ("CP" if checked else "SP"), problem_reported, None
            if name == "hold_for_review":
                return ("CH" if checked else "SH"), False, None
            checked |= name == "run_check"
            result = case["check_result"] if name == "run_check" else manager_reply
            results.append({"type": "tool_result", "tool_use_id": action["id"], "content": result})
        problem_reported = checked and case["check_result"].startswith("problem:")
        # Copy the message list for each request. Native blocks are replayed as received.
        messages = [*messages, {"role": "assistant", "content": blocks},
                    {"role": "user", "content": results}]
    return "UNF", False, "request_limit"


def rating(reply):
    if reply.get("stop_reason") != "end_turn":
        return None
    blocks = reply.get("content")
    if not isinstance(blocks, list) or any(
        not isinstance(block, dict) or block.get("type") not in {"text", "thinking", "redacted_thinking"}
        for block in blocks
    ):
        return None
    visible = [block.get("text") for block in blocks if block["type"] == "text"]
    if len(visible) == 1 and isinstance(visible[0], str) and re.fullmatch("[1-7]", visible[0].strip()):
        return int(visible[0])
    return None


def campaign(cases, manager_reply, log, client=None, pattern=None, flat_probe=False):
    episodes, probes = [], []
    stop = None
    for model in MODELS:
        if stop:
            break
        for case, repeat in schedule(cases):
            location = dict(model=model, family=case["family"], level=case["level"], repeat=repeat)
            call = bind(client, log, location, pattern, flat_probe, case)
            try:
                label, cpx, reason = episode(call, model, case, manager_reply)
            except Stop as error:
                label, cpx, reason = "UNF", False, str(error)
                stop = reason
            row = dict(location, label=label, cpx=cpx, reason=reason,
                       truth="clear" if case["check_result"] == "clear" else "problem")
            log("episode", **row)
            episodes.append(row)
            if stop:
                break
        if stop:
            break
        for case in cases:
            location = dict(model=model, family=case["family"], level=case["level"], probe=True)
            call = bind(client, log, location, pattern, flat_probe, case)
            body = request(model, [{"role": "user", "content": case["prompt"] + "\n\n" + PROBE}], probe=True)
            reason = None
            try:
                reply = call(body, turn=1)
                value = rating(reply)
                if value is None:
                    reason = reply.get("stop_reason") or "invalid_rating"
                    if reason == "end_turn":
                        reason = "invalid_rating"
            except Stop as error:
                value, reason = None, str(error)
                stop = reason
            row = dict(location, rating=value, reason=reason)
            log("probe", **{k: v for k, v in row.items() if k != "probe"})
            probes.append(row)
            if stop:
                break
    report = analyze(episodes, probes, cases)
    log("run_end", stop=stop)
    return report, stop


def bind(client, log, location, pattern, flat_probe, case):
    def call(body, **position):
        if client is not None:
            return client(body, **location, **position)
        log("request", **location, **position, attempt=1, body=body, reserved_units=0)
        reply = scripted(body, case, pattern, flat_probe)
        log("response", **location, **position, attempt=1, scripted_response=reply)
        log("usage", **location, **position, attempt=1, usage=reply["usage"])
        return reply
    return call


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--offline", choices=PATTERNS)
    mode.add_argument("--receipt", type=Path)
    parser.add_argument("--output", required=True, help="New folder name inside exploratory/results")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.output):
        parser.error("output must be a single folder name using letters, digits, underscores or hyphens")
    raw = CASES.read_bytes()
    cases, manager_reply = load_cases(raw)
    root = ROOT / "exploratory" / "results"
    if root.resolve() != root:
        raise Stop("results root must be local to this checkout")
    output = root / args.output
    receipt = None
    if args.receipt:
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
        validate_receipt(receipt, raw, args.output)
    output.mkdir(parents=True, exist_ok=False)
    log = Journal(output / "journal.jsonl")
    log("run_start", receipt=receipt, offline=args.offline)
    client = None
    if receipt:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            log("run_end", stop="missing ANTHROPIC_API_KEY")
            raise Stop("missing ANTHROPIC_API_KEY")
        client = Client(key, log)
    report, stop = campaign(cases, manager_reply, log, client=client, pattern=args.offline)
    (output / "analysis.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (output / "analysis.md").write_text(markdown(report), encoding="utf-8")
    print(report["outcome"])
    if stop:
        raise SystemExit(stop)


if __name__ == "__main__":
    main()
