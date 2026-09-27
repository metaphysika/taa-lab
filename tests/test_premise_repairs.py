"""Regression checks for the v0.18.1 premise-watch defects."""
import json
import unittest

from taa.gate import TAAGate
from taa.preview import plan_acts
from taa.records import Plan
from run import build


class PremiseRepairs(unittest.TestCase):
    def make_gate(self):
        with open("scenarios/express_allocation.json") as source:
            world, warrant, registry = build(json.load(source))
        seen = []

        def reviewer(plan, context=None):
            seen.append({"context": context, "requested_now": plan.requested_now,
                         "order": [args["shipment_id"] for _, args in plan_acts(plan, world)]})
            plan.status = "approved"
            plan.review_notes = ["fixture approval"]
            return plan

        gate = TAAGate(world.tools(), warrant, registry, world, reviewer=reviewer)
        gate.submit_plan(Plan(end="storm relief", warrant_id=warrant.id,
                              tools=["reroute_shipment"], max_uses={"reroute_shipment": 2},
                              targets=["MED-7", "A103"]))
        return world, gate, seen

    def test_requested_target_reaches_premise_review_and_preview_first(self):
        world, gate, seen = self.make_gate()
        world.advance()
        world.record("A101")["eta_hours"] += 1  # external fact, not the plan's act
        gate.request("reroute_shipment", {"shipment_id": "A103"})
        self.assertEqual(gate.premise_rereviews, 1)
        self.assertEqual(seen[1]["requested_now"], "A103")
        self.assertEqual(seen[1]["order"], ["A103", "MED-7"])

    def test_report_does_not_erase_unreviewed_external_change(self):
        world, gate, seen = self.make_gate()
        world.advance()
        world.record("A101")["eta_hours"] += 1
        self.assertTrue(gate._premises_changed())
        gate.request("report_to_human", {"message": "A shipment fact changed."})
        self.assertTrue(gate._premises_changed())
        gate.request("reroute_shipment", {"shipment_id": "A103"})
        self.assertEqual(gate.premise_rereviews, 1)
        self.assertIsNotNone(seen[1]["context"])

    def test_read_does_not_erase_unreviewed_external_change(self):
        world, gate, seen = self.make_gate()
        gate.registry.entries["read_shipments"]["always_allowed"] = True
        world.advance()
        world.record("A101")["eta_hours"] += 1
        self.assertIn("shipments", gate.request("read_shipments", {}))
        self.assertTrue(gate._premises_changed())
        gate.request("reroute_shipment", {"shipment_id": "A103"})
        self.assertEqual(gate.premise_rereviews, 1)
        self.assertEqual(seen[1]["requested_now"], "A103")

    def test_ordinary_approved_sequence_does_not_rereview_its_own_effect(self):
        world, gate, seen = self.make_gate()
        world.advance()
        self.assertTrue(gate.request("reroute_shipment", {"shipment_id": "A103"})["ok"])
        world.advance()
        self.assertTrue(gate.request("reroute_shipment", {"shipment_id": "MED-7"})["ok"])
        self.assertEqual(gate.premise_rereviews, 0)
        self.assertEqual(len(seen), 1)


if __name__ == "__main__":
    unittest.main()
