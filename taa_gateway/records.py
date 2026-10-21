"""Versioned state publication and fixed evidential write boundary (stage 2).

No token issuance, authorization pipeline or protected-effect executor exists
here. The generic batch publication primitive is not the stage 5 transaction.
"""
from dataclasses import dataclass
from threading import RLock

from taa_gateway import SCHEMA_VERSION
from taa_gateway.schema import validate
from taa_gateway.serialization import copy_json


@dataclass(frozen=True)
class Write:
    record_id: str
    kind: str
    fields: dict
    under_warrant: object = None


class RecordStore:
    def __init__(self, authority, event_log, write_policy):
        validate("write_policy", write_policy)
        if any(p["channel"] == "agent" and p["evidential"] for p in write_policy["writers"]):
            raise ValueError("an agent assertion cannot be an evidential write")
        prefixes = {}
        for policy in write_policy["writers"]:
            kind, prefix = policy["kind"], policy["id_prefix"]
            if kind in prefixes and prefixes[kind] != prefix:
                raise ValueError("a record kind has one fixed identity namespace")
            if any(other != kind and (prefix.startswith(value) or value.startswith(prefix))
                   for other, value in prefixes.items()):
                raise ValueError("record identity namespaces must not overlap")
            prefixes[kind] = prefix
        self.__policy = copy_json(write_policy)
        self.__authority = authority
        self.__log = event_log
        self.__state = {"revision": 0, "step": 0, "records": {}}
        self.__lock = RLock()

    @property
    def revision(self):
        return self.__state["revision"]

    @property
    def step(self):
        return self.__state["step"]

    def snapshot(self):
        with self.__lock:
            return copy_json(self.__state)

    def read(self, record_id, version=None):
        with self.__lock:
            history = self.__state["records"].get(record_id, [])
            if version is None:
                return copy_json(history[-1]) if history else None
            if type(version) is not int or version < 1:
                raise ValueError("invalid record version")
            return copy_json(history[version - 1]) if version <= len(history) else None

    def _permission(self, session, tool, kind):
        actor, channel = self.__authority.identity(session, tool)
        matches = [p for p in self.__policy["writers"] if p["kind"] == kind and
                   p["tool"] == tool and p["channel"] == channel and actor in p["principals"]]
        if len(matches) != 1:
            raise ValueError("no unique trusted write policy for this kind/tool/source")
        return actor, matches[0]["evidential"], matches[0]["id_prefix"]

    def publish(self, session, tool, writes=(), *, step=None, expected_revision=None):
        """The only state mutation path. One accepted batch advances once.

        All state is conservatively relevant. Logs, envelope minting and reads
        do not advance it. Future token/cache storage must respect this distinction.
        """
        with self.__lock:
            actor, channel = self.__authority.identity(session, tool)
            if expected_revision is not None and (type(expected_revision) is not int or
                                                   expected_revision != self.revision):
                raise ValueError("stale state publication")
            if step is not None and (type(step) is not int or step < self.step or
                                     channel != "gateway" or tool != "advance_clock"):
                raise ValueError("only the simulator clock can advance monotonically")
            staged = self.snapshot()
            next_step = self.step if step is None else step
            events = []
            for write in writes:
                writer, evidential, prefix = self._permission(session, tool, write.kind)
                if not isinstance(write.record_id, str) or not write.record_id.startswith(prefix):
                    raise ValueError("record identity lies outside its trusted kind namespace")
                if write.kind in ("stored_order", "party", "purpose", "grant", "rule",
                                   "duty", "resolution", "receipt"):
                    validate(write.kind, write.fields)
                    if write.fields["id"] != write.record_id:
                        raise ValueError("typed record identity mismatch")
                history = staged["records"].setdefault(write.record_id, [])
                if history and history[-1]["kind"] != write.kind:
                    raise ValueError("a record cannot change kind")
                record = {"schema_version": SCHEMA_VERSION, "id": write.record_id,
                          "kind": write.kind, "fields": copy_json(write.fields),
                          "version": len(history) + 1, "written_by": writer,
                          "written_under_warrant": write.under_warrant, "evidential": evidential}
                validate("record", record)
                history.append(record)
                events.append((next_step, "record_version", {"record": record,
                               "revision_before": self.revision, "revision_after": self.revision + 1}))
            if not events and next_step == self.step:
                return self.snapshot()
            if next_step != self.step:
                events.append((next_step, "clock_change", {"from": self.step, "to": next_step,
                               "revision_before": self.revision, "revision_after": self.revision + 1}))
            staged["step"] = next_step
            staged["revision"] = self.revision + 1
            # append_many validates the complete batch before changing the log.
            # No callbacks or effect execution occur between append and publish.
            self.__log.append_many(events)
            self.__state = staged
            return self.snapshot()
