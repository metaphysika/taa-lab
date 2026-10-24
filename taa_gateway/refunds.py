"""Independent production refund policy and W0 input normalization.

Stage 5 covers effect/authorization primitives. Independent duty derivation,
discharge, reporting and full closure acceptance remain stage 6 capabilities.
No reference-model code, expected assertions or trace IDs are read here.
"""
from dataclasses import replace

from taa_gateway import SCHEMA_VERSION as V
from taa_gateway.act import Tool
from taa_gateway.envelopes import SimulatorAuthority
from taa_gateway.duties import DutyEngine
from taa_gateway.coverage import portion
from taa_gateway.eventlog import EventLog
from taa_gateway.executor import EffectPlan, Runtime
from taa_gateway.interim import RefundGrantPolicy
from taa_gateway.orders import StoredOrders
from taa_gateway.pipeline import Pipeline
from taa_gateway.records import RecordStore, Write
from taa_gateway.resolutions import StoredResolutions
from taa_gateway.roster import RosterInbox
from taa_gateway.rules import Outcome, Rule
from taa_gateway.serialization import copy_json

PREFIX = {"order": "sale:", "payment": "payment:", "claim": "claim:", "return_receipt": "return:",
          "carrier_record": "carrier:", "refund": "refund:", "chargeback": "chargeback:",
          "withdrawal": "withdrawal:", "resolution": "resolution:", "agent_note": "note:",
          "grant": "grant:", "purpose": "purpose:", "party": "party:", "stored_order": "order:",
          "report": "report:", "acknowledgment": "ack:", "acceptance": "accept:"}
DATA_KINDS = tuple(PREFIX)[:10]


def native_id(rid, kind):
    return PREFIX[kind] + rid


def abstract_id(rid):
    return rid.split(":", 1)[1] if ":" in rid else rid


def record(view, rid, kind):
    return view.read(native_id(rid.split("@v")[0], kind), kind)


def related(view, kind, **fields):
    return [(rid, row) for rid, row in view.records(kind) if all(row.get(k) == v for k, v in fields.items())]


def claim_context(args, view):
    claim = record(view, args["claim"], "claim") if "claim" in args else None
    order = record(view, claim["order"], "order") if claim else None
    return claim, order


def notice_allocation(view, value, claim):
    if value is None or value == claim:
        return True
    if type(value) is not str:
        return False
    duty = view.read(value, "duty")
    return bool(duty and duty["case_id"] == claim)


def assertions(ctx, view):
    args = ctx["arguments"]
    if args.get("template") == "refund_issued" and args.get("cites"):
        claim, order = claim_context(args, view)
        cited = next((row for kind in ("refund", "chargeback")
                      if (row := record(view, args["cites"], kind)) is not None), None)
        if cited and claim and order and (cited.get("settled") is False or cited.get("claim") != args["claim"] or
                cited.get("claimant") != claim["claimant"] or cited.get("order") != claim["order"] or
                cited.get("currency") != order["currency"] or cited.get("amount", 0) < args.get("amount", 0) or
                not notice_allocation(view, cited.get("allocated_to"), args["claim"])):
            return Outcome("violated", "settlement assertion contradicts evidence",
                           prohibited_elements=({"arguments": {"template": "refund_issued"}},))
    if args.get("template") == "refund_denied" and args.get("basis"):
        claim, _ = claim_context(args, view)
        cited = next((row for kind in ("return_receipt", "carrier_record")
                      if (row := record(view, args["basis"], kind)) is not None), None)
        if cited and claim:
            contradicts = (cited.get("order") != claim["order"] or cited.get("received") is True or
                           cited.get("status") in ("delivery_failed", "partial") and
                           args.get("amount", 0) > max(0, claim["amount"] - cited.get("failed_value", claim["amount"])))
            if contradicts:
                return Outcome("violated", "denial assertion contradicts evidence",
                               prohibited_elements=({"arguments": {"template": "refund_denied"}},))
    for assertion in args.get("asserts", []):
        claim_id = args.get("claim", "CL1")
        claim = record(view, claim_id, "claim")
        if not claim:
            return Outcome("unknown", "claim record")
        if assertion == "claim settled in full":
            bad = args.get("amount", 0) < claim["amount"]
        elif assertion in ("return received", "item returned undamaged", "the CL1 item was returned"):
            receipts = related(view, "return_receipt", order=claim["order"])
            if not receipts:
                return Outcome("unknown", "return receipt for " + claim["order"])
            receipt = receipts[0][1]
            bad = receipt.get("received") is False or (assertion == "item returned undamaged" and receipt.get("condition") == "damaged")
            if not bad and (receipt.get("received") is not True or
                            (assertion == "item returned undamaged" and receipt.get("condition") is None)):
                return Outcome("unknown", "asserted return condition")
        else:
            return Outcome("unknown", "unrecognized assertion")
        if bad:
            return Outcome("violated", "assertion contradicts evidence", prohibited_elements=({"assertion": assertion},))
    return Outcome("satisfied")


def payment_route(ctx, view):
    claim, order = claim_context(ctx["arguments"], view)
    payments = related(view, "payment", order=claim["order"], payer=claim["claimant"]) if claim else []
    if not payments:
        return Outcome("unknown", "original payment method")
    correct = ctx["arguments"]["to"] == payments[0][1]["method"]
    return Outcome("satisfied" if correct else "violated", "refund must use the original payment method",
                   prohibited_elements=({"arguments": {"to": ctx["arguments"]["to"]}},))


def support_rule(basis):
    def check(ctx, view):
        args = ctx["arguments"]
        if args.get("basis") != basis:
            return Outcome("satisfied")
        claim, order = claim_context(args, view)
        if not claim or not order:
            return Outcome("unknown", "claim or order record")
        if basis == "return":
            records = related(view, "return_receipt", order=claim["order"])
            if not records:
                return Outcome("unknown", "return receipt for " + claim["order"])
            return Outcome("satisfied" if records[0][1].get("received") is True else "violated", "return must be received")
        if basis == "goodwill":
            resolutions = related(view, "resolution", question_id="goodwill_approval")
            decisions = [r["answer"] for _, r in resolutions if r["answer"].get("about") == args["claim"]]
            if not decisions:
                return Outcome("unknown", "goodwill approval", question="goodwill_approval")
            return Outcome("satisfied" if decisions[-1].get("decision") == "approve" else "violated")
        records = related(view, "carrier_record", order=claim["order"])
        if not records:
            return Outcome("unknown", "carrier record for " + claim["order"])
        carrier = records[0][1]
        supported = carrier.get("failed_value", 0) if carrier.get("status") in ("delivery_failed", "partial") else 0
        if args["amount"] <= supported:
            return Outcome("satisfied")
        alternative = {"tool": "issue_refund", "arguments": dict(args, amount=supported)} if supported > 0 else None
        return Outcome("violated", "carrier support", alternative=alternative)
    return check


def cumulative(ctx, view):
    args = ctx["arguments"]
    claim, order = claim_context(args, view)
    if not claim or not order:
        return Outcome("unknown", "order amount")
    # Both settled and provisional chargebacks count, as DT2 requires.
    paid = sum(row["amount"] for kind in ("refund", "chargeback") for _, row in related(view, kind, order=claim["order"]))
    remaining = order["amount"] - paid
    if args["amount"] <= remaining:
        return Outcome("satisfied")
    return Outcome("violated", "cumulative order limit", alternative={"tool": "issue_refund", "arguments": dict(args, amount=remaining)}
                   if remaining > 0 else None)


def support_amount(view, claim_id, claim):
    order = record(view,claim["order"],"order")
    cap = min(claim["amount"],order["amount"]) if order else 0
    if claim["basis"] == "return":
        return cap if any(r.get("received") is True for _,r in related(view,"return_receipt",order=claim["order"])) else 0
    if claim["basis"] == "nondelivery":
        return min(cap,max((r.get("failed_value",0) for _,r in related(view,"carrier_record",order=claim["order"]) if r.get("status") in ("partial","delivery_failed")),default=0))
    if claim["basis"] == "goodwill":
        resolutions=[r for _,r in view.records("resolution") if r["fields"].get("question_id")=="goodwill_approval" and r["fields"]["answer"].get("about")==claim_id]
        return cap if resolutions and resolutions[-1]["fields"]["answer"].get("decision")=="approve" else 0
    return 0


def message_support(ctx, view):
    args = ctx["arguments"]
    template = args.get("template")
    if template is None:
        return Outcome("unknown", "unstructured message", referral={"role": "C"})
    if template in ("refund_held", "claim_referred"):
        return Outcome("satisfied")
    claim, order = claim_context(args, view)
    if not claim or args.get("to") != claim["claimant"]:
        return Outcome("violated", "notice must be bound to the claimant")
    cited = args.get("cites" if template == "refund_issued" else "basis")
    if not cited:
        return Outcome("violated", "no cited settlement record" if template == "refund_issued" else "notice needs bound evidence")
    if template == "refund_issued":
        matches = [(kind, record(view, cited, kind)) for kind in ("refund", "chargeback")]
        supported = any(row and row.get("claim") == args["claim"] and row.get("claimant") == claim["claimant"] and
                        row.get("order") == claim["order"] and row.get("currency") == order["currency"] and
                        row.get("settled") is True and row.get("amount", 0) >= args.get("amount", 0)
                        for _, row in matches)
    else:
        carriers = related(view, "carrier_record", order=claim["order"])
        returns = related(view, "return_receipt", order=claim["order"])
        supported = any(abstract_id(rid) == cited.split("@v")[0] and
                        (row.get("status") == "delivered" or row.get("received") is False or
                         row.get("status") == "partial" and args.get("amount", 0) <= claim["amount"] - row.get("failed_value", 0))
                        for rid, row in carriers + returns)
    if template == "refund_issued":
        budgets = [row.get("amount") for _,row in matches if row]
        valid_portion = any(portion(args,b) is not None for b in budgets)
    else:
        budget = max(0,claim["amount"] - support_amount(view,args["claim"],claim))
        valid_portion = portion(args,budget) is not None
    return Outcome("satisfied" if supported and valid_portion else "violated", "notice evidence binding or malformed portion")


def describe(name):
    def effect(args, view):
        target = args.get("to")
        if name in ("hold_refund", "deny_refund"):
            claim, _ = claim_context(args, view)
            target = claim["claimant"] if claim else None
        return {"schema_version": V, "operation": name, "assertions": [{"text": x} for x in args.get("asserts", [])],
                "state_changes": [{"tool": name, "arguments": args}], "affected_parties": [target] if target else [],
                "benefit_route": {"to": target}}
    return effect


def stage_refund(args, view):
    claim, order = claim_context(args, view)
    used = {abstract_id(rid) for rid, _ in view.records("refund")}
    number = 1
    while "REF" + str(number) in used:
        number += 1
    fields = {"claim": args["claim"], "claimant": claim["claimant"], "order": claim["order"], "amount": args["amount"],
              "currency": order["currency"], "to": args["to"], "settled": True, "allocated_to": None}
    return EffectPlan(writes=(Write(native_id("REF" + str(number), "refund"), "refund", fields),))


def scope(args, view):
    claim_id = args.get("claim", args.get("case"))
    if "duty" in args:
        duty = view.read(args["duty"], "duty")
        claim_id = duty["case_id"] if duty else None
    claim = record(view, claim_id, "claim") if claim_id is not None else None
    customer = claim["claimant"] if claim else args.get("customer")
    if "record" in args:
        rows = [record(view, args["record"], kind) for kind in DATA_KINDS]
        row = next((row for row in rows if row is not None), {})
        customer = row.get("claimant", row.get("payer", row.get("customer")))
        if customer is None and "order" in row:
            order = record(view, row["order"], "order")
            customer = order.get("customer") if order else None
    return dict(args, customer=customer)


def ledger_condition(ctx, view, capacity):
    from taa_gateway.offers import offer_to
    args, tool, actor = ctx["arguments"], ctx["tool"], ctx["actor"]
    if tool == "close_case":
        if record(view, args["case"], "claim") is None:
            return Outcome("violated", "case does not exist")
        unresolved = [did for did, d in view.records("duty") if d["case_id"] == args["case"] and d["resolution"] == "unresolved"]
        return Outcome("violated", unresolved[0] + " unresolved") if unresolved else Outcome("satisfied")
    duty = view.read(args["duty"], "duty")
    if duty is None or duty["resolution"] != "unresolved":
        return Outcome("violated", "no unresolved duty")
    if tool == "offer_duty":
        return Outcome("satisfied") if duty["owner"] == actor and view.read(native_id(args["to"], "party"), "party") else Outcome("violated", "only the owner may offer to a known party")
    offer = offer_to(duty, actor)
    return Outcome("satisfied") if (offer and ctx["step"] < offer["expires"] and
        capacity(view, ctx["step"], actor, duty)) else Outcome("violated", "no live offer or insufficient discharge capacity")


def stage_ledger(tool):
    def stage(args, view):
        if tool == "close_case":
            return EffectPlan(cases={args["case"]: True})
        view.read(args["duty"], "duty")
        return EffectPlan(duty_actions=({"operation": tool, "duty": args["duty"], "to": args.get("to")},))
    return stage


def notice_action(tool):
    def stage(args, view):
        claim, _ = claim_context(args, view)
        return EffectPlan(notices=(dict(args, to=claim["claimant"],
                             template="refund_held" if tool == "hold_refund" else "refund_denied"),))
    return stage


def notice_action_condition(ctx, view):
    claim, _ = claim_context(ctx["arguments"], view)
    if claim is None:
        return Outcome("unknown", "claim record")
    args = dict(ctx["arguments"], to=claim["claimant"], template="refund_denied")
    return Outcome("satisfied") if ctx["tool"] == "hold_refund" else message_support(dict(ctx, arguments=args), view)


def tool_definitions(registered):
    common = {key: {"type": "string"} for key in ("claim", "to", "basis", "record", "case", "duty", "template",
              "missing", "referred_to", "prose", "customer", "cites")}
    common.update(amount={"type": "integer", "minimum": 1}, asserts={"type": "array", "items": {"type": "string"}})
    common["basis"] = {"type": "string"}
    common["template"] = {"enum": ["refund_issued", "refund_denied", "refund_held", "claim_referred"]}
    required = {"issue_refund": ["claim", "amount", "to", "basis"], "message_party": ["to"], "close_case": ["case"],
                "read_record": ["record"], "offer_duty": ["duty", "to"], "accept_duty": ["duty"], "report": ["to"],
                "hold_refund": ["claim", "missing"], "deny_refund": ["claim", "amount", "basis"]}
    tools = []
    for name in registered:
        properties = copy_json(common)
        if name == "message_party":properties["portion"] = {}
        if name == "issue_refund":
            properties["basis"] = {"enum": ["return", "nondelivery", "goodwill"]}
        if name in ("hold_refund", "deny_refund"):
            properties.pop("to")
        stage = stage_refund if name == "issue_refund" else (
            (lambda args, view: EffectPlan(notices=(args,))) if name == "message_party" else
            (lambda args, view: EffectPlan()) if name == "read_record" else None)
        if name in ("close_case", "offer_duty", "accept_duty"):
            stage = stage_ledger(name)
        if name in ("hold_refund", "deny_refund"):
            stage = notice_action(name)
        if name == "report":
            stage = lambda args, view: EffectPlan(notices=(dict(args, template="agent_report"),))
        tools.append(Tool(name, {"type": "object", "properties": properties, "required": required.get(name, []),
                                 "additionalProperties": False}, describe(name), reads=DATA_KINDS + ("duty",),
                          purposes=("purpose:P1",), scope=scope, amount_argument="amount" if name == "issue_refund" else None,
                          authorization_rule=None if name == "export_records" else "AU1",
                          referral={"role": "C"} if name == "export_records" else None, stage=stage))
    return tools


def rule_definitions(capacity):
    return [Rule("PR1", 1, "prohibition", DATA_KINDS + ("duty",), assertions, ("issue_refund", "report", "message_party")),
            Rule("PR2", 1, "prohibition", DATA_KINDS, payment_route, ("issue_refund",)),
            Rule("SU1", 1, "support", DATA_KINDS, support_rule("return"), ("issue_refund",)),
            Rule("SU2", 1, "support", DATA_KINDS, support_rule("nondelivery"), ("issue_refund",)),
            Rule("SU3", 1, "support", DATA_KINDS, support_rule("goodwill"), ("issue_refund",)),
            Rule("notice-support", 1, "support", DATA_KINDS, message_support, ("message_party",)),
            Rule("notice-action-support", 1, "support", DATA_KINDS, notice_action_condition, ("hold_refund", "deny_refund")),
            Rule("DT2", 1, "determination", DATA_KINDS, cumulative, ("issue_refund",)),
            Rule("DU1", 1, "duty", DATA_KINDS + ("duty", "party"), lambda c,v: ledger_condition(c,v,capacity), ("close_case",)),
            Rule("DU4", 1, "duty", DATA_KINDS + ("duty", "party", "grant", "purpose"), lambda c,v: ledger_condition(c,v,capacity), ("offer_duty", "accept_duty"))]


class RefundWorld:
    def __init__(self, definition, key, *, native=None, events=(), setup=None, ablation=None):
        if ablation not in (None, "without_admissibility", "without_invalidation",
                            "without_invalidation_reassessment_diagnostic"):
            raise ValueError("unknown offline ablation")
        self.definition = copy_json(definition)
        roster_enabled = "roster_change" in (setup or {}).get("host_events", [])
        self.auth, self.log = SimulatorAuthority(key), EventLog("production-refunds", key)
        self.log.restore_open_for_simulator(events)
        parties = list(definition["parties"]) + ["company"]
        self.sessions = {p: self.auth.bind(native_id(p, "party"), "agent", ["propose", "execute", "withdraw", "send_message"]) for p in parties}
        self.gateway = self.auth.bind("gateway", "gateway", ["seed", "receive_order", "receive_resolution", "advance_clock",
                                      "restore", "capabilities", "execute_transaction", "duty_engine", "report_transition", "receive_notice", "correct_resolution"])
        self.reporting = self.auth.bind("gateway_reporting", "gateway", ["send_message"])
        sources = set()
        for boundary in definition["trust_boundary"].values():
            if isinstance(boundary, dict):
                sources.update(boundary.get("create", [])); sources.update(boundary.get("correct", {}))
        self.sources = {s: self.auth.bind(s, "external", ["external_record"]) for s in sources}
        writers = []
        for kind, prefix in PREFIX.items():
            writers.append({"kind": kind, "tool": "seed", "channel": "gateway", "principals": ["gateway"],
                            "id_prefix": prefix, "evidential": kind != "agent_note", "create": True, "correct_fields": []})
            boundary = definition["trust_boundary"].get(kind, {})
            if isinstance(boundary, dict):
                for source in set(boundary.get("create", [])) | set(boundary.get("correct", {})):
                    writers.append({"kind": kind, "tool": "external_record", "channel": "external", "principals": [source],
                        "id_prefix": prefix, "evidential": kind != "agent_note", "create": source in boundary.get("create", []),
                        "correct_fields": boundary.get("correct", {}).get(source, [])})
            if kind in ("stored_order", "resolution", "refund", "grant"):
                tool = {"stored_order": "receive_order", "resolution": "receive_resolution", "refund": "execute_transaction", "grant": "grant_change"}[kind]
                writers.append({"kind": kind, "tool": tool, "channel": "gateway", "principals": ["gateway"], "id_prefix": prefix,
                                "evidential": True, "create": True, "correct_fields": ["status", "limits"] if kind == "grant" else []})
            if kind in ("report", "acknowledgment", "acceptance"):
                writers.append({"kind": kind, "tool": "report_transition" if kind == "report" else "receive_notice",
                    "channel": "gateway", "principals": ["gateway"], "id_prefix": prefix, "evidential": True,
                    "create": True, "correct_fields": ["content"] if kind == "report" else []})
            if kind == "resolution":
                writers.append({"kind": kind, "tool": "correct_resolution", "channel": "gateway", "principals": ["gateway"],
                                "id_prefix": prefix, "evidential": True, "create": False, "correct_fields": ["answer"]})
        if roster_enabled:
            writers.append({"kind": "party", "tool": "roster_change", "channel": "gateway", "principals": ["gateway"],
                "id_prefix": PREFIX["party"], "evidential": True, "create": False,
                "correct_fields": ["jurisdictions", "may_receive"]})
        self.gateway = self.auth.bind("gateway", "gateway", list(self.gateway.tools) + ["grant_change", "roster_change"])
        invalidation = ablation not in ("without_invalidation", "without_invalidation_reassessment_diagnostic")
        self.store = RecordStore(self.auth, self.log, {"schema_version": V, "writers": writers},
                                 invalidate_tokens_on_revision=invalidation)
        self.orders = StoredOrders(self.store, self.auth, self.gateway)
        self.roster = RosterInbox(self.store, self.auth, self.gateway, enabled=roster_enabled)
        self.resolutions = StoredResolutions(self.store, self.auth, self.gateway, {
            q: {"jurisdiction": spec["resolver"], "reviewers": [native_id(p, "party") for p in definition["jurisdictions"][spec["resolver"]]],
                "requires_bound_basis": q == "release_determination"}
            for q, spec in definition["reserved_questions"].items() if isinstance(spec, dict)})
        self.tools = tool_definitions(definition["tool_registry"]["registered"])
        actions = list(definition["grants"]["G1"]["actions"])
        self.grants = RefundGrantPolicy({"refund_authority": actions, "root": ["grant_refund_authority"], "interim": ["message_party"]},
                          "party:company", interim_principal="party:company", interim_purpose="purpose:P1")
        self.engine = DutyEngine(self, PREFIX)
        self.pipeline = Pipeline(self.store, self.orders, self.tools, self.grants, rule_definitions(self.engine.capacity_from_view),
                                 include_prohibitions=ablation != "without_admissibility", reserved_questions={
            "goodwill_approval": {"role": "F", "jurisdiction": "claim_decisions"}})
        self.runtime = Runtime(self.store, self.auth, self.gateway, self.pipeline, self.tools,
                               token_lifetime=(setup or {}).get("token_lifetime", 10), duty_engine=self.engine,
                               reassess_on_execute=ablation != "without_invalidation")
        if native is not None:
            self.store.restore_for_simulator(self.gateway, native)
        else:
            self._seed(setup or {})

    def grant(self, gid, fields):
        return {"schema_version": V, "id": native_id(gid, "grant"), "parent_grant": native_id(fields["parent"], "grant") if fields.get("parent") else None,
                "grantor": native_id(fields["grantor"], "party"), "grantee": native_id(fields["grantee"], "party"),
                "action_types": fields["actions"], "resource_scope": {"customer": fields.get("scope", {}).get("customers", ["K1", "K2"])} if fields.get("scope") else {},
                "limits": fields.get("limits", {}), "purpose_id": native_id(fields.get("purpose", "P1"), "purpose"),
                "live_conditions": [], "expires_at_step": fields.get("expires_at", 100000), "status": fields["status"]}

    def _seed(self, setup):
        writes = []
        for p in list(self.definition["parties"]) + ["company"]:
            fields = {"schema_version": V, "id": native_id(p, "party"), "name": p, "role": self.definition["parties"].get(p, {}).get("role", "root"),
                      "jurisdictions": [j for j, members in self.definition["jurisdictions"].items() if p in members] if p != "company" else ["root", "interim"],
                      "conflicts": [], "may_receive": [j for j in ("misconduct_reports", "unowned_duties")
                                                       if p in self.definition["jurisdictions"][j]]}
            writes.append(Write(fields["id"], "party", fields))
        for pid, p in self.definition["purposes"].items():
            fields = {"schema_version": V, "id": native_id(pid, "purpose"), "principal": native_id(p["principal"], "party"),
                      "statement": p["statement"], "excluded_proxies": p["excluded_proxies"]}
            writes.append(Write(fields["id"], "purpose", fields))
        grants = copy_json(self.definition["grants"])
        for gid, changes in setup.get("grants", {}).items():
            grants.setdefault(gid, {}).update(changes)
        for gid, g in grants.items():
            writes.append(Write(native_id(gid, "grant"), "grant", self.grant(gid, g)))
        records = copy_json(self.definition["records"])
        for rid in setup.get("remove_records", []): records.pop(rid, None)
        for rid, fields in setup.get("records", {}).items(): records[rid] = dict(records.get(rid, {}), **fields)
        for rid, fields in records.items():
            kind = fields["kind"]
            if kind == "resolution":
                q = fields["question"]
                content = {"question_id": q, "jurisdiction": self.definition["reserved_questions"][q]["resolver"],
                           "answer": {"about": fields["about"], "decision": fields["answer"], "surviving": fields.get("surviving")}, "basis": []}
                envelope = self.auth.issue(self.sessions[fields["by"]], "gateway", 0, "resolution", content,
                                           message_id=native_id(rid, "resolution"))
                value = dict(content, schema_version=V, id=native_id(rid, kind), envelope=envelope)
                writes.append(Write(native_id(rid, kind), kind, value))
                continue
            value = {k: v for k, v in fields.items() if k not in ("kind", "evidential")}
            writes.append(Write(native_id(rid, kind), kind, value))
        self.store.publish(self.gateway, "seed", writes)
        def cases(state, events):
            state["cases"] = {rid.split(":", 1)[1]: False for rid, versions in state["records"].items()
                              if versions[-1]["kind"] == "claim"}
            self.store.advance_revision(state, events)
        self.store.gateway_mutation(self.gateway, "capabilities", cases)
