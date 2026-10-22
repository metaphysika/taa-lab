"""Spec-derived component assertions, NOT Claude's independent expected traces."""
import ast
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import unittest

from taa_gateway_reference.model import (Event, Rule, Spec, UNKNOWN, VIOLATED,
                                         initial, rule_result, transition)


def policy(duties=False):
    tools = {"refund": {"effect": "refund"}, "close": {"effect": "close"},
             "read": {"effect": "read"}, "offer": {"effect": "offer"},
             "accept": {"effect": "accept"}, "report": {"effect": "report"}}
    duty_rules = ({"id": "owed", "source_kind": "claim", "when": {"argument": "owed"},
                   "template": {"case_id": "$case_id", "claimant": "$claimant", "owner": "agent",
                                "kind": "refund", "deadline": 2, "under_grant": "G", "fallback_owner": "fallback",
                                "condition": {"kind": "settlement", "bindings": {"claim_id": "$claim_id",
                                  "claimant": "$claimant", "amount_minor": "$amount_minor", "currency": "$currency", "settled": True}},
                                "release_conditions": [{"kind": "release_determination", "bindings": {
                                  "claim_id": "$claim_id", "claimant": "$claimant", "withdrawn": True}, "standing": ["customer"]}]}},) if duties else ()
    return Spec(tools=tools,
                rules=(Rule("truthful-return", "prohibition", ("refund",),
                            {"eq": [{"fact": ["return", "received"]}, {"literal": True}]}),),
                authorizations=tuple({"tool": tool, "purpose": "refunds"} for tool in tools),
                standing={"lead": tuple(tools), "finance": ("report",)},
                fact_sources={"return": ("carrier",), "claim": ("claims",),
                              "settlement": ("payments",), "withdrawal": ("customer", "ombuds"),
                              "report_ack": ("officer", "fallback-officer"), "release_determination": ("customer",)},
                correction_rights={"return": {"carrier": ["received"]}, "settlement": {"payments": list(ARGS) + ["settled", "order_id", "transaction_id", "allocation_id"]}, "withdrawal": {"customer": ["withdrawn"]}, "release_determination": {"customer": ["withdrawn"]}},
                questions={"Q": {"reviewers": ["reviewer"], "jurisdiction": "refunds"}},
                duty_rules=duty_rules, report_priority=("lead", "conflicted", "officer", "fallback-officer"))


def grant(gid="G", grantee="agent", parent=None, grantor="lead", limit=1000, expires=10):
    return {"id": gid, "grantor": grantor, "grantee": grantee,
            "tools": ["refund", "close", "read", "offer", "accept", "report"],
            "purpose": "refunds", "scope": {}, "limit_minor": limit,
            "expires": expires, "status": "live", "parent": parent}


ARGS = {"case_id": "case", "claim_id": "C", "claimant": "customer",
        "amount_minor": 1000, "currency": "USD"}


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.spec = policy()
        self.state = initial(self.spec)
        self.apply("configuration", "configuration", {
            "entitlements": {"C": {"claimant": "customer", "currency": "USD", "order_id": "O", "amount_minor": 1000}},
            "parties": {"lead": {"jurisdictions": ["refunds"], "may_receive": ["private"]},
                        "conflicted": {"jurisdictions": ["refunds"], "conflicts": ["lead"], "may_receive": ["private"]},
                        "officer": {"jurisdictions": ["refunds"], "may_receive": ["private"]},
                        "fallback-officer": {"jurisdictions": ["refunds"], "may_receive": ["private"]}}})
        self.apply("record", "carrier", {"id": "return", "kind": "return", "fields": {"received": True}})
        self.apply("grant", "lead", grant())

    def apply(self, kind, actor, data):
        before = deepcopy(self.state)
        result = transition(self.state, Event(kind, actor, data), self.spec)
        self.assertEqual(self.state, before, "reference must be pure")
        self.state = result.state
        return result

    def propose(self, tool="refund", actor="agent", arguments=None, **claims):
        return self.apply("propose", actor, {"tool": tool, "arguments": deepcopy(ARGS if arguments is None else arguments), **claims})

    def execute(self, token, actor="agent", arguments=None, **extra):
        return self.apply("execute", actor, {"token": token, "arguments": deepcopy(ARGS if arguments is None else arguments), **extra})

    def add_duty(self):
        self.spec = policy(duties=True)
        return self.apply("record", "claims", {"id": "C", "kind": "claim", "fields": {**ARGS, "owed": True}})

    def ordered_report(self):
        return next(d for d in self.state["duties"].values() if d.get("origin_order") == "bad")

    def test_unknown_never_counts_as_no_prohibition(self):
        expression = {"eq": [{"fact": ["missing", "allowed"]}, {"literal": True}]}
        self.assertEqual(rule_result(expression, self.state, {}), UNKNOWN)
        self.assertEqual(rule_result({"exists": "missing"}, self.state, {}), VIOLATED)
        self.apply("configuration", "configuration", {"rules": [Rule("unknown", "prohibition", ("refund",), expression)]})
        self.assertEqual(self.propose().outcome, "HOLD")

    def test_unrelated_change_voids_token_and_permits_replacement(self):
        old = self.propose().detail["token"]
        self.apply("grant", "lead", grant("unrelated", grantee="elsewhere"))
        self.assertEqual(self.execute(old).outcome, "rejected")
        replacement = self.propose()
        self.assertEqual(replacement.outcome, "PERMIT")
        self.assertNotEqual(replacement.detail["token"], old)

    def test_unchanged_prohibition_survives_re_evaluation(self):
        self.apply("record", "carrier", {"id": "return", "kind": "return", "fields": {"received": False}})
        self.assertEqual(self.propose().outcome, "PROHIBIT")
        self.assertEqual(self.propose().outcome, "repeat")
        self.apply("grant", "lead", grant("unrelated", grantee="elsewhere"))
        self.assertEqual(self.propose().outcome, "PROHIBIT")

    def test_absent_record_insertion_invalidates_other_approval(self):
        token = self.propose("read").detail["token"]
        self.apply("record", "carrier", {"id": "new-record", "kind": "return", "fields": {"received": True}})
        self.assertEqual(self.execute(token).outcome, "rejected")

    def test_actor_and_exact_arguments_bound(self):
        token = self.propose().detail["token"]
        self.assertEqual(self.execute(token, actor="someone-else").outcome, "rejected")
        self.assertEqual(self.execute(token, arguments=dict(ARGS, amount_minor=999)).outcome, "rejected")
        self.assertEqual(self.execute(token).outcome, "committed")
        self.assertEqual(self.execute(token).outcome, "rejected")

    def test_two_tokens_one_revision_only_one_can_commit(self):
        one = self.propose(arguments=dict(ARGS, amount_minor=500)).detail["token"]
        two = self.propose(arguments=dict(ARGS, amount_minor=499)).detail["token"]
        revision = self.state["revision"]
        result = self.execute(one, arguments=dict(ARGS, amount_minor=500))
        self.assertEqual(result.detail["receipt"]["pre_transaction_revision"], revision)
        self.assertEqual(self.state["revision"], revision + 1)
        self.assertEqual(self.execute(two, arguments=dict(ARGS, amount_minor=499)).outcome, "rejected")

    def test_every_injected_boundary_aborts_all_changes(self):
        token = self.propose().detail["token"]
        before = deepcopy(self.state)
        for boundary in ("validate", "stage", "consume", "effect", "duties", "receipt", "revision", "commit"):
            with self.subTest(boundary=boundary):
                self.assertEqual(self.execute(token, fail_at=boundary).outcome, "rejected")
                self.assertEqual(self.state, before)
        self.assertEqual(self.execute(token, staged_effect={"wrong": "effect"}).outcome, "rejected")
        self.assertEqual(self.state, before)

    def test_expiry_processed_before_execution(self):
        token = self.propose(ttl=1).detail["token"]
        self.apply("tick", "clock", {"step": 1})
        self.assertEqual(self.execute(token).outcome, "rejected")

    def test_revocation_and_regrant_do_not_reset_totals(self):
        token = self.propose().detail["token"]
        self.execute(token)
        self.apply("revoke", "lead", {"id": "G"})
        self.apply("grant", "lead", grant())
        self.assertEqual(self.propose().outcome, "REFUSE")
        self.assertEqual(self.state["totals"]["O"], 1000)

    def test_parent_revocation_invalidates_child(self):
        root = grant("ROOT", grantee="delegate")
        self.apply("grant", "lead", root)
        self.apply("grant", "delegate", grant("CHILD", parent="ROOT", grantor="delegate"))
        self.apply("revoke", "lead", {"id": "G"})
        token = self.propose().detail["token"]
        self.apply("revoke", "lead", {"id": "ROOT"})
        self.assertEqual(self.execute(token).outcome, "rejected")
        self.assertEqual(self.propose().outcome, "REFUSE")

    def test_authority_can_use_a_complete_alternative_grant(self):
        self.apply("grant", "lead", grant("A-small", limit=1))
        self.assertEqual(self.propose().outcome, "PERMIT")

    def test_unknown_live_condition_is_hold(self):
        conditioned = grant()
        conditioned["conditions"] = [{"fact": ["unknown", "allowed"]}]
        self.apply("grant", "lead", conditioned)
        self.assertEqual(self.propose().outcome, "HOLD")

    def test_no_authorization_declaration_cannot_permit(self):
        self.apply("configuration", "configuration", {"authorizations": []})
        self.assertEqual(self.propose().outcome, "REFER")

    def test_reviewer_cannot_supply_missing_grant_unknown_evidence_or_tool(self):
        self.apply("resolution", "reviewer", {"question_id": "Q", "jurisdiction": "refunds", "answer": True})
        self.apply("revoke", "lead", {"id": "G"})
        self.assertEqual(self.propose().outcome, "REFUSE")
        self.assertEqual(self.propose("unregistered").outcome, "REJECT")
        self.apply("grant", "lead", grant())
        self.apply("configuration", "configuration", {"rules": [Rule("missing", "support", ("refund",), {"fact": ["absent", "value"]})]})
        self.assertEqual(self.propose().outcome, "HOLD")

    def test_wrong_reviewer_or_jurisdiction_cannot_answer(self):
        before = deepcopy(self.state)
        self.assertEqual(self.apply("resolution", "agent", {"question_id": "Q", "jurisdiction": "refunds", "answer": True}).outcome, "rejected")
        self.assertEqual(self.apply("resolution", "reviewer", {"question_id": "Q", "jurisdiction": "other", "answer": True}).outcome, "rejected")
        self.assertEqual(self.state["revision"], before["revision"])
        self.assertEqual(self.state["records"], before["records"])
        self.assertEqual(len(self.state["history"]), len(before["history"]) + 2)

    def test_claimed_actor_and_order_reference_do_not_control_reports(self):
        self.apply("order", "lead", {"id": "O1", "recipient": "agent", "tool": "refund",
                   "requested_effects": [{"tool": "refund", "arguments": {"claim_id": "C"}, "prohibited_effects": ["truthful-return"]}], "matter": "refunds", "disclosure": ["private"]})
        self.apply("order", "lead", {"id": "other", "recipient": "agent", "tool": "refund",
                   "requested_effects": [{"tool": "refund", "arguments": {"claim_id": "unrelated"}, "prohibited_effects": ["truthful-return"]}], "matter": "refunds", "disclosure": ["private"]})
        self.apply("record", "carrier", {"id": "return", "kind": "return", "fields": {"received": False}})
        self.propose(acting_party="lead", order_reference="other")
        reports = [d for d in self.state["duties"].values() if d["kind"] == "report"]
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["recipient"], "officer")
        self.propose()
        self.assertEqual(len(self.state["duties"]), 1)

    def test_duty_engine_runs_without_proposal_and_overdue_blocks_closure(self):
        self.add_duty()
        self.assertEqual(self.state["duties"]["owed:C"]["resolution"], "unresolved")
        self.apply("tick", "clock", {"step": 3})
        self.assertTrue(self.state["duties"]["owed:C"]["overdue"])
        self.assertEqual(self.propose("close", arguments={"case_id": "case"}).outcome, "REFUSE")

    def test_refund_receipt_is_bound_to_duty_and_corrected_evidence_reopens_case(self):
        self.add_duty()
        token = self.propose().detail["token"]
        self.execute(token)
        duty = self.state["duties"]["owed:C"]
        self.assertEqual(duty["resolution"], "discharged")
        close = self.propose("close", arguments={"case_id": "case"}).detail["token"]
        self.execute(close, arguments={"case_id": "case"})
        record_id = duty["basis"][0]["record_id"]
        original = self.state["records"][record_id][-1]["fields"]
        self.apply("record", "payments", {"id": record_id, "kind": "settlement", "fields": dict(original, settled=False)})
        self.assertEqual(self.state["duties"]["owed:C"]["resolution"], "unresolved")
        self.assertFalse(self.state["cases"]["case"]["closed"])
        self.assertTrue(any(h["event"] == "discharged" for h in self.state["duties"]["owed:C"]["history"]))
        self.assertEqual(self.state["totals"], {})
        self.assertEqual(len(self.state["receipts"]), 2, "actual prior effects remain in history")

    def test_corrected_release_basis_reopens_duty_and_case(self):
        self.add_duty()
        withdrawal = {"claim_id": "C", "claimant": "customer", "withdrawn": True}
        self.apply("record", "customer", {"id": "withdraw", "kind": "withdrawal", "fields": withdrawal})
        self.assertEqual(self.state["duties"]["owed:C"]["resolution"], "unresolved")
        self.apply("record", "customer", {"id": "release", "kind": "release_determination", "fields": dict(withdrawal, substantive_basis="claimant withdrew", evidence_id="withdraw", evidence_version=1)})
        self.assertEqual(self.state["duties"]["owed:C"]["resolution"], "released")
        token = self.propose("close", arguments={"case_id": "case"}).detail["token"]
        self.execute(token, arguments={"case_id": "case"})
        self.apply("record", "customer", {"id": "release", "kind": "release_determination", "fields": dict(withdrawal, substantive_basis="claimant withdrew", evidence_id="withdraw", evidence_version=1, withdrawn=False)})
        self.assertEqual(self.state["duties"]["owed:C"]["resolution"], "unresolved")
        self.assertFalse(self.state["cases"]["case"]["closed"])

    def test_wrong_claim_receipt_and_false_completion_do_not_discharge(self):
        self.add_duty()
        receipt = dict(ARGS, claim_id="other", settled=True, transaction_id="P", allocation_id="A", order_id="O")
        self.apply("record", "payments", {"id": "P", "kind": "settlement", "fields": receipt})
        self.assertEqual(self.state["duties"]["owed:C"]["resolution"], "unresolved")
        self.assertEqual(self.apply("record", "agent", {"id": "fake", "kind": "settlement", "fields": dict(receipt, claim_id="C")}).outcome, "rejected")

    def test_one_payment_allocation_cannot_discharge_two_duties(self):
        self.add_duty()
        second = deepcopy(self.spec.duty_rules[0]); second["id"] = "also-owed"
        self.spec = replace(self.spec, duty_rules=self.spec.duty_rules + (second,))
        self.apply("tick", "clock", {"step": 1})
        token = self.propose().detail["token"]
        self.execute(token)
        resolved = [d for d in self.state["duties"].values() if d["resolution"] == "discharged"]
        self.assertEqual(len(resolved), 1)

    def test_revocation_offer_never_implies_acceptance(self):
        self.add_duty()
        self.apply("revoke", "lead", {"id": "G"})
        duty = self.state["duties"]["owed:C"]
        self.assertEqual((duty["owner"], duty["offered_to"], duty["resolution"]), ("agent", "fallback", "unresolved"))
        self.assertEqual(self.apply("accept", "stranger", {"duty_id": "owed:C"}).outcome, "rejected")
        self.apply("accept", "fallback", {"duty_id": "owed:C"})
        self.assertEqual(self.state["duties"]["owed:C"]["owner"], "fallback")
        self.assertEqual(self.state["duties"]["owed:C"]["resolution"], "unresolved")

    def test_unaccepted_fallback_becomes_unowned_and_reports(self):
        self.add_duty()
        self.apply("revoke", "lead", {"id": "G"})
        self.apply("tick", "clock", {"step": 1})
        self.assertIsNone(self.state["duties"]["owed:C"]["owner"])
        self.assertIn("report:unowned:owed:C", self.state["duties"])
        self.assertEqual(self.propose("close", arguments={"case_id": "case"}).outcome, "REFUSE")

    def test_resolution_record_invalidates_outstanding_token(self):
        token = self.propose().detail["token"]
        self.apply("resolution", "reviewer", {"question_id": "Q", "jurisdiction": "refunds", "answer": True})
        self.assertEqual(self.execute(token).outcome, "rejected")
        self.assertEqual(self.state["records"]["resolution:Q"][-1]["writer"], "reviewer")

    def test_assertion_never_authorizes(self):
        self.apply("assertion", "agent", {"id": "return", "fields": {"received": True}})
        self.assertFalse(self.state["records"]["assertion:agent:return"][-1]["evidential"])
        expression = {"fact": ["assertion:agent:return", "received"]}
        self.assertEqual(rule_result(expression, self.state, {}), UNKNOWN)

    def test_repeated_input_is_deterministic(self):
        event = Event("propose", "agent", {"tool": "refund", "arguments": ARGS})
        self.assertEqual(transition(self.state, event, self.spec), transition(self.state, event, self.spec))

    def test_negative_query_is_recorded_in_the_justification(self):
        self.apply("configuration", "configuration", {"rules": [
            Rule("not-paid", "support", ("refund",), {"not": {"exists": "prior-payment"}})]})
        token = self.propose().detail["token"]
        warrant = self.state["warrants"][self.state["tokens"][token]["warrant"]]
        query = warrant["justification"]["rule_results"][0]["queries"][0]
        self.assertEqual((query["record_id"], query["version"]), ("prior-payment", None))

    def test_report_is_not_discharged_by_send_or_wrong_ack(self):
        self.apply("grant", "finance", dict(grant("REPORT", grantee="gateway", grantor="finance"), tools=["report"]))
        self.apply("order", "lead", {"id": "bad", "recipient": "agent", "tool": "refund",
                   "requested_effects": [{"tool": "refund", "arguments": {"claim_id": "C"}, "prohibited_effects": ["truthful-return"]}], "matter": "refunds", "disclosure": ["private"]})
        self.apply("record", "carrier", {"id": "return", "kind": "return", "fields": {"received": False}})
        self.propose()
        report_id = self.ordered_report()["id"]
        args = {"duty_id": report_id, "recipient": "officer"}
        token = self.propose("report", actor="gateway", arguments=args).detail["token"]
        self.execute(token, actor="gateway", arguments=args)
        self.assertEqual(self.state["duties"][report_id]["resolution"], "unresolved")
        self.apply("record", "fallback-officer", {"id": "wrong-ack", "kind": "report_ack", "fields": {
            "report_id": report_id, "recipient": "officer", "report_version": 1, "acknowledged": True}})
        self.assertEqual(self.state["duties"][report_id]["resolution"], "unresolved")
        self.apply("record", "officer", {"id": "ack", "kind": "report_ack", "fields": {
            "report_id": report_id, "recipient": "officer", "report_version": 1, "acknowledged": True}})
        self.assertEqual(self.state["duties"][report_id]["resolution"], "discharged")

    def test_report_fallback_and_no_eligible_route_remain_visible(self):
        self.apply("order", "lead", {"id": "bad", "recipient": "agent", "tool": "refund",
                   "requested_effects": [{"tool": "refund", "arguments": {"claim_id": "C"}, "prohibited_effects": ["truthful-return"]}], "matter": "refunds", "disclosure": ["private"]})
        self.apply("record", "carrier", {"id": "return", "kind": "return", "fields": {"received": False}})
        self.propose()
        self.apply("tick", "clock", {"step": 2})
        self.assertEqual(self.ordered_report()["recipient"], "fallback-officer")
        self.apply("configuration", "configuration", {"parties": {}})
        self.assertIsNone(self.ordered_report()["recipient"])
        self.assertEqual(self.ordered_report()["resolution"], "unresolved")

    def test_equal_python_values_do_not_match_different_json_types(self):
        self.assertEqual(rule_result({"eq": [{"literal": True}, {"literal": 1}]}, self.state, {}), VIOLATED)

    def test_due_external_events_precede_duty_reconciliation(self):
        self.spec = policy(duties=True)
        self.apply("tick", "clock", {"step": 3, "due_records": [{"id": "C", "kind": "claim", "source": "claims",
                   "fields": {**ARGS, "owed": True}}]})
        self.assertTrue(self.state["duties"]["owed:C"]["overdue"])
        self.assertEqual(self.propose("close", arguments={"case_id": "case"}).outcome, "REFUSE")

    def test_duty_declarations_reach_a_fixed_point_independent_of_declaration_order(self):
        self.spec = policy(duties=True)
        dependent = deepcopy(self.spec.duty_rules[0])
        dependent["id"] = "dependent"
        dependent["when"] = {"eq": [{"duty": ["owed:C", "resolution"]}, {"literal": "unresolved"}]}
        self.spec = replace(self.spec, duty_rules=(dependent,) + self.spec.duty_rules)
        self.apply("record", "claims", {"id": "C", "kind": "claim", "fields": {**ARGS, "owed": True}})
        self.assertEqual(set(self.state["duties"]), {"dependent:C", "owed:C"})

    def test_same_issuer_claim_and_prohibited_effect_are_one_matter(self):
        self.apply("order", "lead", {"id": "bad", "recipient": "agent", "tool": "refund",
                   "requested_effects": [{"tool": "refund", "arguments": {"claim_id": "C"}, "prohibited_effects": ["truthful-return"]}], "matter": "refunds", "disclosure": ["private"]})
        self.apply("record", "carrier", {"id": "return", "kind": "return", "fields": {"received": False}})
        self.propose()
        self.propose(arguments=dict(ARGS, amount_minor=500))
        self.propose()
        self.assertEqual(len([d for d in self.state["duties"].values() if d.get("origin_order") == "bad"]), 1)


class ReferenceIndependenceTests(unittest.TestCase):
    def test_reference_has_no_core_or_model_client_imports(self):
        directory = Path(__file__).parents[1] / "taa_gateway_reference"
        allowed = {"copy", "dataclasses", "json", "hashlib"}
        for path in directory.glob("*.py"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertTrue({alias.name.split('.')[0] for alias in node.names} <= allowed)
                if isinstance(node, ast.ImportFrom):
                    self.assertIn(node.module.split('.')[0], allowed)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {"eval", "exec", "__import__"})


if __name__ == "__main__":
    unittest.main()
