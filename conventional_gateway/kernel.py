"""Serializable relational transitions, independent of both gateway implementations.

This is trusted host plumbing, not a W0 authorization policy. Only a configured
policy can issue a handle; callbacks receive detached read snapshots. No agent
interface exposes Store, sessions, key material, policy callbacks or fault hooks.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import hmac
import json
import secrets
import sqlite3


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def copy(value):
    return json.loads(encode(value))


def digest(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


FAULTS = ("after_validate", "after_stage", "during_effect_commit",
          "during_token_consumption", "during_duty_update",
          "during_receipt_write", "during_revision_advance")
RELATIONS = ("records", "handles", "duties", "notices", "allocations",
             "cases", "grants", "orders", "reports", "receipts", "decisions")


@dataclass(frozen=True)
class Session:
    nonce: str


class Authentication:
    """Host issues sessions; sender identity never comes from an agent payload."""
    def __init__(self, key):
        if not isinstance(key, bytes) or len(key) < 32:
            raise ValueError("host key must have at least 32 bytes")
        self._key, self._sessions = key, {}

    def session(self, sender, channels):
        token = Session(secrets.token_hex(24))
        self._sessions[token.nonce] = (sender, frozenset(channels))
        return token

    def identity(self, session, channel):
        found = self._sessions.get(getattr(session, "nonce", None))
        if found is None or channel not in found[1]:
            raise PermissionError("session does not hold this channel")
        return found[0]

    def envelope(self, session, channel, recipient, step, payload, message_id):
        row = dict(sender=self.identity(session, channel), channel=channel,
                   recipient=recipient, step=step, payload=copy(payload), id=message_id)
        row["signature"] = hmac.new(self._key, encode(row).encode(), "sha256").hexdigest()
        return row

    def verify(self, envelope, *, channel, recipient, step):
        row = copy(envelope)
        signature = row.pop("signature", None)
        expected = hmac.new(self._key, encode(row).encode(), "sha256").hexdigest()
        if not isinstance(signature, str) or not hmac.compare_digest(signature, expected):
            raise PermissionError("unauthenticated envelope")
        if (row["channel"] != channel or row["recipient"] != recipient or
                type(row["step"]) is not int or row["step"] > step):
            raise PermissionError("envelope channel, recipient or clock mismatch")
        return row


class Fault(RuntimeError):
    def __init__(self, point, partial):
        super().__init__(point)
        self.point, self.partial = point, partial


class Refused(ValueError):
    pass


class Store:
    """Append-only version relations; one transaction updates state and epoch.

    All committed historical rows have SQLite UPDATE/DELETE guards. SQL rollback
    discards only uncommitted writes. Audit-only changes do not advance epoch.
    """
    def __init__(self, key, *, checkpoint=None):
        if not isinstance(key, bytes) or len(key) < 32:
            raise ValueError("host checkpoint key required")
        self._key, self._db = key, sqlite3.connect(":memory:", isolation_level=None)
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.execute("CREATE TABLE meta (id INTEGER PRIMARY KEY CHECK(id=1), step INTEGER, epoch INTEGER)")
        self._db.execute("INSERT INTO meta VALUES (1,0,0)")
        for table in RELATIONS:
            self._db.execute(f"CREATE TABLE {table} (id TEXT, version INTEGER, payload TEXT NOT NULL, PRIMARY KEY(id,version))")
            self._immutable(table)
        self._db.execute("CREATE TABLE inbox (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        self._immutable("inbox")
        self._db.execute("CREATE TABLE staged (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        self._immutable("staged")
        self._db.execute("CREATE TABLE audit (position INTEGER PRIMARY KEY, payload TEXT NOT NULL)")
        self._immutable("audit")
        self._active = False
        self._dirty = False
        if checkpoint is not None:
            self._restore(checkpoint)

    def _immutable(self, table):
        for verb in ("UPDATE", "DELETE"):
            self._db.execute(f"CREATE TRIGGER immutable_{table}_{verb} BEFORE {verb} ON {table} BEGIN SELECT RAISE(ABORT, 'append-only relation'); END")

    @property
    def epoch(self):
        return self._db.execute("SELECT epoch FROM meta").fetchone()[0]

    @property
    def step(self):
        return self._db.execute("SELECT step FROM meta").fetchone()[0]

    def versions(self, table):
        self._relation(table)
        out = {}
        for rid, version, payload in self._db.execute(f"SELECT id,version,payload FROM {table} ORDER BY id,version"):
            out.setdefault(rid, []).append(json.loads(payload))
        return out

    def current(self, table):
        return {rid: rows[-1] for rid, rows in self.versions(table).items()}

    def snapshot(self):
        return {"step": self.step, "epoch": self.epoch,
                **{table: self.versions(table) for table in RELATIONS},
                "inbox": [list(r) for r in self._db.execute("SELECT id,payload FROM inbox ORDER BY id")],
                "staged": [list(r) for r in self._db.execute("SELECT id,payload FROM staged ORDER BY id")]}

    def _relation(self, table):
        if table not in RELATIONS:
            raise ValueError("unknown relation")

    def _require_transaction(self):
        if not self._active:
            raise RuntimeError("write outside the single transaction path")

    def append(self, table, rid, payload, *, relevant=True):
        self._relation(table)
        self._require_transaction()
        version = self._db.execute(f"SELECT COALESCE(MAX(version),0)+1 FROM {table} WHERE id=?", (rid,)).fetchone()[0]
        self._db.execute(f"INSERT INTO {table} VALUES (?,?,?)", (rid, version, encode(payload)))
        self._dirty |= relevant
        self.event("version_written", {"relation": table, "id": rid,
                                       "version": version, "payload": copy(payload)})
        return version

    def event(self, kind, payload):
        self._require_transaction()
        previous = self._db.execute("SELECT payload FROM audit ORDER BY position DESC LIMIT 1").fetchone()
        tail = json.loads(previous[0]) if previous else None
        event = {"position": 1 if tail is None else tail["position"] + 1,
                 "previous": "0" * 64 if tail is None else tail["hash"],
                 "step": self.step, "kind": kind, "payload": copy(payload)}
        event["hash"] = digest(event)
        self._db.execute("INSERT INTO audit VALUES (?,?)", (event["position"], encode(event)))

    def events(self):
        return [json.loads(r[0]) for r in self._db.execute("SELECT payload FROM audit ORDER BY position")]

    def _advance(self):
        self._require_transaction()
        self._db.execute("UPDATE meta SET epoch=epoch+1")
        for hid, handle in self.current("handles").items():
            if handle["status"] == "live":
                handle["status"] = "void"
                self.append("handles", hid, handle, relevant=False)
        self.event("epoch_advanced", {"epoch": self.epoch})

    @contextmanager
    def transaction(self):
        if self._active:
            raise RuntimeError("nested transactions are forbidden")
        self._db.execute("BEGIN IMMEDIATE")
        self._active, self._dirty = True, False
        try:
            yield self
            if self._dirty:
                self._advance()
            self._db.execute("COMMIT")
        except BaseException:
            self._db.execute("ROLLBACK")
            raise
        finally:
            self._active, self._dirty = False, False

    def audit(self, kind, payload):
        with self.transaction():
            self.event(kind, payload)

    def clock(self, step, boundary=None):
        if type(step) is not int or step < self.step:
            raise ValueError("clock must be a monotonic integer")
        with self.transaction():
            self._db.execute("UPDATE meta SET step=?", (step,))
            for hid, handle in self.current("handles").items():
                if handle["status"] == "live" and step >= handle["expires"]:
                    handle["status"] = "expired"
                    self.append("handles", hid, handle)
                    self.event("handle_expired", {"handle": hid})
            if boundary is not None:
                boundary(self)
            self.event("clock", {"step": step})

    def accept_envelope(self, authentication, envelope, *, channel, recipient):
        self._require_transaction()
        row = authentication.verify(envelope, channel=channel, recipient=recipient, step=self.step)
        self._db.execute("INSERT INTO inbox VALUES (?,?)", (row["id"], encode(row)))
        self.event("envelope_accepted", row)
        return row

    def source_write(self, authentication, envelope, boundary, *, agents=()):
        """A host record event; trust policy sets evidential, never the payload."""
        with self.transaction():
            row = self.accept_envelope(authentication, envelope, channel="record", recipient="records")
            request, writer = row["payload"], row["sender"]
            if set(request) != {"record", "kind", "operation", "fields"}:
                raise PermissionError("record event fields outside interface")
            rid, kind = request["record"], request["kind"]
            policy = boundary.get(kind)
            if not isinstance(policy, dict):
                raise PermissionError("no record-write policy")
            previous = self.current("records").get(rid)
            if request["operation"] == "create":
                allowed = policy.get("create", [])
                if previous is not None or not (writer in allowed or "any_agent" in allowed and writer in agents):
                    raise PermissionError("record create denied")
                fields = request["fields"]
            elif request["operation"] == "correct":
                allowed = policy.get("correct", {}).get(writer, [])
                if (previous is None or previous["kind"] != kind or not allowed or
                        not set(request["fields"]).issubset(allowed)):
                    raise PermissionError("record correction denied")
                fields = dict(previous["fields"], **request["fields"])
            else:
                raise PermissionError("unknown record operation")
            version = self.append("records", rid, {"kind": kind, "writer": writer,
                                  "evidential": bool(policy.get("evidential", True)), "fields": fields})
            self.event("record_version", {"record": rid, "version": version})

    def checkpoint(self):
        if self._active:
            raise RuntimeError("cannot checkpoint an uncommitted transaction")
        data = {"schema": "conventional-sql/0.1", "step": self.step, "epoch": self.epoch,
                "relations": {table: list(self._db.execute(f"SELECT id,version,payload FROM {table} ORDER BY id,version")) for table in RELATIONS},
                "inbox": list(self._db.execute("SELECT id,payload FROM inbox ORDER BY id")),
                "staged": list(self._db.execute("SELECT id,payload FROM staged ORDER BY id")),
                "events": self.events()}
        data["signature"] = hmac.new(self._key, encode(data).encode(), "sha256").hexdigest()
        return copy(data)

    def _restore(self, checkpoint):
        data = copy(checkpoint)
        signature = data.pop("signature", None)
        expected = hmac.new(self._key, encode(data).encode(), "sha256").hexdigest()
        if not isinstance(signature, str) or not hmac.compare_digest(signature, expected):
            raise PermissionError("checkpoint authentication failed")
        if data["schema"] != "conventional-sql/0.1" or set(data["relations"]) != set(RELATIONS):
            raise ValueError("checkpoint schema mismatch")
        previous = "0" * 64
        with self.transaction():
            self._db.execute("UPDATE meta SET step=?,epoch=?", (data["step"], data["epoch"]))
            for table, rows in data["relations"].items():
                self._db.executemany(f"INSERT INTO {table} VALUES (?,?,?)", rows)
            for table in ("inbox", "staged"):
                self._db.executemany(f"INSERT INTO {table} VALUES (?,?)", data[table])
            for index, event in enumerate(data["events"], 1):
                body = {k: v for k, v in event.items() if k != "hash"}
                if event["position"] != index or event["previous"] != previous or event["hash"] != digest(body):
                    raise ValueError("audit chain mismatch")
                self._db.execute("INSERT INTO audit VALUES (?,?)", (index, encode(event)))
                previous = event["hash"]


class Kernel:
    """Opaque handles and actual SQL rollback, with host-configured flat policy.

    authorize(snapshot, actor, tool, args) returns True only for permission.
    stage(snapshot, actor, tool, args) returns relational writes. Both operate on
    detached snapshots. The independent W0 layer has not yet been supplied.
    """
    def __init__(self, store, authentication, authorize, stage, reconcile=None):
        self.store, self.auth = store, authentication
        self.authorize, self.stage, self.reconcile = authorize, stage, reconcile

    def issue(self, session, tool, args, *, lifetime=10):
        actor = self.auth.identity(session, "act")
        if type(lifetime) is not int or lifetime <= 0:
            raise ValueError("positive lifetime required")
        with self.store.transaction():
            view = self.store.snapshot()
            if self.authorize(copy(view), actor, tool, copy(args)) is not True:
                self.store.event("permission_refused", {"actor": actor, "tool": tool, "args": args})
                return None
            plan = self._plan(view, actor, tool, args)
            hid = "H" + str(len(self.store.current("handles")) + 1)
            handle = {"actor": actor, "tool": tool, "args": copy(args), "epoch": self.store.epoch,
                      "expires": self.store.step + lifetime, "plan": digest(plan), "status": "live"}
            self.store.append("handles", hid, handle, relevant=False)
            self.store.event("handle_issued", {"handle": hid, **handle})
            return hid

    def _plan(self, view, actor, tool, args):
        rows = copy(self.stage(copy(view), actor, tool, copy(args)))
        targets = set()
        for row in rows:
            if set(row) != {"relation", "id", "payload"} or row["relation"] not in RELATIONS or row["relation"] in ("handles", "receipts", "decisions"):
                raise ValueError("effect outside host service interface")
            target = (row["relation"], row["id"])
            if target in targets:
                raise ValueError("duplicate staged effect target")
            targets.add(target)
        return rows

    def execute(self, session, hid, *, tool=None, args=None, fault=None):
        actor = self.auth.identity(session, "act")
        if fault is not None and fault not in FAULTS:
            raise ValueError("unknown fault point")
        store = self.store
        def hit(point):
            if point == fault:
                raise Fault(point, {"state": store.snapshot(), "staged": list(store._db.execute("SELECT id,payload FROM staged")), "events": store.events()})
        try:
            with store.transaction():
                handle = store.current("handles").get(hid)
                if handle is None:
                    raise Refused("unknown_handle")
                if handle["actor"] != actor:
                    raise Refused("wrong_actor")
                if tool is not None and tool != handle["tool"] or args is not None and encode(args) != encode(handle["args"]):
                    raise Refused("argument_mismatch")
                if store.step >= handle["expires"]:
                    raise Refused("expired_handle")
                if store.epoch != handle["epoch"]:
                    raise Refused("stale_epoch")
                if handle["status"] != "live":
                    raise Refused("spent_handle")
                pre_epoch = store.epoch
                view = store.snapshot()
                if self.authorize(copy(view), actor, handle["tool"], copy(handle["args"])) is not True:
                    raise Refused("current_policy_refused")
                hit("after_validate")
                plan = self._plan(view, actor, handle["tool"], handle["args"])
                if digest(plan) != handle["plan"]:
                    raise Refused("effect_changed")
                store._db.execute("INSERT INTO staged VALUES (?,?)", (hid, encode(plan)))
                hit("after_stage")
                for row in plan:
                    store.append(row["relation"], row["id"], row["payload"])
                    hit("during_effect_commit")
                # Empty effects still have a real commit boundary (e.g. read).
                hit("during_effect_commit")
                handle["status"] = "consumed"
                store.append("handles", hid, handle, relevant=False)
                hit("during_token_consumption")
                if self.reconcile is not None:
                    self.reconcile(store)
                hit("during_duty_update")
                receipt = {"handle": hid, "actor": actor, "pre_transaction_epoch": pre_epoch, "effects": plan}
                store.append("receipts", hid, receipt, relevant=False)
                store.event("receipt", receipt)
                hit("during_receipt_write")
                # Execute advances exactly once even for a read-only tool.
                store._advance()
                store._dirty = False
                hit("during_revision_advance")
            return {"committed": True, "receipt": copy(receipt)}
        except (Refused, Fault) as error:
            detail = {"actor": actor, "handle": hid, "reason": str(error)}
            if isinstance(error, Fault):
                detail["partial_transaction"] = error.partial
            store.audit("execution_refused", detail)
            return {"committed": False, **detail}
