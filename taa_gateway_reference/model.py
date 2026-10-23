"""Pure declarative transition model for gateway v0.3 property checkers.

No imports from taa_gateway, historical lab gates, world tools or model clients.
The trusted test driver supplies Event.actor; an agent payload cannot set it.
This model does not generate, save or bless independent expected traces.
"""
from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json

SATISFIED, VIOLATED, UNKNOWN = "satisfied", "violated", "unknown"
_ABSENT = object()
_SEVERITY = {"PERMIT": 0, "ALTERNATIVE": 1, "HOLD": 2, "REFER": 3, "REFUSE": 4, "PROHIBIT": 5}


class InvalidTransition(ValueError):
    pass


@dataclass(frozen=True)
class Rule:
    id: str
    stage: str
    tools: tuple
    expression: dict
    version: int = 1


@dataclass(frozen=True)
class Spec:
    tools: dict
    rules: tuple = ()
    # Authorization declarations, not inferred from presence of a grant.
    authorizations: tuple = ()
    fact_sources: dict = field(default_factory=dict)
    standing: dict = field(default_factory=dict)
    questions: dict = field(default_factory=dict)
    duty_rules: tuple = ()
    report_priority: tuple = ()
    clock_actor: str = "clock"
    configuration_actor: str = "configuration"
    report_owner: str = "gateway"
    report_deadline_steps: int = 2
    agent_actors: tuple = ("agent",)
    correction_rights: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Event:
    kind: str
    actor: str
    data: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Result:
    state: dict
    outcome: str
    detail: dict = field(default_factory=dict)


def initial(spec):
    """All policy comes from explicit declarations; an empty policy denies."""
    return {"revision": 0, "step": 0, "serial": 0, "records": {}, "grants": {},
            "orders": {}, "parties": {}, "duties": {}, "cases": {}, "totals": {},
            "entitlements": {}, "allocations": {}, "tokens": {}, "warrants": {},
            "decisions": [], "receipts": [], "history": [], "resolutions": {},
            "tools": deepcopy(spec.tools), "rules": deepcopy(list(spec.rules)),
            "authorizations": deepcopy(list(spec.authorizations)), "standing": deepcopy(spec.standing)}


def _same(a, b):
    # Python's True == 1 is not an acceptable scope or evidence match.
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def _now(state, record_id):
    versions = state["records"].get(record_id, [])
    return versions[-1] if versions else None


def _fact(state, record_id, name):
    record = _now(state, record_id)
    if record is None or not record["evidential"]:
        return _ABSENT
    return record["fields"].get(name, _ABSENT)


def _value(expression, state, arguments):
    if type(expression) is not dict or len(expression) != 1:
        raise ValueError("a model expression has exactly one declarative operator")
    operator, operand = next(iter(expression.items()))
    if operator == "literal":
        return operand
    if operator == "argument":
        return arguments.get(operand, _ABSENT)
    if operator in ("duty", "case", "grant"):
        collection = {"duty": "duties", "case": "cases", "grant": "grants"}[operator]
        return state[collection].get(operand[0], {}).get(operand[1], _ABSENT)
    if operator == "fact":
        return _fact(state, operand[0], operand[1])
    if operator == "exists":
        record = _now(state, operand)
        return False if record is None else (True if record["evidential"] else _ABSENT)
    if operator == "reserved":
        record_id = state["resolutions"].get(operand)
        return _fact(state, record_id, "answer") if record_id else _ABSENT
    if operator == "not":
        value = _value(operand, state, arguments)
        return _ABSENT if value is _ABSENT else not value if type(value) is bool else _ABSENT
    if operator in ("all", "any"):
        values = [_value(item, state, arguments) for item in operand]
        if any(value is not _ABSENT and type(value) is not bool for value in values):
            raise ValueError("logical expressions require Boolean operands")
        if operator == "all":
            return False if False in values else _ABSENT if _ABSENT in values else True
        return True if True in values else _ABSENT if _ABSENT in values else False
    if operator in ("eq", "ne", "lt", "le", "gt", "ge"):
        left, right = [_value(item, state, arguments) for item in operand]
        if left is _ABSENT or right is _ABSENT:
            return _ABSENT
        if operator in ("eq", "ne"):
            return _same(left, right) if operator == "eq" else not _same(left, right)
        if type(left) not in (int, float) or type(right) not in (int, float):
            return _ABSENT
        return {"lt": left < right, "le": left <= right, "gt": left > right, "ge": left >= right}[operator]
    raise ValueError("unsupported model expression: " + operator)


def rule_result(expression, state, arguments):
    value = _value(expression, state, arguments)
    return SATISFIED if value is True else VIOLATED if value is False else UNKNOWN


def _queries(expression, state):
    """Record negative queries as well as current evidence versions."""
    result = []
    if type(expression) is not dict:
        return result
    for operator, operand in expression.items():
        if operator in ("fact", "exists", "reserved"):
            record_id = operand[0] if operator == "fact" else operand if operator == "exists" else state["resolutions"].get(operand, "resolution:" + operand)
            record = _now(state, record_id)
            result.append({"record_id": record_id, "version": record["version"] if record else None,
                           "field": operand[1] if operator == "fact" else None,
                           "evidential": bool(record and record["evidential"])})
        elif operator not in ("literal", "argument", "duty", "case", "grant"):
            for item in operand if isinstance(operand, list) else [operand]:
                result.extend(_queries(item, state))
    return result


def _tighten(current, candidate):
    # Strict v0.3.1 Q1 precedence, independent of declaration order.
    return candidate if _SEVERITY[candidate] > _SEVERITY[current] else current


def _revision(state, reason):
    state["revision"] += 1
    for token in state["tokens"].values():
        if token["status"] == "live":
            token["status"] = "void"
    for warrant in state["warrants"].values():
        if warrant["status"] == "live":
            warrant["status"] = "void"
    state["history"].append({"event": "revision", "revision": state["revision"], "reason": reason})


def _put(state, record_id, kind, fields, writer, evidential):
    versions = state["records"].setdefault(record_id, [])
    if versions and versions[-1]["kind"] != kind:
        raise InvalidTransition("a source cannot replace another record kind")
    versions.append({"id": record_id, "kind": kind, "fields": deepcopy(fields),
                     "version": len(versions) + 1, "writer": writer, "evidential": evidential})


def _authority_result(grant, actor, tool, arguments, purpose, state, spec, visited=()):
    gid = grant["id"]
    if (gid in visited or len(visited) > 1 or grant["status"] != "live" or
            state["step"] >= grant["expires"] or grant["grantee"] != actor or
            tool not in grant["tools"] or grant["purpose"] != purpose or
            any(key not in arguments or not _same(arguments[key], value)
                for key, value in grant.get("scope", {}).items())):
        return VIOLATED
    conditions = [rule_result(condition, state, arguments) for condition in grant.get("conditions", [])]
    if VIOLATED in conditions:
        return VIOLATED
    parent_id = grant.get("parent")
    if parent_id:
        parent = state["grants"].get(parent_id)
        if not parent or grant["expires"] > parent["expires"]:
            return VIOLATED
        ancestor = _authority_result(parent, grant["grantor"], tool, arguments, purpose, state, spec, visited + (gid,))
        if ancestor == VIOLATED:
            return VIOLATED
        conditions.append(ancestor)
    elif tool not in state["standing"].get(grant["grantor"], ()):
        return VIOLATED
    return UNKNOWN if UNKNOWN in conditions else SATISFIED


def _limit(state, grant):
    limits, seen = [], set()
    while grant and grant["id"] not in seen:
        seen.add(grant["id"])
        if "limit_minor" in grant:
            limits.append(grant["limit_minor"])
        grant = state["grants"].get(grant.get("parent"))
    return min(limits) if limits else float("inf")


def _chain_live(state, grant):
    seen = set()
    while grant:
        if grant["id"] in seen or len(seen) > 1 or grant["status"] != "live" or state["step"] >= grant["expires"]:
            return False
        seen.add(grant["id"])
        parent_id = grant.get("parent")
        if parent_id and parent_id not in state["grants"]:
            return False
        grant = state["grants"].get(parent_id)
    return bool(seen)


def _binding_matches(record, condition):
    return (record is not None and record["evidential"] and
            record["kind"] == condition["kind"] and
            ("standing" not in condition or record["writer"] in condition["standing"]) and
            (record["kind"] != "settlement" or
             (record["fields"].get("settled") is True and
              bool(record["fields"].get("transaction_id")) and bool(record["fields"].get("allocation_id")))) and
            all(key in record["fields"] and _same(record["fields"][key], value)
                for key, value in condition["bindings"].items()))


def _eligible(state, spec, matter, issuer, disclosure):
    eligible = []
    for party_id in spec.report_priority:
        party = state["parties"].get(party_id)
        if (party and party_id != issuer and matter in party["jurisdictions"] and
                issuer not in party.get("conflicts", []) and
                all(item in party["may_receive"] for item in disclosure)):
            eligible.append(party_id)
    return eligible


def _report(state, spec, identity, case_id, issuer, matter, disclosure):
    duty_id = "report:" + identity
    if duty_id in state["duties"]:
        return False
    routes = _eligible(state, spec, matter, issuer, disclosure)
    recipient = routes[0] if routes else None
    state["duties"][duty_id] = {
        "id": duty_id, "case_id": case_id, "claimant": recipient, "owner": spec.report_owner,
        "kind": "report", "resolution": "unresolved", "overdue": False,
        "deadline": state["step"] + spec.report_deadline_steps,
        "offered_to": None, "basis": [], "history": [], "issuer": issuer,
        "matter": matter, "disclosure": list(disclosure), "recipient": recipient,
        "routes_tried": [recipient] if recipient else [], "route_deadline": state["step"] + spec.report_deadline_steps,
        "condition": {"kind": "report_ack", "bindings": {"report_id": duty_id, "report_version": 1, "recipient": recipient, "acknowledged": True}},
        "sent": True, "report_version": 1, "incidents": [],
        "release_conditions": []}
    return True


def _template(value, fields):
    if isinstance(value, str) and value.startswith("$"):
        return deepcopy(fields[value[1:]])
    if isinstance(value, dict):
        return {key: _template(item, fields) for key, item in value.items()}
    if isinstance(value, list):
        return [_template(item, fields) for item in value]
    return deepcopy(value)


def _duty_pass(state, spec, correction=None):
    """One declarative reconciliation pass, with deduplicated identities."""
    changed = False
    totals = {}
    for record_id in state["records"]:
        record = _now(state, record_id)
        values = record["fields"]
        if (record["kind"] == "settlement" and record["evidential"] and values.get("settled") is True and
                type(values.get("amount_minor")) is int and values["amount_minor"] > 0 and values.get("order_id")):
            totals[values["order_id"]] = totals.get(values["order_id"], 0) + values["amount_minor"]
    if totals != state["totals"]:
        state["totals"] = totals
        changed = True
    for declaration in spec.duty_rules:
        for record_id in sorted(state["records"]):
            record = _now(state, record_id)
            if (record["kind"] != declaration["source_kind"] or not record["evidential"] or
                    rule_result(declaration["when"], state, record["fields"]) != SATISFIED):
                continue
            duty_id = declaration["id"] + ":" + record_id
            if duty_id not in state["duties"]:
                duty = _template(declaration["template"], record["fields"])
                duty.update(id=duty_id, resolution="unresolved", overdue=False,
                            offered_to=None, basis=[], history=[], release_conditions=duty.get("release_conditions", []))
                state["duties"][duty_id] = duty
                changed = True
    # New report duties may arise while reconciling ownership. Iterate a stable,
    # deduplicated identity set rather than depending on proposal success.
    pending = list(sorted(state["duties"]))
    seen = set()
    while pending:
        duty_id = pending.pop(0)
        if duty_id in seen:
            continue
        seen.add(duty_id)
        duty = state["duties"][duty_id]
        if duty["resolution"] != "unresolved":
            valid = bool(duty["basis"]) and all(_binding_matches(_now(state, basis["record_id"]), basis["condition"])
                        for basis in duty["basis"])
            if not valid:
                duty["resolution"] = "unresolved"
                duty["history"].append({"event": "reopened", "correction": correction})
                duty["basis"] = []
                state["allocations"] = {key: value for key, value in state["allocations"].items() if value != duty_id}
                state["cases"].setdefault(duty["case_id"], {})["closed"] = False
                changed = True
        overdue = duty["overdue"] or (duty["resolution"] == "unresolved" and state["step"] >= duty["deadline"])
        if duty["overdue"] != overdue:
            duty["overdue"] = overdue
            changed = True
        if duty["resolution"] != "unresolved":
            continue
        grant_id = duty.get("under_grant")
        owner_grant = state["grants"].get(grant_id) if grant_id else None
        revoked_owner = bool(grant_id and (not owner_grant or not _chain_live(state, owner_grant)))
        if revoked_owner and not duty.get("ownership_interrupted"):
            duty["ownership_interrupted"] = True
            duty["offered_to"] = duty.get("fallback_owner")
            duty["offer_deadline"] = state["step"] + duty.get("response_steps", 1)
            if not duty["offered_to"]:
                duty["owner"] = None
            changed = True
        if duty.get("ownership_interrupted") and duty.get("offered_to") and state["step"] >= duty["offer_deadline"]:
            duty["owner"], duty["offered_to"] = None, None
            changed = True
        if (not duty.get("ownership_interrupted") and duty.get("offered_to") and
                state["step"] >= duty.get("offer_deadline", float("inf"))):
            duty["offered_to"] = None
            duty.pop("offer_deadline", None)
            changed = True
        if duty.get("ownership_interrupted") and duty["owner"] is None and duty.get("kind") != "report":
            changed |= _report(state, spec, "unowned:" + duty_id, duty["case_id"],
                               duty.get("issuer", ""), duty.get("matter", "refunds"), duty.get("disclosure", []))
        if duty.get("kind") == "report":
            eligible = _eligible(state, spec, duty["matter"], duty["issuer"], duty["disclosure"])
            if duty["recipient"] not in eligible or state["step"] >= duty["route_deadline"]:
                choices = [p for p in eligible if p not in duty["routes_tried"]]
                recipient = choices[0] if choices else None
                if recipient != duty["recipient"]:
                    duty["recipient"] = duty["claimant"] = recipient
                    duty["condition"]["bindings"]["recipient"] = recipient
                    duty["sent"] = False
                    duty["route_deadline"] = state["step"] + spec.report_deadline_steps
                    if recipient:
                        duty["routes_tried"].append(recipient)
                    changed = True
        candidates = []
        for record_id in sorted(state["records"]):
            record = _now(state, record_id)
            if _binding_matches(record, duty["condition"]):
                # Payment allocation is exclusive; notice/report evidence need
                # not reserve monetary allocation merely because it cites a payment.
                allocation = record["fields"].get("allocation_id")
                if allocation and state["allocations"].get(allocation) not in (None, duty_id):
                    continue
                if duty.get("kind") == "report" and record["writer"] != duty["recipient"]:
                    continue
                if duty.get("kind") == "report" and not duty["sent"]:
                    continue
                proof_condition = (dict(duty["condition"], standing=[duty["recipient"]])
                                   if duty.get("kind") == "report" else duty["condition"])
                candidates.append((record, proof_condition, "discharged"))
            for condition in duty["release_conditions"] if record["kind"] == "release_determination" else ():
                evidence = _now(state, record["fields"].get("evidence_id"))
                if (record["fields"].get("substantive_basis") and evidence and evidence["evidential"] and
                        evidence["version"] == record["fields"].get("evidence_version") and
                        _binding_matches(record, condition) and
                        record["writer"] in condition.get("standing", [duty["claimant"]])):
                    binding = dict(condition, standing=condition.get("standing", [duty["claimant"]]))
                    candidates.append((record, binding, "released"))
        if candidates:
            record, condition, resolution = candidates[0]
            duty["resolution"] = resolution
            duty["basis"] = [{"record_id": record["id"], "record_version": record["version"],
                              "condition": deepcopy(condition)}]
            if resolution == "released":
                evidence = _now(state, record["fields"]["evidence_id"])
                duty["basis"].append({"record_id": evidence["id"], "record_version": evidence["version"],
                                      "condition": {"kind": evidence["kind"], "bindings": deepcopy(evidence["fields"])}})
            duty["history"].append({"event": resolution, "basis": deepcopy(duty["basis"])})
            allocation = record["fields"].get("allocation_id")
            if allocation and resolution == "discharged":
                state["allocations"][allocation] = duty_id
            changed = True
        pending.extend(sorted(set(state["duties"]) - seen - set(pending)))
    return changed


def _stabilize(state, spec, correction=None):
    """Reach a fixed point, including declarations enabled by later duties."""
    changed = False
    for _ in range(1000):
        if not _duty_pass(state, spec, correction):
            return changed
        changed = True
    raise ValueError("duty declarations failed to reach a stable model state")


def decision(state, spec, actor, tool, arguments):
    """Evaluate separate declarative policy; returns a decision, never a token."""
    if tool not in state["tools"]:
        return {"disposition": "REJECT", "evaluated": False, "reasons": ["unregistered_tool"], "grant": None, "rule_results": []}
    disposition, reasons, results, alternative = "PERMIT", [], [], None
    rules = [rule for rule in state["rules"] if tool in rule.tools]
    for stage in ("prohibition", "authority", "support", "determination", "duty"):
        if stage == "authority":
            declarations = [a for a in state["authorizations"] if a["tool"] == tool]
            candidates = [(g, _authority_result(g, actor, tool, arguments, a["purpose"], state, spec))
                          for _, g in sorted(state["grants"].items()) for a in declarations]
            grants = [g for g, result in candidates if result == SATISFIED]
            amount = arguments.get("amount_minor", 0)
            amount = amount if type(amount) is int else 0
            chosen = min(grants, key=lambda g: (_limit(state, g) < amount, g["id"])) if grants else None
            if chosen is None:
                disposition = _tighten(disposition, "HOLD" if any(result == UNKNOWN for _, result in candidates) else "REFUSE" if declarations else "REFER")
                reasons.append("no_complete_live_authority")
        for rule in [r for r in rules if r.stage == stage]:
            result = rule_result(rule.expression, state, arguments)
            results.append({"id": rule.id, "version": rule.version, "result": result,
                            "queries": _queries(rule.expression, state)})
            if result != SATISFIED:
                disposition = _tighten(disposition, "HOLD" if result == UNKNOWN else
                                       "PROHIBIT" if stage == "prohibition" else "REFUSE")
                reasons.append(rule.id)
        if stage == "determination" and state["tools"][tool].get("effect") == "refund":
            claim = state["entitlements"].get(arguments.get("claim_id"))
            amount = arguments.get("amount_minor")
            if (not claim or type(amount) is not int or amount <= 0 or
                    arguments.get("currency") != claim["currency"] or
                    arguments.get("claimant") != claim["claimant"]):
                disposition = _tighten(disposition, "REFUSE")
                reasons.append("refund_binding_unknown_or_invalid")
            elif amount + state["totals"].get(claim["order_id"], 0) > claim["amount_minor"] or (
                    chosen is not None and amount > _limit(state, chosen)):
                room = max(0, min(claim["amount_minor"] - state["totals"].get(claim["order_id"], 0),
                                  _limit(state, chosen) if chosen else claim["amount_minor"]))
                alternative = {"tool": tool, "arguments": dict(arguments, amount_minor=room)} if room else None
                disposition = _tighten(disposition, "ALTERNATIVE" if room else "REFUSE")
                reasons.append("cumulative_or_grant_limit")
        if stage == "duty" and state["tools"][tool].get("effect") == "close":
            if any(d["case_id"] == arguments.get("case_id") and d["resolution"] == "unresolved"
                   for d in state["duties"].values()):
                disposition = _tighten(disposition, "REFUSE")
                reasons.append("unresolved_duty")
    return {"disposition": disposition, "reasons": reasons, "grant": chosen["id"] if chosen else None,
            "rule_results": results, "alternative": alternative}


def _matching_orders(state, actor, tool, arguments):
    return [order for _, order in sorted(state["orders"].items()) if order["recipient"] == actor and any(
        effect["tool"] == tool and all(key in arguments and _same(arguments[key], value)
        for key, value in effect["arguments"].items()) for effect in order["requested_effects"])]


def _propose(state, spec, event):
    tool, arguments = event.data["tool"], event.data["arguments"]
    if type(event.data.get("ttl", 10)) is not int or event.data.get("ttl", 10) <= 0:
        raise InvalidTransition("token lifetime must be positive integral steps")
    prior = next((d for d in reversed(state["decisions"]) if d["revision"] == state["revision"] and
                  d["actor"] == event.actor and d["tool"] == tool and _same(d["arguments"], arguments)), None)
    if prior:
        detail = {"decision": deepcopy(prior["decision"])}
        live = next((tid for tid, t in state["tokens"].items() if t["status"] == "live" and
                     t["revision"] == state["revision"] and t["actor"] == event.actor and
                     t["tool"] == tool and _same(t["arguments"], arguments)), None)
        if live:
            detail["token"] = live
        return "repeat", detail
    verdict = decision(state, spec, event.actor, tool, arguments)
    revision = state["revision"]
    state["decisions"].append({"revision": revision, "actor": event.actor, "tool": tool, "proposal": deepcopy(event.data),
                               "arguments": deepcopy(arguments), "decision": deepcopy(verdict)})
    state["history"].append({"event": "decision", "revision": revision, **deepcopy(verdict)})
    if verdict["disposition"] == "PROHIBIT":
        changed = False
        violated = [r["id"] for r in verdict["rule_results"] if r["result"] == VIOLATED]
        for order in _matching_orders(state, event.actor, tool, arguments):
            for effect in order["requested_effects"]:
                # Generic rule effects are declared by the order, not inferred from context.
                for prohibited in sorted(set(effect["prohibited_effects"]) & set(violated)):
                    key = hashlib.sha256(json.dumps([order["sender"], arguments.get("claim_id"), prohibited], sort_keys=True).encode()).hexdigest()
                    base_id = "ordered-act:" + key
                    prior = [d for d in state["duties"].values() if d.get("report_matter") == base_id]
                    if any(order["id"] in d["incidents"] for d in prior):
                        continue
                    active = next((d for d in prior if d["resolution"] == "unresolved"), None)
                    if active:
                        active["incidents"].append(order["id"])
                        active["report_version"] += 1
                        active["condition"]["bindings"]["report_version"] = active["report_version"]
                        active["sent"] = True
                        changed = True
                    else:
                        identity = base_id + (":supplement:" + order["id"] if prior else "")
                        created = _report(state, spec, identity, order.get("case_id", arguments.get("case_id", "unknown")),
                                          order["sender"], order["matter"], order.get("disclosure", []))
                        if created:
                            duty = state["duties"]["report:" + identity]
                            duty.update(origin_order=order["id"], report_matter=base_id, incidents=[order["id"]],
                                        attempted_act={"actor": event.actor, "tool": tool, "arguments": deepcopy(arguments)})
                            if prior:
                                duty["links_to"] = prior[-1]["id"]
                        changed |= created
        if changed:
            _revision(state, "ordered_refusal_duty")
        # Cache the completed decision at its post-report revision (Q4/Q9).
        state["decisions"][-1]["revision"] = state["revision"]
        return "PROHIBIT", {"decision": verdict}
    if verdict["disposition"] != "PERMIT":
        return verdict["disposition"], {"decision": verdict}
    state["serial"] += 1
    token_id, warrant_id = "T" + str(state["serial"]), "W" + str(state["serial"])
    grant = state["grants"][verdict["grant"]]
    ancestry, cursor = [], grant
    while cursor:
        ancestry.append(deepcopy(cursor))
        cursor = state["grants"].get(cursor.get("parent"))
    justification = {"grant": grant["id"], "purpose": grant["purpose"], "scope": deepcopy(grant.get("scope", {})),
                     "ancestry": ancestry, "rule_results": deepcopy(verdict["rule_results"]),
                     "grant_queries": [query for ancestor in ancestry for condition in ancestor.get("conditions", [])
                                       for query in _queries(condition, state)]}
    state["warrants"][warrant_id] = {"status": "live", "revision": revision,
                                    "grant": grant["id"], "decision": deepcopy(verdict), "justification": justification}
    state["tokens"][token_id] = {"status": "live", "warrant": warrant_id, "revision": revision,
                                "actor": event.actor, "tool": tool, "arguments": deepcopy(arguments),
                                "grant": grant["id"], "purpose": grant["purpose"],
                                "expires": min(grant["expires"], state["step"] + event.data.get("ttl", 10))}
    return "PERMIT", {"decision": verdict, "token": token_id}


def _execute(state, spec, event):
    token = state["tokens"].get(event.data["token"])
    if (not token or token["status"] != "live" or token["actor"] != event.actor or
            token["revision"] != state["revision"] or state["step"] >= token["expires"] or
            not _same(token["arguments"], event.data["arguments"]) or
            state["warrants"][token["warrant"]]["status"] != "live"):
        raise InvalidTransition("invalid token/actor/arguments/pre-state revision")
    grant = state["grants"].get(token["grant"])
    if not grant or _authority_result(grant, event.actor, token["tool"], token["arguments"], token["purpose"], state, spec) != SATISFIED:
        raise InvalidTransition("grant chain or clock no longer valid")
    if decision(state, spec, event.actor, token["tool"], token["arguments"])["disposition"] != "PERMIT":
        raise InvalidTransition("current cumulative or duty constraint")
    failure = event.data.get("fail_at")
    if failure not in (None, "validate", "stage", "consume", "effect", "duties", "receipt", "revision", "commit"):
        raise ValueError("unknown model failure boundary")
    effect = {"tool": token["tool"], "arguments": token["arguments"], "actor": event.actor}
    if not _same(event.data.get("staged_effect", effect), effect):
        raise InvalidTransition("staged effect mismatches token")
    if failure:
        raise InvalidTransition("injected transaction failure: " + failure)
    args = token["arguments"]
    operation = state["tools"][token["tool"]]["effect"]
    pre_revision = state["revision"]
    token["status"] = state["warrants"][token["warrant"]]["status"] = "consumed"
    if operation == "refund":
        claim = state["entitlements"][args["claim_id"]]
        order_id = claim["order_id"]
        state["totals"][order_id] = state["totals"].get(order_id, 0) + args["amount_minor"]
        payment_id = "payment:" + event.data["token"]
        _put(state, payment_id, "settlement", {**args, "settled": True, "order_id": order_id,
             "transaction_id": payment_id, "allocation_id": payment_id}, "gateway", True)
    elif operation == "close":
        state["cases"].setdefault(args["case_id"], {})["closed"] = True
    elif operation == "offer":
        duty = state["duties"][args["duty_id"]]
        if duty["owner"] != event.actor or duty["resolution"] != "unresolved":
            raise InvalidTransition("only an unresolved duty's owner can offer it")
        duty["offered_to"] = args["recipient"]
        duty["offer_deadline"] = state["step"] + duty.get("response_steps", 5)
    elif operation == "accept":
        _accept(state, event.actor, args["duty_id"])
    elif operation == "report":
        duty = state["duties"][args["duty_id"]]
        if (duty.get("kind") != "report" or event.actor != spec.report_owner or
                duty["recipient"] is None or args.get("recipient") != duty["recipient"]):
            raise InvalidTransition("report lacks independent standing or eligible recipient")
        duty["sent"] = True
    elif operation not in ("read", "message", "hold", "deny"):
        raise InvalidTransition("effect is not represented in this declarative model")
    _stabilize(state, spec)
    receipt = {"token": event.data["token"], "actor": event.actor,
               "pre_transaction_revision": pre_revision, "committed_revision": pre_revision + 1,
               "effect": deepcopy(effect)}
    state["receipts"].append(receipt)
    _revision(state, "committed_effect")
    return "committed", {"receipt": receipt}


def _accept(state, actor, duty_id):
    duty = state["duties"][duty_id]
    if duty["resolution"] != "unresolved" or duty["offered_to"] != actor:
        raise InvalidTransition("acceptance must come from the offered recipient")
    duty["owner"], duty["offered_to"] = actor, None
    duty["ownership_interrupted"] = False
    duty.pop("under_grant", None)  # the old owner's grant is never transferred
    duty["history"].append({"event": "accepted", "actor": actor})


def transition(before, event, spec):
    """A pure next-state relation. Rejected transitions leave the input unchanged.

    Event.actor is the independent driver's authenticated identity, not a field
    copied from gateway proposals/logs. No production implementation calls this.
    """
    state = deepcopy(before)
    try:
        if event.kind == "propose":
            outcome, detail = _propose(state, spec, event)
            return Result(state, outcome, detail)
        if event.kind == "execute":
            token = state["tokens"].get(event.data.get("token"))
            if token and token["actor"] != event.actor:
                state["history"].append({"event": "wrong_actor", "actor": event.actor, "token": event.data["token"]})
                return Result(state, "rejected", {"reason": "wrong actor"})
            outcome, detail = _execute(state, spec, event)
            return Result(state, outcome, detail)
        if event.kind == "record":
            kind = event.data["kind"]
            old = _now(state, event.data["id"])
            if event.actor in spec.agent_actors:
                raise InvalidTransition("record source is not independently authoritative")
            if old:
                rights = spec.correction_rights.get(kind, {}).get(event.actor, ())
                changed = {k for k in old["fields"].keys() | event.data["fields"].keys()
                           if not _same(old["fields"].get(k), event.data["fields"].get(k)) or
                           (k in old["fields"]) != (k in event.data["fields"])}
                if changed - set(rights):
                    raise InvalidTransition("source lacks field correction rights")
            elif event.actor not in spec.fact_sources.get(kind, ()):
                raise InvalidTransition("record source cannot create kind")
            _put(state, event.data["id"], kind, event.data["fields"], event.actor, True)
        elif event.kind == "assertion":
            if event.actor not in spec.agent_actors:
                raise InvalidTransition("assertion must come from a declared agent")
            _put(state, "assertion:" + event.actor + ":" + event.data["id"], "assertion",
                 event.data["fields"], event.actor, False)
        elif event.kind == "tick":
            if event.actor != spec.clock_actor or type(event.data["step"]) is not int or event.data["step"] <= state["step"]:
                raise InvalidTransition("invalid independent clock transition")
            state["step"] = event.data["step"]
            for update in event.data.get("due_records", []):
                if update["source"] in spec.agent_actors or update["source"] not in spec.fact_sources.get(update["kind"], ()):
                    raise InvalidTransition("invalid due external event")
                _put(state, update["id"], update["kind"], update["fields"], update["source"], True)
        elif event.kind == "grant":
            grant = deepcopy(event.data)
            if grant["grantor"] != event.actor or not (state["standing"].get(event.actor) or grant.get("parent")):
                raise InvalidTransition("grant issuer lacks standing")
            state["grants"][grant["id"]] = grant
        elif event.kind == "revoke":
            grant = state["grants"].get(event.data["id"])
            if not grant or grant["grantor"] != event.actor:
                raise InvalidTransition("revocation issuer mismatch")
            grant["status"] = "revoked"
        elif event.kind == "order":
            order = deepcopy(event.data)
            if order["id"] in state["orders"]:
                raise InvalidTransition("duplicate order identity")
            if not order.get("requested_effects") or any(not {"tool", "arguments", "prohibited_effects"} <= set(e)
                                                        for e in order["requested_effects"]):
                raise InvalidTransition("stored order needs structured requested effects")
            order["sender"] = event.actor
            state["orders"][order["id"]] = order
        elif event.kind == "resolution":
            question = spec.questions.get(event.data["question_id"])
            if (not question or event.actor not in question["reviewers"] or
                    event.data["jurisdiction"] != question["jurisdiction"] or
                    type(event.data["answer"]) is not bool):
                state["history"].append({"event": "rejected_resolution", "input": deepcopy(event.data), "actor": event.actor})
                return Result(state, "rejected", {"reason": "answer is not a scoped reserved-question resolution"})
            state["resolutions"][event.data["question_id"]] = "resolution:" + event.data["question_id"]
            _put(state, "resolution:" + event.data["question_id"], "resolution",
                 event.data, event.actor, True)
        elif event.kind == "accept":
            if event.actor in spec.agent_actors:
                raise InvalidTransition("agent acceptance must cross the token boundary")
            _accept(state, event.actor, event.data["duty_id"])
        elif event.kind == "configuration":
            if event.actor != spec.configuration_actor or any(key not in (
                    "parties", "entitlements", "cases", "rules", "tools", "authorizations", "standing") for key in event.data):
                raise InvalidTransition("not an authorized configuration transition")
            state.update(deepcopy(event.data))
        else:
            raise InvalidTransition("unknown model transition")
        if event.kind != "tick" or event.data.get("due_records"):
            _revision(state, event.kind)
        elif any(before["step"] < g["expires"] <= state["step"] and g["status"] == "live"
                 for g in state["grants"].values()) or any(
                 before["step"] < t["expires"] <= state["step"] and t["status"] == "live"
                 for t in state["tokens"].values()) or any(
                 d["resolution"] == "unresolved" and any(before["step"] < d.get(k, float("inf")) <= state["step"]
                 for k in ("deadline", "offer_deadline", "route_deadline")) for d in state["duties"].values()):
            _revision(state, "clock_boundary")
        if _stabilize(state, spec, correction=event.data.get("id")):
            _revision(state, "automatic_duty_changes")
        return Result(state, "accepted")
    except InvalidTransition as error:
        return Result(deepcopy(before), "rejected", {"reason": str(error)})
