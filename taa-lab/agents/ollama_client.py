"""A minimal client for a model running on your own computer with Ollama (free, offline).

Install Ollama from https://ollama.com, download a model (for example `ollama pull <name>`),
and leave Ollama running. Set OLLAMA_MODEL to the model's name; otherwise the first installed
model is used. Set OLLAMA_HOST if Ollama runs somewhere other than this computer.
Nothing leaves your machine.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

from agents.gemini_client import ModelUnavailable


class Ollama:
    def __init__(self, model=None):
        self.host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        if not self.host.startswith("http"):
            self.host = "http://" + self.host
        self.calls = 0
        self.model = model or os.environ.get("OLLAMA_MODEL") or self._pick_model()

    def _get(self, path):
        try:
            with urllib.request.urlopen(self.host + path, timeout=30) as r:
                return json.loads(r.read())
        except (urllib.error.URLError, ConnectionError):
            raise SystemExit(f"Cannot reach Ollama at {self.host}. Is the Ollama app running?") from None

    def list_models(self):
        return [m["name"] for m in self._get("/api/tags").get("models", [])]

    def _pick_model(self):
        models = self.list_models()
        if not models:
            raise SystemExit("Ollama has no models yet. Download one first, for example: ollama pull <model-name>")
        print(f"  using {models[0]} (set OLLAMA_MODEL to choose another)", flush=True)
        return models[0]

    def json(self, prompt):
        """Send a prompt and return the model's reply parsed as JSON."""
        self.calls += 1
        print(f"  call {self.calls} to {self.model} (local)", flush=True)
        body = {"model": self.model, "stream": False, "format": "json",
                "options": {"temperature": 0.2},
                "messages": [{"role": "user", "content": prompt + "\n\nReply with a single JSON object and nothing else."}]}
        req = urllib.request.Request(self.host + "/api/chat", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=600) as r:   # large local models can be slow
                    out = json.loads(r.read())
                break
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:600]
                if e.code == 404:
                    raise SystemExit(f"Ollama has no model named '{self.model}'. Run: ollama pull {self.model}\n{detail}") from None
                if attempt == 2:
                    raise ModelUnavailable(f"Ollama error {e.code}: {detail}") from None
                time.sleep(5)
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if attempt == 2:
                    raise ModelUnavailable(f"Ollama not responding: {e}") from None
                time.sleep(5)
        text = out.get("message", {}).get("content", "")
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise ValueError(f"model did not return JSON: {text[:200]}")
        return json.loads(match.group(0))
