"""Input driver and assertion projection; contains no authorization/duty rules.

Expectations are read only from Claude's bundle. Model output is observation,
never an answer key. Unknown assertion vocabulary is incomplete coverage.
"""
from copy import deepcopy
import json

from taa_gateway_reference import refunds as model
from tests.trace_support.bundle import cases, world


class IncompleteCoverage(Exception):
    pass


def contains(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and contains(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return False
        if not expected:
            return not actual
        # Lists of partial records/history entries are ordered subsequences.
        pos = 0
        for e in expected:
            while pos < len(actual) and not contains(actual[pos], e):
                pos += 1
            if pos == len(actual):
                return False
            pos += 1
        return True
    if expected == "none":
        return actual is None or actual == "none"
    return type(actual) is type(expected) and actual == expected


def flatten_committed(s):
    return [e for receipt in s["receipts"] for e in receipt["committed"]]


def observe(key, expected, s, result, ctx, final=False):
    if key == "duties":
        duties = deepcopy(s["duties"])
        for d in duties.values():
            if isinstance(d.get("basis"), list) and len(d["basis"]) == 1:
                d["basis"] = d["basis"][0]
        return [duties.get(d["id"], {"missing_duty": d["id"]}) for d in expected]
    if key == "duties_created":
        ids = result.get("duties_created", [did for did in s["duties"] if did not in ctx["before"]["duties"]])
        return [deepcopy(s["duties"][did]) for did in ids]
    if key == "token":
        return result.get("token", "none")
    if key == "token_state":
        return {tid: s["tokens"].get(tid, {}).get("status") for tid in expected}
    if key in ("token_acting_party", "token_expires_at"):
        return s["tokens"].get(result.get("token"), {}).get("actor" if key == "token_acting_party" else "expires")
    if key == "live_tokens_for_act":
        p = ctx["proposal"]
        return sum(t["status"] == "live" and t["actor"] == p["actor"] and t["tool"] == p["tool"] and model.same(t["args"], p["args"]) for t in s["tokens"].values())
    if key == "same_revision_as":
        return expected if s["tokens"][result["token"]]["revision"] == s["tokens"][expected]["revision"] else "different"
    if key == "revision":
        base = ctx["pre_action"]["revision"] if ctx["has_action"] else ctx["before"]["revision"]
        return "R+" if s["revision"] > base else "R="
    if key == "revision_before_execute":
        t = ctx["pre_action"]["tokens"].get(ctx["execute"].get("token"), {})
        return "R+" if ctx["pre_action"]["revision"] > t.get("revision", ctx["pre_action"]["revision"]) else "R="
    if key == "revision_before_propose":
        return "R+" if ctx["pre_action"]["revision"] > ctx["last_proposal_revision"] else "R="
    if key in ("transaction_changes", "world_equals_pre_transaction"):
        before, after = deepcopy(ctx["pre_action"]), deepcopy(s)
        # Rejected-call audit logging is outside the transaction.
        before.pop("log"); after.pop("log")
        equal = before == after
        return ("none" if equal else "changed") if key == "transaction_changes" else equal
    if key == "committed":
        return flatten_committed(s) if final else result.get("committed", [])
    if key == "associated_order":
        matches = result.get("associated_orders", [])
        return matches[0] if len(matches) == 1 else matches
    if key == "attributed_issuer":
        values = result.get("attributed_issuers", [])
        return values[0] if len(values) == 1 else "none" if not values else values
    if key == "not_attributed":
        return [v for v in expected if v not in result.get("attributed_issuers", [])]
    if key == "not_recipient":
        recipients = {d.get("recipient") for d in s["duties"].values() if d["kind"] == "report"}
        return [v for v in expected if v not in recipients]
    if key == "report_duties_created":
        if final:
            return sum(d["kind"] == "report" for d in s["duties"].values())
        return result.get(key, sum(d["kind"] == "report" for did, d in s["duties"].items() if did not in ctx["before"]["duties"]))
    if key == "gateway_transitions":
        return [{k: v for k, v in e.items() if k != "step"} for e in s["log"][ctx["log_start"]:] if e["type"] == "report_dispatched"]
    if key in ("case_open", "case_closed"):
        closed = key == "case_closed"
        return [claim for claim in expected if s["cases"].get(claim) is closed]
    if key == "reopening_cites":
        return next((d.get(key) for d in s["duties"].values() if d.get(key)), None)
    if key == "executed_history_rewritten":
        return s["receipts"][:len(ctx["before"]["receipts"])] != ctx["before"]["receipts"]
    if key == "record_versions_retained":
        return [ref for ref in expected if ref.split("@v")[0] in s["records"] and len(s["records"][ref.split("@v")[0]]) >= int(ref.split("@v")[1])]
    if key == "released_or_discharged_by_revocation":
        changed = [d for did, d in s["duties"].items() if did in ctx["before"]["duties"] and
                   ctx["before"]["duties"][did]["resolution"] == "unresolved" and d["resolution"] != "unresolved"]
        return "none" if not changed else changed
    if key == "phase_order":
        return ctx["pre_action"]["phase_order"] + (["execute"] if "execute" in ctx else [])
    if key == "transfer_completed":
        return any(did in ctx["before"]["duties"] and d["owner"] != ctx["before"]["duties"][did]["owner"] for did, d in s["duties"].items())
    if key == "arbitrary_recipient_chosen":
        return any(d.get("recipient") is not None for d in s["duties"].values() if d["kind"] == "report")
    if key == "records_unchanged":
        return [rid for rid in expected if s["records"].get(rid) == ctx["initial"]["records"].get(rid)]
    if key == "over_refusal":
        return any(d["result"].get("disposition") in ("REFUSE", "HOLD", "REFER", "PROHIBIT") for d in s["decisions"])
    if key in ("refunds_for_claim", "refunds_to_account", "cumulative_refunds"):
        field = {"refunds_for_claim": "claim", "refunds_to_account": "to", "cumulative_refunds": "order"}[key]
        return {value: sum((f["amount"] if key == "cumulative_refunds" else 1) for _, f in model.records(s, "refund") if f.get(field) == value) for value in expected}
    if key == "reports_naming":
        return {issuer: sum(d.get("issuer") == issuer for d in s["duties"].values() if d["kind"] == "report") for issuer in expected}
    if key == "report_duties_for_matter":
        return {did: sum(d["id"] == did or d.get("links_to") == did for d in s["duties"].values()) for did in expected}
    if key == "duty_engine_reaches_stable_state_each_step":
        return ctx["stable"]
    if key == "log_retains":
        found = []
        for label in expected:
            if label == "first_PROHIBIT":
                exists = any(e["type"] == "decision" and e["result"].get("disposition") == "PROHIBIT" for e in s["log"])
            elif label.startswith("decision_issuing_"):
                tid = label[len("decision_issuing_"):]
                exists = any(e["type"] == "decision" and e["result"].get("token") == tid for e in s["log"])
            else:
                raise IncompleteCoverage("unimplemented log predicate " + label)
            if exists:
                found.append(label)
        return found
    direct = {"disposition", "rule", "rules", "decided_at_stage", "failed_stage", "tokens_issued_by_reviewer",
              "action_executed", "receipt", "fresh_evaluation", "recorded_decision_returned", "repeat_count",
              "missing_fact", "reason", "suggested", "associated_orders", "prohibited_element_origin",
              "cited_reference_rejected", "recipient", "reserved_question", "records_written", "resolution_rejected",
              "authority_basis", "execute_result", "call_result", "evaluated", "validation_compares"}
    if key in direct:
        defaults = {"recorded_decision_returned": False, "repeat_count": 0, "records_written": [],
                    "tokens_issued_by_reviewer": 0, "action_executed": False}
        return result.get(key, defaults.get(key))
    raise IncompleteCoverage("unimplemented assertion " + key)


def run(case):
    t = case["trace"]
    s = model.start(world(), t.get("setup"))
    initial = deepcopy(s)
    checks, stable = [], True
    last_proposal_revision = s["revision"]
    for index, entry in enumerate(t["steps"]):
        ctx = {"before": deepcopy(s), "initial": initial, "log_start": len(s["log"]), "has_action": False,
               "last_proposal_revision": last_proposal_revision}
        s, result = model.enter_step(s, entry["step"], entry.get("events", []))
        ctx["pre_action"] = deepcopy(s)
        if "propose" in entry:
            p = entry["propose"]
            ctx.update(proposal=p, has_action=True)
            s, result = model.propose(s, p["actor"], p["tool"], p["args"], p.get("order_reference"))
            last_proposal_revision = s["revision"]
        if "execute" in entry:
            x = deepcopy(entry["execute"])
            if x.get("inject_fault", "").startswith("${"):
                x["inject_fault"] = case["parameters"][x["inject_fault"][2:-1]]
            ctx.update(execute=x, has_action=True)
            s, result = model.execute(s, x["actor"], x.get("token"), x.get("inject_fault"))
        copy = deepcopy(s)
        model.reconcile(copy)
        stable &= copy == s
        ctx["stable"] = stable
        check_expectations(case, f"steps[{index}]@{entry['step']}", entry.get("expect", {}), s, result, ctx, checks)
    ctx.update(stable=stable, initial=initial)
    check_expectations(case, "final", t.get("final", {}), s, {}, ctx, checks, final=True)
    return checks


def check_expectations(case, location, expected, state, result, ctx, checks, final=False):
    for key, value in expected.items():
        try:
            observed = observe(key, value, state, result, ctx, final)
            status = "pass" if contains(observed, value) else "discrepancy"
        except IncompleteCoverage as error:
            observed, status = str(error), "incomplete"
        checks.append({"trace": case["id"], "assertion": location + "." + key,
                       "expectation": value, "observed": observed, "status": status})


def all_results():
    results = []
    for case in cases():
        try:
            results.extend(run(case))
        except Exception as error:
            results.append({"trace": case["id"], "assertion": "runner", "expectation": "complete trace execution",
                            "observed": type(error).__name__ + ": " + str(error), "status": "incomplete"})
    return results


def main():
    import argparse
    from pathlib import Path
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    a = p.parse_args()
    results = all_results()
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps({"backend": "independent-reference", "assertions": results}, indent=2) + "\n")
    failed = [r for r in results if r["status"] != "pass"]
    print(f"{len(cases())} executable scenarios; {len(results)} assertion blocks; {len(failed)} disagreements/incomplete")
    for r in failed:
        print(json.dumps(r))
    return bool(failed)


if __name__ == "__main__":
    raise SystemExit(main())
