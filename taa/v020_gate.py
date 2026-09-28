"""v0.20 gates over the existing simulated tools; v0.19.5 gates are untouched."""
from taa.duties import DutyLedger
from taa.gate import ExpiringGate
from taa.obligations import ObligationLedger
from taa.records import target_of
from taa.v020_counsel import ask, ledger_contradictions


V020_MODES = ("taa_v020", "judge_v020", "expiring_v020")


def plan_act_target(item):
    """Model plan replies may name a target or return a tool/args object."""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return item.get("target_id") or item.get("act") or target_of(item.get("args", {}))
    return None


class V020Gate:
    def __init__(self, mode, world, warrant, registry, model, specification):
        if mode not in V020_MODES:
            raise ValueError(f"unknown v0.20 mode {mode}")
        self.mode, self.world, self.warrant = mode, world, warrant
        self.model = model
        self.duties = DutyLedger(specification, world)
        self.claims = ObligationLedger(world, policy_enabled=True)
        self.inner = ExpiringGate(world.tools(), warrant, registry, world,
                                  notify=lambda question: ("unanswered", "logged in simulation"))
        self.review_history = []
        self.raw_replies = []
        self.contradictions = []
        self.plan_reply = None
        self.execution_checks = []
        self.step_history = []
        self.specification = specification

    @property
    def log(self):
        return self.inner.log

    @property
    def referrals(self):
        return self.duties.referrals

    def _review(self, kind, act=None, plan=None):
        reply = ask(self.model, kind, self.warrant, self.world, self.duties,
                    self.review_history, act=act, plan=plan)
        self.raw_replies.append({"step": self.world.step, "kind": kind, "reply": reply})
        errors = ledger_contradictions(reply, self.world)
        if errors:
            self.contradictions.append({"step": self.world.step, "kind": kind,
                                        "initial": errors, "corrected": False})
            corrected = ask(self.model, kind, self.warrant, self.world, self.duties,
                            self.review_history, act=act, plan=plan, correction=errors)
            self.raw_replies.append({"step": self.world.step, "kind": kind + " correction",
                                     "reply": corrected})
            remaining = ledger_contradictions(corrected, self.world)
            if remaining:
                self.contradictions[-1]["remaining"] = remaining
                self.duties.refer("review_error", "; ".join(remaining),
                                  target_of(act["args"]) if act else None)
                # A demonstrably false capacity or claim objection is not a veto.
                reply = {"disposition": "permit", "reason": "unsupported factual veto discarded",
                         "grave": False, "raw": corrected}
            else:
                self.contradictions[-1]["corrected"] = True
                reply = corrected
        self.review_history.append({"step": self.world.step, "kind": kind,
                                    "act": act, "disposition": reply["disposition"],
                                    "reason": reply.get("reason", "")})
        return reply

    def submit_plan(self, plan):
        if self.mode != "taa_v020":
            return None
        shown = {"end": plan.end, "tools": plan.tools,
                 "targets": plan.targets_shown(), "max_uses": plan.max_uses}
        reply = self._review("plan", plan=shown)
        if reply["disposition"] != "permit" and not isinstance(reply.get("failed_acts"), list):
            reply["format_error"] = "stopped plan omitted failed_acts"
        if reply["disposition"] != "permit" and not isinstance(reply.get("dependencies"), list):
            reply["format_error"] = "stopped plan omitted dependencies"
        self.plan_reply = reply
        self.inner._record("(plan)", shown,
                           "APPROVED" if reply["disposition"] == "permit" else "STOPPED",
                           reply.get("reason", "") + "; act-scoped review remains available")
        return reply

    def after_advance(self):
        declared = self.specification.get("world_updates", {}).get(str(self.world.step), {})
        for cid, changes in declared.get("claims", {}).items():
            record = next((c for c in self.world.claims if c["claim_id"] == cid), None)
            if record is None:
                raise ValueError(f"declared update names unknown claim {cid}")
            record.update(changes)
            if cid in self.claims.claims and "evidence_status" in changes:
                self.claims.claims[cid].evidence_status = changes["evidence_status"]
        for sid, changes in declared.get("shipments", {}).items():
            record = self.world.record(sid)
            if record is None:
                raise ValueError(f"declared update names unknown shipment {sid}")
            record.update(changes)
        self.claims.reconcile()
        self.duties.advance()
        for duty in self.duties.duties.values():
            if duty["status"] != "open":
                continue
            target = duty["required_service"]["target_id"]
            claim = self.claims.claim_for(target)
            if claim and (claim.authority_status in ("withdrawn", "denied") or
                          (claim.authority_status == "pending" and
                           self.specification.get("pending_duty_referral"))):
                if "duty_restoration" in self.specification.get("referral_policies", {}):
                    self.duties.refer("duty_restoration", "Open duty after permission withdrawal", target)

    def _refuse(self, tool, args, reason, disposition="prohibit"):
        self.inner._record(tool, args, "REFUSED", reason)
        self.execution_checks.append({"step": self.world.step, "tool": tool,
                                      "target": target_of(args), "executed": False,
                                      "disposition": disposition, "reason": reason})
        return {"ok": False, "error": reason}

    def request(self, tool, args):
        self.claims.reconcile()
        self.duties.advance()
        target = target_of(args)
        if self.inner._always_allowed(tool):
            return self.inner.request(tool, args)
        structural = self.inner._refusal(tool, args)
        if structural:
            return self._refuse(tool, args, structural[0])
        amount = args.get("amount", 0) if isinstance(args, dict) else 0
        if target in self.specification.get("rights_conflicts", []):
            panel = self.duties.refer("rights_conflict", "Individual right versus allocation", target)
            if panel["status"] != "answered" or not any(
                    g.get("rights_panel_resolution") == panel["id"] for g in self.duties.grants.values()):
                return self._refuse(tool, args, "rights panel has not authorized this act", "refer")
        if self.mode != "expiring_v020":
            act = {"tool": tool, "args": args}
            reply = self._review("act_scoped_recovery" if self.mode == "taa_v020" and
                                 self.plan_reply and self.plan_reply["disposition"] != "permit"
                                 else "act", act=act)
            disposition = reply["disposition"]
            if disposition == "permit_narrower":
                narrower = reply.get("narrow_act")
                if (not isinstance(narrower, dict) or narrower.get("tool") != tool or
                        target_of(narrower.get("args")) != target or
                        (tool == "issue_credit" and
                         not 0 < narrower["args"].get("amount", 0) <= amount)):
                    return self._refuse(tool, args, "invalid or unstated narrower act", disposition)
                args = narrower["args"]
            elif disposition == "obtain_evidence":
                needed = reply.get("needed_fact")
                if not needed:
                    needed = "reviewer did not name needed fact"
                if "evidence" in self.specification.get("referral_policies", {}):
                    self.duties.refer("evidence", needed, target)
                return self._refuse(tool, args, "obtain evidence: " + needed, disposition)
            elif disposition == "refer":
                kind = "review_error" if reply.get("format_error") else "review"
                if kind in self.specification.get("referral_policies", {}):
                    policy = self.specification["referral_policies"][kind]
                    if (reply.get("recipient") != policy["recipient"] or
                            reply.get("jurisdiction") != policy["jurisdiction"]):
                        return self._refuse(tool, args, "referral lacks declared jurisdiction", disposition)
                    self.duties.refer(kind, reply.get("reason", "review referral"), target)
                return self._refuse(tool, args, "referred; unanswered is not approval", disposition)
            elif disposition == "prohibit":
                if reply.get("grave") and "grave" in self.specification.get("referral_policies", {}):
                    self.duties.refer("grave", reply.get("reason", "grave act refused"), target)
                return self._refuse(tool, args, reply.get("reason", "prohibited"), disposition)
            if self.mode == "taa_v020" and self.plan_reply:
                failed = {name for item in self.plan_reply.get("failed_acts", [])
                          if (name := plan_act_target(item)) is not None}
                dependencies = self.plan_reply.get("dependencies", [])
                if any(isinstance(item, dict) and plan_act_target(item.get("act")) == target and
                       plan_act_target(item.get("depends_on")) in failed
                       for item in dependencies):
                    return self._refuse(tool, args,
                                        "requested act depends on a failed plan act")
        amount = args.get("amount", 0) if isinstance(args, dict) else 0
        claim = (next((c for c in self.claims.claims.values()
                       if c.target_id == target and
                       (c.requires_settlement or c.authority_status in
                        ("withdrawn", "denied", "expired"))), None)
                 if tool == "reroute_shipment" else None)
        required_override = (claim.claim_id if claim and claim.authority_status != "approved"
                             else None)
        permitted, grant_reason = self.duties.grant_check(
            tool, target, amount, purpose=self.warrant.purpose,
            required_override=required_override,
            disallowed_issuer=claim.source_id if required_override else None)
        if not permitted:
            if claim and claim.authority_status != "approved":
                return self._refuse(tool, args, f"{target} has {claim.authority_status} authority")
            return self._refuse(tool, args, grant_reason)
        if tool == "reroute_shipment":
            if claim and claim.authority_status == "approved" and self.claims.authorization_error(target):
                return self._refuse(tool, args, self.claims.authorization_error(target))
            capacity_error = self.claims.capacity_error(target)
            if capacity_error:
                return self._refuse(tool, args, capacity_error)
        result = self.inner.request(tool, args)
        self.execution_checks.append({"step": self.world.step, "tool": tool, "target": target,
                                      "executed": bool(result.get("ok")),
                                      "disposition": "permit", "reason": grant_reason})
        if result.get("ok"):
            self.duties.fulfilled(tool, target)
        self.claims.reconcile()
        return result

    def end_step(self):
        self.claims.reconcile()
        self.duties.advance()
        self.duties.end_step()
        self.step_history.append({"step": self.world.step,
                                  "duties": self.duties.snapshot()["duties"],
                                  "claims": self.claims.snapshot()["claims"]})
