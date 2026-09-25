"""A minimal OpenAI (GPT) API client using only the Python standard library.

Reads the key from the OPENAI_API_KEY environment variable. The key is never written
to disk or to the logs. Set OPENAI_MODEL to choose a model; otherwise the cheapest small
chat model currently available (a "nano" or "mini" tier GPT model) is chosen automatically.
"""
import json
import os
import random
import time
import urllib.error
import urllib.request

from agents.gemini_client import ModelUnavailable, parse_first_json

API = "https://api.openai.com/v1"

CHEAP_TIERS = ("nano", "mini")     # cheapest first
NOT_A_CHAT_MODEL = ("embedding", "whisper", "tts", "dall-e", "dalle", "moderation",
                     "transcribe", "audio", "image", "realtime", "instruct",
                     "davinci", "babbage", "ada", "search")


def choose_model(models):
    """Pick the cheapest small current GPT chat model from a list of model ids.
    /v1/models lists every kind of model the key can use, not just chat models, and
    without a promised order, so this filters by name rather than trusting position 0."""
    chat = [m for m in models if m.startswith("gpt-") and not any(x in m for x in NOT_A_CHAT_MODEL)]
    for tier in CHEAP_TIERS:
        for m in chat:
            if tier in m:
                return m
    if not chat:
        raise SystemExit("Your key can see no GPT chat models. Check billing at platform.openai.com.")
    return chat[0]


class OpenAI:
    def __init__(self, model=None):
        self.key = os.environ.get("OPENAI_API_KEY")
        if not self.key:
            raise SystemExit("Set OPENAI_API_KEY first (see README).")
        self.calls = 0
        self.pace = float(os.environ.get("OPENAI_PACE", "1.3"))
        self._last = 0.0
        self.model = model or os.environ.get("OPENAI_MODEL") or self._pick_model()

    def _headers(self):
        return {"Content-Type": "application/json", "Authorization": f"Bearer {self.key}"}

    def list_models(self):
        req = urllib.request.Request(f"{API}/models", headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise SystemExit(f"OpenAI API error {e.code}: {e.read().decode(errors='replace')[:600]}") from None
        return [m["id"] for m in data.get("data", [])]

    def _pick_model(self):
        picked = choose_model(self.list_models())
        print(f"  using {picked} (set OPENAI_MODEL to choose another)", flush=True)
        return picked

    def _post(self, url, body):
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=self._headers())
        waits = [5, 10, 20, 40, 60]
        for attempt in range(len(waits) + 1):
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:1500]
                if e.code == 429 and self._error_code(detail) == "insufficient_quota":
                    raise SystemExit("Your API account has no credit. Add credits at "
                                      f"platform.openai.com/settings/organization/billing.\n{detail}") from None
                if e.code in (429, 500, 502, 503, 504):
                    if attempt < len(waits):
                        wait = waits[attempt] + random.uniform(0, 3)
                        print(f"  OpenAI busy ({e.code}); waiting {wait:.0f}s and retrying...", flush=True)
                        time.sleep(wait)
                        continue
                    raise ModelUnavailable(f"{e.code} after {len(waits)} retries") from None
                if e.code in (401, 403):
                    raise SystemExit(f"OpenAI rejected the key ({e.code}). Check OPENAI_API_KEY.\n{detail}") from None
                if e.code == 404:
                    raise SystemExit(f"Model '{self.model}' not found. Run: python3 run.py --list-models --provider openai\n{detail}") from None
                raise RuntimeError(f"OpenAI API error {e.code}: {detail}") from None

    @staticmethod
    def _error_code(detail):
        try:
            return json.loads(detail).get("error", {}).get("code", "")
        except (json.JSONDecodeError, AttributeError):
            return ""

    def json(self, prompt):
        """Send a prompt and return the model's reply parsed as JSON."""
        self.calls += 1
        gap = time.time() - self._last
        if gap < self.pace:
            time.sleep(self.pace - gap)
        self._last = time.time()
        print(f"  call {self.calls} to {self.model}", flush=True)
        body = {"model": self.model, "max_completion_tokens": 800, "temperature": 0.2,
                "messages": [{"role": "user", "content": prompt + "\n\nReply with a single JSON object and nothing else."}]}
        out = self._post(f"{API}/chat/completions", body)
        text = out["choices"][0]["message"]["content"] or ""
        return parse_first_json(text)
