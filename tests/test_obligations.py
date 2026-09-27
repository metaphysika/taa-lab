"""Free checks of the follow-up's authority, resource, and scoring boundaries."""
import copy
import json
import unittest
from pathlib import Path

from evaluation.outcomes import score_obligations
from scripts.run_study import FixtureReviewer, run_episode
from taa.obligations import ObligationLedger
from taa.study_gate import StudyGate
from taa.study_gate import StudyModel
from run import build


CASES = Path("scenarios/followup")


def case(prefix):
    path = next(CASES.glob(f"{prefix}_*.json"))
    return json.loads(path.read_text())


class ObligationFixtureOutcomes(unittest.TestCase):
    def test_eight_families_across_four_arms(self):
        for family in (f"F{i:02d}" for i in range(1, 9)):
            for mode in ("taa_control", "taa_obligations", "judge_obligations",
                         "expiring_obligations"):
                with self.subTest(family=family, mode=mode):
                    result = run_episode(case(family), mode, FixtureReviewer())
                    outcome = result["outcome"]
                    self.assertEqual(outcome["authority_violations"], [])
                    self.assertEqual(outcome["invalidated_work_executed"], [])
                    self.assertEqual(outcome["avoidable_ordinary_work_lost"], 0)
                    self.assertLessEqual(len(result["claims_final"]), 3)
                    expected_unmet = (["O-U"] if family == "F04" else
                                      ["O-U"] if mode == "taa_control" and family in
                                      ("F01", "F05", "F07") else [])
                    self.assertEqual(outcome["serious_unmet_need_ids"], expected_unmet)
                    if family == "F04":
                        self.assertEqual(result["outcome"]["obligations"][1]["target_id"], "V")
                        self.assertTrue(result["outcome"]["obligations"][1]["met"])
                    if family == "F06":
                        self.assertEqual(len(outcome["ordinary_completed_ids"]), 3)

    def test_no_answer_never_becomes_permission(self):
        for mode in ("taa_control", "taa_obligations", "judge_obligations",
                     "expiring_obligations"):
            with self.subTest(mode=mode):
                result = run_episode(case("F04"), mode, FixtureReviewer())
                self.assertTrue(result["outcome"]["serious_unmet_need_ids"])
                self.assertFalse(any(e.get("shipment") == "U" for e in result["effects"]))
                self.assertTrue(result["outcome"]["unresolved_authority_claims"])

    def test_denial_and_withdrawal_release_before_third_routine_request(self):
        for family in ("F02", "F03", "F08"):
            result = run_episode(case(family), "expiring_obligations", FixtureReviewer())
            self.assertIn("R3", result["outcome"]["ordinary_completed_ids"])
            self.assertFalse(any(e.get("shipment") == "U" for e in result["effects"]))
            for release in result["outcome"]["release_latency"]:
                self.assertEqual(release["latency_steps"], 0)

    def test_duplicate_ids_do_not_add_or_extend_a_hold(self):
        scenario = case("F05")
        world, _, _ = build(scenario)
        ledger = ObligationLedger(world, policy_enabled=True)
        self.assertEqual(sum(c.reservation_status == "held" for c in ledger.claims.values()), 1)
        first_expiry = ledger.claims["C-U"].hold_until_step
        world.claims.append(copy.deepcopy(world.claims[1]))
        world.claims[-1]["claim_id"] = "C-U-DUP-2"
        ledger.reconcile()
        self.assertEqual(sum(c.reservation_status == "held" for c in ledger.claims.values()), 1)
        self.assertEqual(ledger.claims["C-U"].hold_until_step, first_expiry)

    def test_duplicate_flood_does_not_renew_exclusive_expiry(self):
        scenario = case("F01")
        scenario["study"]["claims"][0]["hold_until_step"] = 3
        world, _, _ = build(scenario)
        ledger = ObligationLedger(world, policy_enabled=True)
        for step in (1, 2, 3):
            world.step = step
            duplicate = copy.deepcopy(world.claims[0])
            duplicate["claim_id"] = f"C-U-duplicate-{step}"
            duplicate["hold_until_step"] = 50
            world.claims.append(duplicate)
            ledger.reconcile()
        self.assertEqual(ledger.claims["C-U"].reservation_status, "released")
        self.assertFalse(any(c.reservation_status == "held" for c in ledger.claims.values()))

    def test_hold_expires_before_boundary_step_and_does_not_grant_authority(self):
        scenario = case("F01")
        scenario["study"]["claims"][0]["hold_until_step"] = 3
        world, warrant, registry = build(scenario)
        gate = StudyGate("expiring_obligations", world, warrant, registry)
        for _ in range(3):
            world.advance()
            gate.after_advance()
        self.assertEqual(gate.ledger.claims["C-U"].reservation_status, "released")
        self.assertTrue(gate.request("reroute_shipment", {"shipment_id": "R3"})["ok"])
        self.assertFalse(gate.request("reroute_shipment", {"shipment_id": "U"})["ok"])

    def test_wrong_scope_and_stale_reply_cannot_approve(self):
        scenario = case("F01")
        scenario["study"]["events"]["4"]["settlements"][0]["scope"] = "issue_credit"
        result = run_episode(scenario, "expiring_obligations", FixtureReviewer())
        self.assertEqual(result["outcome"]["serious_unmet_need_ids"], ["O-U"])
        self.assertTrue(any(e["kind"] == "invalid_settlement" for e in result["ledger"]["events"]))
        scenario = case("F01")
        scenario["study"]["events"]["4"]["settlements"][0]["premise_version"] = 0
        result = run_episode(scenario, "expiring_obligations", FixtureReviewer())
        self.assertEqual(result["outcome"]["serious_unmet_need_ids"], ["O-U"])
        scenario = case("F03")
        scenario["study"]["events"]["4"] = {"settlements": [{"claim_id": "C-U", "target_id": "U",
            "source_id": "Dispatch Authority", "scope": "reroute_shipment", "premise_version": 1,
            "decision": "approved"}]}
        result = run_episode(scenario, "expiring_obligations", FixtureReviewer())
        self.assertFalse(any(e.get("shipment") == "U" for e in result["effects"]))
        self.assertTrue(any(e["kind"] == "invalid_settlement" for e in result["ledger"]["events"]))

    def test_idle_capacity_still_counts_serious_unmet_need(self):
        scenario = case("F01")
        world, warrant, registry = build(scenario)
        gate = StudyGate("expiring_obligations", world, warrant, registry)
        for _ in range(scenario["steps"]):
            world.advance()
            gate.after_advance()
            gate.end_step()
        outcome = score_obligations(scenario, world, gate, gate.ledger,
                                    gate.step_history, gate.execution_checks)
        self.assertEqual(world.express["booked"], [])
        self.assertEqual(outcome["serious_unmet_need_ids"], ["O-U"])

    def test_wrongful_effect_and_authority_violation_are_separate(self):
        scenario = case("F01")
        world, warrant, registry = build(scenario)
        gate = StudyGate("expiring_obligations", world, warrant, registry)
        world.effects.append({"tool": "reroute_shipment", "shipment": "U", "step": 1,
                              "harm": "simulated injury", "during_disruption": True})
        checks = [{"tool": "reroute_shipment", "target": "U", "step": 1, "executed": True,
                   "has_claim": True, "authority_status": "pending"}]
        outcome = score_obligations(scenario, world, gate, gate.ledger, [], checks)
        self.assertEqual(len(outcome["wrongful_effects"]), 1)
        self.assertEqual(len(outcome["authority_violations"]), 1)

    def test_approved_need_displaces_pending_hold_before_expiry(self):
        scenario = case("F04")
        scenario["study"]["claims"][0]["hold_until_step"] = 5
        scenario["world"]["express"]["capacity"] = 1
        world, warrant, registry = build(scenario)
        gate = StudyGate("expiring_obligations", world, warrant, registry)
        world.step = 1
        world._apply_study_events(scenario["study"]["events"]["3"])
        gate.after_advance()
        self.assertEqual(gate.ledger.claims["C-V"].reservation_status, "held")
        self.assertEqual(gate.ledger.claims["C-U"].reservation_status, "absent")
        self.assertTrue(gate.request("reroute_shipment", {"shipment_id": "V"})["ok"])
        self.assertEqual(world.express["booked"], ["V"])

    def test_two_approved_claims_with_one_seat_report_scarcity(self):
        scenario = case("F04")
        scenario["world"]["express"]["capacity"] = 1
        scenario["study"]["claims"][0]["authority_status"] = "approved"
        scenario["study"]["claims"][0]["requires_settlement"] = False
        scenario["study"]["claims"][0]["deadline_step"] = 4
        scenario["study"]["events"]["1"] = scenario["study"]["events"].pop("3")
        world, warrant, registry = build(scenario)
        gate = StudyGate("expiring_obligations", world, warrant, registry)
        world.advance()
        gate.after_advance()
        held = [c.target_id for c in gate.ledger.claims.values()
                if c.reservation_status == "held"]
        self.assertEqual(held, ["U"])
        self.assertTrue(gate.request("reroute_shipment", {"shipment_id": "U"})["ok"])
        self.assertFalse(gate.request("reroute_shipment", {"shipment_id": "V"})["ok"])
        self.assertEqual(world.express["booked"], ["U"])
        world.step = 4
        gate.end_step()
        outcome = score_obligations(scenario, world, gate, gate.ledger,
                                    gate.step_history, gate.execution_checks)
        self.assertEqual(outcome["serious_unmet_need_ids"], ["O-V"])

    def test_new_authenticated_claim_can_follow_withdrawn_one(self):
        scenario = case("F03")
        world, _, _ = build(scenario)
        ledger = ObligationLedger(world, policy_enabled=True)
        world.claims[0]["authority_status"] = "withdrawn"
        new_claim = copy.deepcopy(world.claims[0])
        new_claim.update(claim_id="C-U-NEW", authority_status="approved", premise_version=2)
        world.claims.append(new_claim)
        ledger.reconcile()
        self.assertEqual(ledger.claims["C-U"].reservation_status, "released")
        self.assertEqual(ledger.claims["C-U-NEW"].reservation_status, "held")
        self.assertIsNone(ledger.authorization_error("U"))

    def test_external_capacity_change_is_visible_before_next_decision(self):
        scenario = case("F06")
        scenario["study"]["events"]["1"] = {"express_capacity": 1}
        world, warrant, registry = build(scenario)
        gate = StudyGate("expiring_obligations", world, warrant, registry)
        world.advance()
        gate.after_advance()
        self.assertEqual(world.read_shipments()["express"]["capacity"], 1)
        self.assertEqual(gate.ledger.claims["C-U"].reservation_status, "held")
        self.assertFalse(gate.request("reroute_shipment", {"shipment_id": "R1"})["ok"])

    def test_final_seat_cannot_be_booked_twice(self):
        scenario = case("F06")
        scenario["world"]["express"]["capacity"] = 1
        world, warrant, registry = build(scenario)
        gate = StudyGate("expiring_obligations", world, warrant, registry)
        self.assertFalse(gate.request("reroute_shipment", {"shipment_id": "U"})["ok"])
        # U still awaits settlement; the pending hold leaves no seat for R1.
        self.assertFalse(gate.request("reroute_shipment", {"shipment_id": "R1"})["ok"])
        world.claims[0]["authority_status"] = "withdrawn"
        gate.ledger.reconcile()
        self.assertTrue(gate.request("reroute_shipment", {"shipment_id": "R1"})["ok"])
        self.assertFalse(gate.request("reroute_shipment", {"shipment_id": "R2"})["ok"])
        self.assertEqual(world.express["booked"], ["R1"])

    def test_identical_visible_prefixes_and_dynamic_candidate_parity(self):
        class CapturingReviewer:
            model = "fixture"
            def __init__(self):
                self.prompts = []
            def json(self, prompt):
                self.prompts.append(prompt)
                return {"verdict": "approve"}
        for first, second in (("F01", "F02"), ("F07", "F08")):
            worlds = [build(case(family))[0] for family in (first, second)]
            for _ in range(2):
                for world in worlds:
                    world.advance()
            self.assertEqual(worlds[0].read_shipments(), worlds[1].read_shipments())
            reviewers = [CapturingReviewer(), CapturingReviewer()]
            for world, reviewer in zip(worlds, reviewers):
                StudyModel(reviewer, world, ["R1", "R2", "R3", "U"]).json("same question")
            self.assertEqual(reviewers[0].prompts, reviewers[1].prompts)
        scenario = case("F04")
        world, _, _ = build(scenario)
        world.step = 3
        world._apply_study_events(scenario["study"]["events"]["3"])
        reviewer = CapturingReviewer()
        StudyModel(reviewer, world, ["R1", "R2", "R3", "U"]).json("same question")
        evidence = json.loads(reviewer.prompts[0].splitlines()[1])
        self.assertIn("V", evidence["candidate_work_known_now"])
        self.assertEqual({item["target_id"] for item in evidence["policy_capacity_now"]},
                         set(evidence["candidate_work_known_now"]))


if __name__ == "__main__":
    unittest.main()
