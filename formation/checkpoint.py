"""Append-only trial progress: completed or uncertain trials are never repeated."""
import json
from pathlib import Path


class TrialStore:
    def __init__(self, path, fingerprint):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.states = {}
        if self.path.exists():
            events = [json.loads(line) for line in self.path.read_text().splitlines()]
            if not events or events[0].get("fingerprint") != fingerprint:
                raise ValueError("resume fingerprint differs; preserve this run and use a new folder")
            for event in events[1:]:
                self.states[event["trial"]] = event["state"]
        else:
            self.append({"fingerprint": fingerprint})

    def append(self, event):
        with self.path.open("a") as out:
            out.write(json.dumps(event, sort_keys=True) + "\n")
            out.flush()

    def should_run(self, trial):
        state = self.states.get(trial)
        if state == "inflight":
            raise RuntimeError("uncertain interrupted request; inspect evidence before any new trial")
        return state is None or state == "rate_paused"

    def mark(self, trial, state, **evidence):
        self.append(dict(evidence, trial=trial, state=state))
        self.states[trial] = state
