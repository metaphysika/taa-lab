"""A minimal Gemini client using only the Python standard library.

Reads the key from the GEMINI_API_KEY environment variable. The key is never written
to disk or to the logs. Set GEMINI_MODEL to choose a model (default below).
"""
import json
import os
import random
import time
import urllib.error
import urllib.request

API = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-3.8-flash"


class ModelUnavailable(Exception):
    """Google kept answering 'busy' after several retries."""


class Gemini:
    def __init__(self, model=None):
        self.key = os.environ.get("GEMINI_API_KEY")
        if not self.key:
            raise SystemExit("Set GEMINI_API_KEY first (see README).")
        self.model = model or os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
        self.calls = 0
        # Seconds to wait between calls, to stay under free-tier per-minute limits.
        self.pace = float(os.environ.get("GEMINI_PACE", "6"))
        self._last = 0.0
        self._shown_429 = False

    def _post(self, url, body):
        req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json",
                                              "x-goog-api-key": self.key})
        waits = [5, 10, 20, 40, 60]          # about two and a half minutes in total
        for attempt in range(len(waits) + 1):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:1500]
                if e.code == 429 and not self._shown_429:
                    self._shown_429 = True
                    print("  Google's rate-limit message (shown once):\n  " + detail.replace("\n", "\n  "), flush=True)
                if e.code in (429, 500, 503, 504):
                    if attempt < len(waits):
                        wait = waits[attempt] + random.uniform(0, 3)
                        print(f"  Gemini busy ({e.code}); waiting {wait:.0f}s and retrying...", flush=True)
                        time.sleep(wait)
                        continue
                    raise ModelUnavailable(f"{e.code} after {len(waits)} retries") from None
                if e.code == 404:
                    raise SystemExit(f"Model '{self.model}' is not available to your key.\n"
                                     f"Run: python3 run.py --list-models\n"
                                     f"then: export GEMINI_MODEL=\"<a name from that list>\"\n\nGoogle said: {detail}") from None
                raise RuntimeError(f"Gemini API error {e.code}: {detail}") from None

    def json(self, prompt):
        """Send a prompt and return the model's reply parsed as JSON."""
        self.calls += 1
        gap = time.time() - self._last
        if gap < self.pace:
            time.sleep(self.pace - gap)
        self._last = time.time()
        print(f"  call {self.calls} to {self.model}", flush=True)
        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}}
        out = self._post(f"{API}/models/{self.model}:generateContent", body)
        text = out["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)

    def list_models(self):
        req = urllib.request.Request(f"{API}/models?pageSize=200", headers={"x-goog-api-key": self.key})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
        return [m["name"].split("/", 1)[1] for m in data.get("models", [])
                if "generateContent" in m.get("supportedGenerationMethods", [])]
