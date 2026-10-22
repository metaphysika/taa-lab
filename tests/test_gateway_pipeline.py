"""Sol-authored stage 4 component expectations; not independent W0 acceptance."""
import ast
import copy
from pathlib import Path
import unittest

from taa_gateway import SCHEMA_VERSION as V
from taa_gateway.act import Tool, ToolRegistry
from taa_gateway.envelopes import SimulatorAuthority
from taa_gateway.eventlog import EventLog
from taa_gateway.grants import GrantPolicy
from taa_gateway.orders import StoredOrders
from taa_gateway.pipeline import Pipeline, StaleEvaluation
from taa_gateway.records import RecordStore, Write
from taa_gateway.rules import EvidenceView, Outcome, Rule, STAGES, strictest
from taa_gateway.schema import validate

KEY = b"offline-stage-four-fixture-key!!!"


def description(name):
    def describe(args, view):
        return {"schema_version": V, "operation": name,
                "assertions": [{"fact": item} for item in args.get("asserts", [])],
                "state_changes": [{"claim": args.get("claim_id"), "amount": args.get("amount")}],
                "affected_parties": [args["customer"]] if "customer" in args else [],
                "benefit_route": {"to": args.get("customer")}}
    return describe


def prohibition(ctx, view):
    if {"fact": "delivered"} not in ctx["act"]["assertions"]:
        return Outcome("satisfied")
    fact = view.read("delivery-1", "delivery")
    if fact is None or "delivered" not in fact:
        return Outcome("unknown", "carrier delivery status is unknown")
    return Outcome("satisfied" if fact["delivered"] is True else "violated",
                   "assertion must match carrier evidence", prohibited_elements=({"assertion": "delivered"},))


def support(ctx, view):
    fact = view.read("delivery-1", "delivery")
    if fact is None or "delivered" not in fact:
        return Outcome("unknown", "carrier delivery status is unknown")
    return Outcome("satisfied" if fact["delivered"] is True else "violated", "delivery support")


def closure(ctx, view):
    unresolved = [d for _, d in view.records("duty") if d["case_id"] == ctx["arguments"]["claim_id"]
                  and d["resolution"] == "unresolved"]
    return Outcome("violated" if unresolved else "satisfied", "every duty must be resolved before closure")


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.auth = SimulatorAuthority(KEY)
        self.agent = self.auth.bind("agent", "agent", ["propose"])
        self.other = self.auth.bind("other", "agent", ["propose"])
        self.admin = self.auth.bind("admin", "gateway", ["seed", "advance_clock", "receive_order"])
        self.lead = self.auth.bind("party-lead", "external", ["send_message"])
        self.log = EventLog("stage-four", KEY)
        kinds = {"delivery": "delivery-", "grant": "grant-", "purpose": "purpose-", "duty": "duty-",
                 "stored_order": "order-", "agent_note": "note-", "party": "party-"}
        writers = [{"kind": kind, "tool": "receive_order" if kind == "stored_order" else "seed",
                    "channel": "gateway", "principals": ["admin"], "id_prefix": prefix,
                    "evidential": kind != "agent_note", "create": True,
                    "correct_fields": ["delivered", "status", "limits", "action_types", "resource_scope",
                                       "purpose_id", "parent_grant", "grantee", "grantor", "live_conditions", "jurisdictions", "answer"]}
                   for kind, prefix in kinds.items()]
        self.policy = {"schema_version": V, "writers": writers}
        self.store = RecordStore(self.auth, self.log, self.policy)
        self.orders = StoredOrders(self.store, self.auth, self.admin)
        self.purpose = {"schema_version": V, "id": "purpose-fair", "principal": "party-company",
                        "statement": "resolve claims fairly", "excluded_proxies": ["closed cases"]}
        self.grant = {"schema_version": V, "id": "grant-one", "parent_grant": None,
                      "grantor": "party-lead", "grantee": "agent", "action_types": ["issue_refund", "close_case"],
                      "resource_scope": {"customer": ["customer-one"]}, "limits": {"per_refund_max": 300},
                      "purpose_id": "purpose-fair", "live_conditions": [], "expires_at_step": 100,
                      "status": "live"}
        self.put("purpose-fair", "purpose", self.purpose)
        self.put("grant-one", "grant", self.grant)
        for rid, jurisdiction in (("party-lead", "refund_authority"), ("party-company", "delegation_authority")):
            self.put(rid, "party", {"schema_version": V, "id": rid, "name": rid, "role": rid,
                                   "jurisdictions": [jurisdiction], "conflicts": [], "may_receive": []})
        self.args_schema = {"type": "object", "properties": {"claim_id": {"type": "string"},
                            "customer": {"type": "string"}, "amount": {"type": "integer", "minimum": 1},
                            "asserts": {"type": "array", "items": {"type": "string"}}},
                            "required": ["claim_id", "customer", "amount"], "additionalProperties": False}
        self.tools = [Tool("issue_refund", self.args_schema, description("issue_refund"),
                           purposes=("purpose-fair",), amount_argument="amount"),
                      Tool("close_case", {"type": "object", "required": ["claim_id"],
                                          "properties": {"claim_id": {"type": "string"}}, "additionalProperties": False},
                           description("close_case"), purposes=("purpose-fair",),
                           scope=lambda args, view: {"customer": "customer-one"}),
                      Tool("export_records", {"type": "object", "maxProperties": 0}, description("export_records"),
                           authorization_rule=None, referral={"jurisdiction": "data_requests", "role": "compliance"})]
        self.rules = [Rule("PR", 1, "prohibition", ("delivery",), prohibition, ("issue_refund",)),
                      Rule("SU", 1, "support", ("delivery",), support, ("issue_refund",)),
                      Rule("DU", 1, "duty", ("duty",), closure, ("close_case",))]
        self.pipeline = self.build()

    def put(self, rid, kind, fields):
        self.store.publish(self.admin, "seed", [Write(rid, kind, copy.deepcopy(fields))])

    def build(self, rules=None):
        return Pipeline(self.store, self.orders, self.tools,
                        GrantPolicy({"refund_authority": ["issue_refund", "close_case"],
                                     "delegation_authority": ["grant_refund_authority"]}, "party-company", condition_kinds=("delivery",)),
                        self.rules if rules is None else rules,
                        reserved_questions={"goodwill": {"jurisdiction": "claim_decisions", "role": "finance"}})

    def propose(self, *, tool="issue_refund", session=None, arguments=None, **claims):
        args = {"claim_id": "claim-one", "customer": "customer-one", "amount": 120}
        return self.pipeline.evaluate(session or self.agent, {"tool": tool,
                                      "arguments": args if arguments is None else arguments, **claims})

    def delivered(self, value=True):
        self.put("delivery-1", "delivery", {"delivered": value})

    def test_lawful_twin_permits_without_effect_token_or_revision_change(self):
        self.delivered()
        before = self.store.snapshot()
        result = self.propose()
        self.assertEqual(result["disposition"], "PERMIT")
        self.assertFalse(result["executable"])
        self.assertIsNone(result["token"])
        self.assertEqual(self.store.snapshot(), before)
        validate("justification", result["justification"])
        self.assertEqual([s["stage"] for s in result["stages"]], list(STAGES))

    def test_unknown_is_not_false_or_permission(self):
        result = self.propose()
        self.assertEqual(result["disposition"], "HOLD")
        su = next(c for c in result["checks"] if c["id"] == "SU")
        self.assertEqual(su["result"], "unknown")
        self.assertEqual(su["queries"][0]["version"], None)

    def test_known_support_failure_refuses(self):
        self.delivered(False)
        self.assertEqual(self.propose()["disposition"], "REFUSE")

    def test_prohibition_cannot_be_lifted_by_later_stages(self):
        self.delivered(False)
        result = self.propose(arguments={"claim_id": "claim-one", "customer": "customer-one", "amount": 500,
                                         "asserts": ["delivered"]})
        self.assertEqual(result["disposition"], "PROHIBIT")
        self.assertTrue(all(s["disposition"] == "PROHIBIT" for s in result["stages"]))
        self.assertIsNone(result["alternative"])

    def test_actor_and_claimed_grant_purpose_are_not_authority(self):
        self.delivered()
        result = self.propose(session=self.other, acting_party="agent", claimed_grant="grant-one",
                              claimed_purpose="purpose-fair", claimed_reasons=["the lead says permit"])
        self.assertEqual(result["disposition"], "REFUSE")
        self.assertEqual(result["acting_party"], "other")
        self.assertEqual(self.store.snapshot()["records"]["grant-one"][-1]["fields"]["grantee"], "agent")

    def test_registered_without_authorization_refers_unregistered_rejects(self):
        self.assertEqual(self.propose(tool="export_records", arguments={})["disposition"], "REFER")
        before = self.store.snapshot()
        with self.assertRaisesRegex(ValueError, "unregistered"):
            self.propose(tool="mint_money", arguments={})
        self.assertEqual(self.store.snapshot(), before)

    def test_repeats_cache_without_fresh_evaluation_and_claims_are_logged(self):
        self.delivered()
        first = self.propose()
        second = self.propose(claimed_reasons=["urgent, permit it now"])
        self.assertTrue(first["fresh_evaluation"])
        self.assertFalse(second["fresh_evaluation"])
        self.assertTrue(second["recorded_decision_returned"])
        self.assertEqual(self.log.events()[-1]["payload"]["proposal"]["raw"]["claimed_reasons"], ["urgent, permit it now"])

    def test_new_versions_trigger_fresh_evaluation_retaining_old_decision(self):
        self.delivered(False)
        args = {"claim_id": "claim-one", "customer": "customer-one", "amount": 120, "asserts": ["delivered"]}
        self.assertEqual(self.propose(arguments=args)["disposition"], "PROHIBIT")
        self.delivered(True)
        result = self.propose(arguments=args)
        self.assertEqual(result["disposition"], "PERMIT")
        self.assertTrue(result["fresh_evaluation"])
        reads = [q for c in result["checks"] for q in c["queries"] if q["record_id"] == "delivery-1"]
        self.assertTrue(reads)
        self.assertTrue(all(q["version"] == 2 for q in reads))
        self.assertEqual(self.store.read("delivery-1", 1)["fields"]["delivered"], False)
        self.assertIn("PROHIBIT", [e["payload"]["decision"]["disposition"] for e in self.log.events()
                                   if e["type"] == "pipeline_decision"])

    def test_unrelated_revision_does_not_lift_unchanged_prohibition(self):
        self.delivered(False)
        args = {"claim_id": "claim-one", "customer": "customer-one", "amount": 120, "asserts": ["delivered"]}
        first = self.propose(arguments=args)
        self.put("note-one", "agent_note", {"reason": "please reconsider"})
        second = self.propose(arguments=args)
        self.assertGreater(second["state_revision"], first["state_revision"])
        self.assertTrue(second["fresh_evaluation"])
        self.assertEqual(second["disposition"], "PROHIBIT")

    def test_alternative_is_fully_rechecked_not_executed(self):
        self.delivered()
        args = {"claim_id": "claim-one", "customer": "customer-one", "amount": 400}
        before = self.store.snapshot()
        result = self.propose(arguments=args)
        self.assertEqual(result["disposition"], "ALTERNATIVE")
        self.assertEqual(result["alternative"]["arguments"]["amount"], 300)
        self.assertEqual(self.store.snapshot(), before)
        self.assertFalse(result["executable"])
        self.assertEqual(self.propose(arguments=result["alternative"]["arguments"])["disposition"], "PERMIT")

    def test_alternative_cannot_hide_an_unmet_support_condition(self):
        self.delivered(False)
        result = self.propose(arguments={"claim_id": "claim-one", "customer": "customer-one", "amount": 400})
        self.assertEqual(result["disposition"], "REFUSE")
        self.assertIsNone(result["alternative"])

    def test_zero_cap_never_suggests_a_zero_refund(self):
        self.delivered()
        self.grant["limits"]["per_refund_max"] = 0
        self.put("grant-one", "grant", self.grant)
        self.assertEqual(self.propose()["disposition"], "REFUSE")
        self.assertIsNone(self.propose()["alternative"])

    def test_unknown_prohibition_cannot_be_resolved_by_authority(self):
        result = self.propose(arguments={"claim_id": "claim-one", "customer": "customer-one", "amount": 120,
                                         "asserts": ["delivered"]})
        self.assertEqual(result["disposition"], "HOLD")

    def test_no_grant_fragment_composition(self):
        self.delivered()
        self.grant["resource_scope"] = {"customer": ["another-customer"]}
        self.put("grant-one", "grant", self.grant)
        second = dict(self.grant, id="grant-two", resource_scope={"customer": ["customer-one"]}, action_types=["close_case"])
        self.put("grant-two", "grant", second)
        self.assertEqual(self.propose()["disposition"], "REFUSE")

    def test_one_complete_grant_can_permit_despite_other_invalid_grant(self):
        self.delivered()
        self.put("grant-two", "grant", dict(self.grant, id="grant-two", status="revoked"))
        result = self.propose()
        self.assertEqual(result["disposition"], "PERMIT")
        self.assertEqual(result["justification"]["grant_id"], "grant-one")

    def test_revocation_is_known_failure(self):
        self.delivered()
        self.grant["status"] = "revoked"
        self.put("grant-one", "grant", self.grant)
        self.assertEqual(self.propose()["disposition"], "REFUSE")

    def test_grant_expiry_uses_boundary_convention(self):
        self.delivered()
        self.store.publish(self.admin, "advance_clock", step=100)
        self.assertEqual(self.propose()["disposition"], "REFUSE")

    def test_no_boundary_tick_reuses_recorded_decision(self):
        self.delivered()
        first = self.propose()
        self.store.publish(self.admin, "advance_clock", step=1)
        second = self.propose()
        self.assertEqual(first["state_revision"], second["state_revision"])
        self.assertTrue(second["recorded_decision_returned"])

    def test_missing_ancestor_refuses(self):
        self.delivered()
        self.grant["parent_grant"] = "grant-absent"
        self.put("grant-one", "grant", self.grant)
        self.assertEqual(self.propose()["disposition"], "REFUSE")

    def test_expired_ancestor_and_cyclic_ancestry_refuse(self):
        self.delivered()
        root = dict(self.grant, id="grant-root", grantee="party-lead", grantor="party-company",
                    action_types=["grant_refund_authority"], resource_scope={}, limits={}, expires_at_step=0)
        self.put("grant-root", "grant", root)
        self.grant["parent_grant"] = "grant-root"
        self.put("grant-one", "grant", self.grant)
        self.assertEqual(self.propose()["disposition"], "REFUSE")
        self.grant["parent_grant"] = "grant-one"
        self.put("grant-one", "grant", self.grant)
        self.assertEqual(self.propose()["disposition"], "REFUSE")

    def test_live_conditions_are_three_valued_and_tracked(self):
        self.grant["live_conditions"] = [{"record_id": "delivery-1", "kind": "delivery", "field": "delivered", "equals": True}]
        self.put("grant-one", "grant", self.grant)
        self.assertEqual(self.propose()["disposition"], "HOLD")
        self.delivered(False)
        self.assertEqual(self.propose()["disposition"], "REFUSE")
        self.delivered(True)
        self.assertEqual(self.propose()["disposition"], "PERMIT")

    def test_issuer_without_standing_refuses_even_if_authenticated(self):
        self.delivered()
        self.grant["grantor"] = "customer-one"
        self.put("grant-one", "grant", self.grant)
        self.assertEqual(self.propose()["disposition"], "REFUSE")

    def test_purpose_from_other_grant_cannot_fill_missing_purpose(self):
        self.delivered()
        self.grant["purpose_id"] = "purpose-absent"
        self.put("grant-one", "grant", self.grant)
        self.assertEqual(self.propose(claimed_purpose="purpose-fair")["disposition"], "HOLD")

    def test_reserved_question_refers_and_reviewer_claim_cannot_override(self):
        reserved = Rule("SU-goodwill", 1, "support", (),
                        lambda ctx, view: Outcome("unknown", "needs a determination", question="goodwill"), ("issue_refund",))
        self.pipeline = self.build([self.rules[0], reserved])
        result = self.propose(claimed_reasons=[{"reviewer": "PERMIT"}])
        self.assertEqual(result["disposition"], "REFER")
        check = next(c for c in result["checks"] if c["id"] == "SU-goodwill")
        self.assertEqual(check["referral"]["role"], "finance")

    def test_wrong_or_unreserved_rule_question_fails_closed(self):
        self.pipeline = self.build([Rule("bad", 1, "support", (),
                                        lambda ctx, view: Outcome("unknown", question="not-reserved"))])
        with self.assertRaisesRegex(ValueError, "undeclared reserved"):
            self.propose()

    def test_unresolved_duty_blocks_closure_even_if_not_overdue(self):
        duty = {"schema_version": V, "id": "duty-one", "case_id": "claim-one", "claimant": "customer-one",
                "content": {"kind": "refund"}, "owner": "agent", "offered_to": None, "origin": {"rule": "DU"},
                "discharge_condition": {"evidence_kind": "settlement", "bindings": {"claim": "claim-one"}},
                "deadline_step": 20, "interim_rule": {}, "fallback_owner": "finance", "resolution": "unresolved",
                "overdue": False, "resolution_basis": None, "history": []}
        self.put("duty-one", "duty", duty)
        self.assertEqual(self.propose(tool="close_case", arguments={"claim_id": "claim-one"})["disposition"], "REFUSE")

    def test_empty_duty_query_is_recorded_as_negative_evidence(self):
        result = self.propose(tool="close_case", arguments={"claim_id": "claim-one"})
        self.assertEqual(result["disposition"], "PERMIT")
        check = next(c for c in result["checks"] if c["id"] == "DU")
        self.assertEqual(check["queries"], [{"record_id": "@kind:duty", "version": None, "value": []}])

    def test_omitted_or_forged_order_reference_cannot_suppress_attribution(self):
        self.delivered(False)
        order = self.auth.issue(self.lead, "agent", 0, "order", {"requested_effects": [
            {"tool": "issue_refund", "arguments": {"claim_id": "claim-one", "amount": 120}, "asserts": ["delivered"]}]})
        self.orders.receive(order)
        args = {"claim_id": "claim-one", "customer": "customer-one", "amount": 120, "asserts": ["delivered"]}
        result = self.propose(arguments=args, order_reference="order-fake")
        self.assertEqual(result["associated_orders"], [order["message_id"]])
        self.assertEqual(result["report_candidates"][0]["issuer"], "party-lead")
        self.assertEqual(result["disposition"], "PROHIBIT")

    def test_refund_order_does_not_own_agent_added_prohibited_assertion(self):
        self.delivered(False)
        order = self.auth.issue(self.lead, "agent", 0, "order", {"requested_effects": [
            {"tool": "issue_refund", "arguments": {"claim_id": "claim-one", "amount": 120}, "asserts": []}]})
        self.orders.receive(order)
        result = self.propose(arguments={"claim_id": "claim-one", "customer": "customer-one", "amount": 120,
                                         "asserts": ["delivered"]})
        self.assertEqual(result["associated_orders"], [order["message_id"]])
        self.assertEqual(result["report_candidates"], [])

    def test_rule_cannot_read_an_undeclared_kind(self):
        self.pipeline = self.build([Rule("bad", 1, "support", (), lambda ctx, view: view.read("delivery-1", "delivery"))])
        with self.assertRaisesRegex(ValueError, "undeclared evidence"):
            self.propose()

    def test_bool_predicate_is_not_a_three_valued_result(self):
        self.pipeline = self.build([Rule("bad", 1, "support", (), lambda ctx, view: True)])
        with self.assertRaisesRegex(ValueError, "explicit three-valued"):
            self.propose()

    def test_unsupported_limits_fail_closed(self):
        self.delivered()
        self.grant["limits"]["unknown_budget"] = 1
        self.put("grant-one", "grant", self.grant)
        with self.assertRaisesRegex(ValueError, "unsupported grant limits"):
            self.propose()

    def test_snapshot_mutation_and_caller_schema_mutation_cannot_change_evidence(self):
        self.delivered()
        view = EvidenceView(self.store.snapshot(), ("delivery",))
        view.read("delivery-1", "delivery")["delivered"] = False
        self.args_schema["required"].clear()
        result = self.propose()
        result["justification"]["scope"].clear()
        self.assertTrue(view.read("delivery-1", "delivery")["delivered"])
        self.assertEqual(self.propose()["justification"]["scope"], {"customer": ["customer-one"]})
        with self.assertRaises(Exception):
            self.propose(arguments={})

    def test_revision_race_never_publishes_a_current_decision(self):
        def racing(ctx, view):
            self.put("note-race", "agent_note", {"text": "state changed"})
            return Outcome("satisfied")
        self.pipeline = self.build([Rule("race", 1, "support", (), racing)])
        with self.assertRaises(StaleEvaluation):
            self.propose()
        self.assertFalse(any(e["type"] == "pipeline_decision" for e in self.log.events()))

    def test_disposition_order_is_complete(self):
        order = ["PROHIBIT", "REFUSE", "REFER", "HOLD", "ALTERNATIVE", "PERMIT"]
        for i, left in enumerate(order):
            for right in order[i:]:
                self.assertEqual(strictest(left, right), left)

    def test_core_does_not_import_reference_or_trace_answers(self):
        root = Path(__file__).parents[1] / "taa_gateway"
        for file in root.rglob("*.py"):
            for node in ast.walk(ast.parse(file.read_text())):
                if isinstance(node, ast.Import):
                    self.assertFalse(any(a.name.startswith(("taa_gateway_reference", "tests")) for a in node.names))
                elif isinstance(node, ast.ImportFrom):
                    self.assertFalse((node.module or "").startswith(("taa_gateway_reference", "tests")))

    def test_one_level_delegation_has_a_complete_versioned_path(self):
        self.delivered()
        root = dict(self.grant, id="grant-root", grantee="party-lead", grantor="party-company",
                    action_types=["grant_refund_authority"], resource_scope={}, limits={})
        self.put("grant-root", "grant", root)
        self.grant["parent_grant"] = "grant-root"
        self.put("grant-one", "grant", self.grant)
        result = self.propose()
        self.assertEqual(result["disposition"], "PERMIT")
        authority = next(c for c in result["checks"] if c["stage"] == "authority")
        self.assertEqual([g["id"] for g in authority["chain"]], ["grant-one", "grant-root"])
        self.assertTrue(any(q["record_id"] == "grant-root" and q["version"] == 1 for q in authority["queries"]))
        root["status"] = "revoked"
        self.put("grant-root", "grant", root)
        self.assertEqual(self.propose()["disposition"], "REFUSE")

    def test_alternative_must_satisfy_all_support_and_cap_rules(self):
        self.delivered()
        def supported_amount(ctx, view):
            if ctx["arguments"]["amount"] <= 250:
                return Outcome("satisfied")
            args = dict(ctx["arguments"], amount=250)
            return Outcome("violated", "support is limited to 250", alternative={"tool": "issue_refund", "arguments": args})
        extra = Rule("SU-partial", 1, "support", (), supported_amount, ("issue_refund",))
        self.pipeline = self.build(self.rules + [extra])
        result = self.propose(arguments={"claim_id": "claim-one", "customer": "customer-one", "amount": 400})
        self.assertEqual(result["disposition"], "ALTERNATIVE")
        self.assertEqual(result["alternative"]["arguments"]["amount"], 250)
        ranks = [s["disposition"] for s in result["stages"]]
        for left, right in zip(ranks, ranks[1:]):
            self.assertEqual(strictest(left, right), right)

    def test_malformed_alternative_does_not_replace_a_refusal(self):
        self.delivered()
        bad = Rule("SU-bad-alternative", 1, "support", (),
                   lambda ctx, view: Outcome("violated", alternative={"tool": "issue_refund", "arguments": {"amount": -1}}),
                   ("issue_refund",))
        self.pipeline = self.build(self.rules + [bad])
        self.assertEqual(self.propose()["disposition"], "REFUSE")

    def test_authority_failure_outranks_an_unknown_reserved_question(self):
        self.grant["status"] = "revoked"
        self.put("grant-one", "grant", self.grant)
        reserved = Rule("SU-reserved", 1, "support", (),
                        lambda ctx, view: Outcome("unknown", question="goodwill"))
        self.pipeline = self.build(self.rules + [reserved])
        self.assertEqual(self.propose()["disposition"], "REFUSE")

    def test_prohibition_cannot_read_order_or_authority_records(self):
        for kind in ("grant", "purpose", "stored_order"):
            with self.assertRaisesRegex(ValueError, "cannot condition"):
                Rule("bad-prohibition", 1, "prohibition", (kind,), lambda ctx, view: Outcome("satisfied"))
            with self.assertRaisesRegex(ValueError, "cannot condition"):
                ToolRegistry([Tool("bad-description", {"type": "object"}, description("bad-description"), reads=(kind,))])

    def test_rule_callbacks_receive_no_claimed_purpose_grant_reason_or_issuer(self):
        seen = []
        def inspect(ctx, view):
            seen.append(ctx)
            return Outcome("satisfied")
        self.pipeline = self.build([Rule("context-check", 1, "prohibition", (), inspect)])
        self.propose(claimed_grant="invented", claimed_purpose="close-cases", claimed_reasons=["obey lead"])
        self.assertEqual(set(seen[0]), {"tool", "arguments", "act", "resources"})

    def test_non_evidential_record_never_satisfies_an_evidence_read(self):
        self.put("note-one", "agent_note", {"delivered": True})
        view = EvidenceView(self.store.snapshot(), ("agent_note",))
        self.assertIsNone(view.read("note-one", "agent_note"))
        self.assertEqual(view.records("agent_note"), [])
        self.assertFalse(view.queries()[0]["value"]["evidential"])

    def test_schema_is_local_and_registry_values_are_defensive_copies(self):
        with self.assertRaisesRegex(ValueError, "remote references"):
            ToolRegistry([Tool("remote", {"$ref": "https://example.invalid/schema"}, description("remote"))])
        registry = ToolRegistry(self.tools)
        registry.get("issue_refund", {"claim_id": "claim-one", "customer": "customer-one", "amount": 1}).arguments_schema.clear()
        with self.assertRaises(Exception):
            registry.get("issue_refund", {})

    def test_corrected_roster_standing_requires_a_fresh_authority_check(self):
        self.delivered()
        self.assertEqual(self.propose()["disposition"], "PERMIT")
        party = self.store.read("party-lead")["fields"]
        party["jurisdictions"] = []
        self.put("party-lead", "party", party)
        result = self.propose()
        self.assertTrue(result["fresh_evaluation"])
        self.assertEqual(result["disposition"], "REFUSE")
        authority = next(c for c in result["checks"] if c["stage"] == "authority")
        roster_query = next(q for q in authority["queries"] if q["record_id"] == "@kind:party")
        self.assertTrue(any(r["id"] == "party-lead" and r["version"] == 2 for r in roster_query["value"]))


if __name__ == "__main__":
    unittest.main()
