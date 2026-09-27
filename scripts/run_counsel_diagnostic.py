"""Run the six fixed counsel questions once per pinned provider with usage limits."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.call_telemetry import CallRecorder
from scripts.run_study import digest, paid_model, source_hashes
from taa.counsel_check import check_counsel


PRICE_FILE = ROOT / "studies/provider-prices-2026-09-27.json"
LEDGER = ROOT / "results/obligations-v01941-spending-ledger.json"
OUTPUT = ROOT / "results/2026-09-27 v0.19.5 obligations-counsel-diagnostic r1"
MODELS = {"openai": "gpt-6-luna", "claude": "claude-haiku-4-5-20251001"}
MAX_LOGICAL_CALLS = 12
MAX_REQUEST_ATTEMPTS = 18
STAGE_MAX_DOLLARS = 0.25
GLOBAL_MAX_DOLLARS = 7.0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", required=True, choices=MODELS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    model_id = MODELS[args.provider]
    print(json.dumps({"stage": "counsel_diagnostic", "provider": args.provider,
                      "model": model_id, "questions": 6,
                      "max_logical_calls": MAX_LOGICAL_CALLS,
                      "max_request_attempts": MAX_REQUEST_ATTEMPTS,
                      "stage_max_dollars": STAGE_MAX_DOLLARS,
                      "global_max_dollars": GLOBAL_MAX_DOLLARS}, indent=2))
    if args.dry_run:
        return 0

    from run import build

    out_dir = OUTPUT / args.provider
    if out_dir.exists():
        raise SystemExit(f"diagnostic output exists; preserve it for review: {out_dir}")
    prices = json.loads(PRICE_FILE.read_text())["models"]
    if model_id not in prices:
        raise SystemExit(f"dated price file lacks {model_id}")
    prior = json.loads(LEDGER.read_text())["estimated_api_dollars"] if LEDGER.exists() else 0.0
    out_dir.mkdir(parents=True)
    hashes = source_hashes()
    hashes["taa/counsel_check.py"] = digest(ROOT / "taa/counsel_check.py")
    hashes["scripts/run_counsel_diagnostic.py"] = digest(Path(__file__))
    (out_dir / "run-record.json").write_text(json.dumps({
        "provider": args.provider, "model": model_id,
        "source_hashes": hashes, "price_sha256": digest(PRICE_FILE),
        "scenario_sha256": digest(ROOT / "scenarios/purpose_defeat.json"),
        "start_estimated_api_dollars": prior,
        "limits": {"max_logical_calls": MAX_LOGICAL_CALLS,
                   "max_request_attempts": MAX_REQUEST_ATTEMPTS,
                   "stage_max_dollars": STAGE_MAX_DOLLARS,
                   "global_max_dollars": GLOBAL_MAX_DOLLARS}}, indent=2) + "\n")
    recorder = CallRecorder(out_dir / "calls.jsonl", prices, model_id,
                            MAX_LOGICAL_CALLS, MAX_REQUEST_ATTEMPTS,
                            min(prior + STAGE_MAX_DOLLARS, GLOBAL_MAX_DOLLARS),
                            prior_spend=prior, ledger_path=LEDGER)
    recorder.context = {"stage": "counsel_diagnostic", "case": "purpose_defeat"}
    model = paid_model(args.provider, model_id, recorder)
    with (ROOT / "scenarios/purpose_defeat.json").open() as source:
        world, warrant, _ = build(json.load(source))
    result = check_counsel(model, warrant, world, 1, str(out_dir / "counsel_check.md"))
    (out_dir / "summary.json").write_text(json.dumps({
        "status": "complete", "provider": args.provider, "model": model_id,
        "result": result, "usage": recorder.snapshot()}, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
