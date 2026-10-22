"""Stage 4: snapshot evaluation, not executable permission.

The executor, token lifecycle, independent duty engine and report dispatch are
stages 5–6. A PERMIT here issues no token and cannot change protected state.
"""
from jsonschema.exceptions import ValidationError

from taa_gateway.act import ToolRegistry
from taa_gateway.orders import StoredOrders
from taa_gateway.rules import (DISPOSITIONS, STAGES, EvidenceView, evaluate_rule,
                               strictest)
from taa_gateway.serialization import canonical, copy_json, digest


class StaleEvaluation(ValueError):
    pass


class Pipeline:
    def __init__(self, store, orders, tools, grant_policy, rules, *, reserved_questions=None):
        tools = tuple(tools)
        self.__store, self.__orders = store, orders
        self.__tools = ToolRegistry(tools)
        self.__grants = grant_policy
        self.__rules = tuple(sorted(rules, key=lambda r: (STAGES.index(r.kind), r.id)))
        if len({r.id for r in self.__rules}) != len(self.__rules):
            raise ValueError("rule identities must be unique")
        reserved_ids = {tool.authorization_rule for tool in tools} | {
            "registered-effect-description", "authorization-rule-missing", "stored-order-context"}
        if any(rule.id in reserved_ids or rule.id.startswith("per-refund-cap:") for rule in self.__rules):
            raise ValueError("rule identity collides with a built-in check")
        self.__questions = copy_json(reserved_questions or {})
        self.__cache = {}

    def evaluate(self, session, raw):
        normalized = self.__orders.proposal(session, raw)["proposal"]
        # Validation precedes description, rules, grant lookup and cache access.
        self.__tools.get(normalized["tool"], normalized["arguments"])
        snapshot = self.__store.snapshot()
        identity = {"actor": normalized["acting_party"], "tool": normalized["tool"],
                    "arguments": normalized["arguments"], "revision": snapshot["revision"]}
        key = digest(identity)
        cached = key in self.__cache
        result = copy_json(self.__cache[key]) if cached else self._assess(snapshot, identity)
        if self.__store.revision != snapshot["revision"]:
            raise StaleEvaluation("world changed during snapshot evaluation; resubmit")
        result.update(recorded_decision_returned=cached, fresh_evaluation=not cached,
                      executable=False, token=None)
        # Claims are retained verbatim, but were never passed to a predicate.
        self.__store.audit("pipeline_decision", {"proposal": normalized, "decision": result})
        self.__cache[key] = copy_json(result)
        return copy_json(result)

    def _assess(self, snapshot, identity, *, fixed_grant=None, allow_alternative=True):
        tool = self.__tools.get(identity["tool"], identity["arguments"])
        view = EvidenceView(snapshot, tool.reads)
        act, resources = self.__tools.describe(tool, identity["arguments"], view)
        # Prohibitions see effects and trusted records, not an issuer or grant.
        effects_context = {"tool": tool.name, "arguments": identity["arguments"],
                           "act": act, "resources": resources}
        prohibitions = [evaluate_rule(rule, effects_context, snapshot, self.__questions)
                        for rule in self.__rules if rule.kind == "prohibition" and
                        (not rule.tools or tool.name in rule.tools)]
        if fixed_grant is not None:
            candidates, discovery = [(fixed_grant["id"], fixed_grant)], []
        elif tool.authorization_rule is None:
            candidates, discovery = [(None, None)], []
        else:
            candidates, discovery = self.__grants.candidates(snapshot)
            candidates = [(rid, grant) for rid, grant in candidates if grant["grantee"] == identity["actor"]]
            if not candidates:
                candidates = [(None, None)]
        paths = []
        for _, grant in candidates:
            if tool.authorization_rule is None:
                authority = {"id": "authorization-rule-missing", "version": 1, "stage": "authority",
                             "result": "unknown", "disposition": "REFER", "queries": discovery,
                             "reason": "registered act has no authorization rule",
                             "referral": copy_json(tool.referral), "grant": None, "purpose": None,
                             "chain": [], "alternative": None, "prohibited_elements": []}
            elif grant is None:
                authority = {"id": tool.authorization_rule, "version": 1, "stage": "authority",
                             "result": "violated", "disposition": "REFUSE", "queries": discovery,
                             "reason": "no grant for the acting party", "grant": None, "purpose": None,
                             "chain": [], "alternative": None, "prohibited_elements": []}
            else:
                authority = self.__grants.check(snapshot, grant, identity["actor"], tool, resources)
                authority["queries"] = discovery + authority["queries"]
            checks = copy_json(prohibitions) + [authority]
            context = dict(effects_context, actor=identity["actor"], grant=authority["grant"],
                           purpose=authority["purpose"])
            for stage in STAGES[2:]:
                if stage == "determination":
                    checks.extend(self._limits(tool, identity["arguments"], authority["chain"]))
                for rule in self.__rules:
                    if rule.kind == stage and (not rule.tools or tool.name in rule.tools):
                        checks.append(evaluate_rule(rule, context, snapshot, self.__questions))
            alternative = None
            failures = [c for c in checks if c["disposition"] != "PERMIT"]
            if (allow_alternative and grant is not None and failures and
                    all(c["stage"] in ("support", "determination") and c["result"] == "violated"
                        for c in failures)):
                for check in failures:
                    suggested = check.get("alternative")
                    if not suggested:
                        continue
                    try:
                        alt_tool = self.__tools.get(suggested["tool"], suggested["arguments"])
                        amount_key = alt_tool.amount_argument
                        if amount_key and (type(suggested["arguments"].get(amount_key)) is not int or
                                           suggested["arguments"][amount_key] <= 0):
                            continue
                        reassessed = self._assess(snapshot, dict(identity, tool=suggested["tool"],
                                                               arguments=suggested["arguments"]),
                                                  fixed_grant=grant, allow_alternative=False)
                    except (ValueError, KeyError, ValidationError):
                        # A malformed suggestion is never a route to permission.
                        continue
                    if reassessed["disposition"] == "PERMIT":
                        alternative = copy_json(suggested)
                        for failed in failures:
                            failed["disposition"] = "ALTERNATIVE"
                        break
            aggregate, stages = "PERMIT", []
            for stage in STAGES:
                members = [c for c in checks if c["stage"] == stage]
                aggregate = strictest(aggregate, *(c["disposition"] for c in members))
                stages.append({"stage": stage, "disposition": aggregate,
                               "rules": [c["id"] for c in members]})
            basis = None
            if grant is not None and authority["purpose"] is not None:
                basis = {"grant_id": grant["id"], "purpose_id": grant["purpose_id"],
                         "scope": copy_json(grant["resource_scope"]),
                         "rule_facts": [{"rule_id": c["id"], "rule_version": c["version"],
                                         "result": c["result"], "queries": c["queries"]} for c in checks]}
                basis["rule_facts"].insert(0, {"rule_id": "registered-effect-description", "rule_version": 1,
                                              "result": "satisfied", "queries": view.queries()})
            paths.append({"disposition": aggregate, "act": act, "act_description_hash": digest(act),
                          "state_revision": snapshot["revision"], "acting_party": identity["actor"],
                          "arguments": copy_json(identity["arguments"]), "justification": basis,
                          "checks": checks, "stages": stages, "alternative": alternative})
        # An admissible path must be complete by itself. No result/check is
        # borrowed from another grant, even if that would improve the decision.
        chosen = max(paths, key=lambda path: DISPOSITIONS.index(path["disposition"]))
        order_view = EvidenceView(snapshot, ("stored_order",))
        associated, attributed = [], []
        for _, order in order_view.records("stored_order"):
            if order["envelope"]["recipient"] != identity["actor"]:
                continue
            matches = [effect for effect in order["requested_effects"] if effect["tool"] == tool.name and all(
                key in identity["arguments"] and canonical(identity["arguments"][key]) == canonical(value)
                for key, value in effect["arguments"].items())]
            if not matches:
                continue
            associated.append(order["id"])
            for check in chosen["checks"]:
                if check["stage"] != "prohibition" or check["result"] != "violated":
                    continue
                for element in check["prohibited_elements"]:
                    requested = False
                    if set(element) == {"assertion"}:
                        requested = StoredOrders.requested_by(order, tool.name, identity["arguments"], element["assertion"])
                    elif set(element) == {"arguments"} and element["arguments"]:
                        requested = any(all(key in effect["arguments"] and
                            canonical(effect["arguments"][key]) == canonical(value)
                            for key, value in element["arguments"].items()) for effect in matches)
                    else:
                        raise ValueError("unsupported prohibited-element attribution")
                    if requested:
                        attributed.append({"order_id": order["id"],
                                           "issuer": order["envelope"]["authenticated_sender"],
                                           "rule": check["id"], "element": copy_json(element)})
        chosen["associated_orders"] = associated
        chosen["report_candidates"] = attributed
        chosen["order_queries"] = order_view.queries()
        if chosen["justification"] is not None:
            chosen["justification"]["rule_facts"].append({"rule_id": "stored-order-context", "rule_version": 1,
                                                        "result": "satisfied", "queries": order_view.queries()})
        chosen["candidate_dispositions"] = [{"grant": p["justification"]["grant_id"] if p["justification"] else None,
                                              "disposition": p["disposition"]} for p in paths]
        return copy_json(chosen)

    @staticmethod
    def _limits(tool, arguments, chain):
        checks = []
        for grant in chain:
            if set(grant["limits"]) - {"per_refund_max"}:
                raise ValueError("unsupported grant limits; a policy must not silently ignore them")
            if not tool.amount_argument or "per_refund_max" not in grant["limits"]:
                continue
            maximum, amount = grant["limits"]["per_refund_max"], arguments.get(tool.amount_argument)
            if type(maximum) is not int or maximum < 0 or type(amount) is not int or amount <= 0:
                raise ValueError("refund limits require positive integer amounts and a nonnegative cap")
            failed = amount > maximum
            args = copy_json(arguments)
            args[tool.amount_argument] = maximum
            checks.append({"id": "per-refund-cap:" + grant["id"], "version": 1, "stage": "determination",
                           "result": "violated" if failed else "satisfied",
                           "disposition": "REFUSE" if failed else "PERMIT", "queries": [],
                           "reason": "grant per-refund maximum", "prohibited_elements": [],
                           "alternative": {"tool": tool.name, "arguments": args} if failed and maximum > 0 else None})
        return checks
