"""Governing records: the warrant, the tool registry, and the plan.

These are data, not code the agent can change. In the paper's terms:
- a warrant is a specific, time-limited grant of authority to pursue one purpose;
- the tool registry says what each tool does and how consequential it is;
- a plan is the agent's declared course of action, approved or not.
"""
from dataclasses import dataclass, field

# Effect classes, lowest to highest consequence (paper Section 4.3).
EFFECT_CLASSES = ["read_only", "changes_records", "communicates", "moves_resources", "irreversible"]


def target_of(args):
    """The record an act is aimed at: the value of its first *_id argument (shipment_id,
    vehicle_id, customer_id), or None for an act with no target."""
    if not isinstance(args, dict):
        return None
    for key, value in args.items():
        if key.endswith("_id"):
            return value
    return None


@dataclass
class Warrant:
    id: str
    issuer: str
    purpose: str
    allowed_tools: list
    live_while: dict            # e.g. {"disruption_status": "active"}: facts that must hold
    budget: dict                # e.g. {"reroute_shipment": 20}
    used: dict = field(default_factory=dict)
    caps: dict = field(default_factory=dict)  # fixed limits the gate enforces (v0.13), taa/determinations.py

    def is_live(self, world):
        """A warrant is live only while every condition it names still holds."""
        for fact, required in self.live_while.items():
            if world.fact(fact) != required:
                return False, f"condition '{fact} == {required}' no longer holds (now '{world.fact(fact)}')"
        return True, "live"

    def remaining(self, tool):
        if tool not in self.budget:
            return None
        return self.budget[tool] - self.used.get(tool, 0)


@dataclass
class ToolRegistry:
    entries: dict               # tool name -> {"effect_class": ..., "description": ...}

    def effect_class(self, tool):
        # An unregistered tool counts as the most consequential kind (paper Section 4.3).
        return self.entries.get(tool, {}).get("effect_class", "irreversible")

    def is_registered(self, tool):
        return tool in self.entries

    def always_allowed(self, tool):
        """Tools that need no authority, such as telling a human supervisor something."""
        return bool(self.entries.get(tool, {}).get("always_allowed"))


def normalize_targets(raw):
    """A plan's targets as (ids, limits). Targets may be plain ids (the old format) or entries
    with per-target limits, e.g. {"id": "C-9", "uses": 1, "amount": 300}: at most 1 act on C-9,
    and at most $300 in total to it. Both formats can be mixed."""
    ids, limits = [], {}
    for entry in raw or []:
        if isinstance(entry, dict) and "id" in entry:
            ids.append(str(entry["id"]))
            lim = {}
            for key in ("uses", "amount"):
                try:
                    if entry.get(key) is not None:
                        lim[key] = int(entry[key])
                except (TypeError, ValueError):
                    pass
            if lim:
                limits[str(entry["id"])] = lim
        else:
            ids.append(str(entry))
    return ids, limits


@dataclass
class Plan:
    end: str                    # the purpose the plan claims to serve
    warrant_id: str
    tools: list
    max_uses: dict              # e.g. {"reroute_shipment": 8}
    targets: list = field(default_factory=list)
    status: str = "proposed"    # proposed | approved | stopped | referred
    review_notes: list = field(default_factory=list)
    amended: bool = False       # True when a step departed from the plan and it came back for review
    revision: bool = False      # True when this plan was proposed again after a stop
    dropped_targets: list = field(default_factory=list)   # targets counsel did not approve
    referrals: list = field(default_factory=list)          # questions sent to the human at this review
    limits: dict = field(default_factory=dict)  # per-target limits: id -> {"uses": n, "amount": dollars}
    pending_limits: dict = field(default_factory=dict)  # approved ceiling while a larger request awaits an answer
    pending_targets: list = field(default_factory=list)  # whole targets referred without an approved portion
    salvage_calls: int = 0
    salvaged_targets: list = field(default_factory=list)
    scope_calls: int = 0        # clarifications asked because an approval didn't say what may proceed (v0.13)
    portion_calls: int = 0      # follow-ups asking what part of an unanswered referral may proceed now (v0.14)
    premises: list = field(default_factory=list)  # facts the reviewer said its approval rests on (v0.13)

    def __post_init__(self):
        ids, limits = normalize_targets(self.targets)
        self.targets = ids
        self.limits = {**limits, **self.limits}

    def targets_shown(self):
        """Targets as a reviewer sees them: plain ids when no target has limits (so old-format
        plans read exactly as before), otherwise {"id", "uses", "amount"} for limited targets."""
        if not self.limits:
            return list(self.targets)
        return [dict({"id": t}, **self.limits[t]) if t in self.limits else t for t in self.targets]
