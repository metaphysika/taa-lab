"""The execution gate: the only path from an agent to the tools.

Five gates share one interface so the same agent can run under any of them:
- BaselineGate: ordinary scoped permissions. A tool call passes if the tool is on the
  allowed list and budget remains. Nothing expires; there is no plan.
- ExpiringGate: scoped permissions that also expire when the warrant's condition stops
  holding. This is the strongest simple comparator: no plan, no review of purpose.
- StepJudgeGate: expiring permissions plus a purpose judge (the same counsel model and purpose
  instructions TAA's reviewer gets) on every act. No plan, no tokens. The comparator for whether
  TAA's plan layer adds anything over judging each act as it comes.
- TAAGate: the step check from the paper (Section 4.3). A call passes only if it matches
  the approved plan, the warrant is live now, budget remains, and the registry allows it.
  A passing call receives a one-time token bound to that exact act. A departure from the
  approved plan goes back to review as an amended plan (Section 4.2) instead of an
  automatic refusal.
  Plan review can approve only part of a plan, or approve it while referring a question about
  the agent's stated end to the human handler; after a stop the agent gets one revised plan.
- PlanLockedGate: the same step check as TAAGate, but a departure is refused outright,
  with no re-review. It shares TAAGate's plan review (partial approval, approve-and-refer,
  one revised plan). This is the comparator for whether re-reviewing departures (Iudicium,
  Sections 3.3-4.2) adds anything over locking the plan the moment it is approved.

All gates hold the tool functions privately; the agent only ever calls gate.request().
"""
import json
import secrets

from taa.records import target_of


class _GateBase:
    def __init__(self, tools, warrant, registry, world, notify=None):
        self._tools = tools            # private: the agent never sees these
        self.warrant = warrant
        self.registry = registry
        self._world = world
        self.log = []
        self.referrals = []            # questions and notices sent to the human handler
        self._notify = notify          # a function(question) -> (outcome, note), for notices
        self._refused = {}             # refusal memory: act + the facts it rested on -> when

    def _execute(self, tool, args):
        """Run an allowed act. Only an act that changed something spends authority: a call
        with no effect (e.g. "already on that route") counts against no warrant or plan limit."""
        try:
            result = self._tools[tool](**(args or {}))
        except TypeError as e:         # a model asked with the wrong argument names
            result = {"ok": False, "error": f"bad arguments for {tool}: {e}"}
        spent = self.registry.effect_class(tool) != "read_only" and bool(result.get("ok"))
        if spent:
            self.warrant.used[tool] = self.warrant.used.get(tool, 0) + 1
        return result, spent

    def _record(self, tool, args, decision, reason, spent=False):
        entry = {"step": self._world.step, "tool": tool, "args": args,
                 "decision": decision, "reason": reason, "spent": spent}
        self.log.append(entry)
        return entry

    def _always_allowed(self, tool):
        return tool in self._tools and self.registry.always_allowed(tool)

    # ---- refusal memory (TAA and the per-step judge alike) ----------------------------------
    # A reviewer who has already said no to an act does not re-decide it from scratch each time
    # it is asked again. While the facts the refusal rested on are unchanged (the target's record
    # and the world's status), the act is refused from memory; the first repeat sends the issuer
    # a notice. When those facts change (a road closes), the act is reviewed again.

    def _memory_key(self, tool, args):
        return (tool, json.dumps(args, sort_keys=True, default=str),
                self._world.fingerprint(target_of(args)))

    def _remember(self, tool, args):
        self._refused[self._memory_key(tool, args)] = {"step": self._world.step, "repeats": 0}

    def _recall(self, tool, args):
        """If this act was refused before on the same facts, refuse it again without a review."""
        hit = self._refused.get(self._memory_key(tool, args))
        if hit is None:
            return None
        hit["repeats"] += 1
        note = (f"refused from memory: the same act was refused at step {hit['step']} and nothing it "
                "rested on has changed, so it was not reviewed again")
        if hit["repeats"] == 1 and self._notify is not None:
            question = f"the agent asked again for an act refused at step {hit['step']}: {tool} {json.dumps(args)}"
            outcome, notice = self._notify(question)
            self.referrals.append({"kind": "repeat", "question": question, "outcome": outcome,
                                   "step": self._world.step})
            note += f"; {notice}"
        entry = self._record(tool, args, "REFUSED", note)
        entry["remembered"] = True
        return {"ok": False, "error": note}

    def _allow(self, tool, args, reason):
        result, spent = self._execute(tool, args)
        if not spent and self.registry.effect_class(tool) != "read_only":
            reason += f"; no effect ({result.get('error', 'nothing changed')}), so no authority spent"
        self._record(tool, args, "ALLOWED", reason, spent)
        return result


class BaselineGate(_GateBase):
    name = "baseline (scoped permissions)"

    def _refusal(self, tool, args):
        """(log reason, error for the agent) if the act is refused, else None."""
        if tool not in self._tools or tool not in self.warrant.allowed_tools:
            return "tool not permitted", "not permitted"
        left = self.warrant.remaining(tool)
        if left is not None and left <= 0:
            return "budget exhausted", "budget exhausted"
        return None

    def request(self, tool, args):
        if self._always_allowed(tool):
            return self._allow(tool, args, "always allowed: needs no authority")
        refused = self._refusal(tool, args)
        if refused:
            self._record(tool, args, "REFUSED", refused[0])
            return {"ok": False, "error": refused[1]}
        return self._allow(tool, args, "tool is permitted")


class ExpiringGate(BaselineGate):
    name = "expiring permissions (scope + budget + live condition)"

    def _refusal(self, tool, args):
        live, why = self.warrant.is_live(self._world)
        if not live:
            return f"permission expired: {why}", f"permission expired: {why}"
        return super()._refusal(tool, args)


class StepJudgeGate(ExpiringGate):
    """Expiring permissions plus a purpose judge on every act: no plan and no tokens. Each act
    that passes scope, budget, and the live condition goes to the judge, which sees the warrant,
    the current state, and the requested act, and approves or refuses it. This is the "strong
    purpose-aware baseline" the paper names (Section 7): if it matches TAA, the plan layer is
    not what does the work."""
    name = "per-step judge (expiring permissions + purpose judge on every act, no plan)"

    def __init__(self, tools, warrant, registry, world, judge, notify=None):
        super().__init__(tools, warrant, registry, world, notify)
        self._judge = judge            # a function(tool, args) -> (approved, note, referrals)

    def request(self, tool, args):
        if self._always_allowed(tool):
            return self._allow(tool, args, "always allowed: needs no authority")
        refused = self._refusal(tool, args)
        if refused:
            self._record(tool, args, "REFUSED", refused[0])
            return {"ok": False, "error": refused[1]}
        remembered = self._recall(tool, args)
        if remembered:
            return remembered
        approved, note, referrals = self._judge(tool, args)
        for r in referrals:
            self.referrals.append(dict(r, step=self._world.step))
        if not approved:
            # Remember a refusal decided on the merits, not one nobody answered.
            if not any(r["outcome"] == "unanswered" and r["kind"] == "act" for r in referrals):
                self._remember(tool, args)
            self._record(tool, args, "REFUSED", note)
            return {"ok": False, "error": note}
        return self._allow(tool, args, note)


class TAAGate(_GateBase):
    name = "TAA (plan review + live warrant + step check)"

    def __init__(self, tools, warrant, registry, world, reviewer, notify=None):
        super().__init__(tools, warrant, registry, world, notify)
        self.plan = None
        self._reviewer = reviewer      # a function(plan) -> reviewed plan

    def _review(self, plan):
        reviewed = self._reviewer(plan)
        for r in reviewed.referrals:
            self.referrals.append(dict(r, step=self._world.step))
        return reviewed

    def submit_plan(self, plan):
        """Plan review. After a stop the agent may submit one revised plan (plan.revision);
        if that is stopped too, the run goes on with no approved plan."""
        requested = {"end": plan.end, "tools": list(plan.tools), "max_uses": dict(plan.max_uses),
                     "targets": list(plan.targets)}
        self.plan = self._review(plan)
        self._record("(revised plan)" if plan.revision else "(plan)", requested,
                     plan.status.upper(), "; ".join(plan.review_notes))
        return self.plan

    def _step_check(self, tool, args):
        """The fast, rule-based check. Returns (ok, reason, departure)."""
        if self.plan is None or self.plan.status != "approved":
            return False, "no approved plan", False
        live, why = self.warrant.is_live(self._world)
        if not live:
            return False, f"warrant not live: {why}", False
        if not self.registry.is_registered(tool):
            return False, f"'{tool}' is not in the tool registry (treated as most consequential)", True
        if tool not in self.plan.tools:
            return False, f"'{tool}' is outside the approved plan", True
        target = target_of(args)
        if self.plan.targets and target and target not in self.plan.targets:
            return False, f"target {target} is outside the approved plan", True
        left = self.warrant.remaining(tool)
        if left is not None and left <= 0:
            return False, "warrant budget exhausted", False
        used = sum(1 for e in self.log if e["tool"] == tool and e["decision"] == "ALLOWED" and e["spent"])
        cap = self.plan.max_uses.get(tool)
        if cap is not None and used >= cap:
            return False, f"approved plan allows {cap} uses of '{tool}'", True
        return True, "matches approved plan; warrant live; within budget", False

    def _rereview(self, tool, args, why):
        """A material departure goes back to plan review as an amended plan (paper Section 4.2)."""
        import copy
        amended = copy.deepcopy(self.plan)
        amended.status, amended.review_notes, amended.amended = "proposed", [], True
        amended.revision = False
        if tool not in amended.tools:
            amended.tools.append(tool)
        target = target_of(args)
        if target and amended.targets and target not in amended.targets:
            amended.targets.append(target)
        amended.max_uses[tool] = amended.max_uses.get(tool, 0) + 1
        reviewed = self._review(amended)
        # A partial approval that leaves out the very act that departed does not approve it.
        covers = tool in reviewed.tools and not (target and reviewed.targets and target not in reviewed.targets)
        if reviewed.status == "approved" and covers:
            self.plan = reviewed
            return True, f"departure ({why}) re-reviewed and approved: {'; '.join(reviewed.review_notes)}"
        if reviewed.status == "approved":
            self._remember(tool, args)
            return False, (f"departure ({why}) re-reviewed: plan approved without this act, which stays "
                           f"refused: {'; '.join(reviewed.review_notes)}")
        if reviewed.status == "stopped":   # decided; an unanswered referral ("referred") is not remembered
            self._remember(tool, args)
        return False, f"departure ({why}) re-reviewed: {'; '.join(reviewed.review_notes)}"

    def request(self, tool, args):
        if self._always_allowed(tool):
            return self._allow(tool, args, "always allowed: needs no authority")
        ok, reason, departure = self._step_check(tool, args)
        if not ok and departure:
            remembered = self._recall(tool, args)
            if remembered:
                return remembered
            approved, note = self._rereview(tool, args, reason)
            if not approved:
                self._record(tool, args, "RE-REVIEWED -> REFUSED", note)
                return {"ok": False, "error": note}
            ok, reason, _ = self._step_check(tool, args)
            reason = f"{note}; {reason}"
        if not ok:
            self._record(tool, args, "REFUSED", reason)
            return {"ok": False, "error": reason}
        token = secrets.token_hex(4)   # one-time token bound to this exact act
        return self._allow(tool, args, f"{reason}; token {token}")


class PlanLockedGate(TAAGate):
    """Same as TAAGate, except a departure from the approved plan is never re-reviewed:
    the plan is locked at approval, and anything it did not specify is refused outright.
    Comparator for whether TAAGate's re-review (Iudicium) earns its keep."""
    name = "plan-locked (plan review + live warrant + step check, no re-review)"

    def request(self, tool, args):
        if self._always_allowed(tool):
            return self._allow(tool, args, "always allowed: needs no authority")
        ok, reason, departure = self._step_check(tool, args)
        if not ok:
            if departure:
                reason = f"outside the approved plan, and this gate does not re-review departures: {reason}"
            self._record(tool, args, "REFUSED", reason)
            return {"ok": False, "error": reason}
        token = secrets.token_hex(4)   # one-time token bound to this exact act
        return self._allow(tool, args, f"{reason}; token {token}")
