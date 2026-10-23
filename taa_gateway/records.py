"""Single locked publication path for records and runtime transactions.

Gateway callbacks are trusted simulator code. Agents have no gateway session,
store handle or callback registration interface. Rollback never erases evidence:
it restores uncommitted state and logs a failed attempt outside the transaction.
"""
from taa_gateway.offers import entries, project
from dataclasses import dataclass
from threading import RLock

from taa_gateway import SCHEMA_VERSION
from taa_gateway.schema import validate
from taa_gateway.serialization import canonical, copy_json


@dataclass(frozen=True)
class Write:
    record_id: str
    kind: str
    fields: dict
    under_warrant: object = None


class RecordStore:
    def __init__(self, authority, event_log, write_policy, *, invalidate_tokens_on_revision=True):
        if type(invalidate_tokens_on_revision) is not bool:
            raise ValueError("invalidate_tokens_on_revision must be a boolean")
        self.__invalidate_tokens_on_revision = invalidate_tokens_on_revision
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
        self.__state = {"revision": 0, "step": 0, "records": {}, "tokens": {}, "warrants": {},
                        "receipts": [], "decisions": [], "notices": [], "allocations": {},
                        "cases": {}, "reports": {}, "duty_records": {}}
        self.__lock = RLock()
        self.__mutating = False

    @property
    def invalidates_tokens_on_revision(self):
        """Trusted episode configuration, not an agent-writable state field."""
        return self.__invalidate_tokens_on_revision

    @property
    def revision(self):
        with self.__lock:
            return self.__state["revision"]

    @property
    def step(self):
        with self.__lock:
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
        return actor, matches[0]

    def _mutate(self, callback, *, execution=False):
        """One private mutation path. No unlocked partial state or partial log."""
        with self.__lock:
            if self.__mutating:
                raise ValueError("nested state mutation is forbidden")
            prior = self.__state
            self.__state = copy_json(prior)
            self.__mutating = True
            events = []
            try:
                callback(self.__state, events)
                self._check_publication(prior, events, execution)
                canonical(self.__state)
                self.__log.append_many(events)
            except BaseException:
                self.__state = prior
                raise
            finally:
                self.__mutating = False
            return self.snapshot()

    def _check_publication(self, prior, events, execution):
        state = self.__state
        if state["step"] < prior["step"] or state["revision"] < prior["revision"]:
            raise ValueError("state clock/revision cannot regress")
        for key in ("records", "duty_records", "reports"):
            for rid, history in prior[key].items():
                if rid not in state[key] or canonical(state[key][rid][:len(history)]) != canonical(history):
                    raise ValueError("published record versions are immutable")
        if canonical(state["receipts"][:len(prior["receipts"])]) != canonical(prior["receipts"]):
            raise ValueError("published receipts are immutable")
        for tid, old in prior["tokens"].items():
            if tid not in state["tokens"] or any(canonical(old[k]) != canonical(state["tokens"][tid].get(k))
                    for k in ("certificate", "tool", "args", "plan_hash", "basis_hash")):
                raise ValueError("issued token bindings are immutable")
        for wid, old in prior["warrants"].items():
            if wid not in state["warrants"] or canonical({k: v for k, v in old.items() if k != "status"}) != canonical(
                    {k: v for k, v in state["warrants"][wid].items() if k != "status"}):
                raise ValueError("issued warrant basis is immutable")
        metadata = {"step", "revision", "tokens", "warrants", "decisions"}
        relevant = any(canonical(prior.get(k)) != canonical(state.get(k)) for k in prior.keys() | state.keys() if k not in metadata)
        relevant |= any(old["status"] == "live" and state["tokens"][tid]["status"] != "live" for tid, old in prior["tokens"].items())
        if relevant and state["revision"] == prior["revision"]:
            self.advance_revision(state, events)
        for tid, row in state["tokens"].items():
            if (self.__invalidate_tokens_on_revision and row["status"] == "live" and
                    row["certificate"]["state_revision"] != state["revision"]):
                row["status"], row["void_reason"] = "void", "revision"
                state["warrants"][row["certificate"]["warrant_id"]]["status"] = "void"
                events.append((state["step"], "token_voided", {"token": tid, "revision": state["revision"]}))
        consumed = [tid for tid, row in state["tokens"].items() if row["status"] == "consumed" and
                    (tid not in prior["tokens"] or prior["tokens"][tid]["status"] != "consumed")]
        receipts = state["receipts"][len(prior["receipts"]):]
        if execution and (len(consumed) != 1 or len(receipts) != 1):
            raise ValueError("execution consumes exactly one token and writes exactly one receipt")
        if consumed != [receipt["token_id"] for receipt in receipts]:
            raise ValueError("receipt/consumption mismatch")
        for receipt in receipts:
            validate("receipt", receipt)
            cert = state["tokens"][receipt["token_id"]]["certificate"]
            if (receipt["pre_transaction_revision"] != prior["revision"] or receipt["committed_revision"] != state["revision"] or
                    receipt["acting_party"] != cert["acting_party"] or receipt["warrant_id"] != cert["warrant_id"]):
                raise ValueError("receipt is not bound to this transaction")

    def advance_revision(self, state, events, count=1):
        """Trusted transaction helper; the working state must be the live one."""
        if not self.__mutating or state is not self.__state or type(count) is not int or count < 1:
            raise ValueError("not the locked working state")
        state["revision"] += count
        if not self.__invalidate_tokens_on_revision:
            return
        for tid, row in state["tokens"].items():
            if row["status"] == "live":
                row["status"] = "void"
                row["void_reason"] = "revision"
                state["warrants"][row["certificate"]["warrant_id"]]["status"] = "void"
                events.append((state["step"], "token_voided", {"token": tid, "revision": state["revision"]}))

    def append_write(self, state, events, session, tool, write):
        if not self.__mutating or state is not self.__state:
            raise ValueError("not the locked working state")
        writer, permission = self._permission(session, tool, write.kind)
        if not isinstance(write.record_id, str) or not write.record_id.startswith(permission["id_prefix"]):
            raise ValueError("record identity lies outside its trusted kind namespace")
        if write.kind in ("stored_order", "party", "purpose", "grant", "rule", "duty", "resolution", "receipt"):
            validate(write.kind, write.fields)
            if write.fields["id"] != write.record_id:
                raise ValueError("typed record identity mismatch")
        history = state["records"].setdefault(write.record_id, [])
        if history and history[-1]["kind"] != write.kind:
            raise ValueError("a record cannot change kind")
        if not history and not permission["create"]:
            raise ValueError("source cannot create this kind")
        if history:
            old = history[-1]["fields"]
            changed = {key for key in old.keys() | write.fields.keys() if key not in old or key not in write.fields or
                       canonical(old[key]) != canonical(write.fields[key])}
            if changed - set(permission["correct_fields"]):
                raise ValueError("source cannot correct these fields")
        record = {"schema_version": SCHEMA_VERSION, "id": write.record_id, "kind": write.kind,
                  "fields": copy_json(write.fields), "version": len(history) + 1, "written_by": writer,
                  "written_under_warrant": write.under_warrant, "evidential": permission["evidential"]}
        validate("record", record)
        history.append(record)
        events.append((state["step"], "record_version", {"record": record}))
        return record

    def gateway_mutation(self, session, tool, callback):
        _, channel = self.__authority.identity(session, tool)
        if channel != "gateway":
            raise ValueError("only the simulator owns transaction operations")
        return self._mutate(callback, execution=tool == "execute_transaction")

    def publish(self, session, tool, writes=(), *, step=None, expected_revision=None):
        writes = tuple(writes)
        if tool == "execute_transaction":
            raise ValueError("protected effects require the atomic executor")
        _, channel = self.__authority.identity(session, tool)
        def change(state, events):
            if expected_revision is not None and (type(expected_revision) is not int or expected_revision != state["revision"]):
                raise ValueError("stale state publication")
            old_step = state["step"]
            if step is not None and (type(step) is not int or step < old_step or channel != "gateway" or tool != "advance_clock"):
                raise ValueError("only the simulator clock can advance monotonically")
            next_step = old_step if step is None else step
            boundaries = self._boundaries(old_step, next_step)
            state["step"] = next_step
            ledger_boundaries = self._ledger_clock(state, events, old_step, next_step)
            for write in writes:
                self.append_write(state, events, session, tool, write)
            if next_step != old_step:
                events.append((next_step, "clock_change", {"from": old_step, "to": next_step}))
            expired = [tid for tid, row in state["tokens"].items() if row["status"] == "live" and
                       old_step < row["certificate"]["expires_at_step"] <= next_step]
            if writes or boundaries or expired or ledger_boundaries:
                self.advance_revision(state, events, int(bool(writes)) + len(boundaries) + int(bool(expired)) + ledger_boundaries)
                for tid in expired:
                    # C2 removes world-change invalidation, not intrinsic expiry.
                    # Only this expired token is retired; other handles stay live.
                    if not self.__invalidate_tokens_on_revision:
                        row = state["tokens"][tid]
                        row["status"] = "void"
                        state["warrants"][row["certificate"]["warrant_id"]]["status"] = "void"
                        events.append((state["step"], "token_voided", {"token": tid, "revision": state["revision"]}))
                    state["tokens"][tid]["void_reason"] = "expired"
            for boundary in boundaries:
                events.append((next_step, "clock_boundary", boundary))
        return self._mutate(change)

    def append_duty(self, state, events, duty, writer, under_warrant=None):
        if not self.__mutating or state is not self.__state:
            raise ValueError("not the locked working state")
        validate("duty", duty)
        history = state["duty_records"].setdefault(duty["id"], [])
        history.append({"schema_version": SCHEMA_VERSION, "id": duty["id"], "kind": "duty", "fields": copy_json(duty),
                        "version": len(history) + 1, "evidential": True, "written_by": writer,
                        "written_under_warrant": under_warrant})
        events.append((state["step"], "duty_transition", {"duty": history[-1]}))

    def _ledger_clock(self, state, events, old_step, next_step):
        """Clock primitives only; independent duty derivation/routing is stage 6."""
        changed = 0
        for versions in list(state["duty_records"].values()):
            duty = copy_json(versions[-1]["fields"])
            if duty["resolution"] != "unresolved":
                continue
            transitions = []
            if not duty["overdue"] and old_step < duty["deadline_step"] <= next_step:
                duty["overdue"] = True
                transitions.append({"type": "overdue", "at": duty["deadline_step"]})
            offers = entries(duty)
            expired = [o for o in offers if o["status"] == "live" and old_step < o["expires"] <= next_step]
            if expired:
                duty["content"]["transfer_offers"] = offers
                for offer in expired:
                    offer["status"] = "expired"
                lost = duty["interim_rule"].get("authority_lost", False)
                unowned = lost and not any(o["status"] == "live" for o in offers)
                if unowned:
                    duty["owner"] = None
                project(duty)
                transitions.extend({"type": "unowned" if unowned else "offer_lapsed", "at": o["expires"]} for o in expired)
            route = duty.get("route_deadline_step")
            if type(route) is int and old_step < route <= next_step and not duty["content"].get("routing_due"):
                duty["content"]["routing_due"] = True
                transitions.append({"type": "routing_due", "at": route})
            if transitions:
                duty["history"].extend(transitions)
                self.append_duty(state, events, duty, "gateway_clock")
                changed += len(transitions)
        return changed

    def restore_for_simulator(self, session, snapshot):
        """Trusted offline adapter reconstruction, never available to an agent."""
        _, channel = self.__authority.identity(session, "restore")
        if channel != "gateway":
            raise ValueError("only the simulator can restore a trace checkpoint")
        with self.__lock:
            if self.__mutating:
                raise ValueError("cannot restore during a transaction")
            if self.__state["revision"] != 0 or self.__state["step"] != 0 or self.__state["records"] or self.__state["tokens"]:
                raise ValueError("restore requires a new empty simulator store")
            self.__state = copy_json(snapshot)

    def audit(self, kind, payload):
        """Append observational/rejected input only; this path cannot write state."""
        with self.__lock:
            self.__log.append(self.step, kind, payload)

    def _boundaries(self, old_step, new_step):
        crossed = []
        for history in self.__state["records"].values():
            record = history[-1]
            fields, kind = record["fields"], record["kind"]
            deadlines = []
            if kind in ("grant", "token") and fields.get("status", "live") == "live":
                deadlines.append(fields.get("expires_at_step"))
            if kind == "duty" and fields.get("resolution") == "unresolved":
                deadlines.extend(fields.get(k) for k in ("deadline_step", "route_deadline_step"))
                deadlines.extend(o["expires"] for o in entries(fields) if o["status"] == "live")
            for at in deadlines:
                if type(at) is int and old_step < at <= new_step:
                    crossed.append({"id": record["id"], "at": at})
        return crossed
