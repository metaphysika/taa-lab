#!/usr/bin/env python3
"""Offline component and mutation evidence; not full comparator acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MUTANTS = (
    ("actor_binding", 'if handle["actor"] != actor:', 'if False:',
     "test_authenticated_actor_and_exact_arguments_are_bound"),
    ("argument_binding", 'if tool is not None and tool != handle["tool"] or args is not None and encode(args) != encode(handle["args"]):', 'if False:',
     "test_authenticated_actor_and_exact_arguments_are_bound"),
    ("epoch_binding", 'if store.epoch != handle["epoch"]:', 'if False:',
     "test_epoch_changes_once_for_batch_and_insert_voids_all_handles"),
    ("expiry_boundary", 'handle["status"] == "live" and step >= handle["expires"]', 'handle["status"] == "live" and step > handle["expires"]',
     "test_plain_tick_and_exact_live_handle_expiry"),
    ("actual_rollback", 'self._db.execute("ROLLBACK")', 'self._db.execute("COMMIT")',
     "test_every_fault_rolls_back_actual_partial_sql_and_can_retry"),
    ("field_correction_rights", 'not set(request["fields"]).issubset(allowed)', 'False',
     "test_record_create_correct_and_field_rights_are_distinct"),
)


def run(destination):
    destination.mkdir(parents=True, exist_ok=False)
    files = ("conventional_gateway/__init__.py", "conventional_gateway/kernel.py",
             "tests/test_conventional_kernel.py", "scripts/check_conventional_kernel.py",
             "docs/process/TAA_CONVENTIONAL_COMPARATOR_PROTOCOL_v0.md")
    pins = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files}
    source = (ROOT / "conventional_gateway/kernel.py").read_text()
    original_hash = hashlib.sha256(source.encode()).hexdigest()
    worker = '''
import json, sys, unittest
sys.path.insert(0, sys.argv[1])
sys.path.insert(1, sys.argv[2])
suite = unittest.defaultTestLoader.loadTestsFromName(sys.argv[3])
result = unittest.TextTestRunner(verbosity=2).run(suite)
print(json.dumps({"tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skips": len(result.skipped)}))
sys.exit(0 if result.wasSuccessful() else 1)
'''

    def invoke(package, test, label):
        target = "tests.test_conventional_kernel" + (".RelationalKernelTests." + test if test else "")
        proc = subprocess.run([sys.executable, "-I", "-c", worker, str(package), str(ROOT), target],
                              capture_output=True, text=True)
        (destination / (label + ".stdout")).write_text(proc.stdout)
        (destination / (label + ".stderr")).write_text(proc.stderr)
        try:
            observation = json.loads(proc.stdout.splitlines()[-1])
        except (ValueError, IndexError):
            observation = {"tests": 0, "failures": 0, "errors": 1, "skips": 0}
        return {"exit": proc.returncode, **observation}

    baseline = invoke(ROOT, None, "baseline")
    results = []
    for label, before, after, test in MUTANTS:
        if source.count(before) != 1:
            raise ValueError("mutation anchor no longer unique: " + label)
        package = destination / label
        module = package / "conventional_gateway"
        module.mkdir(parents=True)
        (module / "__init__.py").write_text((ROOT / "conventional_gateway/__init__.py").read_text())
        mutated = source.replace(before, after)
        (module / "kernel.py").write_text(mutated)
        observed = invoke(package, test, label)
        caught = (observed["exit"] == 1 and observed["tests"] == 1 and
                  observed["failures"] > 0 and observed["errors"] == 0 and observed["skips"] == 0)
        results.append({"mutation": label, "test": test, "caught": caught,
                        "mutated_sha256": hashlib.sha256(mutated.encode()).hexdigest(), **observed})
    final_hash = hashlib.sha256((ROOT / "conventional_gateway/kernel.py").read_bytes()).hexdigest()
    report = {"schema": "conventional-kernel-evidence/0.1", "source_sha256": original_hash,
              "input_hashes": pins,
              "all_inputs_unchanged": all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha for name, sha in pins.items()),
              "source_unchanged": original_hash == final_hash, "baseline": baseline,
              "mutations": results, "full_comparator_acceptance": "INCOMPLETE: no W0 policy/backend yet"}
    report["gate_pass"] = (baseline["exit"] == 0 and baseline["tests"] == 21 and
                           baseline["skips"] == 0 and report["source_unchanged"] and report["all_inputs_unchanged"] and all(r["caught"] for r in results))
    (destination / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new evidence directory; existing directories are never overwritten")
    result = run(parser.parse_args().output.resolve())
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["gate_pass"] else 1)
