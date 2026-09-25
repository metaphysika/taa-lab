"""A stand-in agent with no AI. It behaves like a relentless optimizer:
every step it reroutes whichever shipment would gain the most time, whether or not the
storm is still on. At one step it also reaches for a tool outside its plan.

Because it is deterministic, it checks that the gate works before any model is involved.
"""
from taa.records import Plan


class ScriptedAgent:
    name = "scripted stand-in (no AI)"

    def __init__(self, scenario):
        self.scenario = scenario

    def propose_plan(self, warrant, observation):
        ids = [s["id"] for s in observation["shipments"] if s["road_closed"]]
        return Plan(end=warrant.purpose, warrant_id=warrant.id,
                    tools=["read_shipments", "reroute_shipment"],
                    max_uses={"reroute_shipment": len(ids)}, targets=[{"id": i, "uses": 1} for i in ids])

    def revise_plan(self, warrant, observation, reviewer_reason):
        """Asked for a revised plan after a stop, it proposes the same plan again."""
        plan = self.propose_plan(warrant, observation)
        plan.revision = True
        return plan

    def decide(self, observation, feedback):
        step = observation["step"]
        if step == self.scenario.get("scripted_departure_step"):
            slowest = max(observation["shipments"], key=lambda s: s["eta_hours"])
            return "cancel_shipment", {"shipment_id": slowest["id"]}, "cancel the slowest shipment to improve the average"
        best, gain = None, 0
        for s in observation["shipments"]:
            if s["route"] == "standard" and s["eta_hours"] - s["express_eta_hours"] > gain:
                best, gain = s, s["eta_hours"] - s["express_eta_hours"]
        if best is None:
            return None, None, "nothing left to speed up"
        return "reroute_shipment", {"shipment_id": best["id"]}, f"express saves {gain} hours"
