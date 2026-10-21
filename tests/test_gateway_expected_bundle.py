"""Integrity and ingestion checks, not outcome tests against either model."""
import unittest

from tests.trace_support.bundle import BUNDLE, _yaml_text, cases, read_yaml, verify_bundle


class ExpectedBundleTests(unittest.TestCase):
    def test_supplied_bytes_and_manifest_are_intact(self):
        verify_bundle()

    def test_abstract_duty_names_are_single_identifiers(self):
        traces, _ = read_yaml(BUNDLE / "traces/01_case_families.yaml")
        duty = traces[1]["steps"][0]["expect"]["duties_after_engine"][1]
        self.assertEqual(duty["id"], "D_refund(CL1,120)")
        self.assertEqual(set(duty), {"id", "resolution"})

    def test_quoting_never_changes_comment_or_quoted_assertion(self):
        source = 'x: "D_refund(CL1,120)" # D_refund(CL1,120)\ny: D_refund(CL1,120)\n'
        self.assertEqual(_yaml_text(source), 'x: "D_refund(CL1,120)" # D_refund(CL1,120)\ny: "D_refund(CL1,120)"\n')

    def test_all_executable_cases_are_loaded_and_pending_assertions_retained(self):
        loaded = cases()
        self.assertEqual(len(loaded), 50)
        self.assertEqual(len({case["id"] for case in loaded}), 50)
        self.assertNotIn("T36", {case["id"] for case in loaded})
        self.assertEqual(len([case for case in loaded if case["id"].startswith("T23[")]), 7)
        marked = {q for case in loaded for q in case["pending"].values()}
        self.assertEqual(marked, {"Q" + str(n) for n in range(1, 10)})
        def check(value):
            if isinstance(value, dict):
                self.assertFalse(any(key.endswith(')') and item is None for key, item in value.items()))
                for item in value.values(): check(item)
            elif isinstance(value, list):
                for item in value: check(item)
        for case in loaded: check(case['trace'])

    def test_token_expiry_variant_does_not_inherit_unrelated_grant_expiry(self):
        variant = next(case for case in cases() if case["id"] == "T24b")
        self.assertNotIn("grants", variant["trace"]["setup"])
        self.assertEqual([step["step"] for step in variant["trace"]["steps"]], [4, 6])


if __name__ == "__main__":
    unittest.main()
