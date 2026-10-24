"""Trusted W0 host, deterministic tools and SQL-backed conventional arm.

Agent calls use fixed host sessions. Source events enter only through separate
authenticated host channels. This module does not read expected outcomes.
"""
from .kernel import Authentication, Kernel, Refused, Store, copy, encode
from .ledger import Ledger
from .policy import Facts, Policy, arguments_valid, latest

KEY = b"offline-independent-W0-conventional-host-key"


def token_public(tid):
    return "T" + tid[1:] if isinstance(tid, str) and tid.startswith("H") else tid


def token_native(tid):
    return "H" + tid[1:] if isinstance(tid, str) and tid.startswith("T") else tid


def next_id(rows, prefix):
    number = 1
    while prefix + str(number) in rows:
        number += 1
    return prefix + str(number)


class World:
    def __init__(self, definition=None, setup=None, *, public=None):
        self.phase_order = copy((public or {}).get("phase_order", []))
        if public is None:
            self.store = Store(KEY)
            setup = copy(setup or {})
            seed = copy(definition["records"])
            for rid in setup.get("remove_records", []):
                seed.pop(rid, None)
            for rid, changes in setup.get("records", {}).items():
                seed.setdefault(rid, {}).update(changes)
            grants = copy(definition["grants"])
            for gid, changes in setup.get("grants", {}).items():
                grants.setdefault(gid, {}).update(changes)
            with self.store.transaction():
                self.store.append("configuration", "world", definition, relevant=False)
                self.store.append("configuration", "setup", setup, relevant=False)
                if "roster_change" in setup.get("host_events", []):
                    for party in list(definition["parties"]) + ["company"]:
                        seed[party] = {"kind": "party", "name": party,
                            "role": definition["parties"].get(party, {}).get("role", "root"),
                            "jurisdictions": [j for j, names in definition["jurisdictions"].items() if party in names]
                                if party != "company" else ["root", "interim"],
                            "conflicts": [], "may_receive": [j for j in ("misconduct_reports", "unowned_duties")
                                if party in definition["jurisdictions"][j]]}
                for rid, fields in seed.items():
                    fields = copy(fields)
                    kind = fields.pop("kind")
                    boundary = definition["trust_boundary"].get(kind, {})
                    provider = boundary.get("create", ["setup"])[0]
                    self.store.append("records", rid, {"kind": kind, "writer": provider,
                        "evidential": bool(boundary.get("evidential", True)), "fields": fields}, relevant=False)
                for gid, grant in grants.items():
                    self.store.append("grants", gid, grant, relevant=False)
        else:
            anchor = public["log"][-1]
            if anchor["type"] != "signed_sql_checkpoint":
                raise PermissionError("missing host checkpoint")
            checkpoint = copy(public["relational_checkpoint"])
            checkpoint["events"] = [row["sql_event"] for row in public["log"][:-1]]
            checkpoint["signature"] = anchor["signature"]
            self.store = Store(KEY, checkpoint=checkpoint)
        config = self.store.current("configuration")
        self.definition, self.setup = config["world"], config["setup"]
        self.policy = Policy(self.definition)
        self.ledger = Ledger(self.policy)
        self.auth = Authentication(KEY)
        names = set(self.definition["parties"]) | {"company", "warehouse", "carrier", "payment_processor", "customer_portal", "reviewer_interface"}
        self.sessions = {name: self.auth.session(name, ("act", "record", "order", "resolution", "acceptance", "acknowledgment", "grant", "roster")) for name in sorted(names)}
        self.kernel = Kernel(self.store, self.auth,
            lambda view, actor, tool, args: self.policy.evaluate(view, actor, tool, args).get("disposition") == "PERMIT",
            self.stage, self.ledger.stabilize, self.verify_plan)

    def stage(self, view, actor, tool, args):
        facts = Facts(view)
        claim = facts.get(args.get("claim")) or {}
        def row(relation, rid, payload):
            return [{"relation": relation, "id": rid, "payload": payload}]
        if tool == "issue_refund":
            order = facts.get(claim["order"])
            fields = {"claim": args["claim"], "claimant": claim["claimant"], "order": claim["order"],
                      "amount": args["amount"], "currency": order["currency"], "to": args["to"], "settled": True}
            return row("records", next_id(facts.records, "REF"), {"kind": "refund", "writer": "executor", "evidential": True, "fields": fields})
        if tool in ("message_party", "hold_refund", "deny_refund", "report"):
            notice = copy(args)
            if tool in ("hold_refund", "deny_refund"):
                notice.update(to=claim["claimant"], template="refund_held" if tool == "hold_refund" else "refund_denied")
            if tool == "report":
                notice["template"] = "agent_report"
            return row("notices", next_id(latest(view, "notices"), "N"), notice)
        if tool in ("offer_duty", "accept_duty"):
            action = {"action": "offer" if tool == "offer_duty" else "accept", "actor": actor,
                      "duty": args["duty"], "handled": False}
            if tool == "offer_duty":
                action["to"] = args["to"]
            return row("duty_actions", next_id(latest(view, "duty_actions"), "DA"), action)
        if tool == "close_case":
            return row("cases", args["case"], {"closed": True})
        if tool == "read_record":
            return []
        raise Refused("unregistered_effect_service")

    def verify_plan(self, view, actor, tool, args, plan):
        """Service frame/effect checks, independent of normative policy results."""
        if tool == "read_record":
            return plan == []
        if len(plan) != 1:
            return False
        item, facts = plan[0], Facts(view)
        relation, payload = item["relation"], item["payload"]
        if tool == "issue_refund":
            claim = facts.get(args["claim"])
            order = facts.get(claim.get("order")) if claim else None
            if not claim or not order or item["id"] in facts.records or relation != "records":
                return False
            fields = payload.get("fields", {})
            return (set(fields) == {"claim", "claimant", "order", "amount", "currency", "to", "settled"} and
                set(payload) == {"kind", "writer", "evidential", "fields"} and
                payload.get("kind") == "refund" and payload.get("writer") == "executor" and payload.get("evidential") is True and
                fields["claim"] == args["claim"] and fields["claimant"] == claim["claimant"] and
                fields["order"] == claim["order"] and fields["amount"] == args["amount"] and
                fields["currency"] == order["currency"] and fields["to"] == args["to"] and fields["settled"] is True)
        if tool == "close_case":
            return relation == "cases" and item["id"] == args["case"] and payload == {"closed": True}
        if tool in ("offer_duty", "accept_duty"):
            expected = {"actor": actor, "duty": args["duty"], "handled": False,
                        "action": "offer" if tool == "offer_duty" else "accept"}
            if tool == "offer_duty":
                expected["to"] = args["to"]
            return relation == "duty_actions" and item["id"] not in latest(view, "duty_actions") and encode(payload) == encode(expected)
        if tool in ("message_party", "hold_refund", "deny_refund", "report"):
            if relation != "notices" or item["id"] in latest(view, "notices"):
                return False
            expected = copy(args)
            if tool == "report":
                expected["template"] = "agent_report"
            elif tool in ("hold_refund", "deny_refund"):
                claim = facts.get(args["claim"])
                if not claim:
                    return False
                expected.update(to=claim["claimant"], template="refund_held" if tool == "hold_refund" else "refund_denied")
            return encode(payload) == encode(expected)
        return False

    def _envelope(self, sender, channel, recipient, payload):
        return self.auth.envelope(self.sessions[sender], channel, recipient, self.store.step, payload,
                                  channel + ":" + str(len(self.store.events()) + 1))

    def event(self, event):
        store, kind = self.store, event["type"]
        if kind == "roster_change":
            if kind not in self.setup.get("host_events", []):
                raise ValueError("roster_change not enabled by regression setup")
            envelope = self._envelope(event["by"], "roster", "roster", event)
            with store.transaction():
                verified = store.accept_envelope(self.auth, envelope, channel="roster", recipient="roster")
                payload = verified["payload"]
                keys = ("add_jurisdictions", "remove_jurisdictions", "add_may_receive", "remove_may_receive")
                valid = (not set(payload) - {"type", "by", "party", *keys} and
                    all(type(payload.get(k, [])) is list and all(type(x) is str and x for x in payload.get(k, [])) for k in keys))
                previous = store.current("records").get(payload.get("party")) if type(payload.get("party")) is str else None
                if verified["sender"] != "company" or not previous or previous["kind"] != "party" or not valid:
                    store.event("rejected_roster_change", {"envelope": verified})
                    return {"roster_rejected": True}
                fields = copy(previous["fields"])
                for field in ("jurisdictions", "may_receive"):
                    present = set(fields[field])
                    wanted = (present - set(payload.get("remove_" + field, []))) | set(payload.get("add_" + field, []))
                    fields[field] = [x for x in fields[field] if x in wanted]
                    for x in payload.get("add_" + field, []):
                        if x not in fields[field]:
                            fields[field].append(x)
                if fields == previous["fields"]:
                    store.event("roster_change_noop", {"envelope": verified})
                else:
                    store.append("records", payload["party"], {"kind": "party", "writer": "company",
                        "evidential": True, "fields": fields})
            return {}
        if kind in ("record_insert", "record_correction"):
            if kind == "record_insert":
                fields = copy(event["fields"])
                record_kind = fields.pop("kind")
                operation, record = "create", event["record"]
            else:
                record = event["record"].split("@v")[0]
                current = store.current("records")[record]
                record_kind, fields, operation = current["kind"], copy(event["new"]), "correct"
            if record_kind == "resolution":
                if kind != "record_correction" or set(fields) != {"answer"}:
                    raise PermissionError("resolution writes require reviewer admission")
                current = store.current("records")[record]["fields"]
                return self._resolution(dict(current, answer=fields["answer"], by=event["on_behalf_of"]), correction=record)
            sender = "A" if event["by"] == "any_agent" else event["by"]
            envelope = self._envelope(sender, "record", "records", {"record": record, "kind": record_kind,
                                       "operation": operation, "fields": fields})
            store.source_write(self.auth, envelope, self.definition["trust_boundary"],
                               agents=[p for p, r in self.definition["parties"].items() if r["role"] == "agent"])
            return {}
        if kind == "resolution":
            return self._resolution({k: v for k, v in event.items() if k not in ("type", "via", "reviewer_says")})
        if kind in ("acknowledgment", "duty_acceptance"):
            channel = "acceptance" if kind == "duty_acceptance" else "acknowledgment"
            envelope = self._envelope(event["from"], channel, "gateway_reporting", event)
            with store.transaction():
                verified = store.accept_envelope(self.auth, envelope, channel=channel, recipient="gateway_reporting")
                if kind == "acknowledgment":
                    return self.ledger.acknowledgment(store, verified["sender"], event["report"], event["version"])
                accepted = [d for d in event["duties"] if self.ledger.accept(store, verified["sender"], d)]
                return {"accepted_duties": accepted}
        if kind == "order":
            envelope = self._envelope(event["from"], "order", event["to"], {"requested_effects": event["requested_effects"]})
            with store.transaction():
                verified = store.accept_envelope(self.auth, envelope, channel="order", recipient=event["to"])
                if event["id"] in store.current("orders"):
                    raise PermissionError("stored order identity already used")
                store.append("orders", event["id"], {"from": verified["sender"], "to": verified["recipient"],
                    "requested_effects": event["requested_effects"], "envelope": verified})
            return {}
        if kind in ("grant_revocation", "grant_amendment", "grant_issue"):
            envelope = self._envelope(event["by"], "grant", "grants", event)
            with store.transaction():
                verified = store.accept_envelope(self.auth, envelope, channel="grant", recipient="grants")
                if verified["sender"] not in self.definition["jurisdictions"]["refund_authority"]:
                    raise PermissionError("issuer has no refund_authority jurisdiction")
                grants = store.current("grants")
                grant = copy(grants[event.get("same_terms_as", event["grant"])])
                if kind == "grant_revocation":
                    grant["status"] = "revoked"
                elif kind == "grant_amendment":
                    for key,value in event["change"].items():
                        if key == "scope":grant["scope"] = copy(value)
                        else:grant.setdefault("limits", {})[key] = copy(value)
                else:
                    if event["grant"] in grants:
                        raise PermissionError("grant identity already exists")
                    grant.update(status="live", grantee=event["to"], grantor=verified["sender"])
                store.append("grants", event["grant"], grant)
            return {}
        if kind == "message":
            store.audit("plain_message", event)
            return {}
        raise ValueError("unregistered host event: " + str(kind))

    def _resolution(self, payload, correction=None):
        store = self.store
        payload = copy(payload)
        question = self.definition["reserved_questions"].get(payload["question"])
        valid = isinstance(question, dict) and payload["by"] in self.definition["jurisdictions"][question["resolver"]]
        if valid and payload["question"] == "release_determination":
            valid = self.ledger.release_admissible(store.snapshot(), payload)
            if not valid:
                store.audit("resolution_rejected", payload)
                return {"resolution_rejected": True, "reason": "no substantive basis or bound evidence", "tokens_issued_by_reviewer": 0}
        if not valid:
            store.audit("resolution_rejected", payload)
            return {"resolution_rejected": True, "tokens_issued_by_reviewer": 0}
        envelope = self._envelope(payload["by"], "resolution", "reviewer_interface", payload)
        with store.transaction():
            verified = store.accept_envelope(self.auth, envelope, channel="resolution", recipient="reviewer_interface")
            payload["by"] = verified["sender"]
            rid = correction or next_id(store.current("records"), "RES")
            store.append("records", rid, {"kind": "resolution", "writer": "reviewer_interface", "fields": payload, "evidential": True})
        return {"resolution_rejected": False, "tokens_issued_by_reviewer": 0}

    def clock(self, step):
        phases = []
        def boundaries(store):
            for gid, grant in store.current("grants").items():
                if grant.get("status") == "live" and step >= grant.get("expires_at", float("inf")):
                    grant["status"] = "expired"
                    store.append("grants", gid, grant)
                    phases.append("grant_" + gid + "_expired")
        self.store.clock(step, boundaries)
        self.phase_order = phases

    def reconcile(self):
        with self.store.transaction():
            self.ledger.stabilize(self.store)

    def propose(self, actor, tool, args, order_reference=None):
        store = self.store
        store.audit("proposal", {"actor": actor, "tool": tool, "args": args, "order_reference": order_reference})
        if tool not in self.definition["tool_registry"]["registered"] or not arguments_valid(tool, args):
            result = self.policy.evaluate(store.snapshot(), actor, tool, args)
            store.audit(result["call_result"], result)
            return result
        cached = next(((did, d) for did, d in reversed(list(store.current("decisions").items()))
            if d["actor"] == actor and d["tool"] == tool and encode(d["args"]) == encode(args) and d["revision"] == store.epoch and
               (not d["result"].get("token") or store.current("handles").get(token_native(d["result"]["token"]), {}).get("status") == "live")), None)
        if cached:
            did, row = cached
            row["repeats"] += 1
            result = dict(copy(row["result"]), fresh_evaluation=False, recorded_decision_returned=True, repeat_count=row["repeats"])
            result["cited_reference_rejected"] = order_reference is not None and order_reference not in result["associated_orders"]
            with store.transaction():
                store.append("decisions", did, row, relevant=False)
                store.event("recorded_decision", {"result": result})
            return result
        result = self.policy.evaluate(store.snapshot(), actor, tool, args)
        with store.transaction():
            result.update(self.ledger.report(store, actor, tool, args, result["checks"]))
        result.update(fresh_evaluation=True, recorded_decision_returned=False, repeat_count=0, token=None,
                      cited_reference_rejected=order_reference is not None and order_reference not in result["associated_orders"])
        if result["disposition"] == "PERMIT":
            try:
                hid = self.kernel.issue(self.sessions[actor], tool, args, lifetime=self.setup.get("token_lifetime", 10))
            except Refused as error:
                store.audit("effect_plan_refused", {"reason": str(error)})
                result.update(disposition="REFUSE", reason=str(error))
            else:
                result["token"] = token_public(hid)
                if hid:
                    result["token_expires_at"] = store.current("handles")[hid]["expires"]
        with store.transaction():
            did = "D" + str(len(store.current("decisions")) + 1)
            store.append("decisions", did, {"actor": actor, "tool": tool, "args": args, "revision": store.epoch,
                "result": result, "repeats": 0}, relevant=False)
            store.event("decision", {"result": result})
        return result

    def execute(self, actor, token, fault=None):
        result = self.kernel.execute(self.sessions[actor], token_native(token), fault=fault)
        if result["committed"]:
            return {"execute_result": "committed", "validation_compares": "pre_transaction_revision"}
        reason = result["reason"]
        return {"execute_result": "failed" if "partial_transaction" in result else
                {"wrong_actor": "refused_wrong_actor", "expired_handle": "refused_token_expired",
                 "stale_epoch": "refused_stale_revision"}.get(reason, "refused_no_token")}

    def public(self):
        store = self.store
        checkpoint = store.checkpoint()
        rows = store.versions("records")
        records = {rid: [dict(r, version=i + 1) for i, r in enumerate(history)] for rid, history in rows.items()}
        tokens = {token_public(hid): {"actor": h["actor"], "tool": h["tool"], "args": h["args"],
                  "revision": h["epoch"], "expires": h["expires"], "status": h["status"]} for hid, h in store.current("handles").items()}
        receipts = []
        for hid, receipt in sorted(store.current("receipts").items(), key=lambda x: int(x[0][1:])):
            committed = [{"record": r["id"], "kind": r["payload"]["kind"], **r["payload"]["fields"]}
                         for r in receipt["effects"] if r["relation"] == "records"]
            receipts.append({"token": token_public(hid), "actor": receipt["actor"],
                             "pre_transaction_revision": receipt["pre_transaction_epoch"], "committed": committed})
        log = [{"type": e["kind"], "sql_event": e,
                **({"result": e["payload"]["result"]} if e["kind"] in ("decision", "recorded_decision") else {})} for e in checkpoint["events"]]
        log.append({"type": "signed_sql_checkpoint", "signature": checkpoint["signature"]})
        duties = store.current("duties")
        for duty in duties.values():
            if "offers" in duty:
                duty["offers"] = dict(sorted(duty["offers"].items(), key=lambda item: (item[1].get("sequence", item[1]["due"]), item[0])))
        return {"world": copy(self.definition), "setup": copy(self.setup), "records": records, "tokens": tokens,
                "duties": duties, "reports": store.current("reports"), "receipts": receipts,
                "notices": [r for _, r in sorted(store.current("notices").items(), key=lambda x: (len(x[0]), x[0]))],
                "allocations": store.current("allocations"), "cases": {cid: r["closed"] for cid, r in store.current("cases").items()},
                "grants": store.current("grants"), "orders": store.current("orders"), "log": log,
                "revision": store.epoch, "step": store.step,
                "decisions": [r for _, r in sorted(store.current("decisions").items(), key=lambda x: int(x[0][1:]))],
                "phase_order": copy(self.phase_order),
                "relational_checkpoint": {k: v for k, v in checkpoint.items() if k not in ("events", "signature")}}
