"""Persistent conservative Groq free-tier pacing, shared across formation runs."""
import json
import re
import time
from pathlib import Path


class RatePaused(RuntimeError):
    pass


class FreeTierLimiter:
    def __init__(self, path, now=time.time, sleep=time.sleep):
        self.path = Path(path)
        self.now, self.sleep = now, sleep

    def before(self, token_reserve):
        now = self.now()
        state = json.loads(self.path.read_text()) if self.path.exists() else {}
        if now < state.get("paused_until", 0):
            raise RatePaused("provider asked us to pause; resume after its reset")
        events = [e for e in state.get("events", []) if now - e[0] < 86400]
        if len(events) >= 1000 or sum(e[1] for e in events) + token_reserve > 200000:
            raise RatePaused("rolling daily free-tier allowance reached; resume later")
        if token_reserve > 8000:
            raise RatePaused("request exceeds free-tier minute token allowance; reduce its ceiling")
        # No more than 20 RPM, below the documented 30. Stop instead of long sleeps.
        minute = [e for e in events if now - e[0] < 60]
        if sum(e[1] for e in minute) + token_reserve > 8000:
            raise RatePaused("minute token allowance reached; resume in a minute")
        if events:
            wait = max(0, 3 - (now - events[-1][0]))
            if wait:
                self.sleep(wait)
                now = self.now()
        events.append([now, token_reserve])
        self._save({"events": events})

    def pause(self, seconds):
        state = json.loads(self.path.read_text()) if self.path.exists() else {}
        state["paused_until"] = self.now() + max(60, seconds)
        self._save(state)

    def observe(self, headers):
        # Headers report account-wide usage, including calls outside this harness.
        for kind in ("requests", "tokens"):
            remaining = headers.get("x-ratelimit-remaining-" + kind)
            if remaining is not None and float(remaining) <= 0:
                reset = headers.get("x-ratelimit-reset-" + kind, "")
                parts = re.findall(r"([0-9.]+)(ms|s|m|h|d)", reset)
                factors = {"ms": .001, "s": 1, "m": 60, "h": 3600, "d": 86400}
                seconds = sum(float(value) * factors[unit] for value, unit in parts)
                self.pause(seconds or (86400 if kind == "requests" else 60))

    def _save(self, state):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(state) + "\n")
        temp.replace(self.path)
