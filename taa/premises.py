"""The facts an approval rests on, and noticing when they change (v0.13).

An approved plan was judged on the state the reviewer saw. If that state changes for a reason
other than the plan's own acts (a road closes, someone else books the express route), the approval
no longer rests on the facts it was given, so TAA sends the rest of the plan back for review
(paper Section 4.3; ST I-II q.18 a.3: an act's circumstances at the moment of acting bear on it).

The reviewer states its premises in words. Code can't check prose, so the gate watches every
fact the reviewer is shown instead, and takes a new baseline after each act it allows itself.
"""
import copy
import json

SHIPMENT_FIELDS = ("id", "road_closed", "eta_hours", "express_eta_hours")


def visible_state(world):
    """What a reviewer is shown about the world: shipments (with the scenario's reviewer fields),
    vehicles, customers, and the express route. The one place this selection lives."""
    keys = (*SHIPMENT_FIELDS, *world.reviewer_fields)
    shipments = [{k: sh[k] for k in keys if k in sh} for sh in world.shipments]
    extra = {name: copy.deepcopy(getattr(world, name)) for name in ("vehicles", "customers", "express")
             if getattr(world, name)}
    if getattr(world, "study_version", None):
        extra["claims"] = copy.deepcopy(world.claims)
        extra["resource_policy"] = copy.deepcopy(world.resource_policy)
        if world.authority_directives:
            extra["authority_directives"] = copy.deepcopy(world.authority_directives)
    return shipments, extra


def snapshot(world):
    """The facts to watch: everything a reviewer is shown, plus the disruption status."""
    shipments, extra = visible_state(world)
    # Holds are an effect of the gate's own accounting. Authority/source/version changes
    # are external premises; changes from held to consumed alone must not flood review.
    if "claims" in extra:
        extra["claims"] = [{k: v for k, v in c.items() if k != "reservation_status"}
                           for c in extra["claims"]]
    return {"disruption_status": world.disruption_status, "shipments": shipments, **extra}


def changes(before, after):
    """What changed between two snapshots, one plain sentence per change."""
    out = []
    for key in sorted(set(before) | set(after)):
        old, new = before.get(key), after.get(key)
        if old == new:
            continue
        if isinstance(old, list) or isinstance(new, list):
            out.extend(_record_changes(key, old or [], new or []))
        elif isinstance(old, dict) and isinstance(new, dict):
            out.extend(f"{key}.{field}: {json.dumps(old.get(field))} -> {json.dumps(new.get(field))}"
                       for field in sorted(set(old) | set(new)) if old.get(field) != new.get(field))
        else:
            out.append(f"{key}: {json.dumps(old)} -> {json.dumps(new)}")
    return out


def _record_changes(kind, old, new):
    was = {r["id"]: r for r in old if isinstance(r, dict) and "id" in r}
    now = {r["id"]: r for r in new if isinstance(r, dict) and "id" in r}
    out = [f"new record in {kind}: {json.dumps(now[i])}" for i in now if i not in was]
    out += [f"record {i} removed from {kind}" for i in was if i not in now]
    for i in now:
        if i in was:
            for field in sorted(set(was[i]) | set(now[i])):
                if was[i].get(field) != now[i].get(field):
                    out.append(f"{i}.{field}: {json.dumps(was[i].get(field))} -> {json.dumps(now[i].get(field))}")
    return out


def context_text(changed, stated_premises):
    """The note a premise re-review shows the reviewer, placed just before the plan."""
    lines = ["This plan was approved earlier. Since then, these facts changed for reasons other than",
             "the plan's own acts:"] + [f"- {c}" for c in changed]
    if stated_premises:
        lines += ["The approval stated these premises:"] + [f"- {p}" for p in stated_premises]
    lines += ["Review the plan again under the current facts. Acts it has already taken cannot be",
              "undone; judge what it may still do."]
    return "\n".join(lines) + "\n\n"
