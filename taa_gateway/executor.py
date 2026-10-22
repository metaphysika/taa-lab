"""Revision-bound capabilities and rollback of actual locked working state.

Only trusted simulator sessions can register effects or call store primitives.
An agent presents its authenticated session and an opaque issued token ID.
"""
from dataclasses import dataclass

from jsonschema.exceptions import ValidationError

from taa_gateway import SCHEMA_VERSION as V
from taa_gateway.act import ToolRegistry
from taa_gateway.records import Write
from taa_gateway.rules import EvidenceView
from taa_gateway.schema import validate
from taa_gateway.serialization import canonical, copy_json, digest

FAULTS = ("after_validate", "after_stage", "during_effect_commit", "during_token_consumption",
          "during_duty_update", "during_receipt_write", "during_revision_advance")


@dataclass(frozen=True)
class EffectPlan:
    writes: tuple = ()
    notices: tuple = ()
    allocations: object = None
    cases: object = None
    duties: tuple = ()
    duty_actions: tuple = ()

    def json(self):
        return copy_json({"writes": [{"record": w.record_id, "kind": w.kind, "fields": w.fields} for w in self.writes],
                          "notices": list(self.notices), "allocations": self.allocations or {},
                          "cases": self.cases or {}, "duties": list(self.duties), "duty_actions": list(self.duty_actions)})


class ExecutionRefused(ValueError):
    pass


class InjectedFault(RuntimeError):
    def __init__(self, point, snapshot):
        self.point, self.snapshot = point, copy_json(snapshot)


class Runtime:
    def __init__(self, store, authority, gateway_session, pipeline, tools, *, token_lifetime=10, duty_engine=None):
        actor, channel = authority.identity(gateway_session, "capabilities")
        authority.identity(gateway_session, "execute_transaction")
        if channel != "gateway" or type(token_lifetime) is not int or token_lifetime < 1:
            raise ValueError("trusted gateway and positive token lifetime required")
        self.store, self.authority, self.gateway, self.pipeline = store, authority, gateway_session, pipeline
        self.tools, self.lifetime, self.writer = ToolRegistry(tools), token_lifetime, actor
        self.duty_engine = duty_engine

    def _plan(self, snapshot, name, args):
        tool = self.tools.get(name, args)
        if tool.stage is None:
            raise ExecutionRefused("refused_unimplemented_effect")
        view = EvidenceView(snapshot, tool.reads)
        plan = tool.stage(copy_json(args), view)
        if not isinstance(plan, EffectPlan):
            raise ValueError("registered effect must return an EffectPlan")
        value = plan.json()
        if len({w["record"] for w in value["writes"]}) != len(value["writes"]):
            raise ValueError("a transaction stages one version per record")
        return value, view.queries()

    def propose(self, session, raw):
        actor, _ = self.authority.identity(session, "propose")
        answer = {}
        def issue(state, events):
            # Validate/log even non-object JSON before reading proposal fields.
            decision = self.pipeline.evaluate(session, raw)
            key = digest({"actor": actor, "tool": raw.get("tool"), "args": raw.get("arguments"),
                          "revision": state["revision"]})
            previous = next((d for d in reversed(state["decisions"]) if d["key"] == key), None)
            if previous is not None:
                tid = previous["result"].get("token")
                if not tid or state["tokens"].get(tid, {}).get("status") == "live":
                    previous["repeats"] += 1
                    answer.update(copy_json(previous["result"]), fresh_evaluation=False,
                                  recorded_decision_returned=True, repeat_count=previous["repeats"])
                    events.append((state["step"], "recorded_decision", {"result": copy_json(answer), "raw": raw}))
                    return
            answer.update(decision, fresh_evaluation=True, recorded_decision_returned=False, repeat_count=0)
            if self.duty_engine is not None and state["step"] >= 1 and self.duty_engine.report_from_log(state, events):
                self.store.advance_revision(state, events)
                key = digest({"actor": actor, "tool": raw["tool"], "args": raw["arguments"], "revision": state["revision"]})
            if decision["disposition"] == "PERMIT":
                plan, reads = self._plan(state, raw["tool"], raw["arguments"])
                tid, wid = "T" + str(len(state["tokens"]) + 1), "W" + str(len(state["warrants"]) + 1)
                basis = copy_json(decision["justification"])
                if basis is None:
                    raise ExecutionRefused("refused_missing_complete_justification")
                basis["rule_facts"].append({"rule_id": "staged-effect", "rule_version": 1,
                                            "result": "satisfied", "queries": reads})
                warrant = {"schema_version": V, "id": wid, "act_description_hash": decision["act_description_hash"],
                           "justification": basis, "state_revision": state["revision"],
                           "disposition": "PERMIT", "status": "live"}
                certificate = {"schema_version": V, "id": tid, "warrant_id": wid, "acting_party": actor,
                               "exact_argument_digest": digest({"tool": raw["tool"], "arguments": raw["arguments"]}),
                               "state_revision": state["revision"], "expires_at_step": state["step"] + self.lifetime}
                validate("warrant", warrant)
                validate("token", certificate)
                state["warrants"][wid] = warrant
                state["tokens"][tid] = {"certificate": certificate, "status": "live", "tool": raw["tool"],
                                        "args": copy_json(raw["arguments"]), "plan_hash": digest(plan),
                                        "basis_hash": digest(decision["justification"])}
                answer.update(token=tid, executable=True, token_expires_at=certificate["expires_at_step"])
                events.append((state["step"], "token_issued", {"token": certificate, "warrant": warrant}))
            state["decisions"].append({"key": key, "actor": actor, "tool": raw["tool"],
                                       "args": copy_json(raw["arguments"]), "revision": state["revision"],
                                       "result": copy_json(answer), "repeats": 0})
            events.append((state["step"], "decision", {"result": copy_json(answer), "raw": raw}))
        try:
            self.store.gateway_mutation(self.gateway, "capabilities", issue)
        except ExecutionRefused as error:
            self.store.audit("capability_not_issued", {"reason": str(error), "raw": raw})
            answer = {"call_result": str(error), "evaluated": True, "action_executed": False, "token": None}
        except (ValueError, ValidationError) as error:
            answer = {"call_result": "rejected_unregistered_tool" if "unregistered tool" in str(error) else "rejected_arguments",
                      "evaluated": False, "action_executed": False, "reason": str(error), "token": None}
        return copy_json(answer)

    def execute(self, session, token_id, *, tool=None, arguments=None, fault=None):
        actor, _ = self.authority.identity(session, "execute")
        if fault is not None and fault not in FAULTS:
            raise ValueError("unknown fault point")
        result = {}
        def transaction(state, events):
            def at(point):
                if point == fault:
                    raise InjectedFault(point, state)
            row = state["tokens"].get(token_id)
            if row is None:
                raise ExecutionRefused("refused_no_token" if token_id is None else "refused_unknown_token")
            cert = row["certificate"]
            if actor != cert["acting_party"]:
                raise ExecutionRefused("refused_wrong_actor")
            if row["status"] == "consumed":
                raise ExecutionRefused("refused_token_consumed")
            if state["step"] >= cert["expires_at_step"]:
                raise ExecutionRefused("refused_token_expired")
            if state["revision"] != cert["state_revision"]:
                raise ExecutionRefused("refused_stale_revision")
            warrant = state["warrants"][cert["warrant_id"]]
            if row["status"] != "live" or warrant["status"] != "live":
                raise ExecutionRefused("refused_token_not_live")
            name = row["tool"] if tool is None else tool
            args = row["args"] if arguments is None else arguments
            if digest({"tool": name, "arguments": args}) != cert["exact_argument_digest"]:
                raise ExecutionRefused("refused_argument_mismatch")
            current = self.pipeline.assess_snapshot(state, actor, name, args)
            if (current["disposition"] != "PERMIT" or current["act_description_hash"] != warrant["act_description_hash"] or
                    digest(current["justification"]) != row["basis_hash"]):
                raise ExecutionRefused("refused_revalidation")
            at("after_validate")
            plan, _ = self._plan(state, name, args)
            if digest(plan) != row["plan_hash"]:
                raise ExecutionRefused("refused_staging_mismatch")
            at("after_stage")
            versions, committed = [], []
            for change in plan["writes"]:
                written = self.store.append_write(state, events, self.gateway, "execute_transaction",
                              Write(change["record"], change["kind"], change["fields"], cert["warrant_id"]))
                versions.append({"record_id": written["id"], "record_version": written["version"]})
                committed.append({"record": written["id"], "kind": written["kind"], **copy_json(written["fields"])})
                at("during_effect_commit")
            state["notices"].extend(copy_json(plan["notices"]))
            state["allocations"].update(copy_json(plan["allocations"]))
            state["cases"].update(copy_json(plan["cases"]))
            at("during_effect_commit")
            row["status"] = "consumed"
            warrant["status"] = "consumed"
            at("during_token_consumption")
            for duty in plan["duties"]:
                self.append_duty(state, events, duty, cert["warrant_id"])
            for action in plan["duty_actions"]:
                if self.duty_engine is None:
                    raise ExecutionRefused("refused_unimplemented_duty_action")
                self.duty_engine.apply_action(state, events, action, actor, cert["warrant_id"])
            if self.duty_engine is not None:
                self.duty_engine.reconcile_mutation(state, events)
            at("during_duty_update")
            receipt = {"schema_version": V, "id": "receipt:" + str(len(state["receipts"]) + 1),
                       "warrant_id": cert["warrant_id"], "token_id": token_id, "acting_party": actor,
                       "pre_transaction_revision": state["revision"], "committed_revision": state["revision"] + 1,
                       "effect": dict(plan, committed=committed,
                                      duty_state=copy_json(state["duty_records"]),
                                      allocations_committed=copy_json(state["allocations"]),
                                      cases_committed=copy_json(state["cases"])), "record_versions": versions}
            validate("receipt", receipt)
            state["receipts"].append(receipt)
            at("during_receipt_write")
            self.store.advance_revision(state, events)
            at("during_revision_advance")
            result.update(execute_result="committed", committed=committed, action_executed=True,
                          validation_compares="pre_transaction_revision")
            events.append((state["step"], "receipt", receipt))
        try:
            self.store.gateway_mutation(self.gateway, "execute_transaction", transaction)
        except InjectedFault as error:
            self.store.audit("execution_rolled_back", {"token": token_id, "fault": error.point,
                                                       "partial_state": error.snapshot,
                                                       "restored_state_hash": digest(self.store.snapshot())})
            result = {"execute_result": "failed", "action_executed": False, "committed": []}
        except (ExecutionRefused, ValidationError, ValueError) as error:
            self.store.audit("execution_refused", {"token": token_id, "actor": actor, "reason": str(error)})
            result = {"execute_result": str(error) if isinstance(error, ExecutionRefused) else "failed",
                      "action_executed": False, "committed": []}
        return copy_json(result)

    def withdraw(self, session, token_id):
        actor, _ = self.authority.identity(session, "withdraw")
        def change(state, events):
            row = state["tokens"].get(token_id)
            if row is None or row["certificate"]["acting_party"] != actor:
                raise ExecutionRefused("refused_wrong_actor")
            if row["status"] != "live":
                raise ExecutionRefused("refused_token_not_live")
            row["status"] = "withdrawn"
            state["warrants"][row["certificate"]["warrant_id"]]["status"] = "withdrawn"
            self.store.advance_revision(state, events)
            events.append((state["step"], "token_withdrawn", {"token": token_id, "actor": actor}))
        self.store.gateway_mutation(self.gateway, "capabilities", change)

    def append_duty(self, state, events, duty, under_warrant=None):
        self.store.append_duty(state, events, duty, self.writer, under_warrant)
