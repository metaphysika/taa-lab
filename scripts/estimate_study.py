"""Free prompt census and price scenarios; no provider client is constructed."""
import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_study import FixtureReviewer, load_manifest, run_episode


class PromptCensus:
    def __init__(self):
        self.prompts = []

    def logical(self, prompt, kind):
        self.prompts.append({"kind": kind, "bytes": len(prompt.encode()),
                             "input_token_estimate": math.ceil(len(prompt.encode()) / 3) + 50})

    def snapshot(self):
        return {"logical_calls": len(self.prompts), "request_attempts": 0,
                "input_tokens": 0, "output_tokens": 0,
                "cached_input_tokens": 0, "cache_write_tokens": 0,
                "estimated_api_dollars": 0.0}


def census(manifest, prices):
    rows = []
    for path in manifest["cases"]:
        scenario = json.loads((ROOT / path).read_text())
        for mode in (mode for mode in manifest["modes"]
                     if mode != "expiring_obligations"):
            recorder = PromptCensus()
            run_episode(scenario, mode, FixtureReviewer(), recorder=recorder,
                        agent_kind=manifest.get("agents", {}).get(path, "timeline"))
            rows.append({"case": path, "mode": mode,
                         "calls": len(recorder.prompts),
                         "input_token_estimate": sum(p["input_token_estimate"]
                                                     for p in recorder.prompts),
                         "max_prompt_bytes": max((p["bytes"] for p in recorder.prompts),
                                                 default=0)})
    total_calls = sum(row["calls"] for row in rows)
    total_input = sum(row["input_token_estimate"] for row in rows)
    projections = {}
    for model, price in prices["models"].items():
        projections[model] = {}
        for assumed_output in (300, 800, 1500):
            one_repeat = (total_input * price["input_per_million"]
                          + total_calls * assumed_output * price["output_per_million"]) / 1_000_000
            projections[model][str(assumed_output)] = {
                "one_repeat_dollars": round(one_repeat, 4),
                "five_repeats_dollars": round(one_repeat * 5, 4)}
    return {"basis": "deterministic all-approve fixture; calls may rise with real referrals, "
                     "clarification, retries, and refusals; input uses prompt bytes/3 plus 50 tokens",
            "rows": rows, "one_repeat_calls": total_calls,
            "one_repeat_input_token_estimate": total_input,
            "five_repeat_calls_per_provider": total_calls * 5,
            "projections_without_retries_or_extra_calls": projections}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="studies/obligations-free-v0194.json")
    parser.add_argument("--prices", default="studies/provider-prices-2026-09-27.json")
    parser.add_argument("--output", default="studies/obligations-free-cost-census-v0194.json")
    args = parser.parse_args(argv)
    manifest = load_manifest(ROOT / args.manifest)
    prices = json.loads((ROOT / args.prices).read_text())
    report = census(manifest, prices)
    (ROOT / args.output).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
