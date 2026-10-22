"""Deterministic event chain with a separately retained authenticated ending.

The ending uses a simulator-held HMAC key, not a public-key signature. A
collaborator needs that key/trusted checkpoint to authenticate it. Host compromise
is outside the design's threat model; this does not prove event truthfulness.
"""
import hashlib
import hmac
from threading import RLock

from taa_gateway import SCHEMA_VERSION
from taa_gateway.schema import validate
from taa_gateway.serialization import canonical, copy_json, digest, parse_json

GENESIS = "0" * 64


def _tag(key, value):
    return hmac.new(key, b"taa-log-v03\0" + canonical(value), hashlib.sha256).hexdigest()


class EventLog:
    def __init__(self, episode_id, checkpoint_key):
        if not isinstance(checkpoint_key, bytes) or len(checkpoint_key) < 32:
            raise ValueError("supply an explicit simulator checkpoint key of at least 32 bytes")
        self.episode_id = episode_id
        self.__key = checkpoint_key
        self.__events = []
        self.__checkpoint = None
        self._lock = RLock()

    @property
    def closed(self):
        return self.__checkpoint is not None

    def append_many(self, events):
        """Validate a complete append before publishing; no partial batch on error."""
        with self._lock:
            if self.closed:
                raise ValueError("event log is sealed")
            staged = list(self.__events)
            for step, kind, payload in events:
                entry = {"schema_version": SCHEMA_VERSION, "episode_id": self.episode_id,
                         "sequence": len(staged), "step": step, "type": kind,
                         "payload": copy_json(payload),
                         "previous_hash": staged[-1]["hash"] if staged else GENESIS}
                entry["hash"] = digest(entry)
                validate("event", entry)
                staged.append(entry)
            self.__events = staged

    def append(self, step, kind, payload):
        self.append_many([(step, kind, payload)])

    def events(self):
        with self._lock:
            return copy_json(self.__events)

    def restore_open_for_simulator(self, events):
        """Trusted trace reconstruction; verify every supplied chain element."""
        if self.__events or self.closed:
            raise ValueError("restore requires an empty open log")
        events = list(events)
        staged = EventLog(self.episode_id, self.__key)
        staged.append_many([(e["step"], e["type"], e["payload"]) for e in events])
        if canonical(staged.events()) != canonical(events):
            raise ValueError("open log chain mismatch")
        self.__events = staged.events()

    def seal(self):
        with self._lock:
            if self.__checkpoint is None:
                checkpoint = {"schema_version": SCHEMA_VERSION, "episode_id": self.episode_id,
                              "event_count": len(self.__events),
                              "head_hash": self.__events[-1]["hash"] if self.__events else GENESIS,
                              "algorithm": "HMAC-SHA256"}
                checkpoint["authentication_tag"] = _tag(self.__key, checkpoint)
                validate("checkpoint", checkpoint)
                self.__checkpoint = checkpoint
            return copy_json(self.__checkpoint)

    def jsonl(self):
        with self._lock:
            if not self.closed:
                raise ValueError("seal and retain the checkpoint before exporting a complete log")
            return b"".join(canonical(row) + b"\n" for row in
                            self.__events + [self.__checkpoint])


def verify_jsonl(blob, checkpoint_key, trusted_checkpoint):
    """A log's own final count alone is not a trusted truncation checkpoint."""
    if not isinstance(blob, bytes) or not blob.endswith(b"\n"):
        raise ValueError("complete canonical JSONL required")
    lines = blob.splitlines()
    rows = [parse_json(line) for line in lines]
    if not rows or any(canonical(row) != line for row, line in zip(rows, lines)):
        raise ValueError("noncanonical or empty event log")
    checkpoint = rows.pop()
    validate("checkpoint", checkpoint)
    if canonical(checkpoint) != canonical(trusted_checkpoint):
        raise ValueError("ending differs from the retained checkpoint")
    unsigned = {k: v for k, v in checkpoint.items() if k != "authentication_tag"}
    if not hmac.compare_digest(checkpoint["authentication_tag"], _tag(checkpoint_key, unsigned)):
        raise ValueError("checkpoint authentication failed")
    previous = GENESIS
    for sequence, entry in enumerate(rows):
        validate("event", entry)
        unsigned = {k: v for k, v in entry.items() if k != "hash"}
        if (entry["sequence"] != sequence or entry["previous_hash"] != previous or
                entry["episode_id"] != checkpoint["episode_id"] or entry["hash"] != digest(unsigned)):
            raise ValueError("event chain mismatch")
        previous = entry["hash"]
    if len(rows) != checkpoint["event_count"] or previous != checkpoint["head_hash"]:
        raise ValueError("event count or head mismatch")
    return copy_json(rows)
