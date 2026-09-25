"""Governing records: the warrant, the tool registry, and the plan.

These are data, not code the agent can change. In the paper's terms:
- a warrant is a specific, time-limited grant of authority to pursue one purpose;
- the tool registry says what each tool does and how consequential it is;
- a plan is the agent's declared course of action, approved or not.
"""
from dataclasses import dataclass, field

# Effect classes, lowest to highest consequence (paper Section 4.3).
EFFECT_CLASSES = ["read_only", "changes_records", "communicates", "moves_resources", "irreversible"]


@dataclass
class Warrant:
    id: str
    issuer: str
    purpose: str
    allowed_tools: list
    live_while: dict            # e.g. {"disruption_status": "active"}: facts that must hold
    budget: dict                # e.g. {"reroute_shipment": 20}
    used: dict = field(default_factory=dict)

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
