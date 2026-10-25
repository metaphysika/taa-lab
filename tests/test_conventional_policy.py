"""Sol-authored component expectations from W0/Q1–Q13; Claude review pending."""
from copy import deepcopy
import unittest

from conventional_gateway.kernel import Store
from conventional_gateway.policy import Policy, arguments_valid
from tests.trace_support.bundle import world


class FlatPolicyTests(unittest.TestCase):
    def setUp(self):
        self.world = world()
        self.policy = Policy(self.world)
        store = Store(b"independent-conventional-policy-test")
        with store.transaction():
            for rid, raw in self.world["records"].items():
                data = deepcopy(raw)
                kind = data.pop("kind")
                store.append("records", rid, {"kind": kind, "fields": data, "writer": "setup", "evidential": True}, relevant=False)
            for gid, grant in self.world["grants"].items():
                store.append("grants", gid, grant, relevant=False)
        self.state = store.snapshot()
        self.state["step"] = 1
        self.args = {"claim": "CL1", "amount": 120, "to": "K1_card", "basis": "return"}

    def record(self, rid, fields, kind=None, evidential=True):
        versions = self.state["records"].setdefault(rid, [])
        old = deepcopy(versions[-1]) if versions else {"fields": {}, "kind": kind, "writer": "test", "evidential": evidential}
        old["fields"].update(fields)
        versions.append(old)

    def grant(self, gid, **changes):
        versions = self.state["grants"].setdefault(gid, [])
        old = deepcopy(versions[-1]) if versions else {}
        old.update(changes)
        versions.append(old)

    def evaluate(self, args=None, actor="A", tool="issue_refund"):
        before = deepcopy(self.state)
        result = self.policy.evaluate(self.state, actor, tool, self.args if args is None else args)
        self.assertEqual(before, self.state, "flat policy must be read-only")
        return result

    def test_known_false_support_refuses_unknown_support_holds_true_permits(self):
        self.assertEqual("REFUSE", self.evaluate()["disposition"])
        self.state["records"].pop("RET1")
        self.assertEqual("HOLD", self.evaluate()["disposition"])
        self.record("RET1", {"received": True, "order": "ORD1"}, "return_receipt")
        self.assertEqual("PERMIT", self.evaluate()["disposition"])

    def test_prohibition_is_first_even_without_actor_authority(self):
        result = self.evaluate(dict(self.args, asserts=["return received"]), actor="B")
        self.assertEqual("PROHIBIT", result["disposition"])
        self.assertEqual("PR1", result["rule"])
        self.assertEqual("prohibition", result["failed_stage"])
        self.assertIn("AU1", result["rules"])

    def test_payment_route_prohibition_is_independent_of_grant(self):
        self.record("RET1", {"received": True})
        self.grant("G1", status="revoked")
        result = self.evaluate(dict(self.args, to="account_X"))
        self.assertEqual("PROHIBIT", result["disposition"])
        self.assertEqual("PR2", result["rule"])

    def test_damaged_item_cannot_be_asserted_undamaged(self):
        self.record("RET1", {"received": True, "condition": "damaged"})
        self.assertEqual("PROHIBIT", self.evaluate(dict(self.args, asserts=["item returned undamaged"]))["disposition"])
        self.assertEqual("PERMIT", self.evaluate()["disposition"])

    def test_agent_note_is_not_evidence_for_an_assertion(self):
        self.record("N1", {"received": True, "by": "A"}, "agent_note", evidential=False)
        result = self.evaluate({"to": "L", "asserts": ["the CL1 item was returned"]}, tool="report")
        self.assertEqual("PROHIBIT", result["disposition"])
        self.assertEqual("PR1", result["rule"])

    def test_missing_grant_parent_or_expired_parent_prevents_authority(self):
        self.record("RET1", {"received": True})
        for change in ({"status": "revoked"}, {"expires_at": 1}, {"actions": []}):
            with self.subTest(change=change):
                original = deepcopy(self.state["grants"]["G0"])
                self.grant("G0", **change)
                self.assertEqual("REFUSE", self.evaluate()["disposition"])
                self.state["grants"]["G0"] = original
        self.state["grants"].pop("G0")
        self.assertEqual("REFUSE", self.evaluate()["disposition"])

    def test_grant_expiry_is_invalid_at_exact_step(self):
        self.record("RET1", {"received": True})
        self.grant("G1", expires_at=3)
        self.state["step"] = 2
        self.assertEqual("PERMIT", self.evaluate()["disposition"])
        self.state["step"] = 3
        result = self.evaluate()
        self.assertEqual("REFUSE", result["disposition"])
        self.assertEqual("authority", result["failed_stage"])

    def test_fragments_from_different_grants_do_not_compose(self):
        self.record("RET1", {"received": True})
        self.grant("G1", scope={"customers": ["K2"]})
        second = deepcopy(self.world["grants"]["G1"])
        second["actions"] = ["message_party"]
        self.state["grants"]["OTHER"] = [second]
        self.assertEqual("REFUSE", self.evaluate()["disposition"])
        self.state["grants"]["OTHER"][-1]["actions"].append("issue_refund")
        self.assertEqual("PERMIT", self.evaluate()["disposition"])

    def test_purpose_does_not_come_from_another_grant(self):
        self.record("RET1", {"received": True})
        self.grant("G1", purpose="unknown-purpose")
        self.assertEqual("REFUSE", self.evaluate()["disposition"])

    def test_ir1_allows_only_interim_messages_and_never_acceptance(self):
        self.grant("G1", status="revoked")
        self.state["duties"]["D_resolve(CL1)"] = [{"kind": "resolve", "claim": "CL1", "owner": "A", "resolution": "unresolved", "ownership_interrupted": True, "offered_to": "F"}]
        for template in ("claim_referred", "refund_held"):
            result = self.evaluate({"claim": "CL1", "to": "K1", "template": template}, tool="message_party")
            self.assertEqual("PERMIT", result["disposition"])
            self.assertEqual("IR1", result["authority_basis"])
        result = self.evaluate({"duty": "D_resolve(CL1)"}, actor="F", tool="accept_duty")
        self.assertEqual("REFUSE", result["disposition"])
        self.assertEqual("AU1", result["rule"])

    def test_acceptance_needs_standing_separately_from_grant(self):
        # Q18: isolate standing on an existing primary object, not missing scope.
        self.state["duties"]["D_resolve(CL1)"] = [{"kind": "resolve", "claim": "CL1", "owner": "B", "resolution": "unresolved", "offers": {}}]
        result = self.evaluate({"duty": "D_resolve(CL1)"}, tool="accept_duty")
        self.assertEqual("REFUSE", result["disposition"])
        self.assertEqual("DU4", result["rule"])
        self.state["duties"]["D_resolve(CL1)"] = [{"kind": "resolve", "claim": "CL1", "owner": "B", "resolution": "unresolved", "offers": {"A": {"active": True, "due": 3}}}]
        self.state["step"] = 2
        self.assertEqual("PERMIT", self.evaluate({"duty": "D_resolve(CL1)"}, tool="accept_duty")["disposition"])
        self.state["step"] = 3
        self.assertEqual("REFUSE", self.evaluate({"duty": "D_resolve(CL1)"}, tool="accept_duty")["disposition"])

    def test_cap_and_carrier_limit_choose_largest_fully_permissible_alternative(self):
        self.record("CL7", {"claimant": "K2", "order": "ORD2", "basis": "nondelivery", "amount": 400}, "claim")
        request = {"claim": "CL7", "amount": 400, "to": "K2_card", "basis": "nondelivery"}
        result = self.evaluate(request)
        self.assertEqual("ALTERNATIVE", result["disposition"])
        self.assertEqual(250, result["suggested"]["args"]["amount"])
        self.assertTrue({"SU2", "DT1", "DT2"} <= set(result["rules"]))
        self.assertEqual("PERMIT", self.evaluate(result["suggested"]["args"])["disposition"])

    def test_alternative_cannot_inherit_a_false_full_settlement_assertion(self):
        self.record("CL7", {"claimant": "K2", "order": "ORD2", "basis": "nondelivery", "amount": 400}, "claim")
        request = {"claim": "CL7", "amount": 400, "to": "K2_card", "basis": "nondelivery", "asserts": ["claim settled in full"]}
        result = self.evaluate(request)
        self.assertEqual("REFUSE", result["disposition"])
        self.assertNotIn("suggested", result)

    def test_multiple_passing_alternatives_choose_largest_whole_grant(self):
        self.record("RET1", {"received": True})
        self.grant("G1", limits={"per_refund_max": 80})
        self.state["grants"]["G2"] = [dict(self.world["grants"]["G1"], limits={"per_refund_max": 100})]
        result = self.evaluate()
        self.assertEqual("ALTERNATIVE", result["disposition"])
        self.assertEqual("G2", result["grant"])
        self.assertEqual(100, result["suggested"]["args"]["amount"])

    def test_cumulative_limit_counts_provisional_chargebacks(self):
        self.record("RET1", {"received": True})
        self.record("CB1", {"order": "ORD1", "amount": 50, "settled": False}, "chargeback")
        result = self.evaluate()
        self.assertEqual("ALTERNATIVE", result["disposition"])
        self.assertEqual(70, result["suggested"]["args"]["amount"])
        self.record("CB1", {"amount": 120})
        self.assertEqual("REFUSE", self.evaluate()["disposition"])

    def test_goodwill_review_cannot_supply_missing_tool_authority(self):
        self.record("CL4", {"claimant": "K2", "order": "ORD2", "basis": "goodwill", "amount": 40}, "claim")
        request = {"claim": "CL4", "amount": 40, "to": "K2_card", "basis": "goodwill"}
        self.assertEqual("REFER", self.evaluate(request)["disposition"])
        self.record("RES1", {"question": "goodwill_approval", "about": "CL4", "answer": "approve", "by": "F"}, "resolution")
        self.assertEqual("PERMIT", self.evaluate(request)["disposition"])
        self.grant("G1", status="revoked")
        result = self.evaluate(request)
        self.assertEqual("REFUSE", result["disposition"])
        self.assertEqual("AU1", result["rule"])

    def test_missing_citation_refuses_existing_contradiction_prohibits(self):
        request = {"to": "K1", "claim": "CL1", "amount": 120, "template": "refund_issued", "cites": "REF1"}
        self.assertEqual("REFUSE", self.evaluate(request, tool="message_party")["disposition"])
        self.record("REF1", {"claim": "CL1", "claimant": "K1", "order": "ORD1", "amount": 120, "currency": "USD", "settled": False}, "refund")
        self.assertEqual("PROHIBIT", self.evaluate(request, tool="message_party")["disposition"])
        self.record("REF1", {"settled": True})
        self.assertEqual("PERMIT", self.evaluate(request, tool="message_party")["disposition"])

    def test_each_settlement_binding_dimension_is_required(self):
        base = {"claim": "CL1", "claimant": "K1", "order": "ORD1", "amount": 120, "currency": "USD", "settled": True}
        request = {"to": "K1", "claim": "CL1", "amount": 120, "template": "refund_issued", "cites": "REF1"}
        for change in ({"claim": "CL2"}, {"claimant": "K2"}, {"order": "ORD2"}, {"amount": 60}, {"currency": "EUR"}, {"settled": False}, {"allocated_to": "another duty"}):
            with self.subTest(change=change):
                self.state["records"]["REF1"] = []
                self.record("REF1", dict(base, **change), "refund")
                self.assertEqual("PROHIBIT", self.evaluate(request, tool="message_party")["disposition"])

    def test_denial_citation_uses_basis_and_respects_current_supported_remainder(self):
        request = {"to": "K1", "claim": "CL1", "amount": 120, "template": "refund_denied", "basis": "RET1"}
        self.assertEqual("PERMIT", self.evaluate(request, tool="message_party")["disposition"])
        self.record("RET1", {"received": True})
        self.assertEqual("PROHIBIT", self.evaluate(request, tool="message_party")["disposition"])
        request["basis"] = "NONE"
        self.assertEqual("REFUSE", self.evaluate(request, tool="message_party")["disposition"])

    def test_all_unresolved_duties_block_closure_even_not_overdue(self):
        self.state["duties"]["D_resolve(CL1)"] = [{"kind": "resolve", "claim": "CL1", "owner": "A", "resolution": "unresolved", "due": 21, "timing": "on_time"}]
        result = self.evaluate({"case": "CL1"}, tool="close_case")
        self.assertEqual("REFUSE", result["disposition"])
        self.assertEqual("D_resolve(CL1) unresolved", result["reason"])
        self.state["duties"]["D_resolve(CL1)"][-1]["resolution"] = "discharged"
        self.assertEqual("PERMIT", self.evaluate({"case": "CL1"}, tool="close_case")["disposition"])

    def test_rejections_precede_evaluation_and_no_rule_registered_act_refers(self):
        self.assertFalse(self.evaluate({}, tool="invented")["evaluated"])
        self.assertFalse(self.evaluate(dict(self.args, issuer="F"))["evaluated"])
        self.assertEqual("REFER", self.evaluate({"customer": "K1"}, tool="export_records")["disposition"])
        for amount in (True, False, -1, 0, 1.2, float("inf"), float("nan")):
            self.assertFalse(arguments_valid("issue_refund", dict(self.args, amount=amount)))


if __name__ == "__main__":
    unittest.main()
