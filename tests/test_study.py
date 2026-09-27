"""Free validation of study provenance, referrals, and provider request accounting."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.call_telemetry import BudgetStopped, CallRecorder
from agents.openai_client import OpenAI
from agents.anthropic_client import Claude
from scripts.run_study import main, paid_model, run_episode
from taa.counsel import judge_act
from taa.study_gate import StudyGate
from agents.timeline_agent import TimelineAgent
from run import build


def scenario():
    return json.loads(Path("scenarios/followup/F01_pending_approval.json").read_text())


class Response:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps(self.value).encode()


class CallEvidence(unittest.TestCase):
    def test_openai_empty_reply_retry_keeps_both_attempts_and_usage(self):
        replies = [
            {"id": "one", "model": "gpt-6-luna", "choices": [{"message": {"content": ""},
              "finish_reason": "length"}], "usage": {"prompt_tokens": 100, "completion_tokens": 50,
              "prompt_tokens_details": {"cached_tokens": 20},
              "completion_tokens_details": {"reasoning_tokens": 45}}},
            {"id": "two", "model": "gpt-6-luna", "choices": [{"message": {"content": '{"verdict":"approve"}'},
              "finish_reason": "stop"}], "usage": {"prompt_tokens": 120, "completion_tokens": 30,
              "prompt_tokens_details": {"cached_tokens": 0}}},
        ]
        with tempfile.TemporaryDirectory() as folder:
            recorder = CallRecorder(Path(folder) / "calls.jsonl",
                                    {"gpt-6-luna": {"input_per_million": 1,
                                                    "cached_input_per_million": .1,
                                                    "output_per_million": 2}},
                                    "gpt-6-luna", 3, 3, 1)
            recorder.logical("test prompt", "act")
            with patch.dict(os.environ, {"OPENAI_API_KEY": "fixture", "OPENAI_PACE": "0"}), \
                 patch("urllib.request.urlopen", side_effect=[Response(r) for r in replies]):
                client = OpenAI(model="gpt-6-luna", recorder=recorder)
                self.assertEqual(client.json("test prompt")["verdict"], "approve")
            self.assertEqual(recorder.snapshot()["request_attempts"], 2)
            self.assertEqual(recorder.snapshot()["output_tokens"], 80)
            self.assertEqual(recorder.snapshot()["cached_input_tokens"], 20)
            events = [json.loads(line) for line in (Path(folder) / "calls.jsonl").read_text().splitlines()]
            self.assertEqual(sum(e["event"] == "attempt_end" for e in events), 2)
            self.assertTrue(any(e.get("raw_text") == "" for e in events if e["event"] == "reply"))
            self.assertFalse(any("fixture" in json.dumps(e) for e in events))

    def test_anthropic_usage_and_raw_reply(self):
        reply = {"id": "msg-1", "model": "claude-haiku-4-5-20251001", "stop_reason": "end_turn",
                 "content": [{"type": "text", "text": '{"verdict":"refer","reason":"ask"}'}],
                 "usage": {"input_tokens": 90, "output_tokens": 25,
                           "cache_read_input_tokens": 10, "cache_creation_input_tokens": 5}}
        prices = {"claude-haiku-4-5-20251001": {"input_per_million": 1,
                  "cached_input_per_million": .1, "cache_write_per_million": 1.25,
                  "output_per_million": 5}}
        with tempfile.TemporaryDirectory() as folder:
            recorder = CallRecorder(Path(folder) / "calls.jsonl", prices,
                                    "claude-haiku-4-5-20251001", 2, 2, 1)
            recorder.logical("test", "act")
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "fixture", "ANTHROPIC_PACE": "0"}), \
                 patch("urllib.request.urlopen", return_value=Response(reply)):
                client = Claude(model="claude-haiku-4-5-20251001", recorder=recorder)
                self.assertEqual(client.json("test")["verdict"], "refer")
            snap = recorder.snapshot()
            self.assertEqual((snap["input_tokens"], snap["output_tokens"],
                              snap["cache_write_tokens"]), (90, 25, 5))
            self.assertGreater(snap["estimated_api_dollars"], 0)

    def test_budget_stops_before_transport(self):
        with tempfile.TemporaryDirectory() as folder:
            recorder = CallRecorder(Path(folder) / "calls.jsonl",
                                    {"gpt-6-luna": {"input_per_million": 10,
                                                    "output_per_million": 100}},
                                    "gpt-6-luna", 2, 2, .001)
            recorder.logical("test", "act")
            with patch.dict(os.environ, {"OPENAI_API_KEY": "fixture", "OPENAI_PACE": "0"}), \
                 patch("urllib.request.urlopen") as transport:
                client = OpenAI(model="gpt-6-luna", recorder=recorder)
                with self.assertRaises(BudgetStopped):
                    client.json("test")
                transport.assert_not_called()

    def test_resume_preserves_attempt_cap_and_token_totals(self):
        prices = {"gpt-6-luna": {"input_per_million": 1,
                                "output_per_million": 2}}
        with tempfile.TemporaryDirectory() as folder:
            journal = Path(folder) / "calls.jsonl"
            ledger = Path(folder) / "spending.json"
            first = CallRecorder(journal, prices, "gpt-6-luna", 2, 1, 1,
                                 ledger_path=ledger)
            first.logical("first", "act")
            aid = first.before_attempt({"messages": [{"content": "first"}],
                                        "max_tokens": 100})
            first.finish_attempt(aid, response={"model": "gpt-6-luna",
                "usage": {"prompt_tokens": 20, "completion_tokens": 10}}, status=200)
            prior = json.loads(ledger.read_text())["estimated_api_dollars"]
            resumed = CallRecorder(journal, prices, "gpt-6-luna", 2, 1, 1,
                                   prior_spend=prior, ledger_path=ledger)
            self.assertEqual(resumed.snapshot()["input_tokens"], 20)
            self.assertEqual(resumed.snapshot()["request_attempts"], 1)
            resumed.logical("second", "act")
            with self.assertRaises(BudgetStopped):
                resumed.before_attempt({"messages": [], "max_tokens": 100})

    def test_openai_cache_write_tokens_are_priced_once(self):
        with tempfile.TemporaryDirectory() as folder:
            recorder = CallRecorder(Path(folder) / "calls.jsonl",
                {"gpt-6-luna": {"input_per_million": 1,
                                "cached_input_per_million": .1,
                                "cache_write_per_million": 1.25,
                                "output_per_million": 2}}, "gpt-6-luna", 1, 1, 1)
            recorder.logical("prompt", "act")
            aid = recorder.before_attempt({"messages": [], "max_tokens": 100})
            recorder.finish_attempt(aid, response={"model": "gpt-6-luna",
                "usage": {"prompt_tokens": 100, "completion_tokens": 20,
                          "prompt_tokens_details": {"cached_tokens": 10,
                                                    "cache_write_tokens": 5}}}, status=200)
            expected = (85 + 1 + 6.25 + 40) / 1_000_000
            self.assertAlmostEqual(recorder.snapshot()["estimated_api_dollars"], expected)


class ReferralAndManifest(unittest.TestCase):
    def test_plan_verdict_shapes_preserve_referral_boundaries(self):
        class SequenceReviewer:
            model = "deterministic-verdict-fixture"
            def __init__(self, *replies):
                self.replies = list(replies)
            def json(self, prompt):
                return self.replies.pop(0)
        base = scenario()
        cases = [
            (SequenceReviewer({"verdict": "refer", "reason": "external judgment"}),
             "referred", "plan"),
            (SequenceReviewer({"verdict": "approve", "approved_targets": ["R1", "R2"],
                               "rest": "refer", "reason": "only routine work now"}),
             "approved", "partial"),
            (SequenceReviewer({"verdict": "approve_and_refer", "approved_targets": "all",
                               "reason": "conflicting stated end", "referral": "check the end"}),
             "approved", "end"),
            (SequenceReviewer({"verdict": "stop", "grave": True,
                               "reason": "grave act"},
                              {"approved_targets": [], "reason": "none safe"}),
             "stopped", "grave"),
            (SequenceReviewer({"verdict": "unknown", "reason": "bad format"}),
             "referred", "plan"),
        ]
        for reviewer, status, referral_kind in cases:
            with self.subTest(status=status, referral_kind=referral_kind):
                world, warrant, registry = build(base)
                gate = StudyGate("taa_obligations", world, warrant, registry, reviewer)
                plan = TimelineAgent(base).propose_plan(warrant, world.observe())
                reviewed = gate.submit_plan(plan)
                self.assertEqual(reviewed.status, status)
                self.assertTrue(any(r["kind"] == referral_kind for r in gate.referrals))
                self.assertEqual(gate.ledger.claims["C-U"].authority_status, "pending")
                self.assertFalse(gate.request("reroute_shipment", {"shipment_id": "U"})["ok"])

    def test_episode_checkpoint_keeps_each_completed_step(self):
        states = []
        from scripts.run_study import FixtureReviewer
        result = run_episode(scenario(), "expiring_obligations", FixtureReviewer(),
                             checkpoint=lambda state: states.append(state["step"]))
        self.assertEqual(states, list(range(0, scenario()["steps"] + 1)))
        self.assertEqual(result["status"], "complete")

    def test_dry_run_uses_no_client_or_network(self):
        with patch("urllib.request.urlopen") as transport:
            self.assertEqual(main(["--manifest", "studies/obligations-luna-smoke.json",
                                   "--provider", "openai", "--dry-run"]), 0)
            transport.assert_not_called()

    def test_paid_client_loads_harness_keys_before_construction(self):
        order = []

        class Client:
            def __init__(self, model, recorder):
                order.append("client")
                self.model = model

            def list_models(self):
                order.append("models")
                return ["gpt-6-luna"]

        with patch("run.load_keys", side_effect=lambda: order.append("load")), \
             patch("agents.openai_client.OpenAI", Client):
            self.assertEqual(paid_model("openai", "gpt-6-luna", None).model, "gpt-6-luna")
        self.assertEqual(order, ["load", "client", "models"])

    def test_judge_separates_substantive_referral_from_bad_format(self):
        world, warrant, _ = build(scenario())
        class Reviewer:
            def __init__(self, reply):
                self.reply = reply
            def json(self, prompt):
                return self.reply
        act = {"shipment_id": "R1"}
        approved, _, refs = judge_act("reroute_shipment", act, warrant, world,
                                      Reviewer({"verdict": "refer", "reason": "needs authority"}),
                                      allow_referral=True)
        self.assertFalse(approved)
        self.assertEqual(refs[0]["category"], "substantive")
        approved, _, refs = judge_act("reroute_shipment", act, warrant, world,
                                      Reviewer({"verdict": "possibly"}), allow_referral=True)
        self.assertFalse(approved)
        self.assertEqual(refs[0]["category"], "api_or_format_failure")

    def test_external_reply_triggers_new_review_not_automatic_plan_approval(self):
        class ReferringReviewer:
            model = "deterministic-refer-fixture"
            def __init__(self):
                self.calls = 0
            def json(self, prompt):
                self.calls += 1
                if self.calls == 1:
                    return {"verdict": "refer", "reason": "U needs the declared external answer"}
                return {"verdict": "approve", "reason": "external reply is now recorded",
                        "approved_targets": "all"}
        result = run_episode(scenario(), "taa_obligations", ReferringReviewer())
        plan_states = [e["decision"] for e in result["gate_log"] if e["tool"] == "(plan)"]
        self.assertEqual(plan_states[:2], ["REFERRED", "APPROVED"])
        self.assertFalse(any(e.get("shipment") == "U" and e["step"] < 4 for e in result["effects"]))


if __name__ == "__main__":
    unittest.main()
