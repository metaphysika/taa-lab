"""Bounded stage-5 gate. Incomplete production acceptance still fails the full runner.

The ledger enumerates observed coverage gaps, not expected decisions. Any new
gap or disagreement fails this gate; shrinking the ledger is permitted. All
source expectations still come unchanged from Claude/Astra's frozen inputs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.trace_support import production_backend, reference_runner, regressions
from tests.trace_support.bundle import cases, verify_bundle


def counts(rows, scenarios):
    return {"scenarios": scenarios, "checks": len(rows),
            "source_assertions": sum(r.get("origin", "source") == "source" and "raw_observations" not in r for r in rows),
            "state_audits": sum(r.get("origin") == "state-audit" for r in rows),
            "detection_guards": sum("raw_observations" in r for r in rows),
            "discrepancies": sum(r["status"] == "discrepancy" for r in rows),
            "incomplete": sum(r["status"] == "incomplete" for r in rows)}


def source_locations(inputs):
    result = set()
    for case in inputs:
        for index, step in enumerate(case["trace"]["steps"]):
            for key in step.get("expect", {}):
                result.add((case["id"], f"steps[{index}]@{step['step']}.{key}"))
        for key in case["trace"].get("final", {}):
            result.add((case["id"], "final." + key))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--require-complete", action="store_true",
                        help="Stage 6 acceptance: fail on ANY remaining incomplete check")
    args = parser.parse_args()
    verify_bundle()
    frozen = reference_runner.all_results(backend=production_backend)
    regression = regressions.run_suite(reference_runner, backend=production_backend)
    controls = regression["negative_controls"]
    report = {"scope": ("complete frozen W0 engineering coverage; NOT empirical H3 validation" if args.require_complete else
                        "partial stage 5 engineering gate; NOT complete production acceptance"),
              "implementation_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "source_hashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for base in ("taa_gateway", "tests/trace_support", "tests/regression_scenarios")
                                for p in sorted((ROOT / base).rglob("*")) if p.suffix in (".py", ".yaml", ".json")},
              "frozen": {"assertions": frozen, "counts": counts(frozen, len(cases()))},
              "regressions": dict(regression, counts=counts(regression["assertions"], regression["scenarios"])),
              "hidden_state_audit_detection": {c["trace"]: any(r["origin"] == "state-audit" and r["status"] == "discrepancy"
                                                               for r in c["raw_observations"]) for c in controls}}
    gaps = json.loads((ROOT / "docs/process/evidence/gateway-stage5/coverage_gaps.json").read_text())
    allowed = {tuple(row) for row in gaps["incomplete_locations"]}
    observed_gaps, errors = set(), []
    suites = (("frozen", frozen, cases()), ("regressions", regression["assertions"], regressions.cases()))
    for name, rows, inputs in suites:
        source_rows = [r for r in rows if "raw_observations" not in r]
        for control in controls if name == "regressions" else []:
            source_rows += control["raw_observations"]
        observed_sources = [(r["trace"], r["assertion"]) for r in source_rows if r.get("origin") == "source"]
        if set(observed_sources) != source_locations(inputs) or len(observed_sources) != len(set(observed_sources)):
            errors.append(name + ": lost or duplicated source assertion")
        if sum(r.get("origin") == "state-audit" for r in rows) < gaps["minimum_state_audits"][name]:
            errors.append(name + ": state-audit coverage shrank")
        for row in rows:
            if row["status"] == "discrepancy":
                errors.append(name + ": " + row["trace"] + ": " + row["assertion"])
        for row in rows + [r for c in controls for r in c["raw_observations"]] if name == "regressions" else rows:
            if row["status"] == "incomplete":
                key = (name, row["trace"], row["assertion"])
                observed_gaps.add(key)
                if key not in allowed or row.get("origin") == "state-audit":
                    errors.append("unexpected incomplete: " + repr(key))
    if len(controls) != 3 or not all(report["hidden_state_audit_detection"].values()):
        errors.append("all three actual hidden-state mutations must trigger independent state-audit discrepancies")
    if args.require_complete and observed_gaps:
        errors.append("full production coverage requires zero incomplete checks, including raw controls")
    report["observed_incomplete_locations"] = sorted(observed_gaps)
    report["gate_errors"] = errors
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({name: report[name]["counts"] for name in ("frozen", "regressions")}))
    print(json.dumps({"hidden_state_audit_detection": report["hidden_state_audit_detection"], "gate_errors": errors}))
    print("FULL FROZEN W0 GATE: zero incomplete required; bounded engineering evidence only." if args.require_complete else
          "PARTIAL STAGE 5 ONLY. Every remaining incomplete check is listed in the report; full acceptance is not green.")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
