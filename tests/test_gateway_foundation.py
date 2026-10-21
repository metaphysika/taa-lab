"""Stage 2 boundary tests, not gateway P1–P6 conformance or H3 evidence."""
import copy
import json
import unittest

from jsonschema import ValidationError

from taa_gateway import SCHEMA_VERSION as V
from taa_gateway.envelopes import Session, SimulatorAuthority
from taa_gateway.eventlog import EventLog, verify_jsonl
from taa_gateway.orders import StoredOrders
from taa_gateway.records import RecordStore, Write
from taa_gateway.resolutions import StoredResolutions
from taa_gateway.schema import validate
from taa_gateway.serialization import canonical, digest, parse_json

KEY = b"stage-two-simulator-test-only-key!"


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.auth = SimulatorAuthority(KEY)
        self.agent = self.auth.bind("agent", "agent", ["assert", "propose", "send_message"])
        self.external = self.auth.bind("carrier", "external", ["carrier_update", "send_message"])
        self.lead = self.auth.bind("lead", "external", ["send_message"])
        self.gateway = self.auth.bind("gateway", "gateway",
                                      ["advance_clock", "receive_order", "receive_resolution"])
        self.log = EventLog("foundation-test", KEY)
        self.policy = {"schema_version": V, "writers": [
            {"kind": "delivery", "tool": "carrier_update", "channel": "external",
             "principals": ["carrier"], "evidential": True},
            {"kind": "assertion", "tool": "assert", "channel": "agent",
             "principals": ["agent"], "evidential": False},
            {"kind": "stored_order", "tool": "receive_order", "channel": "gateway",
             "principals": ["gateway"], "evidential": True},
            {"kind": "resolution", "tool": "receive_resolution", "channel": "gateway",
             "principals": ["gateway"], "evidential": True}]}
        for policy in self.policy["writers"]:
            policy["id_prefix"] = {"stored_order": "order-"}.get(policy["kind"], policy["kind"] + "-")
        self.store = RecordStore(self.auth, self.log, self.policy)
        self.orders = StoredOrders(self.store, self.auth, self.gateway)

    def delivery(self, value=True):
        return Write("delivery-1", "delivery", {"delivered": value})

    def order(self, recipient="agent", claim="C1"):
        return self.auth.issue(self.lead, recipient, 0, "order", {
            "text": "Issue the refund", "scope": {"tool": "issue_refund", "arguments": {"claim_id": claim}}})

    def proposal(self, **claims):
        return self.orders.proposal(self.agent, {"tool": "issue_refund",
                                   "arguments": {"claim_id": "C1", "amount_minor": 500}, **claims})

    def test_versions_preserve_old_evidence(self):
        self.store.publish(self.external, "carrier_update", [self.delivery()])
        self.store.publish(self.external, "carrier_update", [self.delivery(False)])
        self.assertTrue(self.store.read("delivery-1", 1)["fields"]["delivered"])
        self.assertFalse(self.store.read("delivery-1")["fields"]["delivered"])
        self.assertEqual(self.store.revision, 2)

    def test_insertion_and_clock_share_revision_path(self):
        self.assertIsNone(self.store.read("delivery-1"))
        self.store.publish(self.external, "carrier_update", [self.delivery()])
        self.store.publish(self.gateway, "advance_clock", step=1)
        self.assertEqual((self.store.revision, self.store.step), (2, 1))
        self.assertEqual(self.log.events()[-1]["type"], "clock_change")

    def test_batch_advances_once_and_invalid_batch_changes_nothing(self):
        self.store.publish(self.external, "carrier_update", [self.delivery(),
                           Write("delivery-2", "delivery", {})])
        self.assertEqual(self.store.revision, 1)
        before, events = self.store.snapshot(), self.log.events()
        with self.assertRaises(ValueError):
            self.store.publish(self.external, "carrier_update", [self.delivery(False),
                               Write("fake", "payment", {})])
        self.assertEqual(self.store.snapshot(), before)
        self.assertEqual(self.log.events(), events)

    def test_returned_values_cannot_mutate_world_or_history(self):
        write = self.delivery()
        self.store.publish(self.external, "carrier_update", [write])
        write.fields["delivered"] = False
        self.store.read("delivery-1")["fields"]["delivered"] = False
        self.store.snapshot()["records"].clear()
        self.log.events()[0]["payload"].clear()
        self.policy["writers"].clear()
        self.assertTrue(self.store.read("delivery-1")["fields"]["delivered"])
        self.assertEqual(self.log.events()[0]["payload"]["record"]["id"], "delivery-1")

    def test_assertions_cannot_become_evidence(self):
        self.store.publish(self.agent, "assert", [Write("assertion-1", "assertion", {"delivered": True})])
        self.assertFalse(self.store.read("assertion-1")["evidential"])
        with self.assertRaises(ValueError):
            self.store.publish(self.agent, "assert", [self.delivery()])
        policy = copy.deepcopy(self.policy)
        policy["writers"][1]["evidential"] = True
        with self.assertRaises(ValueError):
            RecordStore(self.auth, self.log, policy)

    def test_forged_session_and_wrong_source_rejected(self):
        forged = Session(self.external.actor, self.external.channel, self.external.tools)
        with self.assertRaises(ValueError):
            self.store.publish(forged, "carrier_update", [self.delivery()])
        wrong = self.auth.bind("other-carrier", "external", ["carrier_update"])
        with self.assertRaises(ValueError):
            self.store.publish(wrong, "carrier_update", [self.delivery()])
        self.assertEqual(self.store.revision, 0)

    def test_stale_revision_and_invalid_clock_fail_without_mutation(self):
        self.store.publish(self.external, "carrier_update", [self.delivery()])
        with self.assertRaises(ValueError):
            self.store.publish(self.external, "carrier_update", [self.delivery(False)], expected_revision=0)
        with self.assertRaises(ValueError):
            self.store.publish(self.agent, "assert", step=1)
        with self.assertRaises(ValueError):
            self.store.publish(self.gateway, "advance_clock", step=-1)
        self.assertEqual(self.store.revision, 1)

    def test_sealed_log_rejects_write_before_state_changes(self):
        self.log.seal()
        with self.assertRaises(ValueError):
            self.store.publish(self.external, "carrier_update", [self.delivery()])
        self.assertEqual(self.store.revision, 0)
        self.assertIsNone(self.store.read("delivery-1"))

    def test_order_issuer_is_authenticated_not_claimed(self):
        order = self.order()
        order["authenticated_sender"] = "agent"
        with self.assertRaises(ValueError):
            self.orders.receive(order)
        self.assertEqual(self.store.revision, 0)

    def test_omitted_and_substituted_order_references_do_not_suppress_association(self):
        first, other = self.order(), self.order(claim="unrelated")
        self.orders.receive(first)
        self.orders.receive(other)
        for reference in (None, "invented-order", other["message_id"]):
            result = self.proposal(order_reference=reference)
            self.assertEqual([o["id"] for o in result["related_orders"]], [first["message_id"]])

    def test_actor_set_from_session_raw_claim_retained(self):
        self.orders.receive(self.order())
        result = self.proposal(acting_party="lead", claimed_reasons=["because I said so"])
        self.assertEqual(result["proposal"]["acting_party"], "agent")
        self.assertEqual(result["proposal"]["raw"]["acting_party"], "lead")
        self.assertEqual(len(result["related_orders"]), 1)

    def test_order_for_another_recipient_not_associated(self):
        self.orders.receive(self.order(recipient="other-agent"))
        self.assertEqual(self.proposal()["related_orders"], [])

    def test_replayed_or_future_order_rejected(self):
        envelope = self.order()
        self.orders.receive(envelope)
        with self.assertRaises(ValueError):
            self.orders.receive(envelope)
        future = self.auth.issue(self.lead, "agent", 1, "order", envelope["content"])
        with self.assertRaises(ValueError):
            self.orders.receive(future)

    def test_resolution_written_as_record_never_permission(self):
        inbox = StoredResolutions(self.store, self.auth, self.gateway)
        envelope = self.auth.issue(self.lead, "gateway", 0, "resolution", {
            "question_id": "Q1", "jurisdiction": "refund review", "answer": {"finding": "PERMIT"}, "basis": []})
        inbox.receive(envelope)
        record = self.store.read(envelope["message_id"])
        self.assertEqual(record["kind"], "resolution")
        self.assertEqual(self.store.revision, 1)
        self.assertNotIn("token", record["fields"])

    def test_records_cannot_change_kind(self):
        self.store.publish(self.external, "carrier_update", [self.delivery()])
        with self.assertRaises(ValueError):
            self.store.publish(self.agent, "assert", [Write("delivery-1", "assertion", {})])

    def test_assertion_cannot_preempt_trusted_order_identity(self):
        envelope = self.order()
        with self.assertRaises(ValueError):
            self.store.publish(self.agent, "assert", [Write(envelope["message_id"], "assertion", {})])
        self.orders.receive(envelope)
        self.assertEqual(len(self.proposal()["related_orders"]), 1)


class EventChainTests(unittest.TestCase):
    def make_log(self):
        log = EventLog("episode", KEY)
        log.append(0, "proposal", {"amount_minor": 100})
        log.append(0, "record_version", {"id": "R1", "version": 1})
        return log

    def test_round_trip_and_determinism(self):
        first, second = self.make_log(), self.make_log()
        checkpoint = first.seal()
        second.seal()
        self.assertEqual(first.jsonl(), second.jsonl())
        self.assertEqual(len(verify_jsonl(first.jsonl(), KEY, checkpoint)), 2)

    def test_payload_edit_reorder_and_truncation_rejected(self):
        log = self.make_log()
        checkpoint = log.seal()
        blob = log.jsonl()
        rows = blob.splitlines(keepends=True)
        for changed in (blob.replace(b'100', b'101'), b''.join([rows[1], rows[0], rows[2]]),
                        b''.join(rows[:-1]), b''.join([rows[0], rows[2]])):
            with self.subTest(changed=changed), self.assertRaises((ValueError, ValidationError)):
                verify_jsonl(changed, KEY, checkpoint)

    def test_rehashed_log_cannot_replace_trusted_checkpoint(self):
        log = self.make_log()
        checkpoint = log.seal()
        other = EventLog("episode", KEY)
        other.append(0, "proposal", {"amount_minor": 999})
        other.seal()
        with self.assertRaises(ValueError):
            verify_jsonl(other.jsonl(), KEY, checkpoint)

    def test_wrong_key_and_duplicate_keys_fail(self):
        log = self.make_log()
        checkpoint = log.seal()
        with self.assertRaises(ValueError):
            verify_jsonl(log.jsonl(), b"different-simulator-key-32-bytes!", checkpoint)
        with self.assertRaises(ValueError):
            parse_json('{"sequence":0,"sequence":1}')

    def test_batch_validation_is_not_partial(self):
        log = self.make_log()
        before = log.events()
        with self.assertRaises(ValidationError):
            log.append_many([(1, "valid", {}), (-1, "invalid", {})])
        self.assertEqual(log.events(), before)

    def test_log_does_not_change_state_revision(self):
        auth = SimulatorAuthority(KEY)
        log = self.make_log()
        store = RecordStore(auth, log, {"schema_version": V, "writers": []})
        log.append(0, "proposal", {})
        self.assertEqual(store.revision, 0)


class WireContractTests(unittest.TestCase):
    def test_rejects_non_json_and_wrong_primitive_types(self):
        for value in ({1: "key"}, {"a": float("nan")}, {"a": (1, 2)}):
            with self.assertRaises(ValueError):
                canonical(value)
        token = {"schema_version": V, "id": "T1", "warrant_id": "W1", "acting_party": "agent",
                 "exact_argument_digest": digest({}), "state_revision": True, "expires_at_step": 2}
        with self.assertRaises(ValidationError):
            validate("token", token)

    def test_unknown_is_distinct_and_token_fields_are_required(self):
        validate("rule_result", "unknown")
        with self.assertRaises(ValidationError):
            validate("rule_result", False)
        with self.assertRaises(ValidationError):
            validate("token", {"schema_version": V, "id": "T1"})

    def test_all_published_definitions_are_valid_schemas(self):
        from pathlib import Path
        from jsonschema import Draft202012Validator
        schemas = json.loads((Path(__file__).parents[1] / "taa_gateway/schema/objects.json").read_text())
        Draft202012Validator.check_schema(schemas)
        self.assertTrue({"record", "envelope", "stored_order", "resolution", "token", "duty",
                         "receipt", "event", "checkpoint", "write_policy"} <= set(schemas["$defs"]))


if __name__ == "__main__":
    unittest.main()
