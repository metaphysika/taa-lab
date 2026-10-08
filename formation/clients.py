"""Pinned, multi-turn clients. No sampling, effort, or thinking overrides.

These classes do not alter the historical json clients. Each generation request
has one attempt; errors remain evidence and never trigger an invisible retry.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from agents.gemini_client import parse_first_json
from formation.limits import RatePaused


class ProviderError(RuntimeError):
    pass


class ReplyError(ValueError):
    def __init__(self, label):
        self.label = label
        super().__init__(label)


class ChatClient:
    def __init__(self, model, recorder, max_output_tokens=8192, limiter=None):
        if not model or recorder.model != model:
            raise ValueError("explicit model must match the recorder")
        if not isinstance(max_output_tokens, int) or max_output_tokens < 1:
            raise ValueError("positive output ceiling required")
        self.model, self.recorder = model, recorder
        self.max_output_tokens, self.limiter = max_output_tokens, limiter
        self.calls = 0

    def _key(self):
        key = os.environ.get(self.key_name)
        if not key:
            raise ProviderError("Set %s in keys.env yourself" % self.key_name)
        return key

    def json(self, prompt):
        return self.chat("", [{"role": "user", "content": prompt}])

    def chat(self, system, messages):
        if not isinstance(system, str) or not messages or messages[-1].get("role") != "user":
            raise ValueError("system text and a history ending with user are required")
        for message in messages:
            if message.get("role") not in ("user", "assistant") or not isinstance(message.get("content"), str):
                raise ValueError("history needs user/assistant text messages")
        body = self.body(system, messages)
        key = self._key()  # validate locally before a logical call or rate allowance
        if self.limiter:
            self.limiter.before(len(json.dumps(body).encode()) + self.max_output_tokens)
        self.recorder.logical(json.dumps({"system": system, "messages": messages}), "formation chat")
        self.calls += 1
        aid = self.recorder.before_attempt(body)
        request = urllib.request.Request(self.url, data=json.dumps(body).encode(), headers=self.headers(key))
        try:
            with urllib.request.urlopen(request, timeout=120) as reply:
                response = json.loads(reply.read())
                safe_headers = {k.lower(): v for k, v in reply.headers.items()
                                if k.lower().startswith("x-ratelimit-") or k.lower() in ("retry-after", "request-id", "x-request-id")}
        except urllib.error.HTTPError as error:
            safe_headers = {k.lower(): v for k, v in error.headers.items()
                            if k.lower().startswith("x-ratelimit-") or k.lower() == "retry-after"}
            self.recorder._write({"event": "response_headers", "id": aid, "headers": safe_headers})
            self.recorder.finish_attempt(aid, error="HTTP %s" % error.code, status=error.code)
            if error.code == 429:
                try:
                    wait = float(error.headers.get("retry-after", 86400))
                except (TypeError, ValueError):
                    wait = 86400
                if self.limiter:
                    self.limiter.pause(wait)
                raise RatePaused("HTTP 429; no retry made; resume after rate reset") from None
            # Never include provider error bodies, which can echo request credentials.
            raise ProviderError("HTTP %s; no retry made" % error.code) from None
        except Exception as error:
            self.recorder.finish_attempt(aid, error=type(error).__name__)
            raise ProviderError("%s; request outcome uncertain; inspect journal before retry" % type(error).__name__) from None
        self.recorder._write({"event": "response_headers", "id": aid, "headers": safe_headers})
        self.recorder.finish_native(aid, response, self.provider)
        if self.limiter:
            self.limiter.observe(safe_headers)
        text, stop = self.extract(response)
        label = None
        if stop in ("max_tokens", "length", "MAX_TOKENS"):
            label = "unfinished_reply"
        elif stop in ("refusal", "SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT") or self.refused(response):
            label = "provider_refusal"
        elif not text.strip():
            label = "silent_reply"
        if label:
            self.recorder.raw_reply(text, error=label)
            raise ReplyError(label)
        try:
            parsed = parse_first_json(text)
        except ValueError:
            self.recorder.raw_reply(text, error="malformed_reply")
            raise ReplyError("malformed_reply") from None
        self.recorder.raw_reply(text, parsed=parsed)
        return parsed

    def refused(self, response):
        return False


class OpenAIChat(ChatClient):
    provider = "openai"

    def __init__(self, model, recorder, base_url="https://api.openai.com/v1", key_name="OPENAI_API_KEY", **kwargs):
        super().__init__(model, recorder, **kwargs)
        self.key_name = key_name
        self.url = base_url.rstrip("/") + "/chat/completions"
        if not base_url.startswith("https://"):
            raise ValueError("API endpoint must use HTTPS")

    def headers(self, key):
        return {"Content-Type": "application/json", "Authorization": "Bearer " + key}

    def body(self, system, messages):
        history = ([{"role": "system", "content": system}] if system else []) + messages
        return {"model": self.model, "messages": history, "max_completion_tokens": self.max_output_tokens}

    def extract(self, response):
        choice = (response.get("choices") or [{}])[0]
        return choice.get("message", {}).get("content") or "", choice.get("finish_reason")

    def refused(self, response):
        return bool((response.get("choices") or [{}])[0].get("message", {}).get("refusal"))


class GroqChat(OpenAIChat):
    provider = "groq"

    def __init__(self, model, recorder, free_tier_confirmed=False, **kwargs):
        if model != "qwen/qwen3.8-27b" or not free_tier_confirmed or not kwargs.get("limiter"):
            raise ValueError("confirmed free Qwen model and persistent rate limiter required")
        super().__init__(model, recorder, base_url="https://api.groq.com/openai/v1",
                         key_name="GROQ_API_KEY", **kwargs)


class ClaudeChat(ChatClient):
    provider = "claude"
    key_name = "ANTHROPIC_API_KEY"
    url = "https://api.anthropic.com/v1/messages"

    def headers(self, key):
        return {"Content-Type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"}

    def body(self, system, messages):
        return {"model": self.model, "system": system, "messages": messages, "max_tokens": self.max_output_tokens}

    def extract(self, response):
        return "".join(b.get("text", "") for b in response.get("content", []) if b.get("type") == "text"), response.get("stop_reason")


class GeminiChat(ChatClient):
    provider = "google"
    key_name = "GEMINI_API_KEY"

    def __init__(self, model, recorder, **kwargs):
        super().__init__(model, recorder, **kwargs)
        self.url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % model

    def headers(self, key):
        return {"Content-Type": "application/json", "x-goog-api-key": key}

    def body(self, system, messages):
        return {"systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in messages],
                "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": self.max_output_tokens}}

    def extract(self, response):
        candidate = (response.get("candidates") or [{}])[0]
        text = "".join(p.get("text", "") for p in candidate.get("content", {}).get("parts", []) if not p.get("thought"))
        return text, candidate.get("finishReason")

    def refused(self, response):
        return bool(response.get("promptFeedback", {}).get("blockReason"))


def list_gemini_models():
    """Metadata only. No generation, no key in URLs or returned evidence."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ProviderError("Set GEMINI_API_KEY in keys.env yourself")
    models, token = [], None
    while True:
        query = {"pageSize": 200}
        if token:
            query["pageToken"] = token
        request = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models?" + urllib.parse.urlencode(query), headers={"x-goog-api-key": key})
        try:
            with urllib.request.urlopen(request, timeout=60) as reply:
                data = json.loads(reply.read())
        except Exception as error:
            raise ProviderError("Gemini metadata listing failed (%s); no generation made" % type(error).__name__) from None
        models.extend(m for m in data.get("models", []) if "generateContent" in m.get("supportedGenerationMethods", []))
        token = data.get("nextPageToken")
        if not token:
            return models
