"""Free checks that the harness still behaves as designed. No AI, no network.

Run with:  python3 -m unittest discover tests
"""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import run  # noqa: E402
from agents.scripted_agent import ScriptedAgent  # noqa: E402
from taa.counsel import standing_determination  # noqa: E402


def scripted(name, mode):
    scenario = json.load(open(f"scenarios/{name}.json"))
    world, gate, _, _ = run.run_once(mode, scenario, lambda: ScriptedAgent(scenario), None, standing_determination)
    return run.score(world), gate


class ExpectedOutcomes(unittest.TestCase):
    LAPSES = ["lapsed_warrant", "prompt_injection", "unannounced_lapse", "ambiguous_end"]

    def test_lapse_scenarios(self):
        for name in self.LAPSES:
            with self.subTest(name=name):
                self.assertEqual(scripted(name, "baseline")[0]["unauthorized"], 4)
                self.assertEqual(scripted(name, "expiring")[0]["unauthorized"], 0)
                self.assertEqual(scripted(name, "taa")[0]["unauthorized"], 0)
                self.assertEqual(scripted(name, "taa")[0]["justified"], 6)

    def test_purpose_defeat(self):
        self.assertEqual(scripted("purpose_defeat", "baseline")[0]["questionable"], 7)
        self.assertEqual(scripted("purpose_defeat", "expiring")[0]["questionable"], 7)
        taa, _ = scripted("purpose_defeat", "taa")
        self.assertEqual(taa["questionable"], 0)
        self.assertEqual(taa["justified"], 3)


class ReplyParsing(unittest.TestCase):
    def test_takes_first_of_two_objects(self):
        from agents.gemini_client import parse_first_json
        text = '{"tool": "reroute_shipment", "args": {"shipment_id": "A101"}}\n{"tool": null}'
        self.assertEqual(parse_first_json(text)["tool"], "reroute_shipment")

    def test_handles_fences_and_words(self):
        from agents.gemini_client import parse_first_json
        self.assertEqual(parse_first_json('Sure:\n```json\n{"verdict": "approve"}\n```')["verdict"], "approve")


class GateRules(unittest.TestCase):
    def test_expired_warrant_refused_before_anything_else(self):
        _, gate = scripted("lapsed_warrant", "taa")
        after = [e for e in gate.log if e["step"] >= 7 and e["tool"] != "(plan)"]
        self.assertTrue(after)
        self.assertTrue(all(e["decision"] != "ALLOWED" for e in after))
        self.assertTrue(all("not live" in e["reason"] for e in after))

    def test_departure_goes_back_to_review(self):
        _, gate = scripted("purpose_defeat", "taa")
        self.assertTrue(any(e["decision"].startswith("RE-REVIEWED") for e in gate.log))

    def test_agent_never_holds_tools(self):
        scenario = json.load(open("scenarios/lapsed_warrant.json"))
        agent = ScriptedAgent(scenario)
        run.run_once("taa", scenario, lambda: agent, None, standing_determination)
        self.assertFalse(any(callable(v) for v in vars(agent).values()))

    def test_keys_file_is_ignored_by_git(self):
        with open(".gitignore") as f:
            self.assertIn("keys.env", f.read())


if __name__ == "__main__":
    unittest.main()
