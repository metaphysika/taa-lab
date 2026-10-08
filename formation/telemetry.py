"""Native provider evidence using the frozen CallRecorder event format."""
import json
from agents.call_telemetry import CallRecorder, BudgetStopped


class FormationRecorder(CallRecorder):
    def _restore_journal(self):
        super()._restore_journal()
        for line in self.path.read_text().splitlines():
            event = json.loads(line)
            if event.get("event") == "identity_missing" or event.get("model_mismatch"):
                self.missing_usage = True

    def before_attempt(self, body):
        # Include system instructions and Gemini contents in the reserve. A byte
        # per token is deliberately more conservative than the old /3 estimate.
        encoded = json.dumps(body, ensure_ascii=False).encode()
        price = self.prices[self.model]
        threshold = price.get("long_context_threshold")
        if threshold and len(encoded) > threshold:
            raise BudgetStopped("short-context price ceiling exceeded; estimate a new manifest")
        normalized = {"messages": ["x" * (len(encoded) * 3)],
                      "max_tokens": body.get("max_tokens", body.get("max_completion_tokens",
                          body.get("generationConfig", {}).get("maxOutputTokens")))}
        aid = super().before_attempt(normalized)
        self._write({"event": "native_request", "id": aid, "body": body})
        return aid

    def finish_native(self, aid, response, provider, status=200):
        # Preserve the native response before normalization or validation can fail.
        self._write({"event": "native_response", "id": aid, "response": response})
        normalized = dict(response)
        if provider == "google":
            usage = response.get("usageMetadata") or {}
            normalized["usage"] = {}
            if "promptTokenCount" in usage and "candidatesTokenCount" in usage:
                normalized["usage"] = {
                    "prompt_tokens": usage["promptTokenCount"],
                    "completion_tokens": usage["candidatesTokenCount"] + usage.get("thoughtsTokenCount", 0),
                    "prompt_tokens_details": {"cached_tokens": usage.get("cachedContentTokenCount", 0)}}
            normalized["id"] = response.get("responseId")
            returned = response.get("modelVersion")
            normalized["model"] = returned
            normalized["stop_reason"] = ((response.get("candidates") or [{}])[0]).get("finishReason")
        returned = normalized.get("model")
        # Alias resolution is allowed only when enumerated in the dated price file.
        if returned in self.prices[self.model].get("accepted_response_models", []):
            normalized["model"] = self.model
        super().finish_attempt(aid, response=normalized, status=status)
        if self.missing_usage:
            raise BudgetStopped("response usage missing; stop and inspect evidence")
        if not returned:
            self.missing_usage = True
            self._write({"event": "identity_missing", "id": aid})
            raise BudgetStopped("response has no model identity; inspect evidence")
