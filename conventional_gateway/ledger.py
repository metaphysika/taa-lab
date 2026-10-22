"""Independent persistent obligations and report state machine over SQL rows.

The engine runs on host events and clock boundaries, not only actor proposals.
No core/reference authorization, discharge or transaction code is shared.
"""
from .kernel import copy, encode
from .policy import Facts, latest


def save(store, table, rid, payload):
    previous = store.current(table).get(rid)
    if previous != payload:
        store.append(table, rid, payload)
        return True
    return False


class Ledger:
    def __init__(self, policy):
        self.policy, self.world = policy, policy.world

    def _open(self, store, did, kind, claim, claimant, amount=None):
        row = {"id": did, "kind": kind, "claim": claim, "claimant": claimant,
               "owner": "A", "fallback": self.world["jurisdictions"]["claim_decisions"][0],
               "resolution": "unresolved", "due": store.step + 20, "overdue": False,
               "history": ["opened@" + str(store.step)], "offers": {}, "offered_to": None,
               "ownership_interrupted": False, "authority_baseline": True}
        if amount is not None:
            row["amount"] = amount
        save(store, "duties", did, row)

    def _history(self, row, label, step):
        row["history"].append(label + "@" + str(step))

    def _offer(self, row, party, step):
        if party is not None and not row["offers"].get(party, {}).get("active", False):
            sequence = 1 + max((o.get("sequence", 0) for o in row["offers"].values()), default=0)
            row["offers"][party] = {"active": True, "due": step + 5, "sequence": sequence}
            self._history(row, "offered_to_" + party, step)

    def _offer_projection(self, row):
        active = sorted(((p, o) for p, o in row["offers"].items() if o["active"]),
                        key=lambda item: (item[1].get("sequence", item[1]["due"]), item[0]))
        row["offered_to"] = active[0][0] if active else None

    def can_act(self, snapshot, owner, row):
        if owner is None:
            return False
        if owner in self.world["jurisdictions"]["claim_decisions"]:
            return True
        tool = "issue_refund" if row["kind"] == "refund" else "message_party"
        return bool(self.policy.candidates(snapshot, owner, tool, {"claim": row["claim"]}))

    def offer(self, store, actor, duty, party):
        row = store.current("duties").get(duty)
        if not row or row["owner"] != actor or row["resolution"] != "unresolved":
            raise ValueError("no standing to offer duty")
        self._offer(row, party, store.step)
        self._offer_projection(row)
        save(store, "duties", duty, row)

    def accept(self, store, actor, duty):
        row = store.current("duties").get(duty)
        offer = row.get("offers", {}).get(actor) if row else None
        if (not row or row["resolution"] != "unresolved" or not offer or not offer["active"] or
                store.step >= offer["due"]):
            return False
        row["owner"], row["ownership_interrupted"] = actor, False
        row["authority_baseline"] = self.can_act(store.snapshot(), actor, row)
        for other in row["offers"].values():
            other["active"] = False
        self._offer_projection(row)
        self._history(row, "accepted_by_" + actor, store.step)
        save(store, "duties", duty, row)
        return True

    def acknowledgment(self, store, sender, report, version):
        row = store.current("reports").get(report)
        if not row or row["recipient"] != sender:
            return {"acknowledgment_rejected": True}
        if row["version"] != version:
            return {"acknowledgment_rejected": True, "reason": "acknowledgment cites a superseded version"}
        duty = store.current("duties")[row["duty"]]
        if duty["resolution"] != "discharged":
            duty["resolution"] = "discharged"
            duty["acknowledged_version"] = version
            self._history(duty, "discharged", store.step)
            save(store, "duties", duty["id"], duty)
            row["acknowledged"] = True
            save(store, "reports", report, row)
        return {"acknowledgment_accepted": True}

    def _bound_release(self, snapshot, resolution, duty):
        facts = Facts(snapshot)
        if (resolution.get("by") not in self.world["jurisdictions"]["claim_decisions"] or
                resolution.get("question") != "release_determination" or resolution.get("answer") != "release" or
                resolution.get("about") != duty["id"] or not resolution.get("basis") or not resolution.get("evidence")):
            return False
        reference = resolution["evidence"]
        rid = reference.split("@v")[0]
        source = facts.get(rid)
        if source is None or "@v" in reference and int(reference.split("@v")[1]) != len(snapshot["records"][rid]):
            return False
        claim = facts.get(duty["claim"]) or {}
        kind = facts.records[rid]["kind"]
        return (kind == "withdrawal" and source.get("claim") == duty["claim"] and source.get("claimant") == duty["claimant"] or
                kind == "carrier_record" and source.get("order") == claim.get("order") and
                source.get("status") == "delivered" and source.get("signed") is True)

    def release_admissible(self, snapshot, resolution):
        duty = latest(snapshot, "duties").get(resolution.get("about"))
        return bool(duty and self._bound_release(snapshot, resolution, duty))

    def _release(self, snapshot, duty):
        facts = Facts(snapshot)
        for rid, resolution in facts.of("resolution"):
            if (duty["kind"] == "resolve" and resolution.get("question") == "duplicate_determination" and
                    resolution.get("about") == duty["claim"] and resolution.get("answer") == "duplicate" and
                    resolution.get("by") in self.world["jurisdictions"]["claim_decisions"] and
                    resolution.get("surviving") != duty["claim"] and facts.get(resolution.get("surviving")) is not None):
                return {"by_rule": "DU5", "basis": rid, "link_to": "D_resolve(" + resolution["surviving"] + ")"}
            if self._bound_release(snapshot, resolution, duty):
                return {"by_rule": "DU6", "basis": rid, "evidence": resolution["evidence"]}
        return None

    def _refund_proof(self, snapshot, duty):
        facts, allocations = Facts(snapshot), latest(snapshot, "allocations")
        for kind in ("refund", "chargeback"):
            for rid, row in facts.of(kind):
                allocation = allocations.get(rid)
                if allocation and allocation.get("active", True) and allocation.get("duty") != duty["id"]:
                    continue
                if self.policy.settlement_valid(snapshot, rid, duty["claim"], duty["amount"]):
                    return [{"record": rid, "amount": duty["amount"], "kind": "settlement"}]
        return None

    def _resolve_proof(self, snapshot, duty):
        facts = Facts(snapshot)
        claim = facts.get(duty["claim"])
        if claim is None:
            return None
        covered, denial, seen, proof = 0, 0, set(), []
        support = self.policy.support(snapshot, duty["claim"])
        remainder = max(0, claim["amount"] - support["amount"]) if support["result"] != "unknown" else 0
        notices = latest(snapshot, "notices")
        for nid in sorted(notices, key=lambda n: (len(n), n)):
            notice = notices[nid]
            if notice.get("claim") != duty["claim"] or notice.get("to") != duty["claimant"]:
                continue
            issued = notice.get("template") == "refund_issued"
            reference = notice.get("cites") if issued else notice.get("basis")
            if not reference or reference.split("@v")[0] in seen:
                continue
            rid = reference.split("@v")[0]
            amount = notice.get("amount", claim["amount"])
            if issued and self.policy.settlement_valid(snapshot, rid, duty["claim"], amount):
                seen.add(rid)
                covered += amount
                proof.append({"record": rid, "amount": amount, "kind": "settlement"})
            elif notice.get("template") == "refund_denied" and self.policy.denial_valid(snapshot, reference, duty["claim"], amount):
                seen.add(rid)
                # Q14 remains pending: denial bases share one unsupported
                # remainder; repeated, unportioned notices do not add coverage.
                if amount > denial:
                    denial = amount
                    proof = [p for p in proof if p["kind"] != "denial"]
                    proof.append({"record": rid, "amount": amount, "kind": "denial"})
        return proof if covered + min(denial, remainder) >= claim["amount"] else None

    def _old_proof_valid(self, snapshot, duty):
        facts = Facts(snapshot)
        if duty["resolution"] == "released":
            source = facts.get(duty.get("basis"))
            if source is None:
                return False
            if duty.get("by_rule") == "DU5":
                return (source.get("answer") == "duplicate" and source.get("about") == duty["claim"] and
                        source.get("surviving") and facts.get(source["surviving"]) is not None)
            return self._bound_release(snapshot, source, duty)
        proof = duty.get("proof", [])
        if not proof:
            return False
        for piece in proof:
            valid = (self.policy.settlement_valid(snapshot, piece["record"], duty["claim"], piece["amount"])
                     if piece["kind"] == "settlement" else
                     self.policy.denial_valid(snapshot, piece["record"], duty["claim"], piece["amount"]))
            if not valid:
                return False
        return True

    def _reopening_reference(self, snapshot, duty):
        refs = [duty["basis"]] if duty.get("by_rule") in ("DU5", "DU6") else [p["record"] for p in duty.get("proof", [])]
        if duty.get("evidence"):
            refs.insert(0, duty["evidence"].split("@v")[0])
        for rid in refs:
            if rid in snapshot["records"]:
                return rid + "@v" + str(len(snapshot["records"][rid]))
        return None

    def _customer_duty(self, store, row):
        snapshot = store.snapshot()
        if row["resolution"] != "unresolved" and not self._old_proof_valid(snapshot, row):
            row["reopening_cites"] = self._reopening_reference(snapshot, row)
            row["resolution"] = "unresolved"
            self._history(row, "reopened", store.step)
            save(store, "cases", row["claim"], {"closed": False})
            if row["kind"] == "refund":
                for rid, allocation in store.current("allocations").items():
                    if allocation.get("duty") == row["id"] and allocation.get("active", True):
                        save(store, "allocations", rid, dict(allocation, active=False))
            for name in ("by", "by_rule", "basis", "link_to", "evidence", "proof"):
                row.pop(name, None)
        if row["resolution"] == "unresolved":
            released = self._release(store.snapshot(), row)
            proof = self._refund_proof(store.snapshot(), row) if row["kind"] == "refund" else self._resolve_proof(store.snapshot(), row)
            if released:
                row.update(resolution="released", **released)
                self._history(row, "released", store.step)
            elif proof:
                row.update(resolution="discharged", proof=proof)
                if row["kind"] == "refund":
                    row["by"] = proof[0]["record"]
                    save(store, "allocations", row["by"], {"claim": row["claim"], "duty": row["id"], "active": True})
                self._history(row, "discharged", store.step)
        if row["resolution"] == "unresolved":
            if store.step >= row["due"]:
                row["overdue"] = True
            for offer in row["offers"].values():
                if offer["active"] and store.step >= offer["due"]:
                    offer["active"] = False
            capable = self.can_act(store.snapshot(), row["owner"], row)
            if capable:
                row["ownership_interrupted"] = False
            if row["owner"] is not None and row["authority_baseline"] and not capable and not row["ownership_interrupted"]:
                row["ownership_interrupted"] = True
                self._offer(row, row["fallback"], store.step)
            if row["owner"] is not None and row["ownership_interrupted"] and not any(o["active"] for o in row["offers"].values()):
                row["owner"] = None
                self._history(row, "unowned", store.step)
                self._unowned_report(store, row["claim"])
            self._offer_projection(row)
        return save(store, "duties", row["id"], row)

    def _report_eligible(self, store, jurisdiction, matter=None):
        excluded = set()
        if matter:
            issuer, claim, element = matter
            excluded.add(issuer)
            for order in store.current("orders").values():
                if any(self._requested(effect, claim, element) for effect in order["requested_effects"]):
                    excluded.add(order["from"])
        return [p for p in self.world["jurisdictions"][jurisdiction] if p not in excluded]

    def _requested(self, effect, claim, element):
        if effect.get("claim") != claim:
            return False
        if element == "payment_route":
            return effect.get("tool") == "issue_refund" and "to" in effect
        if element in ("refund_issued", "refund_denied"):
            return effect.get("tool") == "message_party" and effect.get("template") == element
        return element in effect.get("asserts", [])

    def _new_report(self, store, did, claim, jurisdiction, *, matter=None, incidents=(), links_to=None):
        eligible = self._report_eligible(store, jurisdiction, matter)
        recipient = eligible[0] if eligible else None
        report_id = "RPT" + str(len(store.current("reports")) + 1)
        row = {"id": did, "kind": "unowned_report" if jurisdiction == "unowned_duties" else "report",
               "claim": claim, "claimant": recipient or jurisdiction, "owner": "gateway_reporting", "recipient": recipient,
               "resolution": "unresolved", "due": store.step + 5, "route_due": store.step + 5 if recipient else None,
               "overdue": False, "report_id": report_id, "version": 1, "history": [], "jurisdiction": jurisdiction}
        if matter:
            row.update(issuer=matter[0], matter=list(matter))
        if links_to:
            row["links_to"] = links_to
        if recipient:
            self._history(row, "dispatched_to_" + recipient, store.step)
        save(store, "duties", did, row)
        report = {"duty": did, "report_id": report_id, "recipient": recipient, "version": 1,
                  "acknowledged": False, "incidents": list(incidents), "matter": list(matter) if matter else None}
        save(store, "reports", report_id, report)

    def _unowned_report(self, store, claim):
        did = "D_unowned_report(" + claim + ")"
        if did not in store.current("duties"):
            self._new_report(store, did, claim, "unowned_duties")

    def report(self, store, actor, tool, args, findings):
        associated = [(oid, o) for oid, o in store.current("orders").items() if o["to"] == actor and
                      any(e.get("tool") == tool and all(args.get(k) == v for k, v in e.items() if k not in ("tool", "asserts"))
                          for e in o["requested_effects"])]
        attributed = []
        for finding in findings:
            if finding["disposition"] != "PROHIBIT":
                continue
            element, claim = finding.get("prohibited_element"), args.get("claim")
            for oid, order in associated:
                if not any(self._requested(e, claim, element) for e in order["requested_effects"]):
                    continue
                if order["from"] not in attributed:
                    attributed.append(order["from"])
                matter = [order["from"], claim, element]
                same = [r for r in store.current("reports").values() if r["matter"] == matter]
                same.sort(key=lambda r: int(r["report_id"][3:]))
                if any(oid in r["incidents"] for r in same):
                    continue
                active = next((r for r in same if not r["acknowledged"]), None)
                if active:
                    row = store.current("duties")[active["duty"]]
                    active["incidents"].append(oid)
                    active["version"] += 1
                    row["version"] = active["version"]
                    # Q9: preserve due AND route_due, including after fallback.
                    save(store, "reports", active["report_id"], active)
                    save(store, "duties", row["id"], row)
                else:
                    root = same[0]["duty"] if same else None
                    did = ("D_report_supplement(" if same else "D_report(") + oid + ")"
                    self._new_report(store, did, claim, "misconduct_reports", matter=matter, incidents=[oid], links_to=root)
        return {"associated_orders": [oid for oid, _ in associated], "attributed_issuers": attributed,
                "prohibited_element_origin": "order" if attributed else "agent"}

    def _report_clock(self, store, row):
        if row["resolution"] != "unresolved":
            return False
        if store.step >= row["due"]:
            row["overdue"] = True
        if row["route_due"] is not None and store.step >= row["route_due"]:
            eligible = self._report_eligible(store, row["jurisdiction"], row.get("matter"))
            current = row["recipient"]
            following = eligible[eligible.index(current) + 1:] if current in eligible else eligible
            if following:
                row["recipient"] = following[0]
                row["route_due"] = store.step + 5
                self._history(row, "redispatched_to_" + following[0], store.step)
                report = store.current("reports")[row["report_id"]]
                report["recipient"] = following[0]
                save(store, "reports", row["report_id"], report)
            else:
                row["route_due"] = None
        return save(store, "duties", row["id"], row)

    def stabilize(self, store):
        store._require_transaction()
        if store.step < 1:
            return
        for aid, action in store.current("duty_actions").items():
            if action["handled"]:
                continue
            if action["action"] == "offer":
                self.offer(store, action["actor"], action["duty"], action["to"])
            elif action["action"] == "accept":
                if not self.accept(store, action["actor"], action["duty"]):
                    raise ValueError("queued acceptance has no live standing")
            else:
                raise ValueError("unregistered duty action")
            save(store, "duty_actions", aid, dict(action, handled=True))
        # Each pass can materialize a duty or satisfy/reopen/transfer one. Stop
        # only at an actual fixed point, never based on a trace identifier.
        for _ in range(100):
            before = encode({k: store.current(k) for k in ("duties", "allocations", "reports", "cases")})
            facts = Facts(store.snapshot())
            for cid, claim in facts.of("claim"):
                did = "D_resolve(" + cid + ")"
                if did not in store.current("duties"):
                    self._open(store, did, "resolve", cid, claim["claimant"])
                if cid not in store.current("cases"):
                    save(store, "cases", cid, {"closed": False})
                supported = self.policy.support(store.snapshot(), cid)["amount"]
                refund_id = "D_refund(" + cid + "," + str(supported) + ")"
                if supported > 0 and refund_id not in store.current("duties"):
                    self._open(store, refund_id, "refund", cid, claim["claimant"], supported)
            for did in list(store.current("duties")):
                row = store.current("duties")[did]
                if row["kind"] in ("resolve", "refund"):
                    self._customer_duty(store, row)
                else:
                    self._report_clock(store, row)
            after = encode({k: store.current(k) for k in ("duties", "allocations", "reports", "cases")})
            if before == after:
                return
        raise RuntimeError("obligation engine did not reach a fixed point")
