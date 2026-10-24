"""Sol-authored W0/Q1–Q13 component checks; independent review pending."""
import unittest

from conventional_gateway.kernel import Store, Kernel, Authentication
from conventional_gateway.ledger import Ledger
from conventional_gateway.policy import Policy
from tests.trace_support.bundle import world


class LedgerComponentTests(unittest.TestCase):
    def setUp(self):
        self.world = world()
        self.store = Store(b"independent-conventional-ledger-test")
        self.policy = Policy(self.world)
        self.engine = Ledger(self.policy)
        with self.store.transaction():
            for rid, source in self.world["records"].items():
                fields = dict(source)
                kind = fields.pop("kind")
                self.store.append("records", rid, {"kind": kind, "fields": fields, "writer": "setup", "evidential": True}, relevant=False)
            for gid, grant in self.world["grants"].items():
                self.store.append("grants", gid, grant, relevant=False)
        self.tick(1)

    def tick(self, step):
        self.store.clock(step)
        with self.store.transaction():
            self.engine.stabilize(self.store)

    def record(self, rid, fields, kind=None):
        row = self.store.current("records").get(rid, {"kind": kind, "fields": {}, "writer": "test", "evidential": True})
        row["fields"].update(fields)
        with self.store.transaction():
            self.store.append("records", rid, row)
            self.engine.stabilize(self.store)

    def revoke(self):
        grant = self.store.current("grants")["G1"]
        grant["status"] = "revoked"
        with self.store.transaction():
            self.store.append("grants", "G1", grant)
            self.engine.stabilize(self.store)

    def offer(self, to):
        with self.store.transaction():
            self.engine.offer(self.store, "A", "D_resolve(CL1)", to)

    def duty(self, did="D_resolve(CL1)"):
        return self.store.current("duties")[did]

    def settled(self):
        self.record("RET1", {"received": True})
        self.record("REF1", {"claim": "CL1", "claimant": "K1", "order": "ORD1", "amount": 120,
                             "currency": "USD", "settled": True, "to": "K1_card"}, "refund")

    def test_initial_claim_due_and_true_fixed_point(self):
        self.assertEqual(21, self.duty()["due"])
        self.assertEqual("unresolved", self.duty()["resolution"])
        before = self.store.snapshot()
        with self.store.transaction():
            self.engine.stabilize(self.store)
        self.assertEqual(before, self.store.snapshot())

    def test_unknown_or_false_support_never_extinguishes_existing_refund(self):
        self.record("RET1", {"received": True})
        did = "D_refund(CL1,120)"
        self.assertEqual("unresolved", self.duty(did)["resolution"])
        self.record("RET1", {"received": False})
        self.assertEqual("unresolved", self.duty(did)["resolution"])

    def test_resolve_needs_notice_and_each_settlement_counts_once(self):
        self.settled()
        self.assertEqual("discharged", self.duty("D_refund(CL1,120)")["resolution"])
        self.assertEqual("unresolved", self.duty()["resolution"])
        auth = Authentication(b"independent-conventional-ledger-test")
        session = auth.session("A", ("act",))
        def stage(snapshot, actor, tool, args):
            self.assertEqual(tool, "message_party")
            return [{"relation": "notices", "id": "N" + str(len(snapshot["notices"]) + 1), "payload": dict(args)}]
        kernel = Kernel(self.store, auth,
            lambda snapshot, actor, tool, args: self.policy.evaluate(snapshot, actor, tool, args)["disposition"] == "PERMIT",
            stage, self.engine.stabilize)
        def committed_notice():
            args = {"to": "K1", "claim": "CL1", "amount": 120, "template": "refund_issued", "cites": "REF1"}
            handle = kernel.issue(session, "message_party", args)
            self.assertIsNotNone(handle)
            self.assertTrue(kernel.execute(session, handle)["committed"])
        committed_notice()
        self.assertEqual("discharged", self.duty()["resolution"])
        self.record("CL1", {"amount": 240})
        committed_notice()
        proof = self.engine._resolve_proof(self.store, self.duty())
        self.assertIsNone(proof)
        self.assertEqual(120, self.duty()["coverage"])

    def test_settlement_correction_reopens_closed_case_immediately_overdue(self):
        self.settled()
        self.tick(21)
        with self.store.transaction():
            self.store.append("cases", "CL1", {"closed": True})
        self.record("REF1", {"settled": False})
        row = self.duty("D_refund(CL1,120)")
        self.assertEqual("unresolved", row["resolution"])
        self.assertTrue(row["overdue"])
        self.assertIn("reopened@21", row["history"])
        self.assertEqual("REF1@v2", row["reopening_cites"])
        self.assertFalse(self.store.current("cases")["CL1"]["closed"])

    def test_offer_acceptance_last_valid_step_and_exact_deadline(self):
        self.tick(2)
        self.offer("F")
        self.tick(6)
        with self.store.transaction():
            self.assertTrue(self.engine.accept(self.store, "F", "D_resolve(CL1)"))
        self.assertEqual("F", self.duty()["owner"])
        self.setUp()
        self.tick(2)
        self.offer("F")
        self.store.clock(7)
        with self.store.transaction():
            self.assertFalse(self.engine.accept(self.store, "F", "D_resolve(CL1)"))
            self.engine.stabilize(self.store)
        self.assertEqual("A", self.duty()["owner"])
        self.assertIsNone(self.duty()["offered_to"])

    def test_fallback_window_never_resets_and_unowned_only_once(self):
        self.tick(2)
        self.offer("F")
        self.tick(3)
        self.revoke()
        self.assertEqual(7, self.duty()["offers"]["F"]["due"])
        self.tick(7)
        self.assertIsNone(self.duty()["owner"])
        report = self.duty("D_unowned_report(CL1)")
        self.assertEqual("L", report["recipient"])
        self.assertEqual(12, report["due"])
        before = self.store.snapshot()
        with self.store.transaction():
            self.engine.stabilize(self.store)
        self.assertEqual(before, self.store.snapshot())

    def test_q16_incapable_offeree_refused_then_capable_acceptance_closes_both(self):
        self.tick(2)
        self.offer("L")
        self.tick(3)
        self.revoke()
        row = self.duty()
        self.assertEqual(7, row["offers"]["L"]["due"])
        self.assertEqual(8, row["offers"]["F"]["due"])
        with self.store.transaction():
            self.assertFalse(self.engine.accept(self.store, "L", row["id"]))
            self.assertTrue(self.engine.accept(self.store, "F", row["id"]))
            self.engine.stabilize(self.store)
        self.assertEqual("F", self.duty()["owner"])
        self.assertFalse(any(o["active"] for o in self.duty()["offers"].values()))
        self.tick(8)
        self.assertEqual("F", self.duty()["owner"])

    def test_parallel_offers_wait_for_last_window_before_unowned(self):
        self.tick(2)
        self.offer("L")
        self.tick(3)
        self.revoke()
        self.tick(7)
        self.assertEqual("A", self.duty()["owner"])
        self.tick(8)
        self.assertIsNone(self.duty()["owner"])

    def test_report_repeat_preserves_both_deadlines_and_ack_binds_version(self):
        args = {"claim": "CL1", "amount": 120, "to": "K1_card", "basis": "return", "asserts": ["return received"]}
        check = self.policy.evaluate(self.store.snapshot(), "A", "issue_refund", args)["checks"]
        self.tick(2)
        with self.store.transaction():
            self.store.append("orders", "O1", {"from": "L", "to": "A", "requested_effects": [{"tool": "issue_refund", "claim": "CL1", "amount": 120, "asserts": ["return received"]}]})
            self.engine.report(self.store, "A", "issue_refund", args, check)
        before = self.duty("D_report(O1)")
        self.tick(3)
        with self.store.transaction():
            self.store.append("orders", "O2", {"from": "L", "to": "A", "requested_effects": [{"tool": "issue_refund", "claim": "CL1", "amount": 120, "asserts": ["return received"]}]})
            self.engine.report(self.store, "A", "issue_refund", args, check)
        after = self.duty("D_report(O1)")
        self.assertEqual((before["due"], before["route_due"]), (after["due"], after["route_due"]))
        with self.store.transaction():
            self.assertTrue(self.engine.acknowledgment(self.store, "C", "RPT1", 1)["acknowledgment_rejected"])
        self.tick(7)
        self.assertEqual("F", self.duty("D_report(O1)")["recipient"])
        with self.store.transaction():
            self.engine.acknowledgment(self.store, "F", "RPT1", 2)
        self.assertEqual("discharged", self.duty("D_report(O1)")["resolution"])

    def test_order_does_not_attribute_an_assertion_added_only_by_actor(self):
        self.record("RET1", {"received": True, "condition": "damaged"})
        args = {"claim": "CL1", "amount": 120, "to": "K1_card", "basis": "return", "asserts": ["item returned undamaged"]}
        checks = self.policy.evaluate(self.store.snapshot(), "A", "issue_refund", args)["checks"]
        with self.store.transaction():
            self.store.append("orders", "O1", {"from": "L", "to": "A", "requested_effects": [{"tool": "issue_refund", "claim": "CL1", "amount": 120, "asserts": []}]})
            result = self.engine.report(self.store, "A", "issue_refund", args, checks)
        self.assertEqual(["O1"], result["associated_orders"])
        self.assertEqual([], result["attributed_issuers"])
        self.assertEqual({}, self.store.current("reports"))


if __name__ == "__main__":
    unittest.main()
