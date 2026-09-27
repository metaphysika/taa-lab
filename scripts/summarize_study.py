"""Generate reproducible episode tables and a failure index from a study manifest."""
import argparse
import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_study import episode_order, load_manifest


METRICS = ("serious_unmet_need_ids", "preventable_unmet_ids", "wrongful_effects",
           "authority_violations", "invalidated_work_executed", "ordinary_completed_ids",
           "unresolved_authority_claims", "unresolved_model_referrals",
           "avoidable_ordinary_work_lost", "held_seat_steps",
           "retrospectively_unneeded_hold_seat_steps", "invalid_hold_seat_steps",
           "notices_received_by_person", "simulated_shipping_cost",
           "grave", "questionable", "unauthorized", "undone")
FAILURE_METRICS = ("serious_unmet_need_ids", "wrongful_effects", "authority_violations",
                   "invalidated_work_executed", "avoidable_ordinary_work_lost",
                   "invalid_hold_seat_steps", "grave", "undone")


def number(value):
    return len(value) if isinstance(value, list) else (value or 0)


def journal_totals(path):
    if not path.exists():
        return {"logical_calls": 0, "request_attempts": 0,
                "estimated_api_dollars": 0.0, "incomplete_attempts": 0}
    starts = {}
    completed = set()
    result = {"logical_calls": 0, "request_attempts": 0,
              "estimated_api_dollars": 0.0, "incomplete_attempts": 0}
    for line in path.read_text().splitlines():
        event = json.loads(line)
        if event["event"] == "logical_start":
            result["logical_calls"] += 1
        elif event["event"] == "attempt_start":
            starts[event["id"]] = event["reserved_dollars"]
            result["request_attempts"] += 1
        elif event["event"] == "attempt_end":
            completed.add(event["id"])
            charge = event.get("estimated_charge_dollars")
            result["estimated_api_dollars"] += (starts[event["id"]]
                                                   if charge is None else charge)
    for aid, reserve in starts.items():
        if aid not in completed:
            result["estimated_api_dollars"] += reserve
            result["incomplete_attempts"] += 1
    result["estimated_api_dollars"] = round(result["estimated_api_dollars"], 8)
    return result


def summarize(manifest):
    providers = (["fixture"] if manifest["stage"] in ("free", "free_regression")
                 else list(manifest["models"]))
    output_root = ROOT / manifest["output_dir"]
    rows, failures = [], []
    for provider in providers:
        for case, repeat, mode in episode_order(manifest):
            episode_id = f"{Path(case).stem}-{mode}-r{repeat:02d}"
            path = output_root / provider / f"{episode_id}.json"
            if path.exists():
                episode = json.loads(path.read_text())
                status = episode.get("status", "unknown")
            else:
                episode, status = {}, "missing"
            outcome = episode.get("outcome", {})
            row = {"provider": provider, "case": Path(case).stem, "repeat": repeat,
                   "mode": mode, "status": status, "episode_path": str(path),
                   "reviewer_calls": episode.get("reviewer_calls", 0),
                   "estimated_api_dollars": episode.get("api", {}).get(
                       "estimated_api_dollars", 0) if status == "complete" else ""}
            row.update({key: number(outcome.get(key)) if status == "complete" else ""
                        for key in METRICS})
            rows.append(row)
            if status != "complete":
                failures.append({"episode_path": str(path), "status": status,
                                 "error": episode.get("error", "")})
            elif any(row[key] for key in FAILURE_METRICS):
                failures.append({"episode_path": str(path), "status": status,
                                 "metrics": {key: outcome[key] for key in FAILURE_METRICS
                                             if row[key]}})

    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["provider"], row["case"], row["mode"])].append(row)
    cells = []
    for (provider, case, mode), items in sorted(grouped.items()):
        done = [r for r in items if r["status"] == "complete"]
        cell = {"provider": provider, "case": case, "mode": mode,
                "complete": len(done), "expected": len(items)}
        for metric in METRICS:
            values = [r[metric] for r in done]
            cell[metric] = {"values": values,
                            "mean": round(statistics.mean(values), 3) if values else None,
                            "min": min(values) if values else None,
                            "max": max(values) if values else None}
        cells.append(cell)
    calls = {provider: journal_totals(output_root / provider / "calls.jsonl")
             for provider in providers}
    return {"stage": manifest["stage"], "expected_episodes": len(rows),
            "complete_episodes": sum(row["status"] == "complete" for row in rows),
            "rows": rows, "cells": cells, "failure_index": failures,
            "provider_calls_and_estimated_api_cost": calls}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args(argv)
    manifest = load_manifest(ROOT / args.manifest)
    report = summarize(manifest)
    destination = ROOT / manifest["output_dir"]
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    (destination / "failure-index.json").write_text(
        json.dumps(report["failure_index"], indent=2) + "\n")
    with (destination / "episodes.csv").open("w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(report["rows"][0]))
        writer.writeheader()
        writer.writerows(report["rows"])
    print(json.dumps({key: value for key, value in report.items()
                      if key not in ("rows", "cells", "failure_index")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
