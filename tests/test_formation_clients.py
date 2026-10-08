"""Free transport fixtures; no model acts as an experimental subject here."""
import ast
import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from agents.call_telemetry import BudgetStopped
from formation.checkpoint import TrialStore
from formation.clients import ClaudeChat, GeminiChat, GroqChat, OpenAIChat, ProviderError, ReplyError, list_gemini_models
from formation.limits import FreeTierLimiter, RatePaused
from formation.telemetry import FormationRecorder
from scripts.formation_connectivity import journal_spend, run

ROOT = Path(__file__).resolve().parents[1]


class Reply:
    headers = {"x-request-id": "fixture-id"}
    def __init__(self, data):
        self.data = data
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self):
        return json.dumps(self.data).encode()


class FormationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prices = json.loads((ROOT / "studies/provider-prices-2026-10-07.json").read_text())["models"]
        self.env = patch.dict(os.environ, {"OPENAI_API_KEY": "fixture-secret", "ANTHROPIC_API_KEY": "fixture-secret", "GEMINI_API_KEY": "fixture-secret", "GROQ_API_KEY": "fixture-secret"})
        self.env.start()
        self.history = [{"role": "user", "content": "first"}, {"role": "assistant", "content": '{"ok":true}'}, {"role": "user", "content": "last"}]

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def recorder(self, model="gpt-6-luna", **kwargs):
        return FormationRecorder(self.root / "calls.jsonl", self.prices, model, 10, 10, kwargs.pop("max_dollars", 8), **kwargs)

    def openai_reply(self, **kwargs):
        response = {"model": "gpt-6-luna", "id": "fixture", "usage": {"prompt_tokens": 100, "completion_tokens": 20}, "choices": [{"message": {"content": '{"ok":true}'}, "finish_reason": "stop"}]}
        response.update(kwargs)
        return response

    def test_openai_history_and_defaults(self):
        client = OpenAIChat("gpt-6-luna", self.recorder())
        with patch("urllib.request.urlopen", return_value=Reply(self.openai_reply())) as send:
            self.assertEqual(client.chat("system", self.history), {"ok": True})
        body = json.loads(send.call_args[0][0].data)
        self.assertEqual(body["messages"], [{"role": "system", "content": "system"}] + self.history)
        self.assertEqual(set(body), {"model", "messages", "max_completion_tokens"})
        evidence = (self.root / "calls.jsonl").read_text()
        self.assertNotIn("fixture-secret", evidence)
        self.assertIn("native_response", evidence)

    def test_haiku_thinking_blocks_and_defaults(self):
        model = "claude-haiku-5-5"
        client = ClaudeChat(model, self.recorder(model))
        response = {"model": model, "content": [{"type": "thinking", "thinking": "fixture"}, {"type": "text", "text": '{"ok":true}'}], "stop_reason": "end_turn", "usage": {"input_tokens": 100, "output_tokens": 20, "cache_read_input_tokens": 10, "cache_creation_input_tokens": 5}}
        with patch("urllib.request.urlopen", return_value=Reply(response)) as send:
            self.assertEqual(client.chat("system", self.history), {"ok": True})
        body = json.loads(send.call_args[0][0].data)
        self.assertEqual(set(body), {"model", "system", "messages", "max_tokens"})
        self.assertAlmostEqual(client.recorder.spent, (100*.1+20*.5+10*.01+5*.125)/1000000)

    def test_gemini_history_and_thinking_usage(self):
        model = "gemini-2.5-flash-lite"
        client = GeminiChat(model, self.recorder(model))
        response = {"modelVersion": model, "responseId": "google-fixture", "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 20, "thoughtsTokenCount": 30, "cachedContentTokenCount": 10}, "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "not output", "thought": True}, {"text": '{"ok":true}'}]}}]}
        with patch("urllib.request.urlopen", return_value=Reply(response)) as send:
            self.assertEqual(client.chat("system", self.history), {"ok": True})
        body = json.loads(send.call_args[0][0].data)
        self.assertEqual([m["role"] for m in body["contents"]], ["user", "model", "user"])
        self.assertEqual(body["systemInstruction"]["parts"][0]["text"], "system")
        self.assertNotIn("temperature", body["generationConfig"])
        self.assertAlmostEqual(client.recorder.spent, (90*.1+10*.01+50*.4)/1000000)
        self.assertEqual(client.recorder.output_tokens, 50)

    def test_full_system_input_budget_preflight(self):
        recorder = self.recorder(max_dollars=.0001)
        client = OpenAIChat("gpt-6-luna", recorder, max_output_tokens=1)
        with patch("urllib.request.urlopen") as send, self.assertRaises(BudgetStopped):
            client.chat("x" * 10000, self.history)
        send.assert_not_called()

    def test_short_context_price_boundary(self):
        recorder = self.recorder("claude-haiku-5-5")
        with self.assertRaises(BudgetStopped):
            recorder.before_attempt({"system": "x"*100001, "max_tokens": 1})

    def test_missing_usage_halts_next_call(self):
        client = OpenAIChat("gpt-6-luna", self.recorder())
        with patch("urllib.request.urlopen", return_value=Reply(self.openai_reply(usage={}))) as send:
            with self.assertRaises(BudgetStopped):
                client.json("neutral")
            with self.assertRaises(BudgetStopped):
                client.json("neutral")
        self.assertEqual(send.call_count, 1)

    def test_model_mismatch_preserves_raw_evidence(self):
        client = OpenAIChat("gpt-6-luna", self.recorder())
        with patch("urllib.request.urlopen", return_value=Reply(self.openai_reply(model="wrong-model"))), self.assertRaises(BudgetStopped):
            client.json("neutral")
        self.assertIn("wrong-model", (self.root/"calls.jsonl").read_text())

    def test_missing_identity_stops(self):
        client = OpenAIChat("gpt-6-luna", self.recorder())
        with patch("urllib.request.urlopen", return_value=Reply(self.openai_reply(model=None))), self.assertRaises(BudgetStopped):
            client.json("neutral")

    def test_reply_error_categories(self):
        for content, stop, label in [("", "stop", "silent_reply"), ("hello", "stop", "malformed_reply"), ('{"ok":true}', "length", "unfinished_reply"), ("no", "refusal", "provider_refusal")]:
            client = OpenAIChat("gpt-6-luna", self.recorder())
            response = self.openai_reply(choices=[{"message": {"content": content}, "finish_reason": stop}])
            with patch("urllib.request.urlopen", return_value=Reply(response)), self.assertRaises(ReplyError) as caught:
                client.json("neutral")
            self.assertEqual(caught.exception.label, label)

    def test_transport_error_keeps_reserve_and_no_retry(self):
        client = OpenAIChat("gpt-6-luna", self.recorder())
        with patch("urllib.request.urlopen", side_effect=TimeoutError("fixture-secret")) as send, self.assertRaises(ProviderError):
            client.json("neutral")
        self.assertEqual(send.call_count, 1)
        self.assertGreater(client.recorder.spent, 0)
        self.assertNotIn("fixture-secret", (self.root / "calls.jsonl").read_text())
        self.assertAlmostEqual(journal_spend(self.root / "calls.jsonl"), client.recorder.spent)

    def test_rate_pause_persisted(self):
        model = "qwen/qwen3.8-27b"
        limiter = FreeTierLimiter(self.root/"rate.json", sleep=lambda _: None)
        client = GroqChat(model, self.recorder(model), max_output_tokens=4096, limiter=limiter, free_tier_confirmed=True)
        error = urllib.error.HTTPError("https://api.groq.com", 429, "rate", {"retry-after": "3600"}, io.BytesIO())
        with patch("urllib.request.urlopen", side_effect=error) as send, self.assertRaises(RatePaused):
            client.json("neutral")
        self.assertEqual(send.call_count, 1)
        with self.assertRaises(RatePaused):
            FreeTierLimiter(self.root/"rate.json").before(10)

    def test_groq_application_identity_and_neutral_response(self):
        model = "qwen/qwen3.8-27b"
        client = GroqChat(model, self.recorder(model), max_output_tokens=4096,
                          limiter=FreeTierLimiter(self.root / "rate.json"),
                          free_tier_confirmed=True)
        response = self.openai_reply(model=model)
        with patch("urllib.request.urlopen", return_value=Reply(response)) as send:
            self.assertEqual(client.json("neutral"), {"ok": True})
        request = send.call_args[0][0]
        self.assertEqual(request.get_header("User-agent"),
                         "TAA-Lab/0.21.2 (Python standard-library API client)")
        self.assertEqual(send.call_count, 1)
        self.assertEqual(client.recorder.spent, 0)
        self.assertNotIn("fixture-secret", (self.root / "calls.jsonl").read_text())

    def test_free_groq_guard(self):
        with self.assertRaises(ValueError):
            GroqChat("qwen/qwen3.8-27b", self.recorder("qwen/qwen3.8-27b"))

    def test_daily_resume_and_minute_tokens(self):
        clock = [100000]
        limiter = FreeTierLimiter(self.root / "rate.json", now=lambda: clock[0], sleep=lambda _: None)
        limiter.before(5000)
        with self.assertRaises(RatePaused):
            limiter.before(5000)
        clock[0] += 61
        limiter.before(5000)
        limiter._save({"events": [[clock[0], 200] for _ in range(1000)]})
        with self.assertRaises(RatePaused):
            limiter.before(10)
        clock[0] += 86401
        limiter.before(10)

    def test_account_daily_limit_header(self):
        limiter = FreeTierLimiter(self.root/"rate.json")
        limiter.observe({"x-ratelimit-remaining-requests": "0", "x-ratelimit-reset-requests": "2h30m"})
        with self.assertRaises(RatePaused):
            FreeTierLimiter(self.root/"rate.json").before(10)

    def test_provider_budget_shared_across_haiku_models(self):
        ledger = self.root / "claude-ledger.json"
        first = self.recorder("claude-haiku-4-5-20251001", ledger_path=ledger, max_dollars=.01)
        first.logical("fixture", "neutral")
        aid = first.before_attempt({"messages": [{"role": "user", "content": "neutral"}], "max_tokens": 1000})
        first.finish_attempt(aid, response={"model": first.model, "usage": {"input_tokens": 100, "output_tokens": 1000}})
        prior = json.loads(ledger.read_text())["estimated_api_dollars"]
        second = FormationRecorder(self.root/"second.jsonl", self.prices, "claude-haiku-5-5", 10, 10, .006, prior_spend=prior, ledger_path=ledger)
        with self.assertRaises(BudgetStopped):
            second.before_attempt({"system": "neutral", "max_tokens": 8192})

    def test_settled_and_interrupted_journal_spending(self):
        recorder = self.recorder()
        recorder.logical("fixture", "neutral")
        first = recorder.before_attempt({"messages": [], "max_tokens": 8192})
        recorder.finish_native(first, self.openai_reply(), "openai")
        recorder.before_attempt({"messages": [], "max_tokens": 8192})
        self.assertAlmostEqual(journal_spend(self.root/"calls.jsonl"), recorder.spent)

    def test_connectivity_completed_resume_has_no_requests(self):
        manifest = json.loads((ROOT/"studies/formation-connectivity-v021.json").read_text())
        output = self.root/"output"
        from scripts.formation_connectivity import fingerprint
        digest = fingerprint()[0]
        store = TrialStore(output/"progress.jsonl", digest)
        for item in manifest["models"]:
            store.mark(item["model"], "complete")
        with patch("scripts.formation_connectivity.ROOT", self.root), patch("scripts.formation_connectivity.fingerprint", return_value=(digest, {})), patch("scripts.formation_connectivity.load_keys"), patch("urllib.request.urlopen") as send:
            run(manifest, self.prices, output)
        send.assert_not_called()

    def test_trial_resume_never_repeats_complete_or_uncertain(self):
        path = self.root / "progress.jsonl"
        store = TrialStore(path, "fingerprint")
        store.mark("a", "complete")
        store.mark("b", "rate_paused")
        store.mark("c", "inflight")
        resumed = TrialStore(path, "fingerprint")
        self.assertFalse(resumed.should_run("a"))
        self.assertTrue(resumed.should_run("b"))
        with self.assertRaises(RuntimeError):
            resumed.should_run("c")
        with self.assertRaises(ValueError):
            TrialStore(path, "changed")

    def test_missing_key_no_network(self):
        with patch.dict(os.environ, {}, clear=True), patch("urllib.request.urlopen") as send, self.assertRaises(ProviderError):
            OpenAIChat("gpt-6-luna", self.recorder()).json("neutral")
        send.assert_not_called()

    def test_history_validation_no_network(self):
        with patch("urllib.request.urlopen") as send, self.assertRaises(ValueError):
            OpenAIChat("gpt-6-luna", self.recorder()).chat("system", self.history[:-1])
        send.assert_not_called()

    def test_gemini_metadata_pagination(self):
        pages = [Reply({"models": [{"name": "models/a", "supportedGenerationMethods": ["generateContent"]}], "nextPageToken": "page2"}), Reply({"models": [{"name": "models/b", "supportedGenerationMethods": ["generateContent"]}]})]
        with patch("urllib.request.urlopen", side_effect=pages) as send:
            self.assertEqual(len(list_gemini_models()), 2)
        self.assertIn("pageToken=page2", send.call_args[0][0].full_url)
        self.assertNotIn("fixture-secret", send.call_args[0][0].full_url)

    def test_python39_syntax(self):
        for path in list((ROOT/"formation").glob("*.py")) + [ROOT/"scripts/formation_connectivity.py"]:
            ast.parse(path.read_text(), feature_version=(3, 9))


class ConnectivityManifestTests(unittest.TestCase):
    def test_selected_manifest_prices_are_fingerprinted(self):
        from scripts.formation_connectivity import fingerprint
        path = ROOT / "studies/formation-connectivity-gemini31-v021.json"
        manifest = json.loads(path.read_text())
        digest, hashes = fingerprint(manifest, path)
        self.assertIn("studies/provider-prices-2026-10-08.json", hashes)
        self.assertNotIn("studies/provider-prices-2026-10-07.json", hashes)
        changed = dict(manifest, batch_estimated_stop_dollars=.02)
        self.assertNotEqual(digest, fingerprint(changed, path)[0])

    def test_effective_output_change_rejects_resume(self):
        from scripts.formation_connectivity import fingerprint
        path = ROOT / "studies/formation-connectivity-gemini31-v021.json"
        manifest = json.loads(path.read_text())
        with tempfile.TemporaryDirectory() as folder:
            progress = Path(folder) / "progress.jsonl"
            TrialStore(progress, fingerprint(manifest, path)[0])
            changed = dict(manifest, output_dir="results/different")
            with self.assertRaises(ValueError):
                TrialStore(progress, fingerprint(changed, path)[0])
