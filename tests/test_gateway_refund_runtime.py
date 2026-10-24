"""Stage 5 world controls authored by Sol; independent fixtures stay frozen."""
from copy import deepcopy
from dataclasses import replace
import unittest

from taa_gateway.executor import EffectPlan, Runtime
from taa_gateway.refunds import RefundWorld, stage_refund
from tests.trace_support.bundle import world
from tests.trace_support.production_backend import KEY
from tests.trace_support.state_observations import Observer


class RefundRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.context = RefundWorld(world(), KEY, setup={"records": {"RET1": {"received": True}}})

    def duty(self, *, lost=True):
        return {"schema_version": "0.3.1", "id": "D_refund(CL1,120)", "case_id": "CL1", "claimant": "K1",
            "content": {"kind": "refund", "amount": 120, "currency": "USD"}, "owner": "party:A", "offered_to": "party:F",
            "origin": {"rule": "DU2", "claim": "CL1"}, "discharge_condition": {"evidence_kind": "refund",
                "bindings": {"claim": "CL1", "claimant": "K1", "order": "ORD1", "amount": 120, "currency": "USD", "settled": True}},
            "deadline_step": 21, "interim_rule": {"id": "IR1", "authority_lost": lost}, "fallback_owner": "party:F",
            "resolution": "unresolved", "overdue": False, "resolution_basis": None, "history": [],
            "offer_deadline_step": 5}

    def seed_duty(self, duty):
        c = self.context
        def seed(state, events):
            c.store.append_duty(state, events, duty, "gateway")
            c.store.advance_revision(state, events)
        c.store.gateway_mutation(c.gateway, "capabilities", seed)

    def revoke(self):
        c = self.context
        from taa_gateway.records import Write
        grant = c.store.read("grant:G1")["fields"]
        grant["status"] = "revoked"
        c.store.publish(c.gateway, "grant_change", [Write("grant:G1", "grant", grant)])

    def propose(self, tool="issue_refund", args=None, actor="A"):
        return self.context.runtime.propose(self.context.sessions[actor], {"tool": tool, "arguments": args or {
            "claim": "CL1", "amount": 120, "to": "K1_card", "basis": "return"}})

    def test_IR1_is_a_complete_narrow_path_when_original_grant_is_revoked(self):
        self.seed_duty(self.duty())
        self.revoke()
        message = {"to": "K1", "template": "claim_referred", "claim": "CL1", "referred_to": "F"}
        decision = self.propose("message_party", message)
        self.assertEqual(decision["disposition"], "PERMIT")
        authority = next(c for c in decision["checks"] if c["stage"] == "authority")
        self.assertEqual(authority["authority_basis"], "IR1")
        self.assertTrue(decision["justification"]["grant_id"].startswith("IR1:"))
        self.assertEqual(self.context.runtime.execute(self.context.sessions["A"], decision["token"])["execute_result"], "committed")
        self.assertEqual(self.context.store.snapshot()["duty_records"][self.duty()["id"]][-1]["fields"]["resolution"], "unresolved")
        self.assertEqual(self.propose()["disposition"], "REFUSE")
        self.assertEqual(self.propose("message_party", dict(message, to="K2"))["disposition"], "REFUSE")
        self.assertEqual(self.propose("message_party", message, actor="B")["disposition"], "REFUSE")

    def test_IR1_window_boundary_voids_tokens_without_resolving_the_duty(self):
        self.seed_duty(self.duty())
        # Both claim duties originate before this loss episode. Otherwise the
        # first phase-2 run correctly creates a new resolution duty/window (Q16).
        resolve = self.context.engine.new_duty("D_resolve(CL1)", "CL1", "K1", "resolve", 0)
        resolve["interim_rule"]["authority_lost"] = True
        resolve.update(offered_to="party:F", offer_deadline_step=5)
        self.seed_duty(resolve)
        self.revoke()
        message = {"to": "K1", "template": "refund_held", "claim": "CL1", "missing": "claim referral"}
        token = self.propose("message_party", message)["token"]
        before = self.context.store.revision
        self.context.store.publish(self.context.gateway, "advance_clock", step=5)
        phase1 = self.context.store.snapshot()
        self.assertEqual(phase1["duty_records"][self.duty()["id"]][-1]["fields"]["owner"], "party:A")
        # Q16 ownership is phase 2, after all same-step capacity changes.
        self.context.engine.reconcile()
        state = self.context.store.snapshot()
        self.assertGreater(state["revision"], before)
        self.assertEqual(state["tokens"][token]["status"], "void")
        duty = state["duty_records"][self.duty()["id"]][-1]["fields"]
        self.assertIsNone(duty["owner"])
        self.assertEqual(duty["resolution"], "unresolved")
        self.assertEqual(self.propose("message_party", message)["disposition"], "REFUSE")

    def test_voluntary_offer_lapses_with_owner_retained(self):
        self.seed_duty(self.duty(lost=False))
        self.context.store.publish(self.context.gateway, "advance_clock", step=5)
        duty = self.context.store.snapshot()["duty_records"][self.duty()["id"]][-1]["fields"]
        self.assertEqual(duty["owner"], "party:A")
        self.assertIsNone(duty["offered_to"])
        self.assertEqual(duty["resolution"], "unresolved")

    def test_resolved_deadline_is_inactive_and_due_step_is_overdue(self):
        self.seed_duty(self.duty())
        self.context.store.publish(self.context.gateway, "advance_clock", step=21)
        duty = self.context.store.snapshot()["duty_records"][self.duty()["id"]][-1]["fields"]
        self.assertTrue(duty["overdue"])
        after = self.context.store.revision
        self.context.store.publish(self.context.gateway, "advance_clock", step=22)
        self.assertEqual(self.context.store.revision, after)
        resolved = self.duty()
        resolved.update(resolution="discharged", resolution_basis=[{"record_id": "refund:REF1", "record_version": 1}])
        resolved["deadline_step"] = 24
        self.seed_duty(resolved)
        before = self.context.store.revision
        self.context.store.publish(self.context.gateway, "advance_clock", step=24)
        self.assertEqual(self.context.store.revision, before)

    def test_related_duty_notice_and_allocation_updates_rollback_with_effect(self):
        self.seed_duty(self.duty(lost=False))
        def compound(args, view):
            plan = stage_refund(args, view)
            duty = dict(view.records("duty")[0][1], resolution="discharged",
                        resolution_basis=[{"record_id": "refund:REF1", "record_version": 1}])
            return EffectPlan(writes=plan.writes, notices=({"claim": "CL1", "template": "refund_issued"},),
                              allocations={"refund:REF1": duty["id"]}, duties=(duty,))
        c = self.context
        tools = [replace(t, stage=compound) if t.name == "issue_refund" else t for t in c.tools]
        runtime = Runtime(c.store, c.auth, c.gateway, c.pipeline, tools)
        token = runtime.propose(c.sessions["A"], {"tool": "issue_refund", "arguments": {
            "claim": "CL1", "amount": 120, "to": "K1_card", "basis": "return"}})["token"]
        before = c.store.snapshot()
        self.assertEqual(runtime.execute(c.sessions["A"], token, fault="during_duty_update")["execute_result"], "failed")
        self.assertEqual(c.store.snapshot(), before)
        partial = c.log.events()[-1]["payload"]["partial_state"]
        self.assertEqual(len(partial["duty_records"][self.duty()["id"]]), 2)
        self.assertEqual(partial["duty_records"][self.duty()["id"]][-1]["fields"]["resolution"], "discharged")
        self.assertEqual(runtime.execute(c.sessions["A"], token)["execute_result"], "committed")
        self.assertEqual(c.store.snapshot()["duty_records"][self.duty()["id"]][0]["fields"]["resolution"], "unresolved")

    def test_inner_DT2_recheck_stops_a_mutant_that_bypasses_revision_validation(self):
        c = self.context
        c2 = RefundWorld(world(), KEY, setup={"records": {"CL6": {"kind": "claim", "claimant": "K2", "order": "ORD2", "basis": "nondelivery", "amount": 250}}})
        args = {"claim": "CL6", "amount": 150, "to": "K2_card", "basis": "nondelivery"}
        one = c2.runtime.propose(c2.sessions["A"], {"tool": "issue_refund", "arguments": args})["token"]
        two = c2.runtime.propose(c2.sessions["A"], {"tool": "issue_refund", "arguments": dict(args, amount=140)})["token"]
        c2.runtime.execute(c2.sessions["A"], one)
        corrupted = c2.store.snapshot()
        row = corrupted["tokens"][two]
        row["status"] = "live"
        row["certificate"]["state_revision"] = corrupted["revision"]
        corrupted["warrants"][row["certificate"]["warrant_id"]]["status"] = "live"
        # Deliberate host-side mutant in a new checkpoint fork, not a live reset.
        c2 = RefundWorld(world(), KEY, native=corrupted, events=c2.log.events())
        assessment = c2.pipeline.assess_snapshot(corrupted, "party:A", "issue_refund", dict(args, amount=140))
        self.assertEqual(next(r for r in assessment["checks"] if r["id"] == "DT2")["result"], "violated")
        self.assertEqual(c2.runtime.execute(c2.sessions["A"], two)["execute_result"], "refused_revalidation")
        self.assertEqual(len(c2.store.snapshot()["receipts"]), 1)

    def test_W0_alternative_selects_250_and_false_full_settlement_stays_prohibited(self):
        self.context = RefundWorld(world(), KEY, setup={"records": {"CL7": {"kind": "claim", "claimant": "K2", "order": "ORD2", "basis": "nondelivery", "amount": 400}}})
        args = {"claim": "CL7", "amount": 400, "to": "K2_card", "basis": "nondelivery"}
        decision = self.propose(args=args)
        self.assertEqual(decision["disposition"], "ALTERNATIVE")
        self.assertEqual(decision["alternative"]["arguments"]["amount"], 250)
        self.assertEqual(self.propose(args=dict(args, amount=250, asserts=["claim settled in full"]))["disposition"], "PROHIBIT")

    def test_observer_pins_native_only_record_and_ledger_versions(self):
        native = self.context.store.snapshot()
        state = {"records": {}, "native": native}
        observer = Observer(state)
        changed = deepcopy(state)
        changed["native"]["records"]["grant:G1"][0]["fields"]["status"] = "revoked"
        self.assertIn("native.records:grant:G1@v1", observer.capture(changed))


if __name__ == "__main__":
    unittest.main()
