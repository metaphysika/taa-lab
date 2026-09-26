"""A minimal Anthropic (Claude) API client using only the Python standard library.

Reads the key from the ANTHROPIC_API_KEY environment variable. The key is never written
to disk or to the logs. Set ANTHROPIC_MODEL to choose a model; otherwise the newest
available Haiku model (the cheapest tier) is chosen automatically.
"""
import json
import os
import random
import re
import time
import urllib.error
import urllib.request

from agents.gemini_client import ModelUnavailable, parse_first_json

API = "https://api.anthropic.com/v1"
# v0.15.1: reviewer replies grew in v0.13 (premises, scope lists). A reply cut off at the limit
# can't be parsed and would be scored as an unanswered referral, a harness fault posing as a
# reviewer's. Only tokens actually used are billed, so a generous ceiling costs nothing extra.
TOKEN_BUDGET = 2000
HEADERS = {"anthropic-version": "2023-06-01", "content-type": "application/json"}


class Claude:
    def __init__(self, model=None):
        self.key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.key:
            raise SystemExit("Set ANTHROPIC_API_KEY first (see README).")
        self.calls = 0
        self.pace = float(os.environ.get("ANTHROPIC_PACE", "1.3"))
        self._last = 0.0
        self.model = model or os.environ.get("ANTHROPIC_MODEL") or self._pick_model()

    def _headers(self):
        return {**HEADERS, "x-api-key": self.key}

    def list_models(self):
        req = urllib.request.Request(f"{API}/models?limit=100", headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise SystemExit(f"Anthropic API error {e.code}: {e.read().decode(errors='replace')[:600]}") from None
        return [m["id"] for m in data.get("data", [])]

    def _pick_model(self):
        models = self.list_models()           # returned newest first
        for tier in ("haiku", "sonnet"):
            for m in models:
                if tier in m:
                    print(f"  using {m} (set ANTHROPIC_MODEL to choose another)", flush=True)
                    return m
        if not models:
            raise SystemExit("Your key can see no models. Check billing in the Claude Console.")
        return models[0]

    def _post(self, url, body):
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=self._headers())
        waits = [5, 10, 20, 40, 60]
        for attempt in range(len(waits) + 1):
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:1500]
                if e.code in (429, 500, 503, 529):
                    if attempt < len(waits):
                        wait = waits[attempt] + random.uniform(0, 3)
                        print(f"  Claude busy ({e.code}); waiting {wait:.0f}s and retrying...", flush=True)
                        time.sleep(wait)
                        continue
                    raise ModelUnavailable(f"{e.code} after {len(waits)} retries") from None
                if e.code in (401, 403):
                    raise SystemExit(f"Anthropic rejected the key ({e.code}). Check ANTHROPIC_API_KEY.\n{detail}") from None
                if e.code == 400 and "credit" in detail.lower():
                    raise SystemExit(f"Your API account has no credit. Add credits in the Claude Console.\n{detail}") from None
                if e.code == 404:
                    raise SystemExit(f"Model '{self.model}' not found. Run: python3 run.py --list-models --provider claude\n{detail}") from None
                raise RuntimeError(f"Anthropic API error {e.code}: {detail}") from None

    def json(self, prompt):
        """Send a prompt and return the model's reply parsed as JSON."""
        self.calls += 1
        gap = time.time() - self._last
        if gap < self.pace:
            time.sleep(self.pace - gap)
        self._last = time.time()
        print(f"  call {self.calls} to {self.model}", flush=True)
        body = {"model": self.model, "max_tokens": TOKEN_BUDGET, "temperature": 0.2,
                "messages": [{"role": "user", "content": prompt + "\n\nReply with a single JSON object and nothing else."}]}
        out = self._post(f"{API}/messages", body)
        if out.get("stop_reason") == "max_tokens":
            print(f"  warning: {self.model}'s reply hit the {TOKEN_BUDGET}-token limit and may be cut off", flush=True)
        text = "".join(b.get("text", "") for b in out.get("content", []) if b.get("type") == "text")
        return parse_first_json(text)
