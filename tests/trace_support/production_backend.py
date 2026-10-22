"""Actual production-core backend for the COMMON trace runner and state audits.

All normalization is from the native checkpoint, never returned descriptions.
Pending stage 6 capabilities are explicit; expected values are not read here.
"""
from copy import deepcopy

from taa_gateway.refunds import RefundWorld, PREFIX, abstract_id, native_id
from taa_gateway.serialization import canonical, copy_json
from taa_gateway.records import Write

KEY = b"offline-W0-simulator-test-key!!!!"


class UnsupportedCapability(Exception):
    pass


def _context(state):
    return RefundWorld(state["world"], KEY, native=state["native"],
                       events=[row["native_event"] for row in state["log"]], setup=state["setup"])


def _format(result):
    answer = copy_json(result)
    if "committed" in answer:
        for effect in answer["committed"]:
            effect["record"] = abstract_id(effect["record"])
    if "disposition" not in answer:
        return answer
    bad = [c for c in answer["checks"] if c["disposition"] != "PERMIT"]
    ids = ["DT1" if c["id"].startswith("per-refund-cap:") else c["id"] for c in bad]
    answer["rules"] = list(dict.fromkeys(ids))
    if ids:
        rule = "DT2" if "DT2" in ids and answer["disposition"] != "PROHIBIT" else ids[0]
        answer["rule"] = rule
        relevant = next(c for c in bad if ("DT1" if c["id"].startswith("per-refund-cap:") else c["id"]) == rule)
        answer["failed_stage"] = relevant["stage"]
        answer["decided_at_stage"] = "prohibitions" if relevant["stage"] == "prohibition" else relevant["stage"]
        answer["reason"] = relevant.get("reason", "")
        if relevant["result"] == "unknown":
            answer["missing_fact"] = relevant.get("reason", "")
        if relevant.get("question"):
            answer["reserved_question"] = relevant["question"]
        if relevant.get("referral"):
            answer["recipient"] = relevant["referral"].get("role")
    orders = [abstract_id(oid) for oid in answer["associated_orders"]]
    answer["associated_orders"] = orders
    answer["attributed_issuers"] = list(dict.fromkeys(abstract_id(row["issuer"]) for row in answer["report_candidates"]))
    answer["prohibited_element_origin"] = "order" if answer["attributed_issuers"] else "agent"
    if answer.get("alternative"):
        answer["suggested"] = {"tool": answer["alternative"]["tool"], "args": answer["alternative"]["arguments"]}
    for check in answer["checks"]:
        if "authority_basis" in check:
            answer["authority_basis"] = check["authority_basis"]
    answer["action_executed"] = False
    return answer


def _project(context, previous=None):
    state = context.store.snapshot()
    records = {abstract_id(rid): copy_json(versions) for rid, versions in state["records"].items()}
    tokens = {tid: dict(actor=abstract_id(row["certificate"]["acting_party"]), tool=row["tool"], args=row["args"],
                       revision=row["certificate"]["state_revision"], expires=row["certificate"]["expires_at_step"], status=row["status"])
              for tid, row in state["tokens"].items()}
    grants, orders = {}, {}
    for rid, versions in state["records"].items():
        fields, kind = versions[-1]["fields"], versions[-1]["kind"]
        if kind == "grant":
            grants[abstract_id(rid)] = {"grantor": abstract_id(fields["grantor"]), "grantee": abstract_id(fields["grantee"]),
                    "parent": abstract_id(fields["parent_grant"]) if fields["parent_grant"] else None, "actions": fields["action_types"],
                    "purpose": abstract_id(fields["purpose_id"]), "scope": fields["resource_scope"], "limits": fields["limits"],
                    "expires_at": fields["expires_at_step"], "status": fields["status"]}
        if kind == "stored_order":
            orders[abstract_id(rid)] = {"from": abstract_id(fields["envelope"]["authenticated_sender"]),
                "to": abstract_id(fields["envelope"]["recipient"]), "requested_effects": copy_json(fields["requested_effects"])}
    receipts = [{"token": r["token_id"], "actor": abstract_id(r["acting_party"]), "pre_transaction_revision": r["pre_transaction_revision"],
                 "committed": [dict(effect, record=abstract_id(effect["record"])) for effect in r["effect"]["committed"]]}
                for r in state["receipts"]]
    duties = {did: dict(copy_json(h[-1]["fields"]), owner=abstract_id(h[-1]["fields"]["owner"]) if h[-1]["fields"]["owner"] else None,
                        due=h[-1]["fields"]["deadline_step"], kind=h[-1]["fields"]["content"].get("kind"))
              for did, h in state["duty_records"].items()}
    log = [{"type": e["type"], "native_event": e,
            **({"result": _format(e["payload"]["result"])} if e["type"] in ("decision", "recorded_decision") else {})}
           for e in context.log.events()]
    return {"native": state, "world": copy_json(context.definition), "setup": copy_json((previous or {}).get("setup", {})),
            "records": records, "tokens": tokens, "duties": duties, "reports": copy_json(state["reports"]),
            "receipts": receipts, "notices": copy_json(state["notices"]), "allocations": copy_json(state["allocations"]),
            "cases": copy_json(state["cases"]), "grants": grants, "orders": orders, "log": log,
            "revision": state["revision"], "step": state["step"],
            "decisions": [dict(d, actor=abstract_id(d["actor"]), result=_format(d["result"])) for d in state["decisions"]],
            "phase_order": copy_json((previous or {}).get("phase_order", []))}


def _describe(before, after, result):
    result = copy_json(result)
    result["state_delta"] = {key: {"before_present": key in before, "after_present": key in after,
                                    "before": copy_json(before.get(key)), "after": copy_json(after.get(key))}
                             for key in sorted(before.keys() | after.keys())
                             if (key in before) != (key in after) or canonical(before.get(key)) != canonical(after.get(key))}
    return after, result


def start(world, setup=None, *, defer_first_step=False):
    setup = setup or {}
    if any(row.get("kind") == "resolution" for row in setup.get("records", {}).values()):
        raise UnsupportedCapability("stage 6: seeded duplicate/release resolution lifecycle")
    context = RefundWorld(world, KEY, setup=setup)
    state = _project(context, {"setup": setup})
    if not defer_first_step:
        state, _ = enter_step(state, 1)
    return state


def _find(context, rid):
    matches = [(key, versions[-1]) for key, versions in context.store.snapshot()["records"].items() if abstract_id(key) == rid.split("@v")[0]]
    if len(matches) != 1:
        raise ValueError("no unique native record: " + rid)
    return matches[0]


def apply_event(before, event, stabilize=True):
    context, result = _context(before), {}
    typ = event["type"]
    if typ in ("acknowledgment", "duty_acceptance"):
        raise UnsupportedCapability("stage 6: " + typ)
    if typ == "order":
        effects = [{"tool": effect["tool"], "arguments": {k: v for k, v in effect.items() if k not in ("tool", "asserts")},
                    "asserts": effect.get("asserts", [])} for effect in event["requested_effects"]]
        envelope = context.auth.issue(context.sessions[event["from"]], native_id(event["to"], "party"), before["step"],
                    "order", {"requested_effects": effects}, message_id=native_id(event["id"], "stored_order"))
        context.orders.receive(envelope)
    elif typ in ("record_insert", "record_correction"):
        if typ == "record_insert":
            fields = copy_json(event["fields"])
            kind = fields.pop("kind")
            rid = native_id(event["record"], kind)
        else:
            rid, current = _find(context, event["record"])
            kind, fields = current["kind"], copy_json(current["fields"])
            if kind == "resolution":
                raise UnsupportedCapability("stage 6: corrected discharge/release resolution")
            fields.update(event["new"])
        context.store.publish(context.sources[event["by"]], "external_record", [Write(rid, kind, fields)])
    elif typ in ("grant_revocation", "grant_amendment", "grant_issue"):
        if event["by"] not in context.definition["jurisdictions"]["refund_authority"]:
            raise ValueError("grant change outside jurisdiction")
        source_id = event.get("same_terms_as", event["grant"])
        _, record = _find(context, source_id)
        fields = copy_json(record["fields"])
        fields["id"] = native_id(event["grant"], "grant")
        if typ == "grant_revocation": fields["status"] = "revoked"
        elif typ == "grant_issue": fields.update(status="live", grantee=native_id(event["to"], "party"))
        else: fields["limits"].update(event["change"])
        context.store.publish(context.gateway, "grant_change", [Write(fields["id"], "grant", fields)])
    elif typ == "resolution":
        question = event["question"]
        refs = []
        if event.get("evidence"):
            rid, rec = _find(context, event["evidence"])
            requested = event["evidence"].split("@v")
            refs = [{"record_id": rid, "record_version": int(requested[1]) if len(requested) == 2 else rec["version"]}]
        spec = context.definition["reserved_questions"].get(question, {})
        envelope = context.auth.issue(context.sessions[event["by"]], "gateway", before["step"], "resolution",
            {"question_id": question, "jurisdiction": spec.get("resolver", "unreserved"),
             "answer": {"about": event["about"], "decision": event["answer"], "substantive_basis": event.get("basis")},
             "basis": refs}, message_id="resolution:RES" + str(len(context.log.events()) + 1))
        old = context.store.revision
        context.resolutions.receive(envelope)
        result.update(resolution_rejected=context.store.revision == old, tokens_issued_by_reviewer=0)
        if result["resolution_rejected"]:
            rejected = context.log.events()[-1]
            if rejected["type"] == "rejected_resolution":
                result["reason"] = rejected["payload"]["reason"]
    elif typ == "message":
        context.store.audit("message", event)
    else:
        raise UnsupportedCapability("unimplemented event: " + typ)
    after = _project(context, before)
    writes = []
    for rid, versions in after["records"].items():
        for index, version in enumerate(versions):
            if index >= len(before["records"].get(rid, [])):
                writes.append({"kind": version["kind"], "evidential": version["evidential"]})
    result["records_written"] = writes
    return _describe(before, after, result)


def enter_step(before, step, events=(), *, event_observer=None):
    context = _context(before)
    context.store.publish(context.gateway, "advance_clock", step=step)
    state = _project(context, before)
    state["phase_order"] = ["grant_" + gid + "_expired" for gid, grant in before["grants"].items()
                            if grant["status"] == "live" and before["step"] < grant["expires_at"] <= step]
    for number, event in enumerate(events):
        prior = deepcopy(state)
        state, description = apply_event(state, event, stabilize=False)
        if event_observer:
            event_observer(number, prior, state, description)
    state["phase_order"].append("duty_engine_unimplemented")
    return _describe(before, state, {})


def advance(before, step):
    state = before
    for at in range(before["step"] + 1, step + 1):
        state, _ = enter_step(state, at)
    return state


def reconcile(state):
    # No fake ledger transitions. Source stability assertions are incomplete.
    return None


def propose(before, actor, tool, args, order_reference=None):
    if tool in ("close_case", "offer_duty", "accept_duty", "hold_refund", "deny_refund"):
        raise UnsupportedCapability("stage 6: duty-dependent " + tool)
    if tool == "message_party" and any(g["status"] != "live" for gid, g in before["grants"].items() if gid != "G0") and not before["duties"]:
        raise UnsupportedCapability("stage 6: derive pending transfer before IR1 can apply")
    context = _context(before)
    result = context.runtime.propose(context.sessions[actor], {"tool": tool, "arguments": args,
        "order_reference": native_id(order_reference, "stored_order") if order_reference else None})
    result = _format(result)
    result["cited_reference_rejected"] = bool(order_reference and order_reference not in result.get("associated_orders", []))
    return _describe(before, _project(context, before), result)


def execute(before, actor, token_id=None, fault=None):
    context = _context(before)
    result = context.runtime.execute(context.sessions[actor], token_id, fault=fault)
    return _describe(before, _project(context, before), _format(result))


DUTY_ASSERTIONS = {"duties", "duties_created", "gateway_transitions", "not_recipient", "report_duties_created",
                   "reports_naming", "report_duties_for_matter", "arbitrary_recipient_chosen", "reopening_cites",
                   "released_or_discharged_by_revocation", "transfer_completed", "duty_engine_reaches_stable_state_each_step", "phase_order"}


def incomplete_assertion(key, state):
    if key in DUTY_ASSERTIONS:
        return "stage 6: independent duty engine / reporting not implemented"
    if key == "revision" and state["step"] >= 21:
        return "stage 6: claim-duty deadline boundary not yet derived"
    return None


def inject_hidden_state(state, result, kind, args):
    """Test-only host mutants change the authoritative native checkpoint.

    The original description is left untouched. The next exported projection
    is recomputed from the corrupted native state, not a fabricated effect list.
    """
    native = copy_json(state["native"])
    changed = False
    if (kind == "extra_settled_refund" and result.get("execute_result") == "committed" or
            kind == "refused_refund_without_description" and result.get("disposition") == "REFUSE"):
        rid = "refund:HIDDEN"
        native["records"][rid] = [{"schema_version": "0.3.1", "id": rid, "kind": "refund", "version": 1,
            "written_by": "mutant_executor", "written_under_warrant": None, "evidential": True,
            "fields": {"claim": "CL1", "claimant": "K1", "order": "ORD1", "amount": 1 if kind == "extra_settled_refund" else 120,
                       "currency": "USD", "to": "account_X" if kind == "extra_settled_refund" else "K1_card", "settled": True}}]
        changed = True
        if kind == "refused_refund_without_description":
            result.pop("action_executed", None)
    elif kind == "rewrite_REF1_v1" and args[1].get("type") == "record_correction" and args[1].get("record") == "REF1":
        native["records"]["refund:REF1"][0]["fields"]["settled"] = False
        changed = True
    if changed:
        context = RefundWorld(state["world"], KEY, native=native,
                              events=[row["native_event"] for row in state["log"]], setup=state["setup"])
        state = _project(context, state)
    return state, result
