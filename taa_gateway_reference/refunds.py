"""Independent finite refund-world next-state relation for Design v0.3.1.

Policy is expressed as constraints and duty/proof relations, not the core's
five-stage evaluator. The trusted driver supplies W0 and event identities.
This module never reads trace expectations and imports no core code. Atomicity
here is an ideal relation over copies, not a claim about a production executor.
"""
from copy import deepcopy
import json

ORDER = ("PROHIBIT", "REFUSE", "REFER", "HOLD", "ALTERNATIVE", "PERMIT")
FAULTS = ("after_validate", "after_stage", "during_effect_commit", "during_token_consumption",
          "during_duty_update", "during_receipt_write", "during_revision_advance")


def same(a, b):
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def current(s, rid):
    versions = s["records"].get(rid, [])
    return versions[-1] if versions else None


def facts(s, rid):
    r = current(s, rid)
    return r["fields"] if r and r["evidential"] else {}


def records(s, kind):
    return [(rid, history[-1]["fields"]) for rid, history in sorted(s["records"].items())
            if history[-1]["kind"] == kind and history[-1]["evidential"]]


def put(s, rid, fields, writer):
    fields = deepcopy(fields)
    kind = fields.pop("kind")
    versions = s["records"].setdefault(rid, [])
    if versions and versions[-1]["kind"] != kind:
        raise ValueError("record cannot change kind")
    versions.append({"fields": fields, "kind": kind, "writer": writer, "version": len(versions) + 1,
                     "evidential": kind != "agent_note"})
    if kind in ("refund", "chargeback"):
        s["log"].append(dict(type="financial_write",record=rid,version=len(versions),step=s["step"]))
    return rid + "@v" + str(len(versions))


def revision(s, reason):
    s["revision"] += 1
    for t in s["tokens"].values():
        if t["status"] == "live":
            t["status"] = "void"
    s["log"].append({"type": "revision", "reason": reason, "revision": s["revision"], "step": s["step"]})


def start(world, setup=None, *, defer_first_step=False):
    setup = setup or {}
    s = {"world": deepcopy(world), "revision": 0, "step": 0, "records": {}, "orders": {},
         "grants": deepcopy(world["grants"]), "duties": {}, "cases": {}, "tokens": {},
         "decisions": [], "receipts": [], "log": [], "reports": {}, "allocations": {},
         "notices": [], "token_lifetime": setup.get("token_lifetime", 10), "phase_order": []}
    if "roster_change" in setup.get("host_events", []):
        s["host_events"] = ["roster_change"]
        for party in list(world["parties"]) + ["company"]:
            put(s, party, {"kind": "party", "name": party, "role": world["parties"].get(party, {}).get("role", "root"),
                "jurisdictions": [j for j, members in world["jurisdictions"].items() if party in members]
                    if party != "company" else ["root", "interim"],
                "conflicts": [], "may_receive": [j for j in ("misconduct_reports", "unowned_duties")
                    if party in world["jurisdictions"][j]]}, "company")
    seed = deepcopy(world["records"])
    for rid in setup.get("remove_records", []):
        seed.pop(rid, None)
    for rid, changes in setup.get("records", {}).items():
        seed.setdefault(rid, {}).update(deepcopy(changes))
    for rid, fields in seed.items():
        policy = world["trust_boundary"].get(fields["kind"], {})
        writer = policy.get("create", ["setup"])[0]
        put(s, rid, fields, writer)
    for gid, changes in setup.get("grants", {}).items():
        s["grants"].setdefault(gid, {}).update(deepcopy(changes))
    return s if defer_first_step else advance(s, 1)


def grant_live(s, gid, seen=()):
    g = s["grants"].get(gid)
    return bool(g and gid not in seen and len(seen) < 2 and g["status"] == "live" and
                s["step"] < g.get("expires_at", 10**12) and
                (not g.get("parent") or grant_live(s, g["parent"], seen + (gid,))))


def transfer_offers(d):
    return d.get("offers", {d["offered_to"]: {"due": d["offer_due"], "active": True}} if d.get("offered_to") else {})


def project_offer(d):
    live = [(p, o) for p, o in transfer_offers(d).items() if o["active"]]
    d["offered_to"] = live[0][0] if live else None
    if live:
        d["offer_due"] = live[0][1]["due"]
    else:
        d.pop("offer_due", None)


def offer(s, d, party):
    offers = d.setdefault("offers", transfer_offers(d))
    if party not in offers or not offers[party]["active"]:
        offers[party] = {"due": s["step"] + 5, "active": True}
    project_offer(d)


def standing(s, d, party):
    o = transfer_offers(d).get(party)
    return bool(o and o["active"] and s["step"] < o["due"] and d["resolution"] == "unresolved")


def take(s, d, party):
    d["offers"] = {p: dict(o, active=False) for p, o in transfer_offers(d).items()}
    d.update(owner=party, ownership_interrupted=False, authority_baseline=True, incapacity=False)
    project_offer(d)


def member(s, party, jurisdiction):
    row = current(s, party)
    if row and row["kind"] == "party":
        return jurisdiction in facts(s, party).get("jurisdictions", [])
    return party == "company" and jurisdiction == "root" or party in s["world"]["jurisdictions"].get(jurisdiction, [])


def discharge_path(s, gid, actor, tool, claim, template=None, *, check_resources=True):
    """Independent complete-path relation; never combines grant fragments."""
    leaf = s["grants"].get(gid)
    if not leaf or leaf["grantee"] != actor or tool not in leaf["actions"] or not grant_live(s, gid):
        return None
    purpose = leaf.get("purpose", "P1")
    if purpose != "P1" or purpose not in s["world"]["purposes"]:
        return None
    chain = [];g = leaf
    while g:
        chain.append(g)
        if g.get("purpose", "P1") != purpose:
            return None
        scope = g.get("scope", {})
        if check_resources and claim and "customers" in scope and claim["claimant"] not in scope["customers"]:
            return None
        effective_template = {"hold_refund": "refund_held", "deny_refund": "refund_denied", "report": "agent_report"}.get(tool, template)
        if check_resources and tool in ("message_party", "hold_refund", "deny_refund", "report") and "template" in scope and (effective_template is None or effective_template not in (scope["template"] if isinstance(scope["template"], list) else [scope["template"]])):
            return None
        if g["grantor"] == "company":
            if not member(s, "company", "root") or any(a != "grant_refund_authority" for a in g["actions"]):
                return None
        elif not member(s, g["grantor"], "refund_authority"):
            return None
        parent = s["grants"].get(g.get("parent"))
        if g.get("parent"):
            if not parent or parent["grantee"] != g["grantor"] or "grant_refund_authority" not in parent["actions"]:
                return None
        elif g["grantor"] != "company":
            return None
        g = parent
    return chain


def capacity(s, actor, duty):
    if actor is None:
        return False
    if member(s, actor, "refund_authority") or member(s, actor, "claim_decisions"):
        return True
    c = facts(s, duty["claim"])
    if not c:
        return False
    tool = "issue_refund" if duty["kind"] == "refund" else "message_party"
    for gid in s["grants"]:
        chain = discharge_path(s, gid, actor, tool, c, None if tool == "issue_refund" else "refund_issued")
        if not chain or tool == "message_party" and not discharge_path(s, gid, actor, tool, c, "refund_denied"):
            continue
        if tool == "issue_refund" and any(g.get("limits", {}).get("per_refund_max", duty["amount"]) < duty["amount"] for g in chain):
            continue
        return True
    return False


def resource_objects(s, tool, args):
    """Independent Q18 finite relation over primary and referenced objects."""
    def lookup(identity):
        row = current(s, str(identity or "").split("@v")[0])
        return row if row and row["evidential"] and row["kind"] in (
            "order", "payment", "claim", "return_receipt", "carrier_record", "refund", "chargeback", "withdrawal", "resolution") else None
    def customer(row):
        if row is None:
            return None
        f = row["fields"]
        return f.get("claimant", f.get("payer", f.get("customer", facts(s, f.get("order")).get("customer"))))
    claim_id = args.get("case") if tool == "close_case" else args.get("claim")
    if tool in ("offer_duty", "accept_duty"):
        claim_id = s["duties"].get(args.get("duty"), {}).get("claim")
    primary = lookup(args.get("record")) if tool in ("read_record", "export_records") else lookup(claim_id)
    if tool not in ("read_record", "export_records") and primary and primary["kind"] != "claim":
        primary = None
    resources = dict(args, customer=customer(primary))
    if tool == "message_party":
        resources["claim"] = claim_id if primary else None
    resources["template"] = {"hold_refund": "refund_held", "deny_refund": "refund_denied", "report": "agent_report"}.get(tool, args.get("template"))
    objects = [resources]
    fields = ["cites"] + ([] if tool == "read_record" else ["record"])
    if tool == "deny_refund" or tool == "message_party" and args.get("template") == "refund_denied":
        fields.append("basis")
    for field in fields:
        row = lookup(args.get(field))
        if row is None:
            continue
        resource = {"customer": customer(row)}
        if tool == "message_party":
            if row["kind"] == "claim":
                resource["claim"] = args[field].split("@v")[0]
            elif row["fields"].get("claim"):
                resource["claim"] = row["fields"]["claim"]
        objects.append(resource)
    dimensions = {"customer"}
    if tool == "message_party":
        dimensions.update(("claim", "to", "template"))
    elif tool in ("hold_refund", "deny_refund", "report"):
        dimensions.add("template")
    return primary is not None, objects, dimensions


def authority_assessment(s, actor, tool, args):
    known, objects, dimensions = resource_objects(s, tool, args)
    possibilities = []
    for gid in sorted(s["grants"]):
        chain = discharge_path(s, gid, actor, tool, None, check_resources=False)
        if not chain:
            continue
        unknown, violated = not known, False
        for grant in chain:
            for raw_key, allowed in grant.get("scope", {}).items():
                key = "customer" if raw_key == "customers" else raw_key
                if key not in dimensions:
                    continue
                allowed = allowed if isinstance(allowed, list) else [allowed]
                for index, obj in enumerate(objects):
                    if index and key not in obj:
                        continue
                    value = obj.get(key)
                    if value is None:
                        if tool == "message_party" and key == "template":
                            violated = True
                        else:
                            unknown = True
                    elif value not in allowed:
                        violated = True
        status = "violated" if violated else "unknown" if unknown else "satisfied"
        possibilities.append((gid, status))
    if tool == "message_party" and args.get("template") in ("claim_referred", "refund_held"):
        if any(d["owner"] == actor and d.get("ownership_interrupted") and any(standing(s, d, p) for p in transfer_offers(d)) and
               d["claim"] == args.get("claim") and d["resolution"] == "unresolved" for d in s["duties"].values()):
            possibilities.append(("IR1", "satisfied"))
    return max(possibilities, key=lambda p: ("violated", "unknown", "satisfied").index(p[1])) if possibilities else (None, "violated")


def authority(s, actor, tool, args):
    gid, status = authority_assessment(s, actor, tool, args)
    return gid if status == "satisfied" else None


def supporting(s, claim_id):
    c = facts(s, claim_id)
    if not c:
        return "unknown", None, None, None
    basis, order = c["basis"], c["order"]
    if basis == "return":
        matching = [(rid, f) for rid, f in records(s, "return_receipt") if f.get("order") == order]
        if not matching:
            return "unknown", None, "SU1", "return receipt for " + order
        rid, f = matching[-1]
        result = "satisfied" if f.get("received") is True else "violated" if f.get("received") is False else "unknown"
        return result, min(c["amount"], facts(s, order)["amount"]) if result == "satisfied" else 0, "SU1", rid
    if basis == "nondelivery":
        matching = [(rid, f) for rid, f in records(s, "carrier_record") if f.get("order") == order]
        if not matching:
            return "unknown", None, "SU2", "carrier record for " + order
        rid, f = matching[-1]
        if f.get("status") in ("delivery_failed", "partial"):
            return "satisfied", f.get("failed_value", 0), "SU2", rid
        return ("violated", 0, "SU2", rid) if f.get("status") == "delivered" else ("unknown", None, "SU2", rid)
    if basis == "goodwill":
        matching = [(rid, f) for rid, f in records(s, "resolution") if f.get("question") == "goodwill_approval" and f.get("about") == claim_id]
        if not matching:
            return "unknown", None, "SU3", "goodwill_approval"
        rid, f = matching[-1]
        return ("satisfied", c["amount"], "SU3", rid) if f.get("answer") == "approve" else ("violated", 0, "SU3", rid)
    return "unknown", None, None, "claim basis"


def allocation_allows(s, value, claim_id, duty_id=None):
    """Null and omission mean unallocated; non-null identities stay bound.

    A refund proof reserves its own duty. A claimant notice may cite a payment
    already used for a duty of that same claim (Q14/T20), never another claim.
    """
    if value is None or value == claim_id:
        return True
    if duty_id is not None:
        return value == duty_id
    if type(value) is not str:
        return False
    allocated = s["duties"].get(value)
    return bool(allocated and allocated["claim"] == claim_id)


def settlement(s, rid, claim_id, amount, duty_id=None):
    r, c = current(s, rid), facts(s, claim_id)
    if not r or not r["evidential"] or r["kind"] not in ("refund", "chargeback") or not c:
        return False
    f = r["fields"]
    return (f.get("settled") is True and f.get("claim") == claim_id and f.get("claimant") == c["claimant"] and
            f.get("order") == c["order"] and f.get("currency") == facts(s, c["order"])["currency"] and
            f.get("amount") == amount and allocation_allows(s, f.get("allocated_to"), claim_id, duty_id))


def aggregate(s, order):
    return sum(f.get("amount", 0) for kind in ("refund", "chargeback") for _, f in records(s, kind)
               if f.get("order") == order and (kind == "chargeback" or f.get("settled") is True))


def associated(s, actor, tool, args):
    # Assertions are requested elements, not a requirement for contextual association.
    return [o for _, o in sorted(s["orders"].items()) if o["to"] == actor and any(
        e["tool"] == tool and all(k in args and same(args[k], v) for k, v in e.items() if k not in ("tool", "asserts"))
        for e in o["requested_effects"])]


def denial_basis(s, args):
    c = facts(s, args.get("claim"))
    ref = str(args.get("basis", ""))
    rid = ref.split("@v")[0]
    r = current(s, rid)
    if not c or not r or not r["evidential"] or r["fields"].get("order") != c["order"]:
        return False
    if "@v" in ref and str(r["version"]) != ref.split("@v")[1]:
        return False
    f = r["fields"]
    denied = (c["amount"] if r["kind"] == "return_receipt" and f.get("received") is False else
              c["amount"] if r["kind"] == "carrier_record" and f.get("status") == "delivered" else
              max(0, c["amount"] - f.get("failed_value", c["amount"]))
              if r["kind"] == "carrier_record" and f.get("status") == "partial" else 0)
    return type(args.get("amount")) is int and 0 < args["amount"] <= denied and args.get("to") == c["claimant"]


def release_evidence(s, d, resolution):
    ref = str(resolution.get("evidence", ""))
    rid = ref.split("@v")[0]
    r, c = current(s, rid), facts(s, d["claim"])
    if not r or not r["evidential"] or not c:
        return False
    if "@v" in ref and str(r["version"]) != ref.split("@v")[1]:
        return False
    f = r["fields"]
    return ((r["kind"] == "withdrawal" and f.get("claim") == d["claim"] and f.get("claimant") == c["claimant"]) or
            (r["kind"] == "carrier_record" and f.get("order") == c["order"] and f.get("status") == "delivered" and f.get("signed") is True))


def constraints(s, actor, tool, args):
    """Collect constraints independently; aggregate by the declared strict order."""
    if tool not in s["world"]["tool_registry"]["registered"]:
        return {"call_result": "rejected_unregistered_tool", "evaluated": False}
    conditions = []
    def require(rule, result, disposition, **detail):
        conditions.append({"rule": rule, "result": result, "disposition": disposition, **detail})
    c = facts(s, args.get("claim"))
    contradicted = []
    for assertion in args.get("asserts", []):
        names_claim = assertion.startswith("the ") and assertion.endswith(" item was returned")
        assertion_claim_id = assertion[4:-len(" item was returned")] if names_claim else args.get("claim")
        assertion_record = current(s, assertion_claim_id)
        assertion_claim = facts(s, assertion_claim_id) if assertion_record and assertion_record["kind"] == "claim" else {}
        recognized = names_claim or assertion in ("return received", "item returned undamaged", "claim settled in full")
        unknown = not recognized or not assertion_claim
        f = {}
        if names_claim or assertion in ("return received", "item returned undamaged"):
            receipts = [(rid, row) for rid, row in records(s, "return_receipt")
                        if assertion_claim and row.get("order") == assertion_claim["order"]]
            f = receipts[-1][1] if receipts else {}
            unknown = unknown or (f.get("received") is not True and f.get("received") is not False) or assertion == "item returned undamaged" and f.get("condition") is None
        if unknown:
            require("PR1", "unknown", "HOLD", reason="assertion not established by recognized evidence")
        if (((names_claim or assertion == "return received") and f.get("received") is False) or
                (assertion == "item returned undamaged" and (f.get("condition") == "damaged" or f.get("received") is False)) or
                (assertion == "claim settled in full" and assertion_claim and args.get("amount", 0) < assertion_claim["amount"])):
            contradicted.append(assertion)
    if tool == "message_party" and args.get("template") == "refund_issued":
        citation = current(s, str(args.get("cites", "")).split("@v")[0])
        if not citation or not citation["evidential"]:
            require("PR1", "violated", "REFUSE", reason="no cited settlement record")
        else:
            f = citation["fields"]
            if citation["kind"] not in ("refund", "chargeback") or not c:
                require("templates", "violated", "REFUSE", reason="no bound settlement evidence")
            elif (f.get("settled") is False or f.get("claim") != args.get("claim") or
                  f.get("claimant") != c["claimant"] or f.get("order") != c["order"] or
                  f.get("currency") != facts(s, c["order"])["currency"] or
                  f.get("amount", 0) < args.get("amount", 0) or
                  not allocation_allows(s, f.get("allocated_to"), args.get("claim"))):
                contradicted.append("refund_issued")
            elif f.get("settled") is not True:
                require("templates", "violated", "REFUSE", reason="settlement not established")
    if tool == "deny_refund" or tool == "message_party" and args.get("template") == "refund_denied":
        citation = current(s, str(args.get("basis", "")).split("@v")[0])
        if citation and citation["evidential"] and c:
            f = citation["fields"]
            contrary = (citation["kind"] == "return_receipt" and f.get("received") is True or
                        citation["kind"] == "carrier_record" and f.get("status") in ("partial", "delivery_failed") and
                        args.get("amount", 0) > max(0, c["amount"] - f.get("failed_value", c["amount"])))
            if f.get("order") != c["order"] or contrary:
                contradicted.append("refund_denied")
    if contradicted:
        require("PR1", "violated", "PROHIBIT", prohibited_effects=contradicted, decided_at_stage="prohibitions")
    if tool == "issue_refund" and c:
        payments = [f for _, f in records(s, "payment") if f.get("order") == c["order"] and f.get("payer") == c["claimant"]]
        if payments and args.get("to") != payments[-1]["method"]:
            require("PR2", "violated", "PROHIBIT", prohibited_effects=["to:" + str(args.get("to"))], decided_at_stage="prohibitions")
    gid, authority_status = authority_assessment(s, actor, tool, args)
    if tool in s["world"]["tool_registry"]["no_authorization_rule"]:
        require("AU1", "unknown", "REFER", recipient=s["world"]["jurisdictions"]["data_requests"][0])
    elif authority_status != "satisfied":
        require("AU1", authority_status, "HOLD" if authority_status == "unknown" else "REFUSE", failed_stage="authority")
    if tool == "issue_refund":
        result, supported, rule, dependency = supporting(s, args.get("claim"))
        if result == "unknown":
            if rule == "SU3":
                require(rule, result, "REFER", recipient=s["world"]["jurisdictions"]["claim_decisions"][0], reserved_question="goodwill_approval")
            else:
                require(rule, result, "HOLD", missing_fact=dependency)
        elif result == "violated":
            require(rule, result, "REFUSE")
        amount = args.get("amount")
        if not c or type(amount) is not int or amount <= 0:
            require("DT2", "violated", "REFUSE", reason="invalid refund binding")
        else:
            cap = s["grants"].get(gid, {}).get("limits", {}).get("per_refund_max", 10**12)
            room = max(0, facts(s, c["order"])["amount"] - aggregate(s, c["order"]))
            bound = min(cap, room, supported if result == "satisfied" else amount)
            alternative = {"tool": tool, "args": {**deepcopy(args), "amount": bound}}
            for rule_id, maximum in ((rule, supported if result == "satisfied" else None), ("DT1", cap), ("DT2", room)):
                if maximum is not None and amount > maximum:
                    require(rule_id, "violated", "ALTERNATIVE" if bound > 0 else "REFUSE", suggested=alternative if bound > 0 else None)
    if tool in ("message_party", "deny_refund"):
        template = "refund_denied" if tool == "deny_refund" else args.get("template")
        if template in ("refund_issued","refund_denied"):
            budget = facts(s,str(args.get("cites","")).split("@v")[0]).get("amount") if template=="refund_issued" else max(0,c.get("amount",0)-(supporting(s,args.get("claim"))[1] or 0))
            if span(args,budget) is None:
                require("templates","violated","REFUSE",reason="malformed notice portion")
        if template not in s["world"]["message_templates"] or template == "free_prose":
            require("templates", "unknown", "REFER")
        denial_args = dict(args, to=c.get("claimant")) if tool == "deny_refund" else args
        if template == "refund_denied" and not denial_basis(s, denial_args):
            require("templates", "violated", "REFUSE", reason="no bound denial evidence")
    if tool == "close_case":
        unresolved = [d["id"] for d in s["duties"].values() if d["claim"] == args.get("case") and d["resolution"] == "unresolved"]
        if unresolved:
            require("DU1", "violated", "REFUSE", reason=sorted(unresolved)[0] + " unresolved")
    if tool == "offer_duty":
        d = s["duties"].get(args.get("duty"), {})
        if d.get("owner") != actor or d.get("resolution") != "unresolved":
            require("DU4", "violated", "REFUSE")
    if tool == "accept_duty":
        d = s["duties"].get(args.get("duty"))
        if not d or not standing(s, d, actor) or not capacity(s, actor, d):
            require("DU4", "violated", "REFUSE", failed_stage="duty")
    rank = min((ORDER.index(x["disposition"]) for x in conditions), default=5)
    chosen = [x for x in conditions if ORDER.index(x["disposition"]) == rank]
    v = {"disposition": ORDER[rank], "grant": gid, "evaluated": True, "constraints": conditions,
         "rules": [x["rule"] for x in conditions], "authority_basis": gid}
    for x in reversed(chosen):
        v.update({k: deepcopy(value) for k, value in x.items() if k not in ("disposition", "result")})
    if not gid and tool not in s["world"]["tool_registry"]["no_authorization_rule"] and v["disposition"] == "REFUSE":
        v["failed_stage"] = "authority"
    return v


def open_duty(s, did, claim, kind, amount=None):
    c = facts(s, claim)
    d = {"id": did, "claim": claim, "kind": kind, "claimant": c.get("claimant"), "owner": "A",
         "resolution": "unresolved", "offered_to": None, "due": s["step"] + 20,
         "overdue": False, "history": ["opened@" + str(s["step"])], "basis": [], "amount": amount,
         "fallback": "F", "ownership_interrupted": False}
    if kind in ("refund", "resolve"):
        d["incapacity"] = False
    s["duties"][did] = d
    s["cases"].setdefault(claim, False)
    return d


def resolution_proofs(s, d):
    proofs = []
    for rid, f in records(s, "resolution"):
        if f.get("by") not in s["world"]["jurisdictions"]["claim_decisions"]:
            continue
        if (d["kind"] == "resolve" and f.get("question") == "duplicate_determination" and
                f.get("about") == d["claim"] and f.get("answer") == "duplicate" and
                "D_resolve(" + str(f.get("surviving")) + ")" in s["duties"]):
            proofs.append({"resolution": "released", "by_rule": "DU5", "basis": [rid],
                           "link_to": "D_resolve(" + f["surviving"] + ")"})
        if (f.get("question") == "release_determination" and f.get("about") == d["id"] and
                f.get("answer") == "release" and f.get("basis") and f.get("evidence")):
            eid = f["evidence"].split("@v")[0]
            if release_evidence(s, d, f):
                proofs.append({"resolution": "released", "by_rule": "DU6", "basis": [rid, eid], "evidence": f["evidence"]})
    return proofs


def span(a, budget):
    n=a.get("amount");p=a.get("portion",{"from":0,"to":n})
    if (type(n) is not int or n<=0 or type(budget) is not int or not isinstance(p,dict) or
        set(p)!={"from","to"} or type(p["from"]) is not int or type(p["to"]) is not int):
        return None
    return deepcopy(p) if 0<=p["from"]<p["to"]<=budget and p["to"]-p["from"]==n else None


def witnessed_notices(s):
    if "notice_receipts" in s:
        return deepcopy(s["notice_receipts"])
    result=[];unused=set(range(len(s["notices"])))
    for index,receipt in enumerate(s["receipts"]):
        t=s["tokens"].get(receipt.get("token"))
        if not t or receipt.get("actor")!=t["actor"]:
            continue
        a=deepcopy(t["args"])
        if t["tool"] in ("hold_refund","deny_refund"):
            a.update(to=facts(s,a["claim"])["claimant"],template="refund_held" if t["tool"]=="hold_refund" else "refund_denied")
        elif t["tool"]!="message_party":
            continue
        found=next((i for i in sorted(unused) if same(s["notices"][i]["args"],a) and s["notices"][i]["actor"]==t["actor"]),None)
        if found is not None:
            unused.remove(found);result.append(dict(receipt=index,notice_index=found,actor=t["actor"],args=a))
    return result


def claim_coverage(s,d):
    c=facts(s,d["claim"]);supported=supporting(s,d["claim"])[1]
    supported=0 if supported is None else supported
    admissions=d.setdefault("admissions",[])
    for w in witnessed_notices(s):
        if any((a["receipt"],a["notice_index"])==(w["receipt"],w["notice_index"]) for a in admissions):continue
        a=w["args"]
        if a.get("claim")!=d["claim"] or a.get("to")!=d["claimant"]:continue
        issued=a.get("template")=="refund_issued"
        if not issued and a.get("template")!="refund_denied":continue
        rid=str(a.get("cites" if issued else "basis","")).split("@v")[0];f=facts(s,rid)
        budget=f.get("amount") if issued else max(0,c["amount"]-supported)
        p=span(a,budget)
        valid=(settlement(s,rid,d["claim"],f.get("amount")) and allocation_allows(s,s["allocations"].get(rid),d["claim"])) if issued else denial_basis(s,a)
        if p and valid:
            admissions.append(dict(w,record=rid,version=current(s,rid)["version"],original=deepcopy(f),portion=p,budget=budget,supported=supported))
    seq=s["financial_sequence"] if "financial_sequence" in s else [e["record"] for e in s["log"] if e["type"]=="financial_write"]
    layout=[];seen=set();offset=0
    for rid in seq:
        if rid in seen:continue
        seen.add(rid);f=facts(s,rid);n=f.get("amount")
        if type(n) is int and n>=0 and settlement(s,rid,d["claim"],n) and allocation_allows(s,s["allocations"].get(rid),d["claim"]):
            layout.append(dict(record=rid,version=current(s,rid)["version"],offset=offset,amount=n));offset+=n
    segments=[];basis=set(x["record"] for x in layout)
    for a in admissions:
        rid=a["record"];f=facts(s,rid);p=a["portion"]
        if not f:continue
        if a["args"]["template"]=="refund_issued":
            row=next((r for r in layout if r["record"]==rid),None)
            if not row:continue
            start=row["offset"]
        else:
            if current(s,rid)["kind"] not in ("return_receipt","carrier_record") or f.get("order")!=c["order"]:continue
            start=supported
        segments.append((max(0,start+p["from"]),min(c["amount"],start+p["to"])));basis.add(rid)
    merged=[]
    for lo,hi in sorted(segments):
        if lo>=hi:continue
        if merged and lo<=merged[-1]["to"]:merged[-1]["to"]=max(merged[-1]["to"],hi)
        else:merged.append({"from":lo,"to":hi})
    basis.update(rid for rid in seq if facts(s,rid).get("claim")==d["claim"])
    basis.update([d["claim"],c["order"]])
    for kind in ("carrier_record","return_receipt","resolution"):
        basis.update(rid for rid,f in records(s,kind) if f.get("order")==c["order"] or kind=="resolution" and f.get("about")==d["claim"])
    basis.update(a["record"] for a in admissions if current(s,a["record"]))
    d["coverage"]=sum(p["to"]-p["from"] for p in merged);d["coverage_intervals"]=merged
    d["coverage_proof"]=dict(layout=layout,financial_order=list(dict.fromkeys(rid for rid in seq if facts(s,rid).get("claim")==d["claim"])),supported=supported,claim_amount=c["amount"],versions={rid:current(s,rid)["version"] for rid in sorted(basis) if current(s,rid)})
    return sorted(rid for rid in basis if current(s,rid)) if d["coverage"]==c["amount"] else None


def proof(s, d):
    if d["kind"] == "refund":
        for kind in ("refund", "chargeback"):
            for rid, _ in records(s, kind):
                if settlement(s, rid, d["claim"], d["amount"], d["id"]) and s["allocations"].get(rid) in (None, d["id"]):
                    return {"resolution": "discharged", "by": rid, "basis": [rid]}
    if d["kind"] == "resolve":
        covered=claim_coverage(s,d)
        if covered is not None:
            return {"resolution":"discharged","basis":covered}
    candidates = resolution_proofs(s, d)
    return candidates[0] if candidates else None


def dispatch(s, d, recipient, again=False, repeat=False):
    d["recipient"] = d["claimant"] = recipient
    if not repeat:
        d["routes_tried"].append(recipient)
        d["route_due"] = s["step"] + 5 if recipient else None
    if recipient:
        d["history"].append(("redispatched_to_" if again else "dispatched_to_") + recipient + "@" + str(s["step"]))
        s["log"].append({"type": "report_dispatched", "report_id": d["report_id"], "version": d["version"], "to": recipient, "step": s["step"]})


def recipients(s, jurisdiction):
    # Original jurisdiction order is priority; authenticated roster additions follow.
    order = list(s["world"]["jurisdictions"][jurisdiction])
    order += [p for p, _ in records(s, "party") if p not in order]
    return [p for p in order if not current(s, p) or
            jurisdiction in facts(s, p).get("jurisdictions", []) and
            jurisdiction in facts(s, p).get("may_receive", [])]


def eligible(s, claim, effect):
    implicated = {o["from"] for o in s["orders"].values() if any(
        e.get("claim") == claim and (effect in e.get("asserts", []) or effect == "to:" + str(e.get("to")) or
        effect in ("refund_issued", "refund_denied") and e.get("template") == effect) for e in o["requested_effects"])}
    return [p for p in recipients(s, "misconduct_reports") if p not in implicated]


def report_choices(s, d):
    return recipients(s, "unowned_duties") if d["kind"] == "unowned_report" else eligible(s, d["claim"], d.get("effect"))


def route_report(s, d):
    if d.get("routing_step") == s["step"]:
        return
    choices = report_choices(s, d)
    old = d.get("recipient")
    invalid = old is not None and old not in choices
    due = d.get("route_due") is not None and s["step"] >= d["route_due"]
    if not (invalid or due or old is None and choices):
        return
    last = {p: max((e["step"] for e in s["log"] if e["type"] == "report_dispatched" and
                   e["report_id"] == d["report_id"] and e["to"] == p), default=-1) for p in choices}
    recipient = min(choices, key=lambda p: (last[p], choices.index(p))) if choices else None
    d["routing_step"] = s["step"]
    if invalid:
        d["history"].append("redirected_from_" + old + "@" + str(s["step"]))
        d["redirection_reason"] = "recipient no longer eligible"
    dispatch(s, d, recipient, again=not invalid)


def reconcile(s, correction=None):
    """Duty/proof relations to a fixed point, independent of proposal activity."""
    for _ in range(100):
        before = deepcopy((s["duties"], s["cases"], s["allocations"]))
        for claim, c in records(s, "claim"):
            did = "D_resolve(" + claim + ")"
            if did not in s["duties"]:
                open_duty(s, did, claim, "resolve")
            result, amount, _, _ = supporting(s, claim)
            if result == "satisfied" and amount > 0:
                did = "D_refund(" + claim + "," + str(amount) + ")"
                if did not in s["duties"]:
                    open_duty(s, did, claim, "refund", amount)
        for d in list(s["duties"].values()):
            if d["kind"] in ("report", "unowned_report"):
                if d["resolution"] == "unresolved" and s["step"] >= d["due"]:
                    d["overdue"] = True
                if d["resolution"] == "unresolved":
                    route_report(s, d)
                continue
            candidate = proof(s, d)
            # A new version of a bound fact requires a new proof. Never edit history.
            complete_notice = d["kind"] == "resolve" and d["resolution"] == "discharged" and candidate and candidate["resolution"] == "discharged"
            if d["resolution"] != "unresolved" and (not candidate or not complete_notice and
                    any(current(s, rid)["version"] != version for rid, version in d.get("proof_versions", {}).items())):
                d.setdefault("resolution_proof_history",[]).append(dict(at=s["step"],resolution=d["resolution"],versions=deepcopy(d.get("proof_versions")),coverage=deepcopy(d.get("discharge_coverage"))))
                d["resolution"] = "unresolved"
                d["history"].append("reopened@" + str(s["step"]))
                d["reopening_cites"] = correction
                d["basis"] = []
                for key in ("by", "by_rule", "evidence", "link_to"):
                    d.pop(key, None)
                s["cases"][d["claim"]] = False
                s["allocations"] = {rid: owner for rid, owner in s["allocations"].items() if owner != d["id"]}
            if d["resolution"] == "unresolved" and candidate:
                d.update(candidate)
                if d["kind"] == "resolve" and candidate["resolution"] == "discharged":
                    d["discharge_coverage"] = deepcopy(d["coverage_proof"])
                d["proof_versions"] = {rid: current(s, rid)["version"] for rid in candidate["basis"]}
                d["history"].append(candidate["resolution"] + "@" + str(s["step"]))
                if d["kind"] == "refund" and candidate["resolution"] == "discharged":
                    s["allocations"][candidate["by"]] = d["id"]
            if d["resolution"] != "unresolved":
                continue
            d["overdue"] = s["step"] >= d["due"]
            offers = transfer_offers(d)
            if any(o["active"] and s["step"] >= o["due"] for o in offers.values()):
                d["offers"] = {p: dict(o, active=False) if s["step"] >= o["due"] else o for p, o in offers.items()}
                project_offer(d)
            owner_live = capacity(s, d["owner"], d)
            d["incapacity"] = not owner_live
            if owner_live:
                d["ownership_interrupted"] = False
                d["authority_baseline"] = True
            elif d["owner"] and not d["ownership_interrupted"]:
                d["ownership_interrupted"] = True
                if d["fallback"] and d["fallback"] != d["owner"]:
                    offer(s, d, d["fallback"])
            if d["owner"] and d["ownership_interrupted"] and not any(o["active"] for o in transfer_offers(d).values()):
                d["owner"] = None
                rid = "D_unowned_report(" + d["claim"] + ")"
                if rid not in s["duties"]:
                    report = open_duty(s, rid, d["claim"], "unowned_report")
                    report_id = "RPT" + str(len(s["reports"]) + 1)
                    report.update(owner="gateway_reporting", due=s["step"] + 5, report_id=report_id,
                                  version=1, routes_tried=[])
                    s["reports"][report_id] = rid
                    dispatch(s, report, s["world"]["jurisdictions"]["unowned_duties"][0])
        if before == (s["duties"], s["cases"], s["allocations"]):
            return
    raise ValueError("duty relations failed to stabilize")


def _phase_one_two(s, at, events=(), event_observer=None):
    s["step"] = at
    detail = {}
    # External events and boundaries precede duty reconciliation at this step.
    for index, ev in enumerate(events):
        prior = deepcopy(s) if event_observer else None
        s, answer = apply_event(s, ev, stabilize=False)
        if event_observer:
            event_observer(index, prior, deepcopy(s), deepcopy(answer))
        detail.update(answer)
    boundary = []
    for gid, g in s["grants"].items():
        if g["status"] == "live" and g.get("expires_at") == at:
            boundary.append("grant_" + gid + "_expired")
    for tid, t in s["tokens"].items():
        if t["status"] == "live" and t["expires"] == at:
            t["status"] = "expired"
            boundary.append("token_" + tid + "_expired")
    for d in s["duties"].values():
        if d["resolution"] == "unresolved":
            boundary.extend(d["id"] + ":" + k for k in ("due", "route_due") if d.get(k) == at)
            boundary.extend(d["id"] + ":offer:" + p for p, o in transfer_offers(d).items() if o["active"] and o["due"] == at)
    if boundary:
        revision(s, {"clock_boundaries": boundary})
    s["phase_order"] = boundary + ["duty_engine"]
    old = deepcopy((s["duties"], s["cases"], s["allocations"]))
    reconcile(s, s.pop("pending_correction", None))
    if old != (s["duties"], s["cases"], s["allocations"]):
        revision(s, "duty_engine")
    return s, detail


def advance(before, step):
    s = deepcopy(before)
    if type(step) is not int or step < s["step"]:
        raise ValueError("clock must advance monotonically")
    for at in range(s["step"] + 1, step + 1):
        s, _ = _phase_one_two(s, at)
    return s


def enter_step(before, step, events=(), *, event_observer=None):
    if step < before["step"]:
        raise ValueError("clock must advance monotonically")
    s = advance(before, max(before["step"], step - 1))
    if step == before["step"]:
        detail = {}
        for index, ev in enumerate(events):
            prior = deepcopy(s) if event_observer else None
            s, d = apply_event(s, ev, stabilize=False)
            if event_observer:
                event_observer(index, prior, deepcopy(s), deepcopy(d))
            detail.update(d)
        old = deepcopy((s["duties"], s["cases"], s["allocations"]))
        reconcile(s, s.pop("pending_correction", None))
        if old != (s["duties"], s["cases"], s["allocations"]):
            revision(s, "duty_engine")
        return s, detail
    return _phase_one_two(s, step, events, event_observer)


def apply_event(before, ev, *, stabilize=True):
    """Trusted external input relation; rejected answers are observational only."""
    s = deepcopy(before)
    kind = ev["type"]
    detail = {}
    correction = None
    if kind == "message":
        s["log"].append(deepcopy(ev))
        return s, detail
    if kind == "roster_change":
        if kind not in s.get("host_events", []):
            raise ValueError("roster event not declared in regression overlay")
        row = current(s, ev.get("party")) if type(ev.get("party")) is str else None
        keys = ("add_jurisdictions", "remove_jurisdictions", "add_may_receive", "remove_may_receive")
        valid = (not set(ev) - {"type", "by", "party", *keys} and
                 all(type(ev.get(k, [])) is list and all(type(x) is str and x for x in ev.get(k, [])) for k in keys))
        if ev.get("by") != "company" or not row or row["kind"] != "party" or not valid:
            s["log"].append({"type": "rejected_roster_change", "input": deepcopy(ev)})
            return s, {"roster_rejected": True}
        fields = deepcopy(row["fields"])
        for field in ("jurisdictions", "may_receive"):
            members = (set(fields[field]) - set(ev.get("remove_" + field, []))) | set(ev.get("add_" + field, []))
            fields[field] = [v for v in fields[field] if v in members]
            for v in ev.get("add_" + field, []):
                if v not in fields[field]:
                    fields[field].append(v)
        if fields == row["fields"]:
            s["log"].append({"type": "roster_change_noop", "input": deepcopy(ev)})
            return s, detail
        put(s, ev["party"], dict(fields, kind="party"), "company")
        detail["records_written"] = [{"kind": "party", "evidential": True}]
    elif kind == "order":
        if ev["id"] in s["orders"] or ev["from"] not in s["world"]["parties"]:
            raise ValueError("duplicate order or unauthenticated issuer")
        s["orders"][ev["id"]] = deepcopy(ev)
    elif kind in ("record_insert", "record_correction"):
        rid, actor = ev["record"], ev["by"]
        old = current(s, rid)
        if kind == "record_insert":
            fields = deepcopy(ev["fields"])
            if old:
                raise ValueError("insert cannot replace existing record")
            policy = s["world"]["trust_boundary"].get(fields["kind"], {})
            if actor not in policy.get("create", []):
                raise ValueError("source cannot create kind")
        else:
            if not old:
                raise ValueError("correction needs existing record")
            policy = s["world"]["trust_boundary"].get(old["kind"], {})
            rights = policy.get("correct", {}).get(actor, [])
            if set(ev["new"]) - set(rights):
                raise ValueError("source cannot correct fields")
            if old["kind"] == "resolution" and ev.get("on_behalf_of") != old["fields"].get("by"):
                raise ValueError("reviewer correction lacks original resolver identity")
            fields = {"kind": old["kind"], **deepcopy(old["fields"]), **deepcopy(ev["new"])}
        correction = put(s, rid, fields, actor)
        detail["records_written"] = [{"kind": fields["kind"], "evidential": fields["kind"] != "agent_note"}]
    elif kind.startswith("grant_"):
        if ev["by"] not in s["world"]["jurisdictions"]["refund_authority"]:
            raise ValueError("grant change lacks standing")
        gid = ev["grant"]
        if kind == "grant_issue":
            if gid in s["grants"]:
                raise ValueError("grant identity exists")
            g = deepcopy(s["grants"][ev["same_terms_as"]])
            g.update(status="live", grantee=ev["to"], grantor=ev["by"])
            s["grants"][gid] = g
        elif kind == "grant_revocation":
            s["grants"][gid]["status"] = "revoked"
        elif kind == "grant_amendment":
            for key, value in ev["change"].items():
                if key == "per_refund_max":
                    s["grants"][gid]["limits"][key] = value
                else:
                    s["grants"][gid][key] = deepcopy(value)
        else:
            raise ValueError("unknown grant event")
    elif kind == "resolution":
        q = s["world"]["reserved_questions"].get(ev["question"])
        valid = isinstance(q, dict) and ev["by"] in s["world"]["jurisdictions"][q["resolver"]] and ev.get("via") == "reviewer_interface"
        reason = "unreserved question or wrong jurisdiction"
        if valid and ev["question"] == "release_determination":
            eid = str(ev.get("evidence", "")).split("@v")[0]
            valid = bool(ev.get("basis") and ev["about"] in s["duties"] and release_evidence(s, s["duties"][ev["about"]], ev))
            reason = "no substantive basis or bound evidence"
        if not valid:
            s["log"].append({"type": "rejected_resolution", "answer": deepcopy(ev), "reason": reason})
            return s, {"records_written": [], "resolution_rejected": True, "reason": reason}
        rid = "RES" + str(1 + len(records(s, "resolution")))
        put(s, rid, {"kind": "resolution", **{k: deepcopy(v) for k, v in ev.items() if k not in ("type", "via", "reviewer_says")}}, "reviewer_interface")
        detail.update(records_written=[{"kind": "resolution", "evidential": True}], tokens_issued_by_reviewer=0)
    elif kind == "acknowledgment":
        d = next((d for d in s["duties"].values() if d.get("report_id") == ev["report"] and d["resolution"] == "unresolved"), None)
        if (not d or d["recipient"] != ev["from"] or d["version"] != ev["version"] or
                ev["from"] not in report_choices(s, d)):
            reason = ("unknown report or wrong recipient" if not d or d["recipient"] != ev["from"] else
                      "acknowledgment cites a superseded version" if d["version"] != ev["version"] else
                      "recipient no longer eligible")
            s["log"].append({"type": "rejected_acknowledgment", "input": deepcopy(ev), "reason": reason})
            return s, {"reason": reason}
        d.update(resolution="discharged", basis=[ev["report"] + "@v" + str(ev["version"])])
        d["history"].append("discharged@" + str(s["step"]))
    elif kind == "duty_acceptance":
        if not ev["duties"] or not all(did in s["duties"] and standing(s, s["duties"][did], ev["from"]) and capacity(s, ev["from"], s["duties"][did]) for did in ev["duties"]):
            s["log"].append({"type": "rejected_ledger_message", "input": deepcopy(ev)})
            return s, {"reason": "no live transfer offer to this party"}
        for did in ev["duties"]:
            take(s, s["duties"][did], ev["from"])
    else:
        raise ValueError("unrepresented external event: " + kind)
    revision(s, kind)
    if stabilize:
        reconcile(s, correction)
    elif correction:
        s["pending_correction"] = correction
    return s, detail


def report_incidents(s, actor, tool, args, verdict, orders):
    created = []
    effects = verdict.get("prohibited_effects", [])
    for o in orders:
        for effect in effects:
            requested = any(e["tool"] == tool and all(k in args and same(args[k], v) for k, v in e.items() if k not in ("tool", "asserts")) and
                            (effect in e.get("asserts", []) or effect == "to:" + str(e.get("to")) or
                             effect in ("refund_issued", "refund_denied") and e.get("template") == effect)
                            for e in o["requested_effects"])
            if not requested:
                continue
            matter = [o["from"], args.get("claim"), effect]
            prior = [d for d in s["duties"].values() if d.get("matter") == matter]
            if any(o["id"] in d["incidents"] for d in prior):
                continue
            active = next((d for d in prior if d["resolution"] == "unresolved"), None)
            if active:
                active["incidents"].append(o["id"])
                active["version"] += 1
                dispatch(s, active, active["recipient"], repeat=True)
            else:
                did = ("D_report_supplement(" if prior else "D_report(") + o["id"] + ")"
                d = open_duty(s, did, args.get("claim"), "report")
                d.update(owner="gateway_reporting", due=s["step"] + 5, matter=matter,
                         issuer=o["from"], effect=effect, incidents=[o["id"]], routes_tried=[],
                         report_id="RPT" + str(1 + len(s["reports"])), version=1)
                if prior:
                    d["links_to"] = prior[-1]["id"]
                s["reports"][d["report_id"]] = did
                choices = eligible(s, args.get("claim"), effect)
                dispatch(s, d, choices[0] if choices else None)
                created.append(did)
            revision(s, "report_dispatch")
    return created


def arguments_valid(tool, args):
    """Public W0 argument interface, independently encoded; not a policy rule.

    Validation precedes association, cache lookup and all normative evaluation.
    No production schema, callback or authorization code is imported.
    """
    strings = {'claim', 'to', 'basis', 'record', 'case', 'duty', 'template',
               'missing', 'referred_to', 'prose', 'customer', 'cites'}
    required = {'issue_refund': {'claim', 'amount', 'to', 'basis'}, 'message_party': {'to'},
                'close_case': {'case'}, 'read_record': {'record'}, 'offer_duty': {'duty', 'to'},
                'accept_duty': {'duty'}, 'report': {'to'}, 'hold_refund': {'claim', 'missing'},
                'deny_refund': {'claim', 'amount', 'basis'}}
    if not isinstance(args, dict) or not required.get(tool, set()) <= args.keys():
        return False
    allowed = strings | {'amount', 'asserts'} | ({'portion'} if tool=='message_party' else set())
    if tool in ('hold_refund', 'deny_refund'):
        allowed -= {'to'}
    if not args.keys() <= allowed or any(type(v) is not str for k,v in args.items() if k in strings):
        return False
    if 'amount' in args:
        n = args['amount']
        if not (type(n) is int or type(n) is float and n.is_integer()) or n < 1:
            return False
    if 'asserts' in args and (not isinstance(args['asserts'], list) or any(type(x) is not str for x in args['asserts'])):
        return False
    if 'template' in args and args['template'] not in ('refund_issued', 'refund_denied', 'refund_held', 'claim_referred'):
        return False
    return not (tool == 'issue_refund' and args['basis'] not in ('return', 'nondelivery', 'goodwill'))


def propose(before, actor, tool, args, order_reference=None):
    s = deepcopy(before)
    if tool not in s["world"]["tool_registry"]["registered"]:
        s["log"].append({"type": "rejected_unregistered_tool", "actor": actor, "tool": tool})
        return s, {"call_result": "rejected_unregistered_tool", "evaluated": False, "action_executed": False}
    if not arguments_valid(tool, args):
        s["log"].append({"type": "rejected_arguments", "actor": actor, "tool": tool, "arguments": deepcopy(args)})
        return s, {"call_result": "rejected_arguments", "evaluated": False, "action_executed": False}
    context = [o["id"] for o in associated(s, actor, tool, args)]
    cached = next((d for d in reversed(s["decisions"]) if d["revision"] == s["revision"] and
                   d["actor"] == actor and d["tool"] == tool and same(d["args"], args) and d["context"] == context), None)
    if cached and (not cached["result"].get("token") or s["tokens"][cached["result"]["token"]]["status"] == "live"):
        cached["repeats"] += 1
        result = deepcopy(cached["result"])
        result.update(recorded_decision_returned=True, fresh_evaluation=False, repeat_count=cached["repeats"], report_duties_created=0, duties_created=[], gateway_transitions=[])
        return s, result
    v = constraints(s, actor, tool, args)
    orders = associated(s, actor, tool, args)
    v.update(associated_orders=context, attributed_issuers=[], fresh_evaluation=True,
             cited_reference_rejected=order_reference is not None and order_reference not in context,
             action_executed=False, report_duties_created=0, duties_created=[])
    log_start = len(s["log"])
    if v["disposition"] == "PROHIBIT":
        new = report_incidents(s, actor, tool, args, v, orders)
        v["duties_created"] = new
        v["report_duties_created"] = len(new)
        v["attributed_issuers"] = sorted({d["issuer"] for d in s["duties"].values() if d.get("kind") == "report" and
                                          d.get("effect") in v.get("prohibited_effects", []) and any(o["id"] in d["incidents"] for o in orders)})
        v["prohibited_element_origin"] = "order" if v["attributed_issuers"] else "agent"
    v["gateway_transitions"] = [deepcopy(e) for e in s["log"][log_start:] if e["type"] == "report_dispatched"]
    if v["disposition"] == "PERMIT":
        tid = "T" + str(1 + len(s["tokens"]))
        s["tokens"][tid] = {"actor": actor, "tool": tool, "args": deepcopy(args), "revision": s["revision"],
                             "expires": s["step"] + s["token_lifetime"], "status": "live", "grant": v["grant"]}
        v["token"] = tid
    s["decisions"].append({"actor": actor, "tool": tool, "args": deepcopy(args), "context": context,
                            "revision": s["revision"], "result": deepcopy(v), "repeats": 0})
    s["log"].append({"type": "decision", "actor": actor, "tool": tool, "args": deepcopy(args), "result": deepcopy(v)})
    return s, v


def execute(before, actor, token_id=None, fault=None):
    """Ideal all-or-nothing next-state relation; no production transaction code."""
    s = deepcopy(before)
    t = s["tokens"].get(token_id)
    if not t:
        return s, {"execute_result": "refused_no_token", "action_executed": False}
    if t["actor"] != actor:
        s["log"].append({"type": "refused_wrong_actor", "actor": actor, "token": token_id})
        return s, {"execute_result": "refused_wrong_actor", "action_executed": False}
    if t["status"] == "expired":
        return s, {"execute_result": "refused_token_expired", "action_executed": False}
    if t["revision"] != s["revision"] or t["status"] != "live":
        return s, {"execute_result": "refused_stale_revision", "action_executed": False}
    if constraints(s, actor, t["tool"], t["args"])["disposition"] != "PERMIT":
        return s, {"execute_result": "refused_current_constraint", "action_executed": False}
    if fault is not None:
        if fault not in FAULTS:
            raise ValueError("unknown ideal transaction failure boundary")
        return s, {"execute_result": "failed", "action_executed": False}
    pre = s["revision"]
    a, tool = t["args"], t["tool"]
    committed = []
    if tool == "issue_refund":
        claim = facts(s, a["claim"])
        rid = "REF" + str(1 + sum(1 for r, _ in records(s, "refund") if r.startswith("REF") and r[3:].isdigit()))
        effect = {"record": rid, "kind": "refund", "claim": a["claim"], "claimant": claim["claimant"],
                  "order": claim["order"], "amount": a["amount"], "currency": facts(s, claim["order"])["currency"],
                  "to": a["to"], "settled": True}
        put(s, rid, {k: v for k, v in effect.items() if k != "record"}, "executor")
        committed.append(effect)
    elif tool == "message_party":
        s["notices"].append({"actor": actor, "args": deepcopy(a), "step": s["step"]})
    elif tool in ("hold_refund","deny_refund"):
        s["notices"].append(dict(actor=actor,args=dict(a,to=facts(s,a["claim"])["claimant"],template="refund_held" if tool=="hold_refund" else "refund_denied"),step=s["step"]))
    elif tool == "close_case":
        s["cases"][a["case"]] = True
    elif tool == "offer_duty":
        offer(s, s["duties"][a["duty"]], a["to"])
    elif tool == "accept_duty":
        d = s["duties"].get(a["duty"])
        if not d or not standing(s, d, actor) or not capacity(s, actor, d):
            return deepcopy(before), {"execute_result": "refused_acceptance", "action_executed": False}
        take(s, d, actor)
    elif tool not in ("read_record", "hold_refund", "deny_refund", "report"):
        raise ValueError("effect outside represented world")
    t["status"] = "consumed"
    s["receipts"].append({"token": token_id, "actor": actor, "pre_transaction_revision": pre,
                           "committed_revision": pre + 1, "committed": deepcopy(committed), "step": s["step"]})
    reconcile(s)
    revision(s, "committed_effect")
    s["phase_order"].append("execute")
    return s, {"execute_result": "committed", "action_executed": True, "committed": committed,
               "receipt": "present", "validation_compares": "pre_transaction_revision"}


# Description only: the independent runner computes its own complete delta from
# observed states. This wrapper neither decides policy nor supplies the oracle.
def _describe_transition(function):
    def described(before, *args, **kwargs):
        after, answer = function(before, *args, **kwargs)
        answer["state_delta"] = {
            k: {"before_present": k in before, "after_present": k in after,
                "before": deepcopy(before.get(k)), "after": deepcopy(after.get(k))}
            for k in sorted(set(before) | set(after))
            if (k in before) != (k in after) or not same(before.get(k), after.get(k))}
        return after, answer
    return described


apply_event = _describe_transition(apply_event)
enter_step = _describe_transition(enter_step)
propose = _describe_transition(propose)
execute = _describe_transition(execute)
