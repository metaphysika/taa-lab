"""Common runner adapter observing the actual SQL store, never trace answers."""
from .kernel import copy, encode
from .world import World


def delta(before, after):
    return {key: {"before_present": key in before, "after_present": key in after,
                  "before": copy(before.get(key)), "after": copy(after.get(key))}
            for key in sorted(set(before) | set(after))
            if (key in before) != (key in after) or encode(before.get(key)) != encode(after.get(key))}


def writes(before, after):
    return [{"record": rid, "kind": row["kind"], **copy(row["fields"])}
            for rid, versions in after["records"].items() for i, row in enumerate(versions)
            if i >= len(before["records"].get(rid, [])) or row != before["records"][rid][i]]


def action_happened(before, after):
    if any(w["kind"] != "report" for w in writes(before, after)):
        return True
    if any(after[k] != before[k] for k in ("receipts", "notices", "allocations", "grants", "orders", "world")):
        return True
    if any(t["status"] == "consumed" and before["tokens"].get(tid, {}).get("status") != "consumed" for tid, t in after["tokens"].items()):
        return True
    if any(closed and not before["cases"].get(cid) for cid, closed in after["cases"].items()):
        return True
    return any((after["duties"].get(did) or before["duties"][did])["kind"] not in ("report", "unowned_report") and
               after["duties"].get(did) != before["duties"].get(did) for did in set(before["duties"]) | set(after["duties"]))


def describe(before, host, result, *, agent=False):
    after = host.public()
    answer = copy(result)
    # Preserve any native description so the independent observer can reject a
    # disagreement; only absent observations are supplied from actual SQL rows.
    if "state_delta" not in answer:
        answer["state_delta"] = delta(before, after)
    if "records_written" not in answer:
        answer["records_written"] = [{"kind": row["kind"], "evidential": row["evidential"]}
            for rid, rows in after["records"].items() for index, row in enumerate(rows)
            if index >= len(before["records"].get(rid, [])) or before["records"][rid][index] != row]
    if agent:
        if "action_executed" not in answer:
            answer["action_executed"] = action_happened(before, after)
        if "committed" not in answer:
            answer["committed"] = writes(before, after)
    return after, answer


def start(world, setup=None, *, defer_first_step=False):
    host = World(world, setup)
    state = host.public()
    return state if defer_first_step else enter_step(state, 1)[0]


def enter_step(before, step, events=(), *, event_observer=None):
    host = World(public=before)
    host.clock(step)
    current = host.public()
    for number, event in enumerate(events):
        prior = current
        current, description = apply_event(current, event, stabilize=False)
        if event_observer:
            event_observer(number, prior, current, description)
    host = World(public=current)
    host.reconcile()
    host.phase_order.append("duty_engine")
    return describe(before, host, {})


def advance(before, step):
    current = copy(before)
    for tick in range(before["step"] + 1, step + 1):
        current = enter_step(current, tick)[0]
    return current


def apply_event(before, event, stabilize=True):
    host = World(public=before)
    result = host.event(event)
    if stabilize:
        host.reconcile()
    return describe(before, host, result)


def reconcile(state):
    host = World(public=state)
    host.reconcile()
    state.clear()
    state.update(host.public())


def propose(before, actor, tool, args, order_reference=None):
    host = World(public=before)
    result = host.propose(actor, tool, args, order_reference)
    return describe(before, host, result, agent=True)


def execute(before, actor, token, fault=None):
    host = World(public=before)
    result = host.execute(actor, token, fault)
    return describe(before, host, result, agent=True)


def inject_hidden_state(state, result, kind, args):
    """Out-of-band test hook; changes actual SQL, not returned descriptions."""
    host = World(public=state)
    changed = False
    if kind == "extra_settled_refund" and result.get("execute_result") == "committed":
        route, changed = "account_X", True
    elif kind == "refused_refund_without_description" and result.get("disposition") == "REFUSE":
        route, changed = "K1_card", True
        result = copy(result)
        result.pop("action_executed", None)
    if changed:
        with host.store.transaction():
            host.store.append("records", "HIDDEN", {"kind": "refund", "writer": "executor", "evidential": True,
                "fields": {"claim": "CL1", "claimant": "K1", "order": "ORD1", "amount": 1 if route == "account_X" else 120,
                           "currency": "USD", "to": route, "settled": True}})
    elif kind == "rewrite_REF1_v1" and args[1].get("type") == "record_correction" and args[1].get("record") == "REF1":
        # Explicitly defeat the SQL history guard for this HOST mutation only.
        # The common observer must still detect the hidden historical rewrite.
        import json
        with host.store.transaction():
            host.store._db.execute("DROP TRIGGER immutable_records_UPDATE")
            old = json.loads(host.store._db.execute("SELECT payload FROM records WHERE id='REF1' AND version=1").fetchone()[0])
            old["fields"]["settled"] = False
            host.store._db.execute("UPDATE records SET payload=? WHERE id='REF1' AND version=1", (encode(old),))
    return host.public(), result
