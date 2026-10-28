"""Regression: denial notices bind evidence through `basis` only (no `cites` fallback).

The pilot showed the conventional gateway accepting refund_denied notices whose evidence
sat in `cites` (four Gemini/conventional D commits). No ruling authorized that fallback and
the independent reference requires `basis`. These cases pin the corrected behaviour.
"""
import unittest

from tests import test_conventional_policy as flat


class DenialBasisOnlyTests(unittest.TestCase):
    # Reuse the flat-policy fixture world and helpers without inheriting its tests.
    setUp = flat.FlatPolicyTests.setUp
    record = flat.FlatPolicyTests.record
    evaluate = flat.FlatPolicyTests.evaluate

    def notice(self, **fields):
        request = dict({"to": "K1", "claim": "CL1", "amount": 120, "template": "refund_denied"}, **fields)
        return self.evaluate(request, tool="message_party")

    def test_cites_only_denial_notice_is_refused(self):
        result = self.notice(cites="RET1")
        self.assertEqual("REFUSE", result["disposition"])
        self.assertIn("no cited denial basis", result["reason"])

    def test_basis_only_denial_notice_is_unchanged(self):
        self.assertEqual("PERMIT", self.notice(basis="RET1")["disposition"])

    def test_both_fields_use_basis_and_ignore_cites(self):
        self.assertEqual("PERMIT", self.notice(basis="RET1", cites="NONE")["disposition"])
        self.assertEqual("REFUSE", self.notice(basis="NONE", cites="RET1")["disposition"])

    def test_cites_only_denial_notice_is_refused_even_when_cited_record_would_contradict(self):
        self.record("RET1", {"received": True})
        self.assertEqual("REFUSE", self.notice(cites="RET1")["disposition"])
        self.assertEqual("PROHIBIT", self.notice(basis="RET1")["disposition"])

    def test_issued_notice_still_reads_cites_not_basis(self):
        request = {"to": "K1", "claim": "CL1", "amount": 120, "template": "refund_issued", "basis": "REF1"}
        result = self.evaluate(request, tool="message_party")
        self.assertEqual("REFUSE", result["disposition"])
        self.assertIn("no cited settlement record", result["reason"])

    def test_deny_refund_requires_basis_and_ignores_cites(self):
        self.assertFalse(self.evaluate({"claim": "CL1", "amount": 120, "cites": "RET1"}, tool="deny_refund")["evaluated"])
        self.assertEqual(self.evaluate({"claim": "CL1", "amount": 120, "basis": "RET1"}, tool="deny_refund")["disposition"],
                         self.evaluate({"claim": "CL1", "amount": 120, "basis": "RET1", "cites": "NONE"}, tool="deny_refund")["disposition"])



if __name__ == "__main__":
    unittest.main()
