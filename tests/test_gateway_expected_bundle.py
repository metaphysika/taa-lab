"""Integrity, complete reference execution and assertion-runner negative controls."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

from tests.trace_support.bundle import BUNDLE, ROOT, cases, verify_bundle
from tests.trace_support.reference_runner import all_results, run


class IndependentBundleTests(unittest.TestCase):
    def test_source_zip_manifest_and_extracted_bytes_are_unchanged(self):
        verify_bundle()

    def test_superseded_bundle_is_preserved_but_not_executed(self):
        path = ROOT / "archive/v0.1"
        pin = json.loads((ROOT / "PROVENANCE_v01.json").read_text())
        self.assertEqual(hashlib.sha256((path / "taa_expected_traces_v0.1.zip").read_bytes()).hexdigest(), pin["zip_sha256"])
        for line in (path / "MANIFEST.sha256").read_text().splitlines():
            sha, name = line.split("  ", 1)
            self.assertEqual(hashlib.sha256((path / name).read_bytes()).hexdigest(), sha)
        self.assertTrue((path / "SUPERSEDED.md").is_file())
        self.assertTrue(all(c["source"].startswith("v0.2.1/") for c in cases()))

    def test_authors_structural_validator_reports_zero_errors(self):
        r = subprocess.run([sys.executable, "-I", str(BUNDLE / "tools/validate_traces.py"), str(BUNDLE)],
                           text=True, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("49 traces and variants checked, 0 errors", r.stdout)

    def test_variants_and_fault_parameters_are_all_executed(self):
        inputs = cases()
        self.assertEqual(len(inputs), 54)
        self.assertEqual(len({c["id"] for c in inputs}), 54)
        self.assertEqual(len([c for c in inputs if c["id"].startswith("T23[")]), 7)
        self.assertNotIn("T36", [c["id"] for c in inputs])
        self.assertEqual(next(c for c in inputs if c["id"] == "T24b")["trace"]["setup"]["token_lifetime"], 2)

    def test_all_independent_reference_assertions_pass_without_skips(self):
        results = all_results()
        self.assertGreaterEqual(len(results), 532)
        self.assertEqual([r for r in results if r["status"] != "pass"], [])
        self.assertEqual({r["trace"] for r in results}, {c["id"] for c in cases()})

    def test_wrong_expectation_is_a_discrepancy_not_a_new_answer_key(self):
        c = deepcopy(next(c for c in cases() if c["id"] == "T39"))
        c["trace"]["steps"][1]["expect"]["attributed_issuer"] = "L"
        failed = [r for r in run(c) if r["status"] != "pass"]
        self.assertEqual(len(failed), 1)
        self.assertEqual((failed[0]["expectation"], failed[0]["observed"]), ("L", "none"))
        verify_bundle()

    def test_new_assertion_vocabulary_is_incomplete_never_a_silent_pass(self):
        c = deepcopy(next(c for c in cases() if c["id"] == "T39"))
        c["trace"]["steps"][1]["expect"]["unimplemented_check"] = True
        failed = [r for r in run(c) if r["status"] != "pass"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["status"], "incomplete")


if __name__ == "__main__":
    unittest.main()
