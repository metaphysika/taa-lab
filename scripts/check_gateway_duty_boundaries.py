#!/usr/bin/env python3
"""Verify Claude's three stage-6 boundary mutations fail their component tests.

Mutants exist only in child-process memory; production files and fixtures are
never edited. This is a bounded sensitivity check, not a correctness proof.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("accept_action_deadline_removed", "test_apply_action_acceptance_excludes_exact_offer_deadline",
     'duty["offered_to"] != actor or state["step"] >= duty["offer_deadline_step"]',
     'duty["offered_to"] != actor'),
    ("accept_message_deadline_inclusive", "test_receive_acceptance_excludes_exact_offer_deadline",
     'state["step"] < d["offer_deadline_step"]', 'state["step"] <= d["offer_deadline_step"]'),
    ("reopening_overdue_late", "test_reopening_marks_overdue_at_or_after_due_step_in_same_call",
     'duty["overdue"] |= state["step"] >= duty["deadline_step"]',
     'duty["overdue"] |= state["step"] > duty["deadline_step"]'),
]
CHILD = '''
import importlib, io, json, sys, unittest
from pathlib import Path
sys.path.insert(0, sys.argv[1])
module = importlib.import_module("taa_gateway.duties")
source = Path(module.__file__).read_text()
old, new, name = sys.argv[2:]
if old:
    assert source.count(old) == 1, "mutation must have exactly one source target"
    exec(compile(source.replace(old, new), module.__file__, "exec"), module.__dict__)
suite = unittest.defaultTestLoader.loadTestsFromName("tests.test_gateway_duties.DutyEngineTests." + name)
stream = io.StringIO()
result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
print(json.dumps({"tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
                  "successful": result.wasSuccessful(), "output": stream.getvalue()}))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    rows = []
    for identity, name, old, new in CASES:
        for mutated in (False, True):
            proc = subprocess.run([sys.executable, "-I", "-c", CHILD, str(ROOT),
                                   old if mutated else "", new, name], capture_output=True, text=True)
            if proc.returncode:
                raise RuntimeError(proc.stderr or proc.stdout)
            result = json.loads(proc.stdout)
            good = (result["tests"] == 1 and result["errors"] == 0 and
                    (result["failures"] == 1 if mutated else result["successful"]))
            rows.append(dict(mutation=identity, mutated=mutated, test=name, detected=good, **result))
            print(f"{identity} {'mutant' if mutated else 'original'}: {'PASS' if good else 'FAIL'}", flush=True)
    report = {"claim": "DESCRIPTIVE: Sol-authored controls for Claude's stage-6 review",
              "source_sha256": hashlib.sha256((ROOT / "taa_gateway/duties.py").read_bytes()).hexdigest(),
              "tests_sha256": hashlib.sha256((ROOT / "tests/test_gateway_duties.py").read_bytes()).hexdigest(),
              "results": rows, "all_detected": all(r["detected"] for r in rows)}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    return 0 if report["all_detected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
