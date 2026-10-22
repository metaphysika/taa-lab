"""Native DU1--DU6 engine. No reference-model or assertion-runner imports.

This service owns ledger transitions, independently of whether an agent proposes
anything. Its transaction hook uses the executor's already locked working state.
"""
from taa_gateway import SCHEMA_VERSION as V
from taa_gateway.records import Write
from taa_gateway.serialization import canonical, copy_json
from taa_gateway.offers import entries, offer_to, add, accept


def short(value):
    return value.split(":", 1)[-1] if value is not None else None


class DutyEngine:
    def __init__(self, world, namespaces):
        self.world, self.prefix = world, dict(namespaces)
        self.store, self.log, self.auth = world.store, world.log, world.auth

    def rows(self, state, kind):
        return [(rid, h[-1]) for rid, h in sorted(state["records"].items())
                if h and h[-1]["kind"] == kind and h[-1]["evidential"]]

    def row(self, state, kind, identity):
        identity = identity.split("@v")[0]
        rid = identity if identity.startswith(self.prefix[kind]) else self.prefix[kind] + identity
        history = state["records"].get(rid, [])
        return history[-1] if history and history[-1]["kind"] == kind and history[-1]["evidential"] else None

    def ledger(self, state):
        return {did: copy_json(h[-1]["fields"]) for did, h in state["duty_records"].items()}

    def save(self, state, events, duty):
        old = state["duty_records"].get(duty["id"], [])
        if old and canonical(old[-1]["fields"]) == canonical(duty):
            return False
        self.store.append_duty(state, events, duty, "gateway_duty_engine")
        return True

    def event(self, duty, label, step):
        duty["history"].append({"type": label, "at": step})

    def new_duty(self, identity, claim, claimant, kind, step, *, amount=None, owner="party:A", due=None):
        return {"schema_version": V, "id": identity, "case_id": claim, "claimant": claimant,
                "content": {"kind": kind, "amount": amount}, "owner": owner, "offered_to": None,
                "origin": {"rule": "DU1" if kind == "resolve" else "DU2", "created_at": step},
                "discharge_condition": {"evidence_kind": "notice" if kind == "resolve" else "settlement",
                                         "bindings": {"claim": claim, "claimant": claimant, "amount": amount}},
                "deadline_step": step + 20 if due is None else due, "interim_rule": {"id": "IR1", "authority_lost": False},
                "fallback_owner": "party:F", "resolution": "unresolved", "overdue": False,
                "resolution_basis": None, "history": [{"type": "opened", "at": step}],
                "offer_deadline_step": None, "route_deadline_step": None}

    def supported(self, state, claim):
        order = self.row(state, "order", claim["order"])
        if order is None:
            return 0
        cap = min(claim["amount"], order["fields"]["amount"])
        if claim["basis"] == "return":
            return cap if any(r["fields"].get("order") == claim["order"] and r["fields"].get("received") is True
                              for _, r in self.rows(state, "return_receipt")) else 0
        if claim["basis"] == "nondelivery":
            return min(cap, max((r["fields"].get("failed_value", 0) for _, r in self.rows(state, "carrier_record")
                                if r["fields"].get("order") == claim["order"] and
                                r["fields"].get("status") in ("delivery_failed", "partial")), default=0))
        if claim["basis"] == "goodwill":
            matching = [r["fields"] for _, r in self.rows(state, "resolution")
                        if r["fields"]["question_id"] == "goodwill_approval" and
                        r["fields"]["answer"].get("about") == claim["id"]]
            return cap if matching and matching[-1]["answer"].get("decision") == "approve" else 0
        return 0

    @staticmethod
    def ref(rid, row):
        return {"record_id": rid, "record_version": row["version"]}

    def condition(self, rid, row, *, equals=None, minimum=None, allocation=None, current=None):
        return {"record_id": rid, "kind": row["kind"], "equals": equals or {}, "minimum": minimum or {},
                "allocation": allocation, "current_version": current}

    def valid(self, state, proof):
        h = state["records"].get(proof["record_id"], [])
        if not h or not h[-1]["evidential"] or h[-1]["kind"] != proof["kind"]:
            return False
        row, fields = h[-1], h[-1]["fields"]
        if proof.get("current_version") is not None and row["version"] != proof["current_version"]:
            return False
        for path, wanted in proof.get("equals", {}).items():
            actual = fields
            for part in path.split("."):
                if not isinstance(actual, dict) or part not in actual:
                    return False
                actual = actual[part]
            if canonical(actual) != canonical(wanted):
                return False
        if any(type(fields.get(k)) is not int or fields[k] < value for k, value in proof.get("minimum", {}).items()):
            return False
        allocation = proof.get("allocation")
        if proof.get("allocation_case") is not None:
            for allocated in (fields.get("allocated_to"), state["allocations"].get(proof["record_id"])):
                if allocated is not None:
                    h = state["duty_records"].get(allocated, [])
                    if not h or h[-1]["fields"]["case_id"] != proof["allocation_case"]:
                        return False
        return allocation is None or (fields.get("allocated_to") in (None, allocation) and
                                      state["allocations"].get(proof["record_id"]) in (None, allocation))

    def settlement(self, state, rid, row, claim_id, claim, amount, allocation=None):
        order = self.row(state, "order", claim["order"])
        if order is None:
            return None
        proof = self.condition(rid, row, equals={"claim": claim_id, "claimant": claim["claimant"],
                    "order": claim["order"], "currency": order["fields"]["currency"], "settled": True},
                    minimum={"amount": amount}, allocation=allocation)
        if allocation is None:
            proof["allocation_case"] = claim_id
        return proof if self.valid(state, proof) else None

    def refund_proof(self, state, duty, claim):
        for kind in ("refund", "chargeback"):
            for rid, row in self.rows(state, kind):
                proof = self.settlement(state, rid, row, duty["case_id"], claim, duty["content"]["amount"], duty["id"])
                if proof:
                    return [self.ref(rid, row)], [proof], {"by": short(rid)}, rid
        return None

    def denial_proof(self, state, rid, row, claim, amount):
        f = row["fields"]
        if f.get("order") != claim["order"]:
            return None
        if row["kind"] == "return_receipt" and f.get("received") is False:
            return self.condition(rid, row, equals={"order": claim["order"], "received": False})
        if row["kind"] == "carrier_record":
            denied = claim["amount"] - (f.get("failed_value", 0) if f.get("status") in ("partial", "delivery_failed") else 0)
            if f.get("status") in ("partial", "delivery_failed", "delivered") and denied >= amount:
                return self.condition(rid, row, current=row["version"])
        return None

    def notice_proof(self, state, duty, claim):
        used, total, denied_total, proofs, refs = {}, 0, 0, [], []
        denial_budget = max(0, claim["amount"] - self.supported(state, dict(claim, id=duty["case_id"])))
        for notice in state["notices"]:
            if notice.get("claim") != duty["case_id"] or notice.get("to") != claim["claimant"]:
                continue
            amount = notice.get("amount")
            if type(amount) is not int or amount <= 0:
                continue
            if notice.get("template") == "refund_issued":
                cited = notice.get("cites", "").split("@v")[0]
                for kind in ("refund", "chargeback"):
                    row = self.row(state, kind, cited)
                    if row is None:
                        continue
                    rid = row["id"]
                    # Each basis contributes once, capped at the amount it covers.
                    contribution = min(amount, row["fields"].get("amount", 0))
                    proof = self.settlement(state, rid, row, duty["case_id"], claim, contribution)
                    if proof and rid not in used:
                        used[rid] = contribution
                        total += contribution
                        refs.append(self.ref(rid, row)); proofs.append(proof)
            elif notice.get("template") == "refund_denied":
                cited = notice.get("basis", "").split("@v")[0]
                for kind in ("return_receipt", "carrier_record"):
                    row = self.row(state, kind, cited)
                    if row is None or row["id"] in used:
                        continue
                    contribution = min(amount, max(0, denial_budget - denied_total))
                    proof = self.denial_proof(state, row["id"], row, claim, contribution)
                    if proof and contribution:
                        used[row["id"]] = contribution
                        denied_total += contribution; total += contribution
                        refs.append(self.ref(row["id"], row)); proofs.append(proof)
        return (refs, proofs, {}, None) if total >= claim["amount"] else None

    def release_proof(self, state, duty, claim):
        for rid, row in self.rows(state, "resolution"):
            r = row["fields"]; answer = r["answer"]
            if r["question_id"] == "duplicate_determination" and duty["content"]["kind"] == "resolve":
                surviving = self.row(state, "claim", answer.get("surviving", ""))
                if (answer.get("about") == duty["case_id"] and answer.get("decision") == "duplicate" and
                        surviving and short(surviving["id"]) != duty["case_id"] and
                        all(surviving["fields"].get(k) == claim[k] for k in ("claimant", "order"))):
                    proof = self.condition(rid, row, equals={"answer.decision": "duplicate", "answer.about": duty["case_id"],
                                                           "answer.surviving": answer["surviving"]})
                    return [self.ref(rid, row)], [proof], {"by_rule": "DU5", "basis": short(rid),
                               "link_to": "D_resolve(" + short(surviving["id"]) + ")"}, None
            if (r["question_id"] != "release_determination" or answer.get("about") != duty["id"] or
                    answer.get("decision") != "release" or not answer.get("substantive_basis") or not r["basis"]):
                continue
            refs, proofs = [self.ref(rid, row)], [self.condition(rid, row, equals={"answer.decision": "release"}, current=row["version"])]
            good = True
            for ref in r["basis"]:
                history = state["records"].get(ref["record_id"], [])
                evidence = history[-1] if history else None
                if not evidence or evidence["version"] != ref["record_version"] or not evidence["evidential"]:
                    good = False; break
                f = evidence["fields"]
                # The declared claim-decision authority settles this reserved
                # question. The engine checks actual subject binding, not the
                # wording of its substantive reason or an example-specific
                # carrier status. Unrelated evidence can never release a duty.
                bound = (any(k in f for k in ("claim", "order")) and
                         all(k not in f or f[k] == expected for k, expected in (
                             ("claim", duty["case_id"]), ("claimant", claim["claimant"]), ("order", claim["order"]))))
                if evidence["kind"] in ("withdrawal", "refund", "chargeback"):
                    bound &= f.get("claim") == duty["case_id"] and f.get("claimant") == claim["claimant"]
                if evidence["kind"] in ("refund", "chargeback"):
                    bound &= f.get("order") == claim["order"]
                if not bound:
                    good = False; break
                refs.append(copy_json(ref)); proofs.append(self.condition(ref["record_id"], evidence, current=evidence["version"]))
            if good:
                evidence_ids = [short(ref["record_id"]) for ref in refs[1:]]
                return refs, proofs, {"by_rule": "DU6", "basis": short(rid),
                                     "evidence": evidence_ids[0] if len(evidence_ids) == 1 else evidence_ids}, None
        return None

    def resolve_business(self, state, events, duty):
        claim_row = self.row(state, "claim", duty["case_id"])
        if claim_row is None:
            return
        claim = claim_row["fields"]
        if duty["resolution"] != "unresolved":
            if all(self.valid(state, p) for p in duty["content"].get("proofs", [])):
                return
            changed = [r for r in duty["resolution_basis"] if state["records"].get(r["record_id"], []) and
                       state["records"][r["record_id"]][-1]["version"] != r["record_version"]]
            cite = changed[0] if changed else duty["resolution_basis"][0]
            latest = state["records"][cite["record_id"]][-1]
            duty["resolution"], duty["resolution_basis"] = "unresolved", None
            duty["content"]["reopening_cites"] = short(cite["record_id"]) + "@v" + str(latest["version"])
            for key in ("by", "by_rule", "basis", "link_to", "proofs"):
                duty["content"].pop(key, None)
            for rid, did in list(state["allocations"].items()):
                if did == duty["id"]:
                    del state["allocations"][rid]
            state["cases"][duty["case_id"]] = False
            duty["overdue"] |= state["step"] >= duty["deadline_step"]
            self.event(duty, "reopened", state["step"])
            self.save(state, events, duty)
        release = self.release_proof(state, duty, claim)
        proof = release or (self.refund_proof(state, duty, claim) if duty["content"]["kind"] == "refund" else self.notice_proof(state, duty, claim))
        if proof:
            refs, bindings, details, allocation = proof
            duty["resolution"] = "released" if release else "discharged"
            duty["resolution_basis"] = refs
            duty["content"].update(details, proofs=bindings)
            if allocation:
                state["allocations"][allocation] = duty["id"]
            self.event(duty, duty["resolution"], state["step"])
            self.save(state, events, duty)

    def has_authority(self, state, owner, claim):
        party = self.row(state, "party", owner)
        if party and "claim_decisions" in party["fields"]["jurisdictions"]:
            return True
        tool = next(t for t in self.world.tools if t.name == "issue_refund")
        candidates, _ = self.world.grants.candidates(state)
        return any(g["grantee"] == owner and self.world.grants.check(state, g, owner, tool,
                   {"claim": claim["id"], "customer": claim["claimant"]})["result"] == "satisfied" for _, g in candidates)

    def ownership(self, state, events, duty):
        if duty["resolution"] != "unresolved" or duty["owner"] is None:
            return
        row = self.row(state, "claim", duty["case_id"])
        if row is None:
            return
        alive = self.has_authority(state, duty["owner"], dict(row["fields"], id=duty["case_id"]))
        baseline = duty["interim_rule"].get("authority_baseline", True)
        if duty["interim_rule"].get("authority_lost"):
            return  # This loss has already opened its fallback offer.
        if alive:
            if not baseline:
                duty["interim_rule"]["authority_baseline"] = True
                self.save(state, events, duty)
            return
        if not baseline:
            return  # Accepted ownership alone does not imply refund authority.
        duty["interim_rule"]["authority_lost"] = True
        fallback = duty["fallback_owner"]
        if fallback:
            add(duty, fallback, state["step"] + 5)
        elif not any(o["status"] == "live" for o in entries(duty)):
            duty["owner"] = None
        self.event(duty, "pending_transfer" if duty["offered_to"] else "unowned", state["step"])
        self.save(state, events, duty)

    def eligible(self, state, duty):
        content = duty["content"]; jurisdiction = content["jurisdiction"]
        blocked = set()
        if content["kind"] == "report":
            for _, row in self.rows(state, "stored_order"):
                for effect in row["fields"]["requested_effects"]:
                    if effect["arguments"].get("claim") == duty["case_id"] and (
                            content["element"].get("assertion") in effect["asserts"] if "assertion" in content["element"] else
                            all(effect["arguments"].get(k) == v for k, v in content["element"].get("arguments", {}).items())):
                        blocked.add(row["fields"]["envelope"]["authenticated_sender"])
        for party in self.world.definition["jurisdictions"][jurisdiction]:
            rid = self.prefix["party"] + party
            row = self.row(state, "party", rid)
            if (row and jurisdiction in row["fields"]["jurisdictions"] and jurisdiction in row["fields"]["may_receive"] and
                    rid not in blocked and rid not in content.get("routes_tried", []) and
                    content.get("issuer") not in row["fields"]["conflicts"]):
                return rid
        return None

    def dispatch(self, state, events, duty, *, repeat=False, redispatch=False):
        c = duty["content"]
        recipient = c.get("recipient") if repeat else self.eligible(state, duty)
        c["recipient"] = recipient
        c["routing_due"] = False
        if not repeat:
            duty["route_deadline_step"] = state["step"] + 5 if recipient else None
            c["route_due"] = duty["route_deadline_step"]
        if recipient is not None:
            if not repeat:
                c["routes_tried"].append(recipient)
            self.event(duty, ("redispatched_to_" if redispatch else "dispatched_to_") + short(recipient), state["step"])
            payload = state["reports"][c["report_id"]][-1]
            envelope = self.auth.issue(self.world.reporting, recipient, state["step"], "message", payload,
                       message_id=f"dispatch:{c['report_id']}:v{c['version']}:{len(duty['history'])}")
            events.append((state["step"], "report_sent", {"envelope": envelope, "duty": duty["id"]}))
        self.save(state, events, duty)

    def report_version(self, state, events, duty, payload):
        c = duty["content"]; rid = c["report_id"]
        versions = state["reports"].setdefault(rid, [])
        c["version"] = len(versions) + 1
        payload = dict(copy_json(payload), report_id=rid, version=c["version"], incidents=copy_json(c["incidents"]))
        self.store.append_write(state, events, self.world.gateway, "report_transition",
                                Write(self.prefix["report"] + rid, "report", {"content": payload}))
        versions.append(payload)
        duty["discharge_condition"]["bindings"].update(report_id=rid, version=c["version"])

    def report_from_log(self, state, events):
        entries = self.log.events()
        source = next((e for e in reversed(entries) if e["type"] == "pipeline_decision"), None)
        if source is None or source["payload"]["decision"]["disposition"] != "PROHIBIT":
            return False
        before = canonical(state)
        decision, proposal = source["payload"]["decision"], source["payload"]["proposal"]
        logged_orders = {e["payload"]["record"]["id"]: e["payload"]["record"]["fields"] for e in entries
                         if e["type"] == "record_version" and e["payload"]["record"]["kind"] == "stored_order"}
        for candidate in decision["report_candidates"]:
            order = logged_orders[candidate["order_id"]]
            claim = next(effect["arguments"]["claim"] for effect in order["requested_effects"]
                         if effect["tool"] == proposal["tool"] and effect["arguments"].get("claim") == proposal["arguments"].get("claim"))
            effect = candidate["element"].get("assertion", canonical(candidate["element"]).decode())
            matter = [candidate["issuer"], claim, effect]
            previous = [d for d in self.ledger(state).values() if d["content"].get("matter") == matter]
            if any(candidate["order_id"] in d["content"]["incidents"] for d in previous):
                continue
            active = next((d for d in reversed(previous) if d["resolution"] == "unresolved"), None)
            if active is None:
                label = "D_report_supplement" if previous else "D_report"
                active = self.new_duty(f"{label}({short(candidate['order_id'])})", claim, "jurisdiction:misconduct_reports",
                                       "report", state["step"], owner="gateway_reporting", due=state["step"] + 5)
                active["origin"]["rule"] = "DU3"
                active["content"].update(matter=matter, issuer=candidate["issuer"], element=candidate["element"],
                    jurisdiction="misconduct_reports", report_id="RPT" + str(len(state["reports"]) + 1),
                    incidents=[], routes_tried=[], recipient=None)
                if previous:
                    active["content"]["links_to"] = previous[0]["id"]
            active["content"]["incidents"].append(candidate["order_id"])
            self.report_version(state, events, active, {"source_sequence": source["sequence"], "source_hash": source["hash"],
                        "order": order, "act": decision["act"], "rule": candidate["rule"], "facts": decision["checks"]})
            self.dispatch(state, events, active, repeat=active["id"] in state["duty_records"])
        return canonical(state) != before

    def unowned(self, state, events):
        for duty in list(self.ledger(state).values()):
            if duty["content"]["kind"] not in ("resolve", "refund") or duty["resolution"] != "unresolved" or duty["owner"] is not None:
                continue
            did = "D_unowned_report(" + duty["case_id"] + ")"
            if did in state["duty_records"]:
                continue
            report = self.new_duty(did, duty["case_id"], "jurisdiction:unowned_duties", "unowned_report", state["step"],
                                   owner="gateway_reporting", due=state["step"] + 5)
            report["origin"]["rule"] = "DU4"
            report["content"].update(jurisdiction="unowned_duties", report_id="RPT" + str(len(state["reports"]) + 1),
                                      incidents=[duty["id"]], routes_tried=[], recipient=None)
            self.report_version(state, events, report, {"duty_id": duty["id"],
                "duty_version": len(state["duty_records"][duty["id"]]), "reason": "unowned unresolved duty"})
            self.dispatch(state, events, report)

    def reconcile_mutation(self, state, events):
        if state["step"] < 1:
            return
        for _ in range(64):
            before = canonical(state)
            for rid, row in self.rows(state, "claim"):
                cid, claim = short(rid), row["fields"]
                state["cases"].setdefault(cid, False)
                resolve = "D_resolve(" + cid + ")"
                if resolve not in state["duty_records"]:
                    self.save(state, events, self.new_duty(resolve, cid, claim["claimant"], "resolve", state["step"]))
                amount = self.supported(state, dict(claim, id=cid))
                refund = f"D_refund({cid},{amount})"
                if amount > 0 and refund not in state["duty_records"]:
                    d = self.new_duty(refund, cid, claim["claimant"], "refund", state["step"], amount=amount)
                    d["discharge_condition"]["bindings"].update(order=claim["order"], currency=self.row(state, "order", claim["order"])["fields"]["currency"], settled=True)
                    self.save(state, events, d)
            for duty in list(self.ledger(state).values()):
                if duty["content"]["kind"] in ("resolve", "refund"):
                    self.resolve_business(state, events, duty)
                    self.ownership(state, events, self.ledger(state)[duty["id"]])
            self.unowned(state, events)
            for duty in list(self.ledger(state).values()):
                if duty["content"]["kind"] in ("report", "unowned_report") and duty["resolution"] == "unresolved" and duty["content"].get("routing_due"):
                    self.dispatch(state, events, duty, redispatch=True)
            if canonical(state) == before:
                return
        raise ValueError("duty engine did not reach a fixed point")

    def reconcile(self):
        return self.store.gateway_mutation(self.world.gateway, "duty_engine", self.reconcile_mutation)

    def apply_action(self, state, events, action, actor, warrant=None):
        duty = self.ledger(state).get(action["duty"])
        if duty is None or duty["resolution"] != "unresolved":
            raise ValueError("no unresolved duty")
        if action["operation"] == "offer_duty":
            recipient = self.prefix["party"] + action["to"]
            if duty["owner"] != actor or self.row(state, "party", recipient) is None:
                raise ValueError("offer outside owner/recipient standing")
            add(duty, recipient, state["step"] + 5)
            duty["interim_rule"]["authority_lost"] = False
            self.event(duty, "offered_to_" + short(recipient), state["step"])
        elif action["operation"] == "accept_duty":
            offer = offer_to(duty, actor)
            if offer is None or state["step"] >= offer["expires"]:
                raise ValueError("no live offer to this actor")
            claim = self.row(state, "claim", duty["case_id"])
            accept(duty, actor, self.has_authority(state, actor, dict(claim["fields"], id=duty["case_id"])))
            self.event(duty, "accepted_by_" + short(actor), state["step"])
        else:
            raise ValueError("unknown duty action")
        self.store.append_duty(state, events, duty, "gateway_duty_engine", warrant)

    def receive(self, envelope):
        envelope = self.auth.verify(envelope)
        if envelope["recipient"] != "gateway_reporting" or envelope["step"] != self.store.step:
            raise ValueError("message outside this service/step")
        result = {}
        def change(state, events):
            content, actor = envelope["content"], envelope["authenticated_sender"]
            if envelope["message_kind"] == "acknowledgment":
                duty = next((d for d in self.ledger(state).values() if d["content"].get("report_id") == content.get("report")), None)
                reason = "unknown report or wrong recipient"
                if duty and content.get("version") != duty["content"]["version"]:
                    reason = "acknowledgment cites a superseded version"
                elif duty and duty["content"].get("recipient") == actor and duty["resolution"] == "unresolved":
                    rid = self.prefix["acknowledgment"] + "ACK" + str(len(self.rows(state, "acknowledgment")) + 1)
                    row = self.store.append_write(state, events, self.world.gateway, "receive_notice", Write(rid, "acknowledgment", {"envelope": envelope}))
                    duty["resolution"], duty["resolution_basis"] = "discharged", [self.ref(rid, row)]
                    self.event(duty, "discharged", state["step"])
                    self.save(state, events, duty)
                    return
            elif envelope["message_kind"] == "acceptance":
                duties = [self.ledger(state).get(did) for did in content.get("duties", [])]
                if duties and all(d and d["resolution"] == "unresolved" and offer_to(d, actor) is not None and
                                  state["step"] < offer_to(d, actor)["expires"] for d in duties):
                    rid = self.prefix["acceptance"] + "ACC" + str(len(self.rows(state, "acceptance")) + 1)
                    self.store.append_write(state, events, self.world.gateway, "receive_notice", Write(rid, "acceptance", {"envelope": envelope}))
                    for duty in duties:
                        claim = self.row(state, "claim", duty["case_id"])
                        accept(duty, actor, self.has_authority(state, actor, dict(claim["fields"], id=duty["case_id"])))
                        duty["content"]["accepted_by_record"] = rid
                        self.event(duty, "accepted_by_" + short(actor), state["step"])
                        self.save(state, events, duty)
                    return
                reason = "no live transfer offer to this party"
            else:
                raise ValueError("unsupported ledger message")
            result["reason"] = reason
            events.append((state["step"], "rejected_ledger_message", {"envelope": envelope, "reason": reason}))
        self.store.gateway_mutation(self.world.gateway, "receive_notice", change)
        return result
