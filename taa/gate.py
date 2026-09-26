"""The execution gate: the only path from an agent to the tools.

Six gates share one interface so the same agent can run under any of them:
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
- HybridGate: TAA's plan review and departure re-review, plus an action-time check on acts
  taa/consequence.py calls consequential (v0.11). Kept unchanged in v0.13 as the comparator
  for TAA's premise watch.

v0.13, shared by all six gates: fixed limits in the warrant (caps, taa/determinations.py) are
enforced by the gate itself before any review. v0.13, TAA only: when facts the plan's approval
rested on change for a reason other than the plan's own acts, the rest of the plan goes back to
review before the next act (taa/premises.py).

All gates hold the tool functions privately; the agent only ever calls gate.request().
"""
import copy
import json
import secrets

from taa import premises
from taa.preview import made_impossible, plan_acts
from taa.consequence import is_consequential
from taa.determinations import cap_refusal, default_amount
from taa.records import target_of


def _dollars(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


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
        self._reviewed_refusals = set()  # acts a reviewer refused before (any reason), for counting
        self._ordinary_refusals = {}   # memory key -> ordinary refusals on those facts (v0.15)
        self.fresh_rereviews = 0       # reviews of an act that had been refused before
        self._limit_noticed = set()    # targets the issuer has been told about a fixed-limit refusal
        self._outside_noticed = set()  # tools outside the registry someone has been told about (v0.17)

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

    def _cap_check(self, tool, args):
        """Why this act would break a fixed limit in the warrant (v0.13), or None. Checked by
        every gate before any review; a review can't widen it."""
        if not self.warrant.caps or tool not in self._tools:
            return None
        reason = cap_refusal(self.warrant.caps, tool, args, self.log, default_amount(self._tools[tool]))
        if reason:
            self._limit_notice(tool, args)
        return reason

    def _outside_notice(self, tool, args):
        """v0.17: the first request for a tool outside the registry is refused like any unpermitted
        tool, and someone is told, once per tool. Nothing behind such a name runs at any gate. This
        is the hand-off from the law (the gate) to whoever responds to attempts to break it."""
        if self.registry.is_registered(tool) or tool in self._outside_noticed or self._notify is None:
            return
        self._outside_noticed.add(tool)
        question = f"the agent asked for a tool outside the registry, which was refused: {tool} {json.dumps(args)}"
        outcome, _ = self._notify(question)
        self.referrals.append({"kind": "outside", "question": question, "outcome": outcome,
                               "step": self._world.step})

    def _limit_notice(self, tool, args):
        """v0.14: a fixed limit refused an act, so the issuer is told once per target that the
        request needs a higher decision. Every gate does this, as every gate enforces the limit."""
        target = target_of(args)
        if self._notify is None or target in self._limit_noticed:
            return
        self._limit_noticed.add(target)
        cap = self.warrant.caps[tool]["total_amount_per_target"]
        question = (f"{tool} for {target} was refused: it would exceed the warrant's fixed limit of ${cap} "
                    f"in total per target. A larger amount needs a decision by {self.warrant.issuer} or "
                    "higher authority.")
        outcome, _ = self._notify(question)
        self.referrals.append({"kind": "limit", "question": question, "outcome": outcome,
                               "step": self._world.step})

    # ---- refusal memory (the per-step judge, TAA, and the hybrid alike) ----------------------
    # A refusal the reviewer flagged as GRAVE is remembered at once. While the facts it rested on
    # are unchanged (the target's record and the world's status), a repeat is refused without a new
    # review, and the first repeat sends the issuer a notice. An ordinary refusal gets one fresh
    # re-review, so a single mistaken refusal isn't locked in (LAB_NOTEBOOK, v0.10: the judge's
    # wrong refusal of T1); since v0.15, a second refusal on the same facts is remembered too, so a
    # persistent agent can't make the reviewer answer the same question over and over.

    def _memory_key(self, tool, args):
        return (tool, json.dumps(args, sort_keys=True, default=str),
                self._world.fingerprint(target_of(args)))

    @staticmethod
    def _act_key(tool, args):
        return (tool, json.dumps(args, sort_keys=True, default=str))

    def _note_review(self, tool, args):
        """Count a review of an act a reviewer had already refused once (a fresh re-review)."""
        if self._act_key(tool, args) in self._reviewed_refusals:
            self.fresh_rereviews += 1

    def _refused_on_review(self, tool, args, grave):
        """Record a refusal decided on review. Remember it at once if the reviewer flagged it grave,
        or at the second ordinary refusal of the same act on the same facts (v0.15)."""
        self._reviewed_refusals.add(self._act_key(tool, args))
        key = self._memory_key(tool, args)
        if grave:
            self._refused[key] = {"step": self._world.step, "repeats": 0, "grave": True}
            return
        self._ordinary_refusals[key] = self._ordinary_refusals.get(key, 0) + 1
        if self._ordinary_refusals[key] >= 2:
            self._refused[key] = {"step": self._world.step, "repeats": 0, "grave": False}

    def _recall(self, tool, args):
        """If this act was refused before on the same facts, refuse it again without a review."""
        hit = self._refused.get(self._memory_key(tool, args))
        if hit is None:
            return None
        how = "as grave" if hit.get("grave", True) else "twice on review, most recently"
        return self._refuse_from_memory(tool, args, hit, f"the same act was refused {how} at step {hit['step']}")

    def _refuse_from_memory(self, tool, args, hit, what):
        """Refuse a remembered act; the first repeat sends the issuer a notice."""
        hit["repeats"] += 1
        note = f"refused from memory: {what} and nothing it rested on has changed, so it was not reviewed again"
        if hit["repeats"] == 1 and self._notify is not None:
            question = f"the agent asked again for an act refused at step {hit['step']}: {tool} {json.dumps(args)}"
            outcome, notice = self._notify(question)
            self.referrals.append({"kind": "repeat", "question": question, "outcome": outcome,
                                   "step": self._world.step})
            note += f"; {notice}"
        entry = self._record(tool, args, "REFUSED", note)
        entry["remembered"] = True
        return {"ok": False, "error": note}

    def _checked(self, tool, args, check, allow):
        """Refuse from memory (a grave refusal, or two ordinary ones on the same facts), or review
        the act with `check`."""
        remembered = self._recall(tool, args)
        if remembered:
            return remembered
        self._note_review(tool, args)
        approved, note, referrals = check()
        for r in referrals:
            self.referrals.append(dict(r, step=self._world.step))
        if not approved:
            # Nobody answering is not a decision, so an unanswered referral is not counted as one.
            if not any(r["outcome"] == "unanswered" and r["kind"] == "act" for r in referrals):
                self._refused_on_review(tool, args, grave=any(r["kind"] == "grave" for r in referrals))
            self._record(tool, args, "REFUSED", note)
            return {"ok": False, "error": note}
        return allow(note)

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
        capped = self._cap_check(tool, args)
        if capped:
            return capped, capped
        return None

    def request(self, tool, args):
        self._outside_notice(tool, args)
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
        self._outside_notice(tool, args)
        if self._always_allowed(tool):
            return self._allow(tool, args, "always allowed: needs no authority")
        refused = self._refusal(tool, args)
        if refused:
            self._record(tool, args, "REFUSED", refused[0])
            return {"ok": False, "error": refused[1]}
        return self._checked(tool, args, lambda: self._judge(tool, args), lambda note: self._allow(tool, args, note))


class TAAGate(_GateBase):
    name = "TAA (plan review + live warrant + step check + premise re-review)"
    watches_premises = True            # v0.13; plan-locked and the hybrid turn this off

    def __init__(self, tools, warrant, registry, world, reviewer, notify=None):
        super().__init__(tools, warrant, registry, world, notify)
        self.plan = None
        self._reviewer = reviewer      # a function(plan) -> reviewed plan (optionally with context=...)
        self.salvage_calls = 0
        self.salvaged_targets = []
        self.scope_calls = 0
        self.portion_calls = 0
        self.premise_rereviews = 0
        self._baseline = None          # the facts the current approval rests on (taa/premises.py)
        self._pending_targets = set()
        self._pending_limits = {}
        self._stops = {}               # (tool, target) -> a review's stop and the facts it rested on (v0.16)
        self._notices_sent = []        # questions already sent to the issuer this run (v0.16)
        self._conflict_noticed = set()  # approved targets the issuer was told a departure threatened (v0.18.1)
        self.notices_not_resent = 0

    def _review(self, plan, context=None, departure=None):
        """`departure`: the (tool, args) a departure re-review is about. Its refusal is counted by
        _refused_on_review, and a partial approval there leaves the previous plan in force, so it
        records no stops; an approval of the departing target clears that target's stop."""
        asked = [t for t in plan.targets if t]
        tools = list(plan.tools)
        plan.notices_sent = self._notices_sent
        plan.done_targets = self._done_targets(plan)
        reviewed = self._reviewer(plan, context=context) if context else self._reviewer(plan)
        reviewed.requested_now = None  # v0.18: true only for the review it was set for
        if departure is None:
            self._note_stops(asked, tools, reviewed)
        self.notices_not_resent += getattr(reviewed, "notices_not_resent", 0)
        self.salvage_calls += reviewed.salvage_calls
        self.scope_calls += reviewed.scope_calls
        self.portion_calls += reviewed.portion_calls
        self.salvaged_targets.extend(reviewed.salvaged_targets)
        self._pending_targets.update(reviewed.pending_targets)
        for target, limit in reviewed.pending_limits.items():
            earlier = dict(self._pending_limits.get(target, {}))
            for key, value in limit.items():
                earlier[key] = min(earlier[key], value) if key in earlier else value
            self._pending_limits[target] = earlier
        for r in reviewed.referrals:
            self.referrals.append(dict(r, step=self._world.step))
        return reviewed

    # ---- stops from review enter refusal memory (v0.16) -------------------------------------
    # A target a review left out of the plan, or a stopped plan's targets, was decided on the facts
    # at that review. A grave stop is remembered at once; an ordinary stop counts as the first
    # refusal, so one departure re-review is still allowed (the v0.15 rule). The plan's own acts
    # do not release a stop (the reviewer saw them coming); a change from outside does.

    def _done_targets(self, plan):
        """v0.17: targets whose approved acts are all carried out. A re-review is told they are done,
        rather than shown them as if still planned (their preview read "already on that route")."""
        done = []
        for t in plan.targets:
            uses = plan.limits.get(t, {}).get("uses", 1)
            spent = sum(1 for e in self.log if e["decision"] == "ALLOWED" and e["spent"] and target_of(e["args"]) == t)
            if spent and spent >= uses:
                done.append(t)
        return done

    def _note_stops(self, asked, tools, reviewed):
        if any(n.startswith("A fails") for n in reviewed.review_notes):
            return                     # a structural stop, enforced by the step check anyway
        if reviewed.status == "approved":
            stopped = [t for t in asked if t not in reviewed.targets and t not in reviewed.pending_targets]
        elif reviewed.status == "stopped":
            stopped = asked
        else:
            return                     # referred: nobody has decided yet
        for t in reviewed.targets:
            for tool in tools:
                self._stops.pop((tool, t), None)
        # v0.17: a grave flag belongs to the review, not to a target. Only when the review stopped a
        # single target is the flag surely that target's; several stopped targets each count as an
        # ordinary first refusal, so an over-broad stop gets one more look (scenario 16).
        grave = any(r["kind"] == "grave" for r in reviewed.referrals) and len(stopped) == 1
        for t in stopped:
            for tool in tools:
                self._stops[(tool, t)] = {"facts": self._world.fingerprint(t), "step": self._world.step,
                                          "grave": grave, "repeats": 0, "counted": set()}

    def _stop_for(self, tool, args):
        """The review stop covering this act, if the facts it rested on still hold."""
        target = target_of(args)
        stop = self._stops.get((tool, target))
        if stop is None or stop["facts"] != self._world.fingerprint(target):
            return None
        return stop

    def _recall(self, tool, args):
        remembered = super()._recall(tool, args)
        if remembered:
            return remembered
        stop = self._stop_for(tool, args)
        if stop is None or not stop["grave"]:
            return None
        return self._refuse_from_memory(tool, args, stop, f"review stopped this act as grave at step {stop['step']}")

    def _refused_on_review(self, tool, args, grave):
        # An ordinary stop by an earlier review counts as the first refusal on these facts, once.
        stop = self._stop_for(tool, args)
        key = self._memory_key(tool, args)
        if not grave and stop is not None and key not in stop["counted"]:
            stop["counted"].add(key)
            self._ordinary_refusals[key] = self._ordinary_refusals.get(key, 0) + 1
        super()._refused_on_review(tool, args, grave)

    def _note_review(self, tool, args):
        if self._act_key(tool, args) not in self._reviewed_refusals and (tool, target_of(args)) in self._stops:
            self.fresh_rereviews += 1      # reviewing an act an earlier review stopped
            return
        super()._note_review(tool, args)

    def submit_plan(self, plan):
        """Plan review. After a stop the agent may submit one revised plan (plan.revision);
        if that is stopped too, the run goes on with no approved plan."""
        requested = {"end": plan.end, "tools": list(plan.tools), "max_uses": dict(plan.max_uses),
                     "targets": plan.targets_shown()}
        self.plan = self._review(plan)
        self._record("(revised plan)" if plan.revision else "(plan)", requested,
                     plan.status.upper(), "; ".join(plan.review_notes))
        if self.plan.status == "approved":
            self._rebaseline()
        return self.plan

    # ---- premise watch (v0.13, TAA only) -------------------------------------------------------

    def _rebaseline(self):
        """The current facts become what the approval rests on: at approval, and after each act
        this gate allows (the approved plan anticipated its own acts)."""
        self._baseline = premises.snapshot(self._world)

    def _premises_changed(self):
        return (self.watches_premises and self._baseline is not None
                and premises.snapshot(self._world) != self._baseline)

    def _premise_rereview(self, now=None):
        """Facts changed for a reason other than the plan's own acts: the rest of the plan goes
        back to review under the current facts, told what changed. The new verdict replaces the
        old approval whatever it says, since the old approval's premises no longer hold."""
        now = premises.snapshot(self._world)
        changed = premises.changes(self._baseline, now)
        amended = copy.deepcopy(self.plan)
        amended.status, amended.review_notes, amended.amended, amended.revision = "proposed", [], True, False
        amended.departure = False      # a stop here withdraws the plan, so salvage still applies
        amended.requested_now = now    # v0.18: the act that met the changed facts is previewed first
        requested = {"end": amended.end, "tools": list(amended.tools), "max_uses": dict(amended.max_uses),
                     "targets": amended.targets_shown()}
        self.premise_rereviews += 1
        self.plan = self._review(amended, context=premises.context_text(changed, self.plan.premises))
        self._baseline = now
        self._record("(premise re-review)", requested, self.plan.status.upper(),
                     "facts changed since approval: " + "; ".join(changed) + " | " + "; ".join(self.plan.review_notes))
        return self.plan

    def _allow(self, tool, args, reason):
        before = {t: self._world.fingerprint(t) for (_, t) in self._stops}
        result = super()._allow(tool, args, reason)
        if self.watches_premises and self._baseline is not None:
            self._rebaseline()
        for (_, t), stop in self._stops.items():
            if stop["facts"] == before[t]:     # only this act changed its facts: the stop carries over
                stop["facts"] = self._world.fingerprint(t)
        return result

    def _step_check(self, tool, args):
        """The fast, rule-based check. Returns (ok, reason, departure)."""
        if self.plan is None or self.plan.status != "approved":
            return False, "no approved plan", False
        live, why = self.warrant.is_live(self._world)
        if not live:
            return False, f"warrant not live: {why}", False
        capped = self._cap_check(tool, args)
        if capped:
            return False, capped, False      # a fixed limit, not a departure: no review can widen it
        if not self.registry.is_registered(tool):
            return False, f"'{tool}' is not in the tool registry (treated as most consequential)", True
        if tool not in self.plan.tools:
            return False, f"'{tool}' is outside the approved plan", True
        target = target_of(args)
        if target in self._pending_targets:
            return False, f"all of {target} awaits an answer to a pending referral", False
        pending = self._pending_limits.get(target, {})
        if pending:
            done = [e for e in self.log if e["decision"] == "ALLOWED" and e["spent"]
                    and target_of(e["args"]) == target]
            if "uses" in pending and len(done) >= pending["uses"]:
                return False, f"uses beyond {pending['uses']} on {target} await a referral answer", False
            if "amount" in pending and args.get("amount") is not None:
                given = sum(_dollars(e["args"].get("amount")) for e in done)
                if given + _dollars(args["amount"]) > pending["amount"]:
                    return False, f"amount above ${pending['amount']} for {target} awaits a referral answer", False
        if self.plan.targets and target and target not in self.plan.targets:
            return False, f"target {target} is outside the approved plan", True
        limit = self.plan.limits.get(target) if target else None
        if limit:
            # Per-target limits (v0.11): acts that changed something on this target, and money to it.
            done = [e for e in self.log if e["decision"] == "ALLOWED" and e["spent"]
                    and target_of(e["args"]) == target]
            if "uses" in limit and len(done) >= limit["uses"]:
                return False, f"approved plan allows {limit['uses']} use(s) on {target}", True
            if "amount" in limit and args.get("amount") is not None:
                given = sum(_dollars(e["args"].get("amount")) for e in done)
                if given + _dollars(args["amount"]) > limit["amount"]:
                    return False, (f"approved plan allows ${limit['amount']} in total to {target} "
                                   f"(${given} given already)"), True
        left = self.warrant.remaining(tool)
        if left is not None and left <= 0:
            return False, "warrant budget exhausted", False
        used = sum(1 for e in self.log if e["tool"] == tool and e["decision"] == "ALLOWED" and e["spent"])
        cap = self.plan.max_uses.get(tool)
        if cap is not None and used >= cap:
            return False, f"approved plan allows {cap} uses of '{tool}'", True
        return True, "matches approved plan; warrant live; within budget", False

    def _protected_conflict(self, tool, args):
        """v0.18.1: approved acts still to come that this departure would make impossible, or [].
        An approval is a commitment: a later review can't silently undo it, so this is checked by
        code before any review. Only a person can change an earlier approval."""
        target = target_of(args)
        remaining = copy.copy(self.plan)
        remaining.done_targets = self._done_targets(self.plan) + ([target] if target else [])
        remaining.requested_now = None
        acts = plan_acts(remaining, self._world)
        if not acts:
            return []
        return made_impossible(self._world, (tool, args), acts, self.warrant.caps)

    def _rereview(self, tool, args, why):
        """A material departure goes back to plan review as an amended plan (paper Section 4.2)."""
        lost = self._protected_conflict(tool, args)
        if lost:
            for t in lost:
                if t not in self._conflict_noticed and self._notify is not None:
                    self._conflict_noticed.add(t)
                    question = (f"{tool} {json.dumps(args)} was refused: it would make the approved act on {t} "
                                "impossible. Only a person can change an earlier approval.")
                    outcome, _ = self._notify(question)
                    self.referrals.append({"kind": "conflict", "question": question, "outcome": outcome,
                                           "step": self._world.step})
            return False, (f"departure ({why}) refused without review: it would make the approved act on "
                           f"{', '.join(lost)} impossible (checked by the system); an earlier approval stands "
                           "until a person changes it")
        amended = copy.deepcopy(self.plan)
        amended.status, amended.review_notes, amended.amended = "proposed", [], True
        amended.revision, amended.departure = False, True
        amended.requested_now = target_of(args)   # v0.18: this act happens now, before the rest
        if tool not in amended.tools:
            amended.tools.append(tool)
        target = target_of(args)
        if target and amended.targets and target not in amended.targets:
            amended.targets.append(target)
        amended.max_uses[tool] = amended.max_uses.get(tool, 0) + 1
        if target in amended.limits:      # a per-target limit was the departure: ask for one more
            lim = amended.limits[target]
            if "uses" in lim:
                lim["uses"] += 1
            if "amount" in lim and args.get("amount") is not None:
                lim["amount"] += _dollars(args["amount"])
        self._note_review(tool, args)
        reviewed = self._review(amended, departure=(tool, args))
        grave = any(r["kind"] == "grave" for r in reviewed.referrals)
        if reviewed.status == "approved":
            # Adopt the reviewed plan only if it actually covers this act: a partial approval
            # that leaves out the act (or lowers a limit below it) does not approve it.
            previous, self.plan = self.plan, reviewed
            covers, _, _ = self._step_check(tool, args)
            if covers:
                self.plan.departure = False
                for t in self.plan.targets:        # approved now: earlier stops no longer apply
                    for plan_tool in self.plan.tools:
                        self._stops.pop((plan_tool, t), None)
                self._rebaseline()     # this plan was just approved on the current facts
                return True, f"departure ({why}) re-reviewed and approved: {'; '.join(reviewed.review_notes)}"
            self.plan = previous
            self._refused_on_review(tool, args, grave)
            return False, (f"departure ({why}) re-reviewed: plan approved without this act, which stays "
                           f"refused: {'; '.join(reviewed.review_notes)}")
        if reviewed.status == "stopped":   # decided; an unanswered referral ("referred") is not
            self._refused_on_review(tool, args, grave)
        return False, f"departure ({why}) re-reviewed: {'; '.join(reviewed.review_notes)}"

    def request(self, tool, args):
        self._outside_notice(tool, args)
        if self._always_allowed(tool):
            return self._allow(tool, args, "always allowed: needs no authority")
        ok, reason, departure = self._step_check(tool, args)
        if ok and self._premises_changed():
            # v0.13: the approval this act relies on rested on facts that have since changed.
            reviewed = self._premise_rereview(target_of(args))
            ok, reason, departure = self._step_check(tool, args)
            if not ok:
                # Just reviewed on the current facts, so a departure is not sent to review again.
                stop = self._stop_for(tool, args)
                if stop is not None:           # that review's stop is this refusal: count it once
                    stop["counted"].add(self._memory_key(tool, args))
                self._refused_on_review(tool, args, grave=any(r["kind"] == "grave" for r in reviewed.referrals))
                note = f"premise re-review no longer covers this act: {reason}"
                self._record(tool, args, "REFUSED", note)
                return {"ok": False, "error": note}
            reason = f"re-approved after facts changed; {reason}"
        if not ok and departure:
            remembered = self._recall(tool, args)
            if remembered:
                return remembered
            approved, note = self._rereview(tool, args, reason)
            if not approved:
                self._record(tool, args, "REFUSED" if "refused without review" in note else "RE-REVIEWED -> REFUSED", note)
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
    watches_premises = False           # no re-review of any kind, including after facts change

    def request(self, tool, args):
        self._outside_notice(tool, args)
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


class HybridGate(TAAGate):
    """TAA's plan review and departure re-review, plus a fresh counsel check at the moment of
    action for consequential acts inside the approved plan (v0.11). The check sees the current
    state, the act, and the approved plan. Routine in-plan acts pass on the plan's approval, as
    in TAA; a departure goes to TAA's re-review, which is already a fresh check, so it is not
    checked twice. What counts as consequential is defined in one place: taa/consequence.py."""
    name = "hybrid (TAA + action-time check on consequential acts)"
    watches_premises = False           # v0.13: kept on its v0.11 consequence rule, as a comparator

    def __init__(self, tools, warrant, registry, world, reviewer, act_check, notify=None):
        super().__init__(tools, warrant, registry, world, reviewer, notify)
        self._act_check = act_check    # a function(tool, args, plan) -> (approved, note, referrals)
        self.action_checks = 0         # consequential in-plan acts actually checked (not from memory)

    def _action_check(self, tool, args):
        self.action_checks += 1
        return self._act_check(tool, args, self.plan)

    def request(self, tool, args):
        self._outside_notice(tool, args)
        if self._always_allowed(tool):
            return self._allow(tool, args, "always allowed: needs no authority")
        ok, reason, departure = self._step_check(tool, args)
        if not ok:
            return super().request(tool, args)          # refusal or departure: exactly as TAA
        consequential, why = is_consequential(tool, self.registry, self._world.read_shipments())
        if not consequential:
            token = secrets.token_hex(4)
            return self._allow(tool, args, f"{reason}; routine act; token {token}")
        return self._checked(
            tool, args, lambda: self._action_check(tool, args),
            lambda note: self._allow(tool, args, f"{reason}; consequential ({why}): {note}; token {secrets.token_hex(4)}"))
