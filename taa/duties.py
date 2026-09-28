"""v0.20 simulated duties, referrals, and grants.

This ledger records obligations separately from permission to use a tool.  All
authority replies come from a scenario's declared schedule, never from a model.
"""
from copy import deepcopy


FINAL_DUTY_STATES = {"fulfilled", "discharged", "transferred", "unmet_past_deadline"}


def validate_grant(grant):
    required = {"id", "issuer", "jurisdiction", "permitted_acts", "targets",
                "resources", "purpose", "delegation_limit", "expiry_step", "context"}
    if not required.issubset(grant):
        raise ValueError("grant lacks required jurisdiction, purpose, resource, or scope fields")
    if (not isinstance(grant["delegation_limit"], int) or grant["delegation_limit"] < 0 or
            not isinstance(grant["expiry_step"], int)):
        raise ValueError("grant has invalid delegation or expiry limit")
    if not isinstance(grant["jurisdiction"], dict):
        raise ValueError("grant jurisdiction must be explicit")
    return grant


class DutyLedger:
    def __init__(self, specification, world):
        self.world = world
        self.specification = deepcopy(specification)
        self.duties = {d["id"]: dict(d, status=d.get("status", "open"), history=[])
                       for d in specification.get("duties", [])}
        self.grants = {g["id"]: deepcopy(validate_grant(g))
                       for g in specification.get("grants", [])}
        self.referrals = []
        self.events = []
        self._seen_answers = set()

    def _event(self, kind, **fields):
        self.events.append({"step": self.world.step, "kind": kind, **fields})

    def duty_for(self, tool, target):
        return next((d for d in self.duties.values()
                     if d["required_service"] == {"tool": tool, "target_id": target}), None)

    def refer(self, kind, question, target=None):
        existing = next((r for r in self.referrals
                         if r["kind"] == kind and r["target_id"] == target), None)
        if existing:
            return existing
        policy = self.specification.get("referral_policies", {}).get(kind)
        if policy is None:
            raise ValueError(f"no declared referral policy for {kind}")
        if not policy.get("jurisdiction") or not policy.get("recipient"):
            raise ValueError("referral needs a recipient and declared jurisdiction")
        record = {"id": f"R-{len(self.referrals) + 1}", "kind": kind,
                  "target_id": target, "question": question,
                  "recipient": policy["recipient"],
                  "jurisdiction": policy["jurisdiction"],
                  "response_deadline": self.world.step + policy["response_steps"],
                  "interim_policy": policy["interim_policy"],
                  "fallback_recipient": policy.get("fallback_recipient"),
                  "status": "waiting", "accepted_by": None,
                  "opened_step": self.world.step, "resolved_step": None,
                  "history": [{"step": self.world.step, "event": "sent", "recipient": policy["recipient"]}]}
        self.referrals.append(record)
        self._event("referral_sent", referral_id=record["id"], kind_of_referral=kind)
        return record

    def _apply_answer(self, referral, answer):
        if answer.get("recipient") != referral["recipient"]:
            return False
        decision = answer.get("decision")
        if decision not in ("authorize", "deny", "discharge", "transfer"):
            raise ValueError("scripted authority must authorize, deny, discharge, or transfer")
        referral["status"] = "answered"
        referral["accepted_by"] = answer["recipient"]
        referral["resolved_step"] = self.world.step
        referral["history"].append({"step": self.world.step, "event": decision,
                                    "recipient": answer["recipient"]})
        grant = answer.get("grant")
        if decision == "authorize" and grant:
            if grant["issuer"] != answer["recipient"]:
                raise ValueError("scripted grant issuer differs from responding authority")
            self.grants[grant["id"]] = deepcopy(validate_grant(grant))
            self._event("grant_issued", grant_id=grant["id"])
        if decision == "discharge":
            duty = self.duties.get(answer.get("duty_id"))
            if (duty is None or not answer.get("reason") or
                    answer["recipient"] not in duty.get("discharge_jurisdiction", [])):
                raise ValueError("discharge requires a reason and declared jurisdiction")
            self._transition(duty, "discharged", answer["reason"])
        if decision == "transfer":
            duty = self.duties.get(answer.get("duty_id"))
            if (duty is None or answer.get("recipient_accepted") is not True or
                    not answer.get("new_responsible_party")):
                raise ValueError("transfer requires the new recipient's acceptance")
            duty["responsible_party"] = answer["new_responsible_party"]
            self._transition(duty, "transferred", "accepted transfer")
        self._event("referral_answered", referral_id=referral["id"], decision=decision)
        return True

    def _transition(self, duty, status, reason):
        if duty["status"] != "open":
            return
        duty["status"] = status
        duty["history"].append({"step": self.world.step, "status": status, "reason": reason})
        self._event("duty_transition", duty_id=duty["id"], status=status)

    def advance(self):
        """Process declared replies and deadlines even when the agent requests no act."""
        for index, answer in enumerate(self.specification.get("authority_schedule", [])):
            if index in self._seen_answers or answer["step"] > self.world.step:
                continue
            self._seen_answers.add(index)
            for referral in self.referrals:
                if (referral["status"] == "waiting" and
                        answer.get("kind") == referral["kind"] and
                        answer.get("target_id") == referral["target_id"] and
                        self._apply_answer(referral, answer)):
                    break
        for referral in self.referrals:
            if referral["status"] != "waiting" or self.world.step < referral["response_deadline"]:
                continue
            fallback = referral["fallback_recipient"]
            if fallback and not any(h["event"] == "fallback" for h in referral["history"]):
                referral["recipient"] = fallback
                referral["response_deadline"] = self.world.step + 1
                referral["history"].append({"step": self.world.step, "event": "fallback",
                                            "recipient": fallback})
                self._event("referral_fallback", referral_id=referral["id"])
            else:
                referral["status"] = "silent"
                referral["resolved_step"] = self.world.step
                referral["history"].append({"step": self.world.step, "event": "silence"})
                self._event("referral_silent", referral_id=referral["id"])
        for duty in self.duties.values():
            if duty["status"] == "open" and self.world.step > duty["deadline_step"]:
                self._transition(duty, "unmet_past_deadline", "deadline passed without service")

    def end_step(self):
        for duty in self.duties.values():
            if duty["status"] == "open" and self.world.step >= duty["deadline_step"]:
                self._transition(duty, "unmet_past_deadline", "deadline passed without service")

    def fulfilled(self, tool, target):
        duty = self.duty_for(tool, target)
        if duty:
            self._transition(duty, "fulfilled", "service executed")

    def grant_check(self, tool, target, amount=0, purpose=None, required_override=None,
                    disallowed_issuer=None):
        """Only an express, current grant or a declared composition can authorize an act."""
        candidates = [g for g in self.grants.values()
                      if g.get("status", "active") == "active"
                      and self.world.step <= g["expiry_step"]
                      and tool in g["permitted_acts"]
                      and tool in g["jurisdiction"]["permitted_acts"]
                      and (purpose is None or purpose in g.get("permitted_purposes", [g["purpose"]]))
                      and (target in g.get("targets", []) or "*" in g.get("targets", []))
                      and (target in g["jurisdiction"].get("targets", [])
                           or "*" in g["jurisdiction"].get("targets", []))
                      and (required_override is None or
                           g.get("overrides_claim_id") == required_override)
                      and (disallowed_issuer is None or g["issuer"] != disallowed_issuer)
                      and amount <= g.get("max_amount", float("inf"))]
        rules = [r for r in self.specification.get("composition_rules", [])
                 if r["tool"] == tool and
                 (target in r.get("targets", []) or "*" in r.get("targets", []))]
        if rules:
            for rule in rules:
                contexts = {g["context"] for g in candidates
                            if g.get("composition_rule") == rule["id"]}
                if set(rule["required_contexts"]).issubset(contexts):
                    return True, "declared composition rule " + rule["id"]
            return False, "declared composition rule lacks a required valid grant"
        if candidates:
            return True, "grant " + candidates[0]["id"]
        return False, "no current grant covers this act"

    def snapshot(self):
        return {"duties": deepcopy(list(self.duties.values())),
                "grants": deepcopy(list(self.grants.values())),
                "referrals": deepcopy(self.referrals), "events": deepcopy(self.events)}
