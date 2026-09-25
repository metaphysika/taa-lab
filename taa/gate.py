"""The execution gate: the only path from an agent to the tools.

Four gates share one interface so the same agent can run under any of them:
- BaselineGate: ordinary scoped permissions. A tool call passes if the tool is on the
  allowed list and budget remains. Nothing expires; there is no plan.
- ExpiringGate: scoped permissions that also expire when the warrant's condition stops
  holding. This is the strongest simple comparator: no plan, no review of purpose.
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
import secrets


class _GateBase:
    def __init__(self, tools, warrant, registry, world):
        self._tools = tools            # private: the agent never sees these
        self.warrant = warrant
        self.registry = registry
        self._world = world
        self.log = []

    def _execute(self, tool, args):
        """Run an allowed act. Only an act that changed something spends authority: a call
        with no effect (e.g. "already on that route") counts against no warrant or plan limit."""
        result = self._tools[tool](**args)
        spent = self.registry.effect_class(tool) != "read_only" and bool(result.get("ok"))
        if spent:
            self.warrant.used[tool] = self.warrant.used.get(tool, 0) + 1
        return result, spent

    def _record(self, tool, args, decision, reason, spent=False):
        entry = {"step": self._world.step, "tool": tool, "args": args,
                 "decision": decision, "reason": reason, "spent": spent}
        self.log.append(entry)
        return entry

    def _allow(self, tool, args, reason):
        result, spent = self._execute(tool, args)
        if not spent and self.registry.effect_class(tool) != "read_only":
            reason += f"; no effect ({result.get('error', 'nothing changed')}), so no authority spent"
        self._record(tool, args, "ALLOWED", reason, spent)
        return result


class BaselineGate(_GateBase):
    name = "baseline (scoped permissions)"

    def request(self, tool, args):
        if tool not in self._tools or tool not in self.warrant.allowed_tools:
            self._record(tool, args, "REFUSED", "tool not permitted")
            return {"ok": False, "error": "not permitted"}
        left = self.warrant.remaining(tool)
        if left is not None and left <= 0:
            self._record(tool, args, "REFUSED", "budget exhausted")
            return {"ok": False, "error": "budget exhausted"}
        return self._allow(tool, args, "tool is permitted")


class ExpiringGate(BaselineGate):
    name = "expiring permissions (scope + budget + live condition)"

    def request(self, tool, args):
        live, why = self.warrant.is_live(self._world)
        if not live:
            self._record(tool, args, "REFUSED", f"permission expired: {why}")
            return {"ok": False, "error": f"permission expired: {why}"}
        return super().request(tool, args)


class TAAGate(_GateBase):
    name = "TAA (plan review + live warrant + step check)"

    def __init__(self, tools, warrant, registry, world, reviewer):
        super().__init__(tools, warrant, registry, world)
        self.plan = None
        self._reviewer = reviewer      # a function(plan) -> reviewed plan
        self.referrals = []            # every question plan review sent to the human handler

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
        if self.plan.targets and args.get("shipment_id") and args["shipment_id"] not in self.plan.targets:
            return False, f"target {args['shipment_id']} is outside the approved plan", True
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
        if args.get("shipment_id") and amended.targets and args["shipment_id"] not in amended.targets:
            amended.targets.append(args["shipment_id"])
        amended.max_uses[tool] = amended.max_uses.get(tool, 0) + 1
        reviewed = self._review(amended)
        # A partial approval that leaves out the very act that departed does not approve it.
        covers = tool in reviewed.tools and not (args.get("shipment_id") and reviewed.targets
                                                 and args["shipment_id"] not in reviewed.targets)
        if reviewed.status == "approved" and covers:
            self.plan = reviewed
            return True, f"departure ({why}) re-reviewed and approved: {'; '.join(reviewed.review_notes)}"
        if reviewed.status == "approved":
            return False, (f"departure ({why}) re-reviewed: plan approved without this act, which stays "
                           f"refused: {'; '.join(reviewed.review_notes)}")
        return False, f"departure ({why}) re-reviewed: {'; '.join(reviewed.review_notes)}"

    def request(self, tool, args):
        ok, reason, departure = self._step_check(tool, args)
        if not ok and departure:
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
        ok, reason, departure = self._step_check(tool, args)
        if not ok:
            if departure:
                reason = f"outside the approved plan, and this gate does not re-review departures: {reason}"
            self._record(tool, args, "REFUSED", reason)
            return {"ok": False, "error": reason}
        token = secrets.token_hex(4)   # one-time token bound to this exact act
        return self._allow(tool, args, f"{reason}; token {token}")
