"""Fixed decision pressure for the obligation fixtures; no model or adaptive retry."""
from taa.records import Plan


class TimelineAgent:
    name = "fixed-timeline scripted agent"

    def __init__(self, scenario):
        study = scenario["study"]
        self.timeline = {int(step): (tool, args) for step, (tool, args) in study["timeline"].items()}
        self.candidates = list(study["initial_candidates"])
        self.skipped = 0

    def propose_plan(self, warrant, observation):
        return Plan(end="Book supported storm shipments under current authority and resource limits.",
                    warrant_id=warrant.id, tools=["reroute_shipment"],
                    max_uses={"reroute_shipment": len(self.candidates)},
                    targets=[{"id": target, "uses": 1} for target in self.candidates])

    def revise_plan(self, warrant, observation, reviewer_reason):
        plan = self.propose_plan(warrant, observation)
        plan.revision = True
        return plan

    def decide(self, observation, feedback):
        act = self.timeline.get(observation["step"])
        if act is None:
            return None, None, "scheduled wait; no act requested"
        tool, args = act
        return tool, dict(args), "fixed schedule, independent of earlier gate replies"
