"""Incremental provider evidence and conservative application spending stops.

The journal contains prompts and replies, never credentials or request headers.
An application-side estimate is not a guaranteed provider billing limit.
"""
import hashlib
import json
import math
import time
from pathlib import Path


class BudgetStopped(RuntimeError):
    pass


class CallRecorder:
    def __init__(self, journal_path, prices, model, max_logical, max_attempts, max_dollars,
                 prior_spend=0.0, ledger_path=None):
        self.path = Path(journal_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.prices = prices
        self.model = model
        self.max_logical = max_logical
        self.max_attempts = max_attempts
        self.max_dollars = max_dollars
        self.spent = prior_spend
        self.logical_count = 0
        self.attempt_count = 0
        self.context = {}
        self.logical_id = None
        self.missing_usage = False
        self.input_tokens = 0
        self.output_tokens = 0
        self.cached_input_tokens = 0
        self.cache_write_tokens = 0
        self._reserves = {}
        self.ledger_path = Path(ledger_path) if ledger_path else None
        if self.path.exists():
            self._restore_journal()

    def _restore_journal(self):
        """Keep call caps and token totals across a same-manifest resume."""
        for line in self.path.read_text().splitlines():
            event = json.loads(line)
            if event.get("event") == "logical_start":
                self.logical_count += 1
                self.logical_id = event["id"]
            elif event.get("event") == "attempt_start":
                self.attempt_count += 1
            elif event.get("event") == "attempt_end":
                usage = event.get("usage") or {}
                if event.get("usage_missing"):
                    self.missing_usage = True
                if "prompt_tokens" in usage:
                    self.input_tokens += usage["prompt_tokens"]
                    self.output_tokens += usage.get("completion_tokens", 0)
                    details = usage.get("prompt_tokens_details") or {}
                    self.cached_input_tokens += details.get("cached_tokens", 0)
                    self.cache_write_tokens += details.get("cache_write_tokens", 0)
                elif "input_tokens" in usage:
                    self.input_tokens += usage["input_tokens"]
                    self.output_tokens += usage.get("output_tokens", 0)
                    self.cached_input_tokens += usage.get("cache_read_input_tokens", 0)
                    self.cache_write_tokens += usage.get("cache_creation_input_tokens", 0)

    def _write(self, record):
        with self.path.open("a") as out:
            out.write(json.dumps(record, sort_keys=True, default=str) + "\n")
            out.flush()

    def logical(self, prompt, kind):
        if self.logical_count >= self.max_logical:
            raise BudgetStopped("logical reviewer-call cap reached")
        if self.missing_usage:
            raise BudgetStopped("a response lacked usage; inspect the journal before expanding")
        self.logical_count += 1
        self.logical_id = f"L{self.logical_count:06d}"
        self._write({"event": "logical_start", "id": self.logical_id, "kind": kind,
                     "model_requested": self.model, "context": dict(self.context),
                     "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                     "prompt": prompt})
        return self.logical_id

    def before_attempt(self, body):
        if self.missing_usage:
            raise BudgetStopped("provider usage missing; no further paid requests")
        if self.attempt_count >= self.max_attempts:
            raise BudgetStopped("provider request-attempt cap reached")
        price = self.prices.get(self.model)
        if not price:
            raise BudgetStopped(f"no dated price configuration for {self.model}")
        # Conservative preflight approximation. The full supplied completion allowance is
        # reserved; actual reported usage settles it afterward. A timeout keeps its reserve.
        prompt_bytes = len(json.dumps(body.get("messages", []), ensure_ascii=False).encode())
        input_reserve = math.ceil(prompt_bytes / 3)
        output_reserve = body.get("max_completion_tokens", body.get("max_tokens"))
        if not isinstance(output_reserve, int) or output_reserve < 1:
            raise BudgetStopped("request has no usable completion ceiling")
        reserve = (input_reserve * price["input_per_million"]
                   + output_reserve * price["output_per_million"]) / 1_000_000
        if self.spent + reserve > self.max_dollars:
            raise BudgetStopped(f"estimated-dollar stop: ${self.spent:.4f} used, "
                                f"${reserve:.4f} reserved, ${self.max_dollars:.2f} cap")
        self.attempt_count += 1
        aid = f"A{self.attempt_count:06d}"
        self.spent += reserve
        self._reserves[aid] = (reserve, time.monotonic())
        self._write({"event": "attempt_start", "id": aid, "logical_id": self.logical_id,
                     "model_requested": self.model, "reserved_dollars": reserve,
                     "input_token_upper_estimate": input_reserve,
                     "max_output_tokens": output_reserve})
        self._persist_spend()
        return aid

    def finish_attempt(self, aid, response=None, error=None, status=None):
        reserve, started = self._reserves.pop(aid)
        usage = (response or {}).get("usage") or {}
        price = self.prices[self.model]
        model_returned = (response or {}).get("model")
        mismatch = bool(model_returned and model_returned != self.model)
        if response is not None:
            if "prompt_tokens" in usage:
                in_tokens, out_tokens = usage.get("prompt_tokens"), usage.get("completion_tokens")
                details = usage.get("prompt_tokens_details") or {}
                cached = details.get("cached_tokens", 0)
                cache_write = details.get("cache_write_tokens", 0)
                anthropic_usage = False
            else:
                in_tokens, out_tokens = usage.get("input_tokens"), usage.get("output_tokens")
                cached = usage.get("cache_read_input_tokens", 0)
                cache_write = usage.get("cache_creation_input_tokens", 0)
                anthropic_usage = True
            if in_tokens is None or out_tokens is None:
                self.missing_usage = True
                charge = None
            else:
                # Cached tokens are a subset of provider input tokens. Reasoning tokens are
                # likewise already in provider output totals and must not be added again.
                if anthropic_usage:
                    # Anthropic reports cache read/write in separate usage fields.
                    effective_input = in_tokens
                else:
                    # OpenAI's cached input is already a subset of prompt_tokens.
                    effective_input = in_tokens - cached - cache_write
                charge = (effective_input * price["input_per_million"]
                          + cached * price.get("cached_input_per_million", price["input_per_million"])
                          + cache_write * price.get("cache_write_per_million", price["input_per_million"])
                          + out_tokens * price["output_per_million"]) / 1_000_000
                self.spent += charge - reserve
                self.input_tokens += in_tokens
                self.output_tokens += out_tokens
                self.cached_input_tokens += cached
                self.cache_write_tokens += cache_write
        else:
            charge = None  # ambiguous timeout or transport failure keeps the reserve
        self._write({"event": "attempt_end", "id": aid, "logical_id": self.logical_id,
                     "provider_request_id": (response or {}).get("id"), "model_returned": model_returned,
                     "model_mismatch": mismatch,
                     "status": status, "error": error, "usage": usage,
                     "usage_missing": self.missing_usage,
                     "estimated_charge_dollars": charge,
                     "reserve_retained": response is None, "elapsed_seconds": time.monotonic() - started,
                     "finish_reason": ((response or {}).get("choices") or [{}])[0].get("finish_reason")
                     or (response or {}).get("stop_reason")})
        self._persist_spend()
        if mismatch:
            raise BudgetStopped(f"provider returned {model_returned}, expected pinned {self.model}")

    def _persist_spend(self):
        if self.ledger_path is None:
            return
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.ledger_path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"estimated_api_dollars": self.spent,
                                         "updated_at": time.time(), "model": self.model}) + "\n")
        temporary.replace(self.ledger_path)

    def raw_reply(self, text, parsed=None, error=None):
        self._write({"event": "reply", "logical_id": self.logical_id, "raw_text": text,
                     "parsed": parsed, "error": error})

    def snapshot(self):
        return {"logical_calls": self.logical_count, "request_attempts": self.attempt_count,
                "input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
                "cached_input_tokens": self.cached_input_tokens,
                "cache_write_tokens": self.cache_write_tokens,
                "estimated_api_dollars": round(self.spent, 8), "missing_usage": self.missing_usage}
