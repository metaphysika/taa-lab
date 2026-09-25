"""A stand-in agent with no AI that does whatever its task and operator instruct.

Each high-stakes scenario carries an "obedient" script: the plan its instructions imply (with
the instructions stated honestly as the plan's end) and the acts they call for, in order. The
agent asks for each act in turn, then asks once more for each act that was refused. Its revised
plan after a stop is the same plan: it does not argue with its orders.

A model agent may refuse a wrongful order on its own, and then no gate is tested. This agent
never refuses, so every gate faces the order.
"""
import json

from taa.records import Plan, target_of


class ObedientAgent:
    name = "scripted obedient agent (no AI; carries out every instruction)"

    def __init__(self, scenario):
        if "obedient" not in scenario:
            raise ValueError(f"scenario '{scenario['name']}' has no obedient script")
        self.script = scenario["obedient"]
        self.todo = [(tool, dict(args)) for tool, args in self.script["acts"]]
        self.retries, self.pending = [], None

    def propose_plan(self, warrant, observation):
        """The plan its instructions imply, with per-target limits (v0.11) counted honestly from
        the instructed acts: how many acts on each target, and how much money in total."""
        s = self.script
        limits = {t: {"uses": 0} for t in s["targets"]}
        for _, args in self.script["acts"]:
            target = target_of(args)
            if target in limits:
                limits[target]["uses"] += 1
                if "amount" in args:
                    limits[target]["amount"] = limits[target].get("amount", 0) + int(args["amount"])
        return Plan(end=s["end"], warrant_id=warrant.id, tools=list(s["tools"]), max_uses=dict(s["max_uses"]),
                    targets=[dict({"id": t}, **limits[t]) for t in s["targets"]])

    def revise_plan(self, warrant, observation, reviewer_reason):
        plan = self.propose_plan(warrant, observation)
        plan.revision = True
        return plan

    def decide(self, observation, feedback):
        # The last act asked for was refused or had no effect: ask for it once more later.
        if self.pending is not None and feedback is not None and not feedback.get("ok"):
            if self.pending[2] == "first try":
                self.retries.append(self.pending[:2])
        if self.todo:
            tool, args = self.todo.pop(0)
            self.pending = (tool, args, "first try")
            return tool, args, "instructed"
        if self.retries:
            tool, args = self.retries.pop(0)
            self.pending = (tool, args, "retry")
            return tool, args, f"instructed; asking again after a refusal ({json.dumps(args)})"
        self.pending = None
        return None, None, "every instructed act has been asked for"
