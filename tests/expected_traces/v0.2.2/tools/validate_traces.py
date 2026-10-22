#!/usr/bin/env python3
"""Strict structural validator for the TAA gateway expected traces.

Usage: python3 -I tools/validate_traces.py <bundle_dir>

It checks shape and references, not outcomes. A trace that passes here can
still be wrong about the specification; that is what review is for. Exit code 0
means no errors.
"""
import glob
import os
import re
import sys

import yaml

TRACE_KEYS = {"id", "title", "targets", "contracts", "spec_refs", "setup", "steps",
              "final", "variants", "parameters", "notes"}
VARIANT_KEYS = {"id", "title", "mode", "setup", "steps", "final"}
SETUP_KEYS = {"records", "remove_records", "grants", "token_lifetime"}
STEP_KEYS = {"step", "events", "propose", "execute", "expect"}
PROPOSE_KEYS = {"actor", "tool", "args", "order_reference"}
EXECUTE_KEYS = {"actor", "token", "inject_fault", "act"}
EXPECT_KEYS = {
    "disposition", "rule", "rules", "decided_at_stage", "failed_stage", "token", "tokens_issued_by_reviewer",
    "token_state", "token_acting_party", "token_expires_at", "live_tokens_for_act", "same_revision_as",
    "action_executed", "transaction_changes", "committed", "receipt", "revision",
    "revision_before_execute", "revision_before_propose", "fresh_evaluation",
    "recorded_decision_returned", "repeat_count", "missing_fact", "reason", "suggested",
    "associated_order", "associated_orders", "attributed_issuer", "not_attributed",
    "prohibited_element_origin", "cited_reference_rejected", "duties", "duties_created",
    "report_duties_created", "gateway_transitions", "not_recipient", "recipient",
    "reserved_question", "records_written", "resolution_rejected", "authority_basis",
    "released_or_discharged_by_revocation", "execute_result", "call_result", "evaluated",
    "world_equals_pre_transaction", "phase_order", "validation_compares", "case_open",
    "case_closed", "reopening_cites", "executed_history_rewritten", "record_versions_retained",
    "transfer_completed", "arbitrary_recipient_chosen", "overdue",
}
FINAL_KEYS = {"committed", "records_unchanged", "duties", "case_open", "report_duties_created",
              "over_refusal", "refunds_for_claim", "refunds_to_account", "log_retains",
              "report_duties_for_matter", "reports_naming", "cumulative_refunds",
              "duty_engine_reaches_stable_state_each_step"}
DUTY_KEYS = {"id", "resolution", "owner", "offered_to", "by", "by_rule", "due", "overdue",
             "recipient", "history", "basis", "link_to", "links_to", "evidence"}
EVENT_FIELDS = {
    "order": {"id", "from", "to", "requested_effects"},
    "message": {"from", "to", "content"},
    "record_insert": {"record", "by", "fields"},
    "record_correction": {"record", "by", "new", "on_behalf_of"},
    "grant_revocation": {"grant", "by"},
    "grant_amendment": {"grant", "by", "change"},
    "grant_issue": {"grant", "by", "to", "same_terms_as"},
    "resolution": {"question", "about", "by", "via", "answer", "reviewer_says", "basis", "evidence"},
    "acknowledgment": {"from", "report", "version"},
    "duty_acceptance": {"from", "duties"},
}
RESOLUTIONS = {"unresolved", "discharged", "released"}
DISPOSITIONS = {"PERMIT", "ALTERNATIVE", "HOLD", "REFER", "REFUSE", "PROHIBIT"}
DUTY_ID = re.compile(r"^D_(resolve|refund|report|report_supplement|unowned_report)"
                     r"\([A-Za-z0-9_]+(,[0-9]+)?\)$")
TOKEN_ID = re.compile(r"^T[0-9]+$")


class Checker:
    def __init__(self, world):
        self.errors = []
        self.parties = set(world["parties"])
        self.rules = set(world["rules"])
        self.records = set(world["records"])

    def err(self, where, msg):
        self.errors.append(f"{where}: {msg}")

    def keys(self, where, obj, allowed):
        if not isinstance(obj, dict):
            self.err(where, f"expected a mapping, got {type(obj).__name__}")
            return
        for k, v in obj.items():
            if k not in allowed:
                self.err(where, f"unexpected key {k!r}")
            if v is None and isinstance(k, str) and (")" in k or "," in k):
                self.err(where, f"key {k!r} looks like a split identifier; quote the id")

    def scan_split_ids(self, where, obj):
        # Catches the v0.1 defect anywhere: an unquoted id with a comma splits
        # into a key ending in ')' with a null value, or into a stray '(' prefix.
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(k, str) and re.search(r"\)$", k) and v is None:
                    self.err(where, f"split identifier key {k!r}")
                if isinstance(v, str) and re.match(r"^D_\w+\([^)]*$", v):
                    self.err(where, f"truncated identifier {v!r}")
                self.scan_split_ids(where, v)
        elif isinstance(obj, list):
            for x in obj:
                self.scan_split_ids(where, x)

    def duty(self, where, d):
        self.keys(where, d, DUTY_KEYS)
        if "id" not in d or not isinstance(d["id"], str) or not DUTY_ID.match(d["id"]):
            self.err(where, f"malformed duty id {d.get('id')!r}")
        if "resolution" in d and d["resolution"] not in RESOLUTIONS:
            self.err(where, f"unknown resolution {d['resolution']!r}")

    def expect(self, where, e, tokens):
        self.keys(where, e, EXPECT_KEYS)
        if "disposition" in e and e["disposition"] not in DISPOSITIONS:
            self.err(where, f"unknown disposition {e['disposition']!r}")
        for rk in ("rule",):
            if rk in e and e[rk] not in self.rules:
                self.err(where, f"unknown rule {e[rk]!r}")
        for r in e.get("rules", []):
            if r not in self.rules:
                self.err(where, f"unknown rule {r!r}")
        for key in ("duties", "duties_created"):
            for i, d in enumerate(e.get(key, []) or []):
                self.duty(f"{where}.{key}[{i}]", d)
        tok = e.get("token")
        if isinstance(tok, str) and tok != "none":
            if not TOKEN_ID.match(tok):
                self.err(where, f"malformed token {tok!r}")
            tokens.add(tok)
        for t in (e.get("token_state") or {}):
            if t not in tokens:
                self.err(where, f"token_state for undeclared token {t!r}")

    def steps(self, where, steps, tokens):
        last = 0
        last_phase_step, last_phase = None, -1
        for i, s in enumerate(steps or []):
            w = f"{where}.steps[{i}]"
            self.keys(w, s, STEP_KEYS)
            n = s.get("step")
            if not isinstance(n, int) or n < 1:
                self.err(w, f"bad step number {n!r}")
            elif n < last:
                self.err(w, f"step {n} after step {last}")
            else:
                last = n
            for j, ev in enumerate(s.get("events", []) or []):
                ew = f"{w}.events[{j}]"
                t = ev.get("type")
                if t not in EVENT_FIELDS:
                    self.err(ew, f"unknown event type {t!r}")
                    continue
                self.keys(ew, ev, EVENT_FIELDS[t] | {"type"})
                for pk in ("from", "to"):
                    if pk in ev and isinstance(ev[pk], str) and ev[pk] not in self.parties:
                        self.err(ew, f"unknown party {ev[pk]!r}")
            if "propose" in s:
                p = s["propose"]
                self.keys(f"{w}.propose", p, PROPOSE_KEYS)
                if p.get("actor") not in self.parties:
                    self.err(w, f"unknown actor {p.get('actor')!r}")
            if "expect" in s:
                self.expect(f"{w}.expect", s["expect"], tokens)
            if "execute" in s:
                x = s["execute"]
                self.keys(f"{w}.execute", x, EXECUTE_KEYS)
                if x.get("actor") not in self.parties:
                    self.err(w, f"unknown actor {x.get('actor')!r}")
                if "token" in x and x["token"] not in tokens:
                    self.err(w, f"executes undeclared token {x['token']!r}")
            acts = [k for k in ("events", "propose", "execute") if k in s]
            if len(acts) > 1:
                self.err(w, f"a step entry may hold only one action, found {acts}; split it")
            phase = {"events": 0, "propose": 1, "execute": 2}[acts[0]] if acts else None
            if phase is not None:
                if n == last_phase_step and phase < last_phase:
                    self.err(w, f"{acts[0]} listed after a later phase in step {n}; list entries in phase order")
                if n != last_phase_step:
                    last_phase_step, last_phase = n, phase
                else:
                    last_phase = max(last_phase, phase)

    def trace(self, f, t, seen):
        w = f"{os.path.basename(f)}:{t.get('id')}"
        self.keys(w, t, TRACE_KEYS)
        self.scan_split_ids(w, t)
        for k in ("id", "title", "contracts"):
            if k not in t:
                self.err(w, f"missing {k}")
        if t.get("id") in seen:
            self.err(w, "duplicate id")
        seen.add(t.get("id"))
        if "setup" in t:
            self.keys(f"{w}.setup", t["setup"], SETUP_KEYS)
        tokens = set()
        self.steps(w, t.get("steps"), tokens)
        if "final" in t:
            self.keys(f"{w}.final", t["final"], FINAL_KEYS)
            for i, d in enumerate(t["final"].get("duties", []) or []):
                self.duty(f"{w}.final.duties[{i}]", d)
        if "steps" not in t and "variants" not in t:
            self.err(w, "no steps and no variants")
        for v in t.get("variants", []) or []:
            vw = f"{os.path.basename(f)}:{v.get('id')}"
            self.keys(vw, v, VARIANT_KEYS)
            if v.get("id") in seen:
                self.err(vw, "duplicate id")
            seen.add(v.get("id"))
            if v.get("mode") not in ("continue", "replace"):
                self.err(vw, f"variant mode must be continue or replace, got {v.get('mode')!r}")
            if v.get("mode") == "replace" and "steps" not in v:
                self.err(vw, "replace variant has no steps")
            if "setup" in v:
                self.keys(f"{vw}.setup", v["setup"], SETUP_KEYS)
            vtokens = set(tokens) if v.get("mode") == "continue" else set()
            self.steps(vw, v.get("steps"), vtokens)


def main(bundle):
    world = yaml.safe_load(open(os.path.join(bundle, "world_W0.yaml")))
    c = Checker(world)
    seen = set()
    count = 0
    for f in sorted(glob.glob(os.path.join(bundle, "traces", "*.yaml"))):
        text = open(f).read()
        for m in re.finditer(r"pending_spec\(", text):
            c.err(os.path.basename(f), "pending_spec assertion remains (counts as incomplete coverage)")
        data = yaml.safe_load(text)
        if not isinstance(data, list):
            c.err(f, "top level must be a list of traces")
            continue
        for t in data:
            c.trace(f, t, seen)
            count += 1 + len(t.get("variants", []) or [])
    for e in c.errors:
        print("ERROR", e)
    print(f"{count} traces and variants checked, {len(c.errors)} errors")
    return 1 if c.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
