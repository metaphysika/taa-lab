"""Negative controls beyond the independent bundle; not new expected fixtures."""
from copy import deepcopy
import unittest

from taa_gateway_reference import refunds as reference
from taa_gateway.records import RecordStore, Write
from taa_gateway.resolutions import StoredResolutions
from taa_gateway import SCHEMA_VERSION as V
from tests import test_gateway_foundation as foundation
from tests.trace_support.bundle import world


class FoundationAlignmentTests(unittest.TestCase):
    setUp = foundation.FoundationTests.setUp
    delivery = foundation.FoundationTests.delivery
    order = foundation.FoundationTests.order
    proposal = foundation.FoundationTests.proposal
    def test_create_does_not_grant_field_correction_rights(self):
        policy = deepcopy(self.policy)
        policy["writers"][0]["correct_fields"] = []
        store = RecordStore(self.auth, self.log, policy)
        store.publish(self.external, "carrier_update", [self.delivery()])
        before = store.snapshot()
        with self.assertRaises(ValueError):
            store.publish(self.external, "carrier_update", [self.delivery(False)])
        self.assertEqual(store.snapshot(), before)

    def test_correction_permission_cannot_create(self):
        policy = deepcopy(self.policy)
        policy["writers"][0]["create"] = False
        store = RecordStore(self.auth, self.log, policy)
        with self.assertRaises(ValueError):
            store.publish(self.external, "carrier_update", [self.delivery()])
        self.assertIsNone(store.read("delivery-1"))

    def test_correction_cannot_add_immutable_fields(self):
        self.store.publish(self.external, "carrier_update", [self.delivery()])
        with self.assertRaises(ValueError):
            self.store.publish(self.external, "carrier_update", [Write("delivery-1", "delivery", {"delivered": False, "order": "OTHER"})])
        self.assertTrue(self.store.read("delivery-1")["fields"]["delivered"])

    def test_rejected_resolution_logs_only_without_invalidation(self):
        inbox = StoredResolutions(self.store, self.auth, self.gateway,
                                  {"reserved": {"jurisdiction": "claims", "reviewers": ["finance"]}})
        for question in ("unreserved", "reserved"):
            envelope = self.auth.issue(self.lead, "gateway", 0, "resolution", {
                "question_id": question, "jurisdiction": "claims", "answer": {"decision": "approve"}, "basis": []})
            inbox.receive(envelope)
            self.assertIsNone(self.store.read(envelope["message_id"]))
        self.assertEqual(self.store.revision, 0)
        self.assertEqual([e["type"] for e in self.log.events()], ["rejected_resolution", "rejected_resolution"])

    def test_order_context_does_not_attribute_an_added_assertion(self):
        envelope = self.order()
        self.orders.receive(envelope)
        related = self.proposal(arguments={"claim_id": "C1", "amount_minor": 500, "asserts": ["false"]})["related_orders"]
        self.assertEqual(len(related), 1)
        self.assertFalse(self.orders.requested_by(related[0], "issue_refund", {"claim_id": "C1"}, "false"))

    def test_grant_expiry_boundary_advances_once_and_later_tick_does_not(self):
        policy = deepcopy(self.policy)
        policy["writers"].append({"kind": "grant", "tool": "carrier_update", "channel": "external",
                                  "principals": ["carrier"], "evidential": True, "id_prefix": "grant-",
                                  "create": True, "correct_fields": ["status"]})
        store = RecordStore(self.auth, self.log, policy)
        grant = {"schema_version": V, "id": "grant-G1", "parent_grant": None, "grantor": "carrier", "grantee": "agent",
                 "action_types": ["read"], "resource_scope": {}, "limits": {}, "purpose_id": "P", "live_conditions": [],
                 "expires_at_step": 3, "status": "live"}
        store.publish(self.external, "carrier_update", [Write("grant-G1", "grant", grant)])
        store.publish(self.gateway, "advance_clock", step=2)
        self.assertEqual(store.revision, 1)
        store.publish(self.gateway, "advance_clock", step=3)
        self.assertEqual(store.revision, 2)
        store.publish(self.gateway, "advance_clock", step=4)
        self.assertEqual(store.revision, 2)

    def test_plain_clock_tick_has_no_revision_change(self):
        before = self.store.revision
        self.store.publish(self.gateway, "advance_clock", step=10)
        self.assertEqual(self.store.revision, before)
        self.assertEqual(self.store.step, 10)


class RefundReferenceControls(unittest.TestCase):
    def test_plain_tick_preserves_token_but_live_expiry_invalidates_all(self):
        s = reference.start(world(), {"records": {"RET1": {"received": True}}})
        s, first = reference.propose(s, "A", "issue_refund", {"claim": "CL1", "amount": 120, "to": "K1_card", "basis": "return"})
        revision = s["revision"]
        s = reference.advance(s, 2)
        self.assertEqual(s["revision"], revision)
        self.assertEqual(s["tokens"][first["token"]]["status"], "live")
        s, second = reference.propose(s, "A", "read_record", {"record": "PAY1"})
        s = reference.advance(s, 11)
        self.assertGreater(s["revision"], revision)
        self.assertEqual(s["tokens"][first["token"]]["status"], "expired")
        self.assertEqual(s["tokens"][second["token"]]["status"], "void")

    def test_unrelated_evidence_cannot_release_a_duty_or_justify_denial(self):
        s = reference.start(world())
        revised, result = reference.apply_event(s, {"type": "resolution", "question": "release_determination", "about": "D_resolve(CL1)",
                                                  "by": "F", "via": "reviewer_interface", "answer": "release", "basis": "other order", "evidence": "DEL2"})
        self.assertTrue(result["resolution_rejected"])
        self.assertEqual(revised["revision"], s["revision"])
        _, decision = reference.propose(s, "A", "message_party", {"to": "K1", "template": "refund_denied", "claim": "CL1", "amount": 120, "basis": "DEL2"})
        self.assertEqual(decision["disposition"], "REFUSE")

    def test_correction_cannot_change_carrier_order_identity(self):
        s = reference.start(world())
        before = deepcopy(s)
        with self.assertRaises(ValueError):
            reference.apply_event(s, {"type": "record_correction", "record": "DEL2", "by": "carrier", "new": {"order": "ORD1"}})
        self.assertEqual(s, before)

    def test_external_event_phase_precedes_duty_derivation(self):
        s = reference.start(world())
        # At step 2 both changes arrive before the engine runs: no transient
        # refund duty may be created from the first event's temporary value.
        s, _ = reference.enter_step(s, 2, [
            {"type": "record_correction", "record": "RET1", "by": "warehouse", "new": {"received": True}},
            {"type": "record_correction", "record": "RET1", "by": "warehouse", "new": {"received": False}}])
        self.assertNotIn("D_refund(CL1,120)", s["duties"])


if __name__ == "__main__":
    unittest.main()
