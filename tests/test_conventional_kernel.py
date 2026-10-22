"""Component tests only: these do not establish W0 comparator acceptance."""
from copy import deepcopy
import hashlib
import hmac
from pathlib import Path
import sqlite3
import unittest

from conventional_gateway.kernel import Authentication, FAULTS, Kernel, Session, Store, encode


KEY = b"offline-independent-sql-tests-key!"


class RelationalKernelTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(KEY)
        self.auth = Authentication(KEY)
        self.a = self.auth.session("A", ["act"])
        self.b = self.auth.session("B", ["act"])
        self.source = self.auth.session("warehouse", ["record"])
        self.agent_record = self.auth.session("A", ["record"])
        self.policy_live = True
        self.effect_amount = 120

        def authorize(view, actor, tool, args):
            return self.policy_live and actor == "A" and tool == "refund" and args == {"amount": 120}

        def stage(view, actor, tool, args):
            return [{"relation": "records", "id": "REF1", "payload": {
                "kind": "refund", "writer": "executor", "evidential": True,
                "fields": {"amount": self.effect_amount, "to": "K1_card", "settled": True}}}]

        def duties(store):
            store.append("duties", "D_refund(CL1)", {"owner": "A", "claimant": "K1", "resolution": "discharged"})

        self.kernel = Kernel(self.store, self.auth, authorize, stage, duties)
        self.boundary = {
            "return_receipt": {"create": ["warehouse"], "correct": {"warehouse": ["received", "condition"]}},
            "agent_note": {"create": ["any_agent"], "evidential": False}}

    def envelope(self, *, operation="create", fields=None, sender=None, message="M1", kind="return_receipt", record="RET1"):
        return self.auth.envelope(sender or self.source, "record", "records", self.store.step,
                                  {"record": record, "kind": kind, "operation": operation,
                                   "fields": {"received": False} if fields is None else fields}, message)

    def handle(self, **kwargs):
        return self.kernel.issue(self.a, "refund", {"amount": 120}, **kwargs)

    def test_fresh_store_and_checkpoint_roundtrip_preserve_actual_history(self):
        self.store.source_write(self.auth, self.envelope(), self.boundary)
        self.store.source_write(self.auth, self.envelope(operation="correct", fields={"received": True}, message="M2"), self.boundary)
        restored = Store(KEY, checkpoint=self.store.checkpoint())
        self.assertEqual(self.store.snapshot(), restored.snapshot())
        self.assertEqual(self.store.events(), restored.events())
        self.assertFalse(restored.versions("records")["RET1"][0]["fields"]["received"])
        self.assertTrue(restored.current("records")["RET1"]["fields"]["received"])

    def test_checkpoint_authentication_detects_hidden_change_and_truncation(self):
        self.store.source_write(self.auth, self.envelope(), self.boundary)
        original = self.store.checkpoint()
        for mutate in (lambda c: c["relations"]["records"][0].__setitem__(2, '{}'),
                       lambda c: c["events"].pop(), lambda c: c.__setitem__("epoch", 0)):
            changed = deepcopy(original)
            mutate(changed)
            with self.assertRaises(PermissionError):
                Store(KEY, checkpoint=changed)

    def test_chain_is_checked_even_with_authentic_checkpoint(self):
        self.store.audit("test", {})
        pin = self.store.checkpoint()
        pin["events"][0]["previous"] = "f" * 64
        pin.pop("signature")
        pin["signature"] = hmac.new(KEY, encode(pin).encode(), "sha256").hexdigest()
        with self.assertRaisesRegex(ValueError, "chain"):
            Store(KEY, checkpoint=pin)

    def test_sql_forbids_rewriting_and_deleting_record_and_duty_history(self):
        self.store.source_write(self.auth, self.envelope(), self.boundary)
        with self.store.transaction():
            self.store.append("duties", "D1", {"resolution": "unresolved"})
        for table in ("records", "duties"):
            for sql in (f"UPDATE {table} SET payload='{{}}'", f"DELETE FROM {table}"):
                with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
                    self.store._db.execute(sql)

    def test_writes_require_one_transaction_and_cannot_be_nested(self):
        with self.assertRaises(RuntimeError):
            self.store.append("records", "BAD", {})
        with self.assertRaises(RuntimeError):
            self.store._advance()
        with self.store.transaction():
            with self.assertRaises(RuntimeError):
                with self.store.transaction():
                    pass
        self.assertEqual(0, self.store.epoch)

    def test_envelope_sender_cannot_be_substituted_or_payload_modified(self):
        for change in ({"sender": "A"}, {"recipient": "elsewhere"}, {"payload": {}}):
            before = self.store.snapshot()
            bad = dict(self.envelope(), **change)
            with self.assertRaises(PermissionError):
                self.store.source_write(self.auth, bad, self.boundary)
            self.assertEqual(before, self.store.snapshot())

    def test_sessions_cannot_claim_channel_and_future_envelope_cannot_enter(self):
        with self.assertRaises(PermissionError):
            self.auth.envelope(self.a, "record", "records", 0, {}, "forged")
        with self.assertRaises(PermissionError):
            self.auth.identity(Session("invented"), "act")
        future = self.auth.envelope(self.source, "record", "records", 1, {}, "future")
        with self.assertRaises(PermissionError):
            self.store.source_write(self.auth, future, self.boundary)

    def test_record_create_correct_and_field_rights_are_distinct(self):
        self.store.source_write(self.auth, self.envelope(), self.boundary)
        before = self.store.snapshot()
        for env in (self.envelope(operation="create", message="M2"),
                    self.envelope(operation="correct", fields={"order": "ORD2"}, message="M3"),
                    self.envelope(operation="correct", fields={"received": True}, sender=self.agent_record, message="M4")):
            with self.assertRaises(PermissionError):
                self.store.source_write(self.auth, env, self.boundary, agents=["A"])
            self.assertEqual(before, self.store.snapshot())
        self.store.source_write(self.auth, self.envelope(operation="correct", fields={"received": True}, message="M5"), self.boundary)
        self.assertEqual(2, len(self.store.versions("records")["RET1"]))

    def test_source_cannot_choose_evidential_or_promote_agent_note(self):
        env = self.envelope(kind="agent_note", record="N1", fields={"received": True}, sender=self.agent_record)
        self.store.source_write(self.auth, env, self.boundary, agents=["A"])
        self.assertFalse(self.store.current("records")["N1"]["evidential"])
        env = self.envelope(message="M2")
        payload = dict(env["payload"], evidential=True)
        env = self.auth.envelope(self.source, "record", "records", 0, payload, "M2")
        with self.assertRaises(PermissionError):
            self.store.source_write(self.auth, env, self.boundary)

    def test_duplicate_envelope_rolls_back_without_extra_version(self):
        env = self.envelope()
        self.store.source_write(self.auth, env, self.boundary)
        before = self.store.snapshot()
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.source_write(self.auth, env, self.boundary)
        self.assertEqual(before, self.store.snapshot())

    def test_epoch_changes_once_for_batch_and_insert_voids_all_handles(self):
        first, second = self.handle(), self.handle()
        before = self.store.epoch
        with self.store.transaction():
            self.store.append("records", "ONE", {"kind": "record"})
            self.store.append("records", "TWO", {"kind": "record"})
        self.assertEqual(before + 1, self.store.epoch)
        self.assertEqual(["void", "void"], [self.store.current("handles")[h]["status"] for h in (first, second)])
        self.assertEqual("stale_epoch", self.kernel.execute(self.a, first)["reason"])

    def test_issuance_and_audit_do_not_invalidate_handle(self):
        hid = self.handle()
        self.store.audit("diagnostic", {})
        self.assertEqual(0, self.store.epoch)
        self.assertEqual("live", self.store.current("handles")[hid]["status"])

    def test_plain_tick_and_exact_live_handle_expiry(self):
        hid = self.handle(lifetime=3)
        self.store.clock(2)
        self.assertEqual(0, self.store.epoch)
        self.assertEqual("live", self.store.current("handles")[hid]["status"])
        self.store.clock(3)
        self.assertEqual(1, self.store.epoch)
        self.assertEqual("expired", self.store.current("handles")[hid]["status"])
        self.assertEqual("expired_handle", self.kernel.execute(self.a, hid)["reason"])
        self.store.clock(4)
        self.assertEqual(1, self.store.epoch)

    def test_authenticated_actor_and_exact_arguments_are_bound(self):
        hid = self.handle()
        before = self.store.snapshot()
        self.assertEqual("wrong_actor", self.kernel.execute(self.b, hid)["reason"])
        altered = self.kernel.execute(self.a, hid, args={"amount": 120.0})
        self.assertFalse(altered["committed"])
        self.assertEqual("argument_mismatch", altered["reason"])
        self.assertEqual("argument_mismatch", self.kernel.execute(self.a, hid, tool="message")["reason"])
        self.assertEqual(before, self.store.snapshot())
        self.assertEqual("live", self.store.current("handles")[hid]["status"])

    def test_policy_is_rechecked_inside_transaction(self):
        hid = self.handle()
        self.policy_live = False
        result = self.kernel.execute(self.a, hid)
        self.assertEqual("current_policy_refused", result["reason"])
        self.assertEqual({}, self.store.current("records"))
        self.assertEqual("live", self.store.current("handles")[hid]["status"])

    def test_changed_staged_effect_never_commits(self):
        hid = self.handle()
        self.effect_amount = 121
        self.assertEqual("effect_changed", self.kernel.execute(self.a, hid)["reason"])
        self.assertEqual({}, self.store.current("records"))

    def test_atomic_effect_consumption_duties_receipt_and_pre_epoch(self):
        hid, other = self.handle(), self.handle()
        result = self.kernel.execute(self.a, hid)
        self.assertTrue(result["committed"])
        self.assertEqual(0, result["receipt"]["pre_transaction_epoch"])
        self.assertEqual(1, self.store.epoch)
        self.assertEqual("consumed", self.store.current("handles")[hid]["status"])
        self.assertEqual("void", self.store.current("handles")[other]["status"])
        self.assertEqual("discharged", self.store.current("duties")["D_refund(CL1)"]["resolution"])
        self.assertEqual(120, self.store.current("records")["REF1"]["fields"]["amount"])
        self.assertEqual(1, len(self.store.current("receipts")))
        replayed = {}
        for event in self.store.events():
            if event["kind"] == "version_written":
                row = event["payload"]
                replayed.setdefault(row["relation"], {}).setdefault(row["id"], []).append(row["payload"])
        for table in ("records", "handles", "duties", "receipts"):
            self.assertEqual(self.store.versions(table), replayed[table])
        self.assertFalse(self.kernel.execute(self.a, hid)["committed"])

    def test_every_fault_rolls_back_actual_partial_sql_and_can_retry(self):
        for point in FAULTS:
            with self.subTest(point=point):
                self.setUp()
                hid = self.handle()
                other = self.handle()
                before = self.store.snapshot()
                result = self.kernel.execute(self.a, hid, fault=point)
                self.assertFalse(result["committed"])
                self.assertEqual(before, self.store.snapshot())
                partial = result["partial_transaction"]
                if point != "after_validate":
                    self.assertEqual(hid, partial["staged"][0][0])
                if point in FAULTS[2:]:
                    self.assertIn("REF1", partial["state"]["records"])
                if point in FAULTS[3:]:
                    self.assertEqual("consumed", partial["state"]["handles"][hid][-1]["status"])
                if point in FAULTS[4:]:
                    self.assertIn("D_refund(CL1)", partial["state"]["duties"])
                if point in FAULTS[5:]:
                    self.assertIn(hid, partial["state"]["receipts"])
                if point == "during_revision_advance":
                    self.assertEqual(before["epoch"] + 1, partial["state"]["epoch"])
                    self.assertEqual("void", partial["state"]["handles"][other][-1]["status"])
                self.assertEqual("live", self.store.current("handles")[other]["status"])
                self.assertEqual("execution_refused", self.store.events()[-1]["kind"])
                self.assertTrue(self.kernel.execute(self.a, hid)["committed"])

    def test_read_callbacks_cannot_mutate_store_by_editing_snapshot(self):
        def dishonest(view, *args):
            view["records"]["HIDDEN"] = [{"kind": "refund"}]
            return False
        kernel = Kernel(self.store, self.auth, dishonest, lambda *a: [])
        self.assertIsNone(kernel.issue(self.a, "refund", {}))
        self.assertNotIn("HIDDEN", self.store.current("records"))
        self.assertEqual(0, self.store.epoch)

    def test_effects_cannot_issue_handles_or_replace_receipts(self):
        for relation in ("handles", "receipts", "decisions"):
            kernel = Kernel(self.store, self.auth, lambda *a: True,
                            lambda *a: [{"relation": relation, "id": "HIDDEN", "payload": {}}])
            with self.assertRaises(ValueError):
                kernel.issue(self.a, "anything", {})
        self.assertEqual({}, self.store.current("handles"))

    def test_no_policy_or_transaction_imports_from_either_existing_arm(self):
        import ast
        root = Path(__file__).parents[1] / "conventional_gateway"
        for path in root.rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                modules = [node.module] if isinstance(node, ast.ImportFrom) else [n.name for n in node.names] if isinstance(node, ast.Import) else []
                self.assertFalse(any(m and m.split(".")[0] in ("taa_gateway", "taa_gateway_reference") for m in modules))


if __name__ == "__main__":
    unittest.main()
