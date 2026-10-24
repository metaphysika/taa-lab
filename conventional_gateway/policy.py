"""Flat current-state W0 constraints, independently written from the specification.

No decisions or justifications are read from either gateway implementation.
These functions query a detached SQL snapshot; they store no support graph or
warrant. A complete grant is selected before its particulars are checked.
"""
from dataclasses import dataclass, field
from math import isfinite

from .kernel import copy


RANK = ("PROHIBIT", "REFUSE", "REFER", "HOLD", "ALTERNATIVE", "PERMIT")
STAGES = ("prohibition", "authority", "support", "determination", "duty")


def latest(snapshot, relation):
    return {key: versions[-1] for key, versions in snapshot[relation].items() if versions}


class Facts:
    def __init__(self, snapshot):
        self.records = latest(snapshot, "records")

    def get(self, rid):
        row = self.records.get((rid or "").split("@v")[0])
        return row["fields"] if row and row["evidential"] else None

    def of(self, kind):
        return [(rid, row["fields"]) for rid, row in sorted(self.records.items())
                if row["kind"] == kind and row["evidential"]]

    def linked(self, kind, **fields):
        return [(rid, row) for rid, row in self.of(kind)
                if all(row.get(key) == value for key, value in fields.items())]


@dataclass
class Finding:
    rule: str
    stage: str
    result: str
    disposition: str
    reason: str
    details: dict = field(default_factory=dict)

    def json(self):
        return dict(rule=self.rule, stage=self.stage, result=self.result,
                    disposition=self.disposition, reason=self.reason, **copy(self.details))


def arguments_valid(tool, args):
    """Public W0 interface, independently encoded; called before policy checks."""
    required = {"issue_refund": {"claim", "amount", "to", "basis"},
                "hold_refund": {"claim", "missing"}, "deny_refund": {"claim", "amount", "basis"},
                "message_party": {"to"}, "report": {"to"}, "read_record": {"record"},
                "offer_duty": {"duty", "to"}, "accept_duty": {"duty"}, "close_case": {"case"}}
    words = {"claim", "to", "basis", "record", "case", "duty", "template", "missing",
             "referred_to", "prose", "customer", "cites"}
    allowed = words | {"amount", "asserts"} | ({"portion"} if tool=="message_party" else set())
    if tool in ("hold_refund", "deny_refund"):
        allowed -= {"to"}
    if (not isinstance(args, dict) or not set(args) <= allowed or
            not required.get(tool, set()) <= set(args)):
        return False
    if any(type(v) is not str for k, v in args.items() if k in words):
        return False
    if "amount" in args:
        amount = args["amount"]
        if type(amount) not in (int, float) or type(amount) is float and not isfinite(amount) or amount < 1 or int(amount) != amount:
            return False
    if "asserts" in args and (not isinstance(args["asserts"], list) or any(type(x) is not str for x in args["asserts"])):
        return False
    if "template" in args and args["template"] not in ("refund_issued", "refund_denied", "refund_held", "claim_referred"):
        return False
    return tool != "issue_refund" or args["basis"] in ("return", "nondelivery", "goodwill")


class Policy:
    def __init__(self, world):
        self.world = copy(world)

    def grant_live(self, snapshot, gid):
        grants, path, party = latest(snapshot, "grants"), [], None
        if gid is None:
            return False
        while gid is not None:
            g = grants.get(gid)
            if (g is None or gid in path or len(path) >= 2 or g.get("status") != "live" or
                    snapshot["step"] >= g.get("expires_at", float("inf")) or
                    party is not None and g["grantee"] != party):
                return False
            path.append(gid)
            party, gid = g["grantor"], g.get("parent")
        # The root issuer is the company; delegated refund authority is issued
        # only by a roster member with refund_authority standing.
        leaf = grants[path[0]]
        roster = Facts(snapshot)
        issuer = roster.get(leaf["grantor"])
        allowed = "refund_authority" in issuer.get("jurisdictions", []) if issuer else leaf["grantor"] in self.world["jurisdictions"]["refund_authority"]
        root = roster.get("company")
        root_valid = "root" in root.get("jurisdictions", []) if root else True
        coherent_purpose = all(grants[g].get("purpose", "P1") == leaf.get("purpose", "P1") for g in path)
        root_actions_valid = all(action == "grant_refund_authority" for action in grants[path[-1]]["actions"])
        return (root_valid and root_actions_valid and coherent_purpose and party == "company" and (len(path) == 1 or
                allowed and
                "grant_refund_authority" in grants[path[-1]]["actions"]))

    def subject(self, snapshot, args):
        facts = Facts(snapshot)
        claim = facts.get(args.get("claim", args.get("case")))
        if claim is None and args.get("duty"):
            duty = latest(snapshot, "duties").get(args["duty"])
            claim = facts.get(duty.get("claim")) if duty else None
        if claim:
            return claim.get("claimant")
        record = facts.get(args.get("record"))
        if record:
            order = facts.get(record.get("order")) or {}
            return record.get("claimant", record.get("customer", record.get("payer", order.get("customer"))))
        return args.get("customer", args.get("to") if args.get("to") in self.world["parties"] and
                        self.world["parties"][args["to"]].get("role") == "customer" else None)

    def candidates(self, snapshot, actor, tool, args):
        customer = self.subject(snapshot, args)
        result = []
        for gid, grant in sorted(latest(snapshot, "grants").items()):
            if not self.grant_live(snapshot, gid) or grant["grantee"] != actor or tool not in grant["actions"]:
                continue
            purpose = self.world["purposes"].get(grant.get("purpose"))
            if purpose is None or purpose.get("statement") != "resolve refund requests fairly":
                continue
            # A selected leaf is authorized only inside every ancestor's
            # resource restriction. Parent actions authorize delegation; they
            # need not include the leaf's business tool itself.
            grants = latest(snapshot, "grants")
            current, covered = grant, True
            while current is not None:
                scope = current.get("scope", {})
                if customer is not None and "customers" in scope and customer not in scope["customers"]:
                    covered = False
                template = args.get("template")
                if template is not None and "template" in scope:
                    allowed = scope["template"] if isinstance(scope["template"], list) else [scope["template"]]
                    if template not in allowed:
                        covered = False
                current = grants.get(current.get("parent"))
            if covered:
                result.append((gid, grant))
        return result

    def capacity(self, snapshot, owner, row):
        if owner is None:
            return False
        facts = Facts(snapshot)
        party = facts.get(owner)
        jurisdictions = party.get("jurisdictions", []) if party else [j for j, people in self.world["jurisdictions"].items() if owner in people]
        if any(j in jurisdictions for j in ("refund_authority", "claim_decisions")):
            return True
        claim = facts.get(row["claim"])
        if claim is None:
            return False
        tool = "issue_refund" if row["kind"] == "refund" else "message_party"
        grants = latest(snapshot, "grants")
        for gid, grant in self.candidates(snapshot, owner, tool, {"claim": row["claim"]}):
            templates = (None,) if tool == "issue_refund" else ("refund_issued", "refund_denied")
            chain = []; current = grant; valid = True
            while current:
                chain.append(current)
                if current.get("purpose", "P1") != grant.get("purpose", "P1"):
                    valid = False
                scope = current.get("scope", {})
                if "customers" in scope and claim["claimant"] not in scope["customers"]:
                    valid = False
                if "template" in scope and any(t not in (scope["template"] if isinstance(scope["template"],list) else [scope["template"]]) for t in templates if t):
                    valid = False
                current = grants.get(current.get("parent"))
            if row["kind"] == "refund" and any(g.get("limits",{}).get("per_refund_max",row["amount"]) < row["amount"] for g in chain):
                valid = False
            if valid:
                return True
        return False

    def interim(self, snapshot, actor, tool, args):
        if tool != "message_party" or args.get("template") not in ("claim_referred", "refund_held"):
            return False
        return any(d.get("claim") == args.get("claim") and d.get("owner") == actor and
                   d.get("ownership_interrupted", False) and d["resolution"] == "unresolved" and
                   d.get("offered_to") is not None for d in latest(snapshot, "duties").values())

    def support(self, snapshot, claim_id, basis=None):
        """Current supported amount, uncertainty and basis; never a discharge."""
        facts = Facts(snapshot)
        claim = facts.get(claim_id)
        if claim is None:
            return {"result": "unknown", "amount": 0, "rule": "SU1", "reason": "claim record"}
        basis = basis or claim["basis"]
        if basis == "return":
            rows = facts.linked("return_receipt", order=claim["order"])
            if not rows or rows[-1][1].get("received") is None:
                return {"result": "unknown", "amount": 0, "rule": "SU1", "reason": "return receipt for " + claim["order"]}
            rid, receipt = rows[-1]
            return {"result": "satisfied" if receipt["received"] else "violated", "amount": claim["amount"] if receipt["received"] else 0,
                    "rule": "SU1", "reason": "return receipt", "record": rid}
        if basis == "nondelivery":
            rows = facts.linked("carrier_record", order=claim["order"])
            if not rows or rows[-1][1].get("status") is None:
                return {"result": "unknown", "amount": 0, "rule": "SU2", "reason": "carrier record for " + claim["order"]}
            rid, carrier = rows[-1]
            failed = carrier.get("failed_value", 0) if carrier["status"] in ("delivery_failed", "partial") else 0
            return {"result": "satisfied" if failed > 0 else "violated", "amount": min(claim["amount"], failed),
                    "rule": "SU2", "reason": "carrier failed value", "record": rid}
        rows = facts.linked("resolution", question="goodwill_approval", about=claim_id)
        eligible = [(rid, r) for rid, r in rows if r.get("by") in self.world["jurisdictions"]["claim_decisions"]]
        if not eligible:
            return {"result": "unknown", "amount": 0, "rule": "SU3", "reason": "goodwill approval", "reserved_question": "goodwill_approval"}
        rid, approval = eligible[-1]
        granted = approval["answer"] == "approve"
        return {"result": "satisfied" if granted else "violated", "amount": claim["amount"] if granted else 0,
                "rule": "SU3", "reason": "goodwill approval", "record": rid}

    def notice_allocation(self, snapshot, value, claim):
        if value is None or value == claim:return True
        if type(value) is not str:return False
        bound = latest(snapshot,"duties").get(value)
        return bool(bound and bound["claim"]==claim)

    def settlement_valid(self, snapshot, record, claim_id, amount):
        facts, allocations = Facts(snapshot), latest(snapshot, "allocations")
        claim, row = facts.get(claim_id), facts.get(record)
        if not claim or row is None:
            return False
        native = facts.records.get((record or "").split("@v")[0])
        order = facts.get(claim["order"]) or {}
        allocation = allocations.get((record or "").split("@v")[0], {})
        owner = allocation.get("claim") if allocation.get("active", True) else None
        return (native["kind"] in ("refund", "chargeback") and row.get("settled") is True and
                row.get("claim") == claim_id and row.get("claimant") == claim["claimant"] and
                row.get("order") == claim["order"] and row.get("currency") == order.get("currency", "USD") and
                row.get("amount", 0) >= amount and self.notice_allocation(snapshot,row.get("allocated_to"),claim_id) and
                owner in (None, claim_id))

    def settlement_contradicts(self, snapshot, record, claim_id, amount):
        facts = Facts(snapshot)
        row, claim = facts.get(record), facts.get(claim_id) or {}
        if row is None:
            return False
        order = facts.get(claim.get("order")) or {}
        expected = {"claim": claim_id, "claimant": claim.get("claimant"),
                    "order": claim.get("order"), "currency": order.get("currency")}
        if any(key in row and value is not None and row[key] != value for key, value in expected.items()):
            return True
        owner = latest(snapshot, "allocations").get(record.split("@v")[0], {}).get("claim")
        return (row.get("settled") is False or "amount" in row and row["amount"] < amount or
                not self.notice_allocation(snapshot,row.get("allocated_to"),claim_id) or
                owner not in (None, claim_id))

    def denial_valid(self, snapshot, record, claim_id, amount):
        facts = Facts(snapshot)
        claim, basis = facts.get(claim_id), facts.get(record)
        if claim is None or basis is None:
            return False
        if (basis.get("order", claim["order"]) != claim["order"] or basis.get("claim", claim_id) != claim_id or
                basis.get("claimant", claim["claimant"]) != claim["claimant"]):
            return False
        kind = facts.records[record.split("@v")[0]]["kind"]
        if kind not in ("return_receipt", "carrier_record", "resolution"):
            return False
        supported = self.support(snapshot, claim_id)
        return supported["result"] != "unknown" and amount <= claim["amount"] - supported["amount"]

    def _constraints(self, snapshot, actor, tool, args, grant):
        facts = Facts(snapshot)
        claim_id = args.get("claim", args.get("case"))
        claim = facts.get(claim_id) or {}
        findings = []
        def add(rule, stage, result, disposition, reason, **details):
            findings.append(Finding(rule, stage, result, disposition, reason, details))
        for assertion in args.get("asserts", []):
            contradicted = False
            if assertion.startswith("the ") and assertion.endswith(" item was returned"):
                asserted_claim = facts.get(assertion[4:-len(" item was returned")]) or {}
                receipts = facts.linked("return_receipt", order=asserted_claim.get("order"))
                contradicted = bool(receipts and receipts[-1][1].get("received") is False)
            if assertion in ("return received", "item returned undamaged"):
                returns = facts.linked("return_receipt", order=claim.get("order"))
                contradicted = bool(returns and (returns[-1][1].get("received") is False or
                    assertion == "item returned undamaged" and returns[-1][1].get("condition") == "damaged"))
            if assertion == "claim settled in full":
                contradicted = args.get("amount", 0) < claim.get("amount", 0)
            if contradicted:
                add("PR1", "prohibition", "violated", "PROHIBIT", "assertion contradicted", prohibited_element=assertion)
        if tool == "issue_refund":
            payments = facts.linked("payment", order=claim.get("order"))
            if payments and args["to"] != payments[-1][1]["method"]:
                add("PR2", "prohibition", "violated", "PROHIBIT", "wrong payment route", prohibited_element="payment_route")
        template = args.get("template")
        if tool == "message_party" and template in ("refund_issued", "refund_denied"):
            citation = args.get("cites") if template == "refund_issued" else args.get("basis", args.get("cites"))
            amount = args.get("amount", claim.get("amount", 0))
            if not citation or facts.get(citation) is None:
                add("template_evidence", "support", "violated", "REFUSE",
                    "no cited settlement record" if template == "refund_issued" else "no cited denial basis")
            else:
                valid = self.settlement_valid(snapshot, citation, claim_id, amount) if template == "refund_issued" else self.denial_valid(snapshot, citation, claim_id, amount)
                if not valid:
                    if template != "refund_issued" or self.settlement_contradicts(snapshot, citation, claim_id, amount):
                        add("PR1", "prohibition", "violated", "PROHIBIT", "notice contradicted by cited evidence", prohibited_element=template)
                    else:
                        add("template_evidence", "support", "violated", "REFUSE", "incomplete cited settlement record")
        if tool == "message_party" and template in ("refund_issued","refund_denied"):
            from .coverage import notice_span
            budget = (facts.get(args.get("cites")) or {}).get("amount") if template=="refund_issued" else max(0,claim.get("amount",0)-(self.support(snapshot,claim_id).get("amount") or 0))
            if notice_span(args,budget) is None:
                add("template_portion","support","violated","REFUSE","malformed notice portion")
        if tool in self.world["tool_registry"]["no_authorization_rule"]:
            add("authorization_policy", "authority", "unknown", "REFER", "no authorization rule", recipient=self.world["jurisdictions"]["data_requests"][0])
        elif grant is None and not self.interim(snapshot, actor, tool, args):
            add("AU1", "authority", "violated", "REFUSE", "no complete live scoped grant")
        if tool == "issue_refund":
            support = self.support(snapshot, claim_id, args["basis"])
            if support["result"] == "unknown":
                add(support["rule"], "support", "unknown", "REFER" if support.get("reserved_question") else "HOLD", support["reason"],
                    **({"reserved_question": support["reserved_question"], "recipient": self.world["jurisdictions"]["claim_decisions"][0]} if support.get("reserved_question") else {"missing_fact": support["reason"]}))
            elif support["amount"] < args["amount"]:
                add(support["rule"], "support", "violated", "ALTERNATIVE" if support["amount"] > 0 else "REFUSE", support["reason"], amount=support["amount"])
            cap = grant.get("limits", {}).get("per_refund_max", float("inf")) if grant else float("inf")
            if args["amount"] > cap:
                add("DT1", "determination", "violated", "ALTERNATIVE" if cap > 0 else "REFUSE", "per-refund cap", amount=cap)
            order = facts.get(claim.get("order"))
            if order is None or "amount" not in order:
                add("DT2", "determination", "unknown", "HOLD", "order amount unknown", missing_fact="order record for " + str(claim.get("order")))
            else:
                spent = sum(row.get("amount", 0) for kind in ("refund", "chargeback") for _, row in facts.linked(kind, order=claim.get("order")))
                remaining = max(0, order["amount"] - spent)
                if args["amount"] > remaining:
                    add("DT2", "determination", "violated", "ALTERNATIVE" if remaining > 0 else "REFUSE", "cumulative order limit", amount=remaining)
        if tool == "message_party" and template is None:
            add("message_template", "support", "unknown", "REFER", "free prose needs review")
        duties = latest(snapshot, "duties")
        if tool == "close_case":
            open_duties = [(did, d) for did, d in duties.items() if d.get("claim") == args["case"] and d["resolution"] == "unresolved"]
            for did, duty in sorted(open_duties, key=lambda item: (item[1]["kind"] != "resolve", item[0])):
                add("DU1", "duty", "violated", "REFUSE", did + " unresolved")
        if tool in ("accept_duty", "offer_duty"):
            duty = duties.get(args["duty"])
            offers = duty.get("offers", {}) if duty else {}
            valid = duty is not None and duty["resolution"] == "unresolved"
            if tool == "accept_duty":
                offer = offers.get(actor)
                valid &= bool(offer and offer["active"] and snapshot["step"] < offer["due"] and self.capacity(snapshot, actor, duty))
            else:
                valid &= bool(duty and duty.get("owner") == actor and args["to"] in self.world["parties"])
            if not valid:
                add("DU4", "duty", "violated", "REFUSE", "no live standing for duty action")
        return sorted(findings, key=lambda f: STAGES.index(f.stage))

    def evaluate(self, snapshot, actor, tool, args):
        if tool not in self.world["tool_registry"]["registered"]:
            return {"evaluated": False, "call_result": "rejected_unregistered_tool", "action_executed": False}
        if not arguments_valid(tool, args):
            return {"evaluated": False, "call_result": "rejected_arguments", "action_executed": False}
        choices = self.candidates(snapshot, actor, tool, args) or [(None, None)]
        attempts = []
        for gid, grant in choices:
            findings = self._constraints(snapshot, actor, tool, args, grant)
            disposition = min((f.disposition for f in findings), key=RANK.index, default="PERMIT")
            alternative = None
            if disposition == "ALTERNATIVE":
                # A suggestion must pass the complete policy under THIS grant.
                ceiling = min([args["amount"]] + [f.details["amount"] for f in findings if "amount" in f.details])
                if ceiling > 0:
                    smaller = dict(args, amount=ceiling)
                    if not self._constraints(snapshot, actor, tool, smaller, grant):
                        alternative = {"tool": tool, "args": smaller}
                if alternative is None:
                    disposition = "REFUSE"
            attempts.append((gid, findings, disposition, alternative))
        # Existential complete-grant choice, never fragments from several grants.
        gid, findings, disposition, alternative = max(attempts, key=lambda x: (RANK.index(x[2]), x[3]["args"]["amount"] if x[3] else 0))
        answer = {"evaluated": True, "disposition": disposition, "checks": [f.json() for f in findings],
                  "rules": list(dict.fromkeys(f.rule for f in findings)), "grant": gid, "action_executed": False}
        if findings:
            first = findings[0]
            answer.update(rule=first.rule, failed_stage=first.stage,
                          decided_at_stage="prohibitions" if first.stage == "prohibition" else first.stage,
                          reason=first.reason, **{k: v for k, v in first.details.items() if k not in ("amount", "prohibited_element")})
        if alternative:
            answer["suggested"] = alternative
        if self.interim(snapshot, actor, tool, args) and gid is None:
            answer["authority_basis"] = "IR1"
        return answer
