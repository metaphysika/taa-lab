"""Sol-authored stage 6 controls; not independent acceptance fixtures.

Use the production coordinator and inspect actual native state. Independent
outcomes stay in Claude's frozen bundle and the reviewed Astra regressions.
"""
from copy import deepcopy
import unittest

from taa_gateway.schema import validate
from tests.trace_support import production_backend as backend
from tests.trace_support.bundle import world


class DutyEngineTests(unittest.TestCase):
    def setUp(self):
        self.reset()

    def reset(self, setup=None):
        self.state = backend.start(world(), setup)

    def step(self, at, *events):
        if at > self.state["step"] + 1:
            self.state = backend.advance(self.state, at - 1)
        self.state, result = backend.enter_step(self.state, at, list(events))
        return result

    def proposal(self, tool, args, actor="A"):
        self.state, result = backend.propose(self.state, actor, tool, args)
        return result

    def execute(self, decision, actor="A", fault=None):
        self.state, result = backend.execute(self.state, actor, decision.get("token"), fault)
        return result

    def native(self, identity):
        return self.state["native"]["duty_records"][identity][-1]["fields"]

    def pay_and_close(self):
        self.reset({"records": {"RET1": {"received": True}}})
        self.step(2)
        self.assertEqual(self.execute(self.proposal("issue_refund", {
            "claim": "CL1", "amount": 120, "basis": "return", "to": "K1_card"}))["execute_result"], "committed")
        self.execute(self.proposal("message_party", {"claim": "CL1", "to": "K1", "amount": 120,
                                                    "template": "refund_issued", "cites": "REF1"}))
        self.execute(self.proposal("close_case", {"case": "CL1"}))
        self.assertTrue(self.state["native"]["cases"]["CL1"])

    def order(self, at, identity, issuer="L"):
        self.step(at, {"type": "order", "id": identity, "from": issuer, "to": "A", "requested_effects": [
            {"tool": "issue_refund", "claim": "CL1", "amount": 120, "asserts": ["return received"]}]})

    def wrong(self):
        return self.proposal("issue_refund", {"claim": "CL1", "amount": 120, "basis": "return",
                           "to": "K1_card", "asserts": ["return received"]})

    def test_duties_exist_without_any_proposal_and_overdue_begins_at_due_step(self):
        self.assertFalse(self.state["native"]["decisions"])
        d = self.native("D_resolve(CL1)")
        validate("duty", d)
        self.assertEqual((d["claimant"], d["owner"], d["deadline_step"]), ("K1", "party:A", 21))
        self.step(20)
        self.assertFalse(self.native("D_resolve(CL1)")["overdue"])
        self.step(21)
        self.assertTrue(self.native("D_resolve(CL1)")["overdue"])
        self.assertEqual(self.proposal("close_case", {"case": "CL1"})["disposition"], "REFUSE")

    def test_losing_support_never_releases_the_refund(self):
        self.reset({"records": {"RET1": {"received": True}}})
        self.step(2, {"type": "record_correction", "record": "RET1", "by": "warehouse", "new": {"received": False}})
        self.assertEqual(self.native("D_refund(CL1,120)")["resolution"], "unresolved")
        self.assertEqual(self.proposal("close_case", {"case": "CL1"})["disposition"], "REFUSE")

    def test_settlement_evidence_must_match_every_bound_dimension(self):
        valid = {"kind": "refund", "claim": "CL1", "claimant": "K1", "order": "ORD1", "amount": 120,
                 "currency": "USD", "settled": True, "allocated_to": None}
        variants = ({"claim": "OTHER"}, {"claimant": "K2"}, {"order": "ORD2"}, {"currency": "EUR"},
                    {"amount": 119}, {"settled": False}, {"allocated_to": "some other duty"})
        for wrong in variants:
            with self.subTest(wrong=wrong):
                self.reset({"records": {"RET1": {"received": True}, "REFX": dict(valid, **wrong)}})
                self.assertEqual(self.native("D_refund(CL1,120)")["resolution"], "unresolved")

    def test_different_denial_records_share_one_unsupported_remainder(self):
        self.reset({"records": {
            "CL7": {"kind": "claim", "claimant": "K2", "order": "ORD2", "basis": "nondelivery", "amount": 400},
            "DEL2": {"status": "partial", "failed_value": 250},
            "DEL3": {"kind": "carrier_record", "order": "ORD2", "status": "partial", "failed_value": 250},
            "REFX": {"kind": "refund", "claim": "CL7", "claimant": "K2", "order": "ORD2", "amount": 100,
                     "currency": "USD", "settled": True}}})
        for notice in ({"template": "refund_issued", "amount": 100, "cites": "REFX"},
                       {"template": "refund_denied", "amount": 150, "basis": "DEL2"},
                       {"template": "refund_denied", "amount": 150, "basis": "DEL3"}):
            result = self.proposal("message_party", dict(notice, claim="CL7", to="K2"))
            self.assertEqual(result["disposition"], "PERMIT")
            self.assertEqual(self.execute(result)["execute_result"], "committed")
        self.assertEqual(self.native("D_resolve(CL7)")["resolution"], "unresolved")
        self.assertEqual(self.proposal("close_case", {"case": "CL7"})["disposition"], "REFUSE")

    def test_corrected_allocation_reopens_both_duties_and_case_without_rewriting_receipts(self):
        self.pay_and_close()
        receipts = deepcopy(self.state["native"]["receipts"])
        self.step(4, {"type": "record_correction", "record": "REF1", "by": "payment_processor",
                      "new": {"allocated_to": "another claim"}})
        for did in ("D_refund(CL1,120)", "D_resolve(CL1)"):
            self.assertEqual(self.native(did)["resolution"], "unresolved")
        self.assertFalse(self.state["native"]["cases"]["CL1"])
        self.assertEqual(self.state["native"]["receipts"], receipts)
        self.assertEqual(self.state["native"]["records"]["refund:REF1"][0]["fields"]["allocated_to"], None)

    def test_correction_that_preserves_the_bound_proof_does_not_reopen(self):
        self.pay_and_close()
        self.step(4, {"type": "record_correction", "record": "REF1", "by": "payment_processor",
                      "new": {"allocated_to": "D_refund(CL1,120)"}})
        self.assertEqual(self.native("D_refund(CL1,120)")["resolution"], "discharged")
        self.assertEqual(self.native("D_resolve(CL1)")["resolution"], "discharged")
        self.assertTrue(self.state["native"]["cases"]["CL1"])

    def test_withdrawal_for_another_claimant_cannot_release_the_duty(self):
        for fields in ({"claim": "CL1", "claimant": "K2"}, {"claim": "CL1"}, {"order": "ORD1"}):
            with self.subTest(fields=fields):
                self.reset()
                self.step(2, {"type": "record_insert", "record": "WD1", "by": "customer_portal",
                              "fields": dict(fields, kind="withdrawal")},
                             {"type": "resolution", "question": "release_determination", "about": "D_resolve(CL1)",
                              "by": "F", "answer": "release", "basis": "withdrawal", "evidence": "WD1"})
                self.assertEqual(self.native("D_resolve(CL1)")["resolution"], "unresolved")

    def test_bound_determination_can_release_old_amount_without_waiving_new_partial_duty(self):
        self.reset({"records": {"CL2": {"kind": "claim", "claimant": "K2", "order": "ORD2", "basis": "nondelivery", "amount": 250}}})
        self.step(2, {"type": "record_correction", "record": "DEL2", "by": "carrier",
                      "new": {"status": "partial", "failed_value": 100}})
        self.assertEqual(self.native("D_refund(CL2,250)")["resolution"], "unresolved")
        self.step(3, {"type": "resolution", "question": "release_determination", "about": "D_refund(CL2,250)",
                      "by": "F", "answer": "release", "basis": "replace old full amount with corrected partial entitlement",
                      "evidence": "DEL2@v2"})
        self.assertEqual(self.native("D_refund(CL2,250)")["resolution"], "released")
        self.assertEqual(self.native("D_refund(CL2,100)")["resolution"], "unresolved")

    def test_bad_resolution_correction_is_log_only(self):
        self.reset({"records": {"CL5": {"kind": "claim", "claimant": "K1", "order": "ORD1", "basis": "return", "amount": 120},
                    "DUPD1": {"kind": "resolution", "question": "duplicate_determination", "about": "CL5", "by": "F", "answer": "duplicate", "surviving": "CL1"}}})
        for actor, recipient, question in (("L", "gateway", "duplicate_determination"),
                                          ("F", "party:A", "duplicate_determination"), ("F", "gateway", "unreserved")):
            c = backend._context(self.state)
            before = c.store.snapshot()
            e = c.auth.issue(c.sessions[actor], recipient, c.store.step, "resolution", {
                "correction_of": "resolution:DUPD1", "question_id": question, "jurisdiction": "claim_decisions",
                "answer": {"about": "CL5", "decision": "not_duplicate"}})
            c.resolutions.correct(e, "resolution:DUPD1")
            self.assertEqual(c.store.snapshot(), before)
            self.assertEqual(c.log.events()[-1]["type"], "rejected_resolution")

    def test_correcting_the_surviving_claim_invalidates_duplicate_release(self):
        self.reset({"records": {"CL5": {"kind": "claim", "claimant": "K1", "order": "ORD1", "basis": "return", "amount": 120},
                    "DUPD1": {"kind": "resolution", "question": "duplicate_determination", "about": "CL5", "by": "F", "answer": "duplicate", "surviving": "CL1"}}})
        c = backend._context(self.state)
        envelope = c.auth.issue(c.sessions["F"], "gateway", c.store.step, "resolution", {
            "correction_of": "resolution:DUPD1", "question_id": "duplicate_determination", "jurisdiction": "claim_decisions",
            "answer": {"about": "CL5", "decision": "duplicate", "surviving": "UNKNOWN"}})
        c.resolutions.correct(envelope, "resolution:DUPD1")
        c.engine.reconcile()
        duty = c.store.snapshot()["duty_records"]["D_resolve(CL5)"][-1]["fields"]
        self.assertEqual(duty["resolution"], "unresolved")
        self.assertTrue(any(e["type"] == "reopened" for e in duty["history"]))

    def test_report_repeats_preserve_deadlines_and_the_assigned_recipient(self):
        self.order(1, "O1"); self.step(2); self.wrong()
        self.order(3, "OC", "C"); self.wrong()
        before = self.native("D_report(O1)")
        self.order(4, "O2"); self.wrong()
        after = self.native("D_report(O1)")
        self.assertEqual(after["content"]["recipient"], "party:C")
        self.assertEqual((after["deadline_step"], after["route_deadline_step"]),
                         (before["deadline_step"], before["route_deadline_step"]))
        self.assertEqual(after["content"]["version"], 2)
        c = backend._context(self.state)
        self.assertEqual(c.engine.eligible(c.store.snapshot(), after), "party:F")

    def test_reporting_uses_its_own_standing_after_agent_revocation(self):
        self.order(1, "O1"); self.step(2); self.wrong()
        self.step(3, {"type": "grant_revocation", "grant": "G1", "by": "F"})
        self.step(7)
        self.assertEqual(self.native("D_report(O1)")["content"]["recipient"], "party:F")
        sent = [e["native_event"]["payload"]["envelope"] for e in self.state["log"] if e["type"] == "report_sent"]
        self.assertTrue(sent)
        self.assertTrue(all(e["authenticated_sender"] == "gateway_reporting" for e in sent))

    def test_same_step_revoke_and_regrant_does_not_start_a_transfer(self):
        self.step(2, {"type": "grant_revocation", "grant": "G1", "by": "F"},
                     {"type": "grant_issue", "grant": "G1b", "by": "F", "to": "A", "same_terms_as": "G1"})
        self.assertEqual(self.native("D_resolve(CL1)")["owner"], "party:A")
        self.assertIsNone(self.native("D_resolve(CL1)")["offered_to"])

    def test_offer_commit_uses_commit_time_without_invalidating_a_valid_token(self):
        self.step(2)
        offer = self.proposal("offer_duty", {"duty": "D_resolve(CL1)", "to": "F"})
        self.step(3)
        self.assertEqual(self.execute(offer)["execute_result"], "committed")
        self.assertEqual(self.native("D_resolve(CL1)")["offer_deadline_step"], 8)
        accepted = self.proposal("accept_duty", {"duty": "D_resolve(CL1)"}, actor="F")
        self.assertEqual(accepted["disposition"], "REFUSE")
        self.step(3, {"type": "duty_acceptance", "from": "F", "duties": ["D_resolve(CL1)"]})
        self.assertEqual(self.native("D_resolve(CL1)")["owner"], "party:F")
        self.assertIsNone(self.native("D_resolve(CL1)")["offered_to"])

    def test_real_duty_updates_and_allocations_rollback_inside_the_effect_transaction(self):
        self.reset({"records": {"RET1": {"received": True}}})
        self.step(2)
        decision = self.proposal("issue_refund", {"claim": "CL1", "amount": 120, "to": "K1_card", "basis": "return"})
        before = deepcopy(self.state["native"])
        self.assertEqual(self.execute(decision, fault="during_duty_update")["execute_result"], "failed")
        self.assertEqual(self.state["native"], before)
        partial = self.state["log"][-1]["native_event"]["payload"]["partial_state"]
        self.assertEqual(partial["duty_records"]["D_refund(CL1,120)"][-1]["fields"]["resolution"], "discharged")
        self.assertEqual(partial["allocations"]["refund:REF1"], "D_refund(CL1,120)")
        self.assertEqual(self.execute(decision)["execute_result"], "committed")
        receipt = self.state["native"]["receipts"][-1]
        self.assertEqual(receipt["effect"]["duty_state"]["D_refund(CL1,120)"][-1]["fields"]["resolution"], "discharged")

    def test_acceptance_at_the_expired_window_is_log_only(self):
        self.step(2)
        self.execute(self.proposal("offer_duty", {"duty": "D_resolve(CL1)", "to": "F"}))
        self.step(7)
        before = deepcopy(self.state["native"])
        result = self.step(7, {"type": "duty_acceptance", "from": "F", "duties": ["D_resolve(CL1)"]})
        self.assertEqual(self.state["native"], before)
        self.assertEqual(self.native("D_resolve(CL1)")["owner"], "party:A")

    def offer_context_at(self, step):
        """Isolate the component: do not let phase-1 expiry clear the offer first."""
        self.reset()
        self.step(2)
        self.execute(self.proposal("offer_duty", {"duty": "D_resolve(CL1)", "to": "F"}))
        c = backend._context(self.state)
        self.assertEqual(c.engine.ledger(c.store.snapshot())["D_resolve(CL1)"]["offer_deadline_step"], 7)
        c.store.gateway_mutation(c.gateway, "duty_engine", lambda state, events: state.update(step=step))
        return c

    def test_apply_action_acceptance_excludes_exact_offer_deadline(self):
        for step in (6, 7):
            with self.subTest(step=step):
                c = self.offer_context_at(step)
                before = c.store.snapshot()
                def accept(state, events):
                    c.engine.apply_action(state, events, {"operation": "accept_duty", "duty": "D_resolve(CL1)"}, "party:F")
                if step == 7:
                    with self.assertRaisesRegex(ValueError, "no live offer"):
                        c.store.gateway_mutation(c.gateway, "duty_engine", accept)
                    self.assertEqual(c.store.snapshot(), before)
                else:
                    c.store.gateway_mutation(c.gateway, "duty_engine", accept)
                    self.assertEqual(c.engine.ledger(c.store.snapshot())["D_resolve(CL1)"]["owner"], "party:F")

    def test_receive_acceptance_excludes_exact_offer_deadline(self):
        for step in (6, 7):
            with self.subTest(step=step):
                c = self.offer_context_at(step)
                before = c.store.snapshot()
                envelope = c.auth.issue(c.sessions["F"], "gateway_reporting", step, "acceptance",
                                        {"duties": ["D_resolve(CL1)"]})
                result = c.engine.receive(envelope)
                if step == 7:
                    self.assertEqual(result.get("reason"), "no live transfer offer to this party")
                    self.assertEqual(c.store.snapshot(), before)
                    self.assertEqual(c.log.events()[-1]["type"], "rejected_ledger_message")
                else:
                    self.assertEqual(result, {})
                    self.assertEqual(c.engine.ledger(c.store.snapshot())["D_resolve(CL1)"]["owner"], "party:F")
                    self.assertTrue(c.engine.rows(c.store.snapshot(), "acceptance"))

    def test_reopening_marks_overdue_at_or_after_due_step_in_same_call(self):
        from taa_gateway.records import Write
        for offset in (-1, 0, 1):
            with self.subTest(offset=offset):
                self.pay_and_close()
                c = backend._context(self.state)
                did = "D_refund(CL1,120)"
                due = c.engine.ledger(c.store.snapshot())[did]["deadline_step"]
                def reopen(state, events):
                    # Exercise reopening itself, without the separate ledger-clock path.
                    state["step"] = due + offset
                    fields = deepcopy(state["records"]["refund:REF1"][-1]["fields"])
                    fields["settled"] = False
                    c.store.append_write(state, events, c.sources["payment_processor"], "external_record",
                                         Write("refund:REF1", "refund", fields))
                    duty = c.engine.ledger(state)[did]
                    self.assertFalse(duty["overdue"])
                    c.engine.resolve_business(state, events, duty)
                c.store.gateway_mutation(c.gateway, "duty_engine", reopen)
                duty = c.engine.ledger(c.store.snapshot())[did]
                self.assertEqual(duty["resolution"], "unresolved")
                self.assertEqual(duty["overdue"], offset >= 0)
                self.assertEqual(duty["history"][-1], {"type": "reopened", "at": due + offset})
                self.assertFalse(c.store.snapshot()["cases"]["CL1"])

    def test_hold_notice_keeps_work_open_and_does_not_accept_a_forged_recipient(self):
        decision = self.proposal("hold_refund", {"claim": "CL1", "missing": "return receipt"})
        self.assertEqual(decision["disposition"], "PERMIT")
        self.assertEqual(self.execute(decision)["execute_result"], "committed")
        self.assertEqual(self.native("D_resolve(CL1)")["resolution"], "unresolved")
        self.assertEqual(self.state["native"]["notices"][-1]["to"], "K1")
        self.assertFalse(self.proposal("hold_refund", {"claim": "CL1", "missing": "receipt", "to": "K2"})["evaluated"])

    def test_log_reproduces_byte_for_byte_and_reports_cite_real_logged_evidence(self):
        def episode():
            self.reset(); self.order(1, "O1"); self.step(2); self.wrong()
            c = backend._context(self.state)
            payload = c.store.snapshot()["reports"]["RPT1"][0]
            event = c.log.events()[payload["source_sequence"]]
            self.assertEqual(event["hash"], payload["source_hash"])
            self.assertEqual(event["type"], "pipeline_decision")
            self.assertEqual(event["payload"]["decision"]["act"], payload["act"])
            c.log.seal()
            return c.log.jsonl()
        self.assertEqual(episode(), episode())


if __name__ == "__main__":
    unittest.main()
