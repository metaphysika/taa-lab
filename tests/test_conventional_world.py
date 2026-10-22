"""Sol-authored SQL host/observation controls; Claude review pending."""
from copy import deepcopy
import unittest

from conventional_gateway import backend
from conventional_gateway.world import World
from tests.trace_support.bundle import world
from tests.trace_support.state_observations import Observer


class SQLWorldTests(unittest.TestCase):
    def setUp(self):
        self.state = backend.start(world(), {"records": {"RET1": {"received": True}}})
        self.args = {"claim": "CL1", "amount": 120, "to": "K1_card", "basis": "return"}

    def test_cp_authentication_rejects_hidden_state_change(self):
        bad = deepcopy(self.state)
        bad["relational_checkpoint"]["epoch"] += 1
        with self.assertRaises(PermissionError):
            World(public=bad)

    def test_rejected_calls_audit_without_changing_revision_or_native_domain(self):
        before = deepcopy(self.state)
        after, result = backend.propose(before, "A", "issue_refund", dict(self.args, issuer="F"))
        self.assertEqual("rejected_arguments", result["call_result"])
        self.assertEqual(before["revision"], after["revision"])
        self.assertEqual(before["relational_checkpoint"], after["relational_checkpoint"])
        self.assertNotEqual(before["log"], after["log"])
        after, result = backend.propose(after, "A", "write_record", {})
        self.assertEqual("rejected_unregistered_tool", result["call_result"])
        self.assertEqual(before["relational_checkpoint"], after["relational_checkpoint"])

    def test_refund_service_cannot_commit_wrong_route_even_if_stage_function_is_wrong(self):
        host = World(public=self.state)
        original = host.kernel.stage
        def wrong(view, actor, tool, args):
            rows = original(view, actor, tool, args)
            rows[0]["payload"]["fields"]["to"] = "account_X"
            return rows
        host.kernel.stage = wrong
        answer = host.propose("A", "issue_refund", self.args)
        self.assertEqual("REFUSE", answer["disposition"])
        self.assertEqual("effect_plan_invalid", answer["reason"])
        self.assertEqual({}, host.store.current("handles"))
        self.assertNotIn("REF1", host.store.current("records"))

    def test_wrong_actor_uses_real_session_and_preserves_handle(self):
        state, decision = backend.propose(self.state, "A", "issue_refund", self.args)
        after, answer = backend.execute(state, "B", decision["token"])
        self.assertEqual("refused_wrong_actor", answer["execute_result"])
        self.assertEqual(state["relational_checkpoint"], after["relational_checkpoint"])
        self.assertEqual("live", after["tokens"][decision["token"]]["status"])

    def test_report_service_cannot_substitute_a_financial_notice(self):
        host = World(public=self.state)
        original = host.kernel.stage
        def wrong(view, actor, tool, args):
            rows = original(view, actor, tool, args)
            rows[0]["payload"].update(template="refund_issued", claim="CL1", amount=120, cites="MISSING")
            return rows
        host.kernel.stage = wrong
        answer = host.propose("A", "report", {"to": "K1"})
        self.assertEqual("REFUSE", answer["disposition"])
        self.assertEqual("effect_plan_invalid", answer["reason"])
        self.assertEqual({}, host.store.current("handles"))

    def test_offer_execution_uses_execution_step_not_proposal_step(self):
        state = backend.advance(self.state, 2)
        state, proposal = backend.propose(state, "A", "offer_duty", {"duty": "D_resolve(CL1)", "to": "F"})
        state = backend.advance(state, 3)
        state, result = backend.execute(state, "A", proposal["token"])
        self.assertEqual("committed", result["execute_result"])
        self.assertEqual(8, state["duties"]["D_resolve(CL1)"]["offers"]["F"]["due"])

    def test_serialization_preserves_offer_creation_order_even_same_step(self):
        state = backend.advance(self.state, 2)
        for target in ("L", "F"):
            state, proposal = backend.propose(state, "A", "offer_duty", {"duty": "D_resolve(CL1)", "to": target})
            state, result = backend.execute(state, "A", proposal["token"])
            self.assertEqual("committed", result["execute_result"])
        state = World(public=state).public()
        self.assertEqual(["L", "F"], list(state["duties"]["D_resolve(CL1)"]["offers"]))

    def test_independent_observer_detects_hidden_raw_sql_when_public_view_lies(self):
        state, proposal = backend.propose(self.state, "A", "issue_refund", self.args)
        observer = Observer(state)
        after, result = backend.execute(state, "A", proposal["token"])
        after["records"].pop("REF1")  # Leave the real SQL row in the raw checkpoint.
        checks = observer.audit("hidden", state, after, result, agent=True, execute={"actor": "A", "token": proposal["token"]})
        self.assertTrue(any(c["assertion"].endswith("sql_projection.records") and c["status"] == "discrepancy" for c in checks))

    def test_rejected_reviewer_answers_do_not_void_a_live_handle(self):
        state, proposal = backend.propose(self.state, "A", "issue_refund", self.args)
        revision = state["revision"]
        for source in ({"type": "resolution", "question": "pay CL1?", "about": "CL1", "answer": "approve", "by": "F", "via": "reviewer_interface"},
                       {"type": "resolution", "question": "goodwill_approval", "about": "CL1", "answer": "approve", "by": "L", "via": "reviewer_interface"}):
            before_records = deepcopy(state["records"])
            state, result = backend.apply_event(state, source)
            self.assertTrue(result["resolution_rejected"])
            self.assertEqual(revision, state["revision"])
            self.assertEqual(before_records, state["records"])
            self.assertEqual("live", state["tokens"][proposal["token"]]["status"])

    def test_events_are_grouped_before_single_reconciliation(self):
        state = backend.start(world())
        events = [{"type": "record_correction", "record": "RET1", "by": "warehouse", "new": {"received": value}} for value in (True, False)]
        after, result = backend.enter_step(state, 2, events)
        self.assertNotIn("D_refund(CL1,120)", after["duties"])
        self.assertEqual(3, len(after["records"]["RET1"]))

    def test_unchanged_snapshot_returns_recorded_decision_without_another_handle(self):
        state, first = backend.propose(self.state, "A", "issue_refund", self.args)
        after, second = backend.propose(state, "A", "issue_refund", self.args)
        self.assertEqual(first["token"], second["token"])
        self.assertEqual(1, len(after["tokens"]))
        self.assertFalse(second["fresh_evaluation"])
        self.assertTrue(second["recorded_decision_returned"])
        self.assertEqual(1, second["repeat_count"])

    def test_identical_authenticated_script_has_byte_identical_log(self):
        from conventional_gateway.kernel import encode
        def run():
            state = backend.start(world())
            state, _ = backend.enter_step(state, 2, [{"type": "order", "id": "O1", "from": "L", "to": "A",
                "requested_effects": [{"tool": "issue_refund", "claim": "CL1", "amount": 120, "asserts": ["return received"]}]}])
            state, _ = backend.propose(state, "A", "issue_refund", dict(self.args, asserts=["return received"]))
            state, _ = backend.enter_step(state, 3, [{"type": "acknowledgment", "from": "C", "report": "RPT1", "version": 1},
                {"type": "record_correction", "record": "RET1", "by": "warehouse", "new": {"received": True}}])
            state, proposal = backend.propose(state, "A", "issue_refund", self.args)
            state, answer = backend.execute(state, "A", proposal["token"])
            self.assertEqual("committed", answer["execute_result"])
            return encode(state["log"])
        self.assertEqual(run(), run())


if __name__ == "__main__":
    unittest.main()
