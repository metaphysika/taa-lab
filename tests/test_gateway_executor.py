"""Sol-authored stage 5 component controls; no frozen expectations modified."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from threading import Barrier
import unittest

from taa_gateway.executor import EffectPlan, FAULTS, Runtime
from taa_gateway.orders import StoredOrders
from taa_gateway.records import RecordStore, Write
from taa_gateway.rules import Outcome, Rule
from tests import test_gateway_pipeline as pipeline_fixture


class ExecutorTests(unittest.TestCase):
    put = pipeline_fixture.PipelineTests.put
    build = pipeline_fixture.PipelineTests.build
    delivered = pipeline_fixture.PipelineTests.delivered

    def setUp(self):
        pipeline_fixture.PipelineTests.setUp(self)
        snapshot = self.store.snapshot()
        self.agent = self.auth.bind("agent", "agent", ["propose", "execute", "withdraw"])
        self.other = self.auth.bind("other", "agent", ["propose", "execute", "withdraw"])
        self.gateway = self.auth.bind("runtime", "gateway", ["capabilities", "execute_transaction", "restore"])
        self.policy["writers"].append({"kind": "refund", "tool": "execute_transaction", "channel": "gateway",
             "principals": ["runtime"], "id_prefix": "refund-", "evidential": True, "create": True, "correct_fields": []})
        self.store = RecordStore(self.auth, self.log, self.policy)
        self.store.restore_for_simulator(self.gateway, snapshot)
        self.orders = StoredOrders(self.store, self.auth, self.admin)
        self.tools = [replace(t, reads=("delivery", "refund", "duty"), stage=self.refund) if t.name == "issue_refund"
                      else t for t in self.tools]
        self.pipeline = self.build()
        self.runtime = Runtime(self.store, self.auth, self.gateway, self.pipeline, self.tools)
        self.delivered()

    def refund(self, args, view):
        rid = "refund-" + str(len(view.records("refund")) + 1)
        return EffectPlan(writes=(Write(rid, "refund", {"claim": args["claim_id"], "amount": args["amount"],
                          "settled": True, "to": args["customer"] + "-card"}),))

    def propose(self, amount=120, **kwargs):
        return self.runtime.propose(kwargs.pop("session", self.agent), {"tool": "issue_refund", "arguments": {
            "claim_id": "claim-one", "customer": "customer-one", "amount": amount}, **kwargs})

    def test_issue_is_revision_neutral_and_exact_repeat_reuses_token(self):
        revision = self.store.revision
        first, second = self.propose(), self.propose(claimed_reasons=["pressure"])
        self.assertEqual(first["token"], second["token"])
        self.assertTrue(second["recorded_decision_returned"])
        self.assertEqual(len(self.store.snapshot()["tokens"]), 1)
        self.assertEqual(self.store.revision, revision)

    def test_commit_binds_pre_revision_and_consumes_exactly_once(self):
        token = self.propose()["token"]
        revision = self.store.revision
        self.assertEqual(self.runtime.execute(self.agent, token)["execute_result"], "committed")
        state = self.store.snapshot()
        self.assertEqual((state["revision"], len(state["receipts"])), (revision + 1, 1))
        self.assertEqual(state["tokens"][token]["status"], "consumed")
        self.assertEqual(state["receipts"][0]["pre_transaction_revision"], revision)
        self.assertEqual(self.runtime.execute(self.agent, token)["execute_result"], "refused_token_consumed")
        self.assertEqual(self.store.snapshot(), state)

    def test_wrong_actor_does_not_consume_or_advance(self):
        token = self.propose()["token"]
        state = self.store.snapshot()
        self.assertEqual(self.runtime.execute(self.other, token)["execute_result"], "refused_wrong_actor")
        self.assertEqual(self.store.snapshot(), state)
        self.assertEqual(self.runtime.execute(self.agent, token)["execute_result"], "committed")

    def test_argument_and_tool_substitution_are_refused(self):
        token = self.propose()["token"]
        before = self.store.snapshot()
        self.assertEqual(self.runtime.execute(self.agent, token, arguments={"amount": 1})["execute_result"], "refused_argument_mismatch")
        self.assertEqual(self.runtime.execute(self.agent, token, tool="close_case")["execute_result"], "refused_argument_mismatch")
        self.assertEqual(self.store.snapshot(), before)

    def test_relevant_record_insertion_invalidates_all_and_replacement_is_fresh(self):
        token = self.propose()["token"]
        self.put("note-inserted", "agent_note", {"text": "new state"})
        self.assertEqual(self.store.snapshot()["tokens"][token]["status"], "void")
        self.assertEqual(self.runtime.execute(self.agent, token)["execute_result"], "refused_stale_revision")
        replacement = self.propose()
        self.assertNotEqual(replacement["token"], token)
        self.assertTrue(replacement["fresh_evaluation"])

    def test_correction_rechecks_prohibition_and_preserves_original_versions(self):
        token = self.propose()["token"]
        self.delivered(False)
        self.assertEqual(self.runtime.execute(self.agent, token)["execute_result"], "refused_stale_revision")
        self.assertEqual(self.propose()["disposition"], "REFUSE")
        self.assertTrue(self.store.read("delivery-1", 1)["fields"]["delivered"])

    def test_live_expiry_advances_and_already_void_expiry_is_inactive(self):
        self.runtime.lifetime = 2
        token = self.propose()["token"]
        before = self.store.revision
        self.store.publish(self.admin, "advance_clock", step=1)
        self.assertEqual(self.store.revision, before)
        self.assertEqual(self.propose()["token"], token)
        self.store.publish(self.admin, "advance_clock", step=2)
        self.assertGreater(self.store.revision, before)
        self.assertEqual(self.runtime.execute(self.agent, token)["execute_result"], "refused_token_expired")
        after = self.store.revision
        self.store.publish(self.admin, "advance_clock", step=3)
        self.assertEqual(self.store.revision, after)

    def test_commit_voids_other_same_revision_tokens(self):
        first, second = self.propose(100)["token"], self.propose(120)["token"]
        state = self.store.snapshot()
        self.assertEqual(state["tokens"][first]["certificate"]["state_revision"], state["tokens"][second]["certificate"]["state_revision"])
        self.runtime.execute(self.agent, first)
        self.assertEqual(self.store.snapshot()["tokens"][second]["status"], "void")
        self.assertEqual(self.runtime.execute(self.agent, second)["execute_result"], "refused_stale_revision")

    def test_withdrawal_preserves_history_and_invalidates_other_approvals(self):
        one, two = self.propose(100)["token"], self.propose(120)["token"]
        self.runtime.withdraw(self.agent, one)
        state = self.store.snapshot()
        self.assertEqual(state["tokens"][one]["status"], "withdrawn")
        self.assertEqual(state["tokens"][two]["status"], "void")
        self.assertNotEqual(self.propose(100)["token"], one)

    def test_real_faults_rollback_each_partially_mutated_boundary_and_retry(self):
        for fault in FAULTS:
            with self.subTest(fault=fault):
                token = self.propose(100)["token"]
                before = self.store.snapshot()
                self.assertEqual(self.runtime.execute(self.agent, token, fault=fault)["execute_result"], "failed")
                self.assertEqual(self.store.snapshot(), before)
                partial = self.log.events()[-1]["payload"]["partial_state"]
                if fault in FAULTS[2:]:
                    self.assertGreater(len(partial["records"]), len(before["records"]))
                if fault in FAULTS[3:]:
                    self.assertEqual(partial["tokens"][token]["status"], "consumed")
                if fault in FAULTS[5:]:
                    self.assertEqual(len(partial["receipts"]), len(before["receipts"]) + 1)
                if fault == "during_revision_advance":
                    self.assertEqual(partial["revision"], before["revision"] + 1)
                self.assertEqual(self.runtime.execute(self.agent, token)["execute_result"], "committed")

    def test_effect_plan_changed_after_issue_cannot_commit(self):
        token = self.propose()["token"]
        before = self.store.snapshot()
        self.runtime.tools = type(self.runtime.tools)([replace(t, stage=lambda args, view: EffectPlan(writes=(
            Write("refund-1", "refund", {"claim": "claim-one", "amount": 120, "to": "account_X"}),)))
            if t.name == "issue_refund" else t for t in self.tools])
        self.assertEqual(self.runtime.execute(self.agent, token)["execute_result"], "refused_staging_mismatch")
        self.assertEqual(self.store.snapshot(), before)

    def test_parallel_use_of_two_tokens_commits_only_one(self):
        tokens = [self.propose(100)["token"], self.propose(120)["token"]]
        barrier = Barrier(2)
        def attempt(token):
            barrier.wait()
            return self.runtime.execute(self.agent, token)["execute_result"]
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(attempt, tokens))
        self.assertEqual(sorted(results), ["committed", "refused_stale_revision"])
        self.assertEqual(len(self.store.snapshot()["receipts"]), 1)

    def test_agent_cannot_reach_gateway_write_or_restore_boundary(self):
        before = self.store.snapshot()
        with self.assertRaises(ValueError):
            self.store.gateway_mutation(self.agent, "propose", lambda state, events: state.clear())
        with self.assertRaises(ValueError):
            self.store.restore_for_simulator(self.agent, {})
        self.assertEqual(self.store.snapshot(), before)

    def test_rejected_calls_are_logged_without_revision_or_world_changes(self):
        before = self.store.snapshot()
        for raw in (None, [], {"tool": "unregistered", "arguments": {}},
                    {"tool": "issue_refund", "arguments": {"amount": -1}}):
            result = self.runtime.propose(self.agent, raw)
            self.assertFalse(result["evaluated"])
            self.assertEqual(self.log.events()[-1]["type"], "rejected_proposal")
            self.assertEqual(self.store.snapshot(), before)

    def test_largest_passing_alternative_is_independent_of_rule_order(self):
        def offer(amount):
            return lambda ctx, view: (Outcome("satisfied") if ctx["arguments"]["amount"] <= 250 else
                  Outcome("violated", alternative={"tool": "issue_refund", "arguments": dict(ctx["arguments"], amount=amount)}))
        for small_id, large_id in (("early", "late"), ("late", "early")):
            rules = self.rules + [Rule(small_id, 1, "support", (), offer(100), ("issue_refund",)),
                                  Rule(large_id, 1, "support", (), offer(250), ("issue_refund",))]
            pipeline = self.build(rules)
            decision = pipeline.evaluate(self.agent, {"tool": "issue_refund", "arguments": {
                "claim_id": "claim-one", "customer": "customer-one", "amount": 400}})
            self.assertEqual(decision["alternative"]["arguments"]["amount"], 250)

    def test_cumulative_limit_rechecks_actual_state_after_split_and_regrant(self):
        def remaining(ctx, view):
            paid = sum(r["amount"] for _, r in view.records("refund") if r["claim"] == ctx["arguments"]["claim_id"])
            amount, args = 300 - paid, ctx["arguments"]
            return Outcome("satisfied") if args["amount"] <= amount else Outcome("violated", alternative={
                "tool": "issue_refund", "arguments": dict(args, amount=amount)})
        self.pipeline = self.build(self.rules + [Rule("cumulative", 1, "determination", ("refund",), remaining, ("issue_refund",))])
        self.runtime = Runtime(self.store, self.auth, self.gateway, self.pipeline, self.tools)
        one, two = self.propose(200)["token"], self.propose(200)["token"]
        self.assertEqual(one, two)
        self.runtime.execute(self.agent, one)
        self.grant["status"] = "revoked"
        self.put("grant-one", "grant", self.grant)
        self.grant["status"] = "live"
        self.put("grant-one", "grant", self.grant)
        decision = self.propose(200)
        self.assertEqual(decision["disposition"], "ALTERNATIVE")
        self.assertEqual(decision["alternative"]["arguments"]["amount"], 100)
        last = self.propose(100)["token"]
        self.runtime.execute(self.agent, last)
        self.assertEqual(self.propose(1)["disposition"], "REFUSE")

    def test_kernel_advances_relevant_state_even_if_callback_omits_revision(self):
        token = self.propose()["token"]
        before = self.store.revision
        self.store.gateway_mutation(self.gateway, "capabilities", lambda state, events: state["cases"].update({"new-case": False}))
        self.assertEqual(self.store.revision, before + 1)
        self.assertEqual(self.store.snapshot()["tokens"][token]["status"], "void")

    def test_kernel_rejects_historical_rewrite_and_untokened_protected_publication(self):
        before = self.store.snapshot()
        def corrupt(state, events):
            state["records"]["delivery-1"][0]["fields"]["delivered"] = False
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.store.gateway_mutation(self.gateway, "capabilities", corrupt)
        with self.assertRaisesRegex(ValueError, "atomic executor"):
            self.store.publish(self.gateway, "execute_transaction", [Write("refund-unbound", "refund", {"amount": 1})])
        self.assertEqual(self.store.snapshot(), before)

    def test_existing_store_cannot_be_reset_by_checkpoint_import(self):
        before = self.store.snapshot()
        with self.assertRaisesRegex(ValueError, "new empty"):
            self.store.restore_for_simulator(self.gateway, before)
        self.assertEqual(self.store.snapshot(), before)

    def test_largest_alternative_is_selected_across_complete_grant_paths(self):
        second = dict(self.grant, id="grant-two", limits={"per_refund_max": 350})
        self.put("grant-two", "grant", second)
        decision = self.propose(400)
        self.assertEqual(decision["disposition"], "ALTERNATIVE")
        self.assertEqual(decision["alternative"]["arguments"]["amount"], 350)
        self.assertEqual(decision["justification"]["grant_id"], "grant-two")


if __name__ == "__main__":
    unittest.main()
