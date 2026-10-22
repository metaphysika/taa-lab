#!/usr/bin/env python3
"""Run the four $0 scripted controllers on the reviewed paired development cases."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from worlds.refunds.harness import run_suite


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--case", action="append", dest="cases")
    args = parser.parse_args()
    result = run_suite(args.cases)
    if not result["episodes"]:
        parser.error("no matching cases")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    text = ["DESCRIPTIVE: scripted development coverage only; not H3 evidence.", str(result["counts"])]
    for e in result["episodes"]:
        text.append(e["case"] + " " + e["controller"] + " " + json.dumps(e["metrics"], sort_keys=True))
    args.report.with_suffix(".txt").write_text("\n".join(text) + "\n")
    print(json.dumps(result["counts"]))
    return int(bool(result["counts"]["discrepancies"] or result["counts"]["incomplete"]))


if __name__ == "__main__":
    raise SystemExit(main())
