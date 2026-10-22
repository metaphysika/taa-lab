"""Trusted rule callbacks and tracked snapshot reads for the stage 4 evaluator.

Callbacks are simulator policy code, never supplied by a proposal or reviewer.
No reference-model decision, authorization or transaction code is imported.
"""
from dataclasses import dataclass

from taa_gateway.schema import validate
from taa_gateway.serialization import copy_json, digest

STAGES = ("prohibition", "authority", "support", "determination", "duty")
DISPOSITIONS = ("PROHIBIT", "REFUSE", "REFER", "HOLD", "ALTERNATIVE", "PERMIT")


def strictest(*values):
    if not values or any(value not in DISPOSITIONS for value in values):
        raise ValueError("a disposition must use the declared ordering")
    return min(values, key=DISPOSITIONS.index)


@dataclass(frozen=True)
class Outcome:
    result: str
    reason: str = ""
    question: object = None
    alternative: object = None
    prohibited_elements: tuple = ()
    referral: object = None

    def __post_init__(self):
        validate("rule_result", self.result)
        if self.question is not None and self.result != "unknown":
            raise ValueError("only an unknown result can reserve a question")
        if self.referral is not None and (self.result != "unknown" or self.question is not None):
            raise ValueError("a counsel referral is distinct from a reserved question")
        if self.alternative is not None:
            validate("scope", self.alternative)
        copy_json(list(self.prohibited_elements))


@dataclass(frozen=True)
class Rule:
    id: str
    version: int
    kind: str
    reads: tuple
    predicate: object
    tools: tuple = ()
    text: str = ""

    def __post_init__(self):
        if (not isinstance(self.id, str) or not self.id or type(self.version) is not int or self.version < 1 or
                self.kind not in ("prohibition", "support", "determination", "duty") or
                not callable(self.predicate)):
            raise ValueError("invalid trusted rule definition")
        object.__setattr__(self, "reads", tuple(self.reads))
        object.__setattr__(self, "tools", tuple(self.tools))
        if not all(isinstance(value, str) and value for value in self.reads + self.tools):
            raise ValueError("read kinds and tool identities must be nonempty strings")
        if self.kind == "prohibition" and set(self.reads) & {"grant", "purpose", "stored_order"}:
            raise ValueError("prohibitions cannot condition on authority or an order's issuer")


class EvidenceView:
    """A private snapshot; every read names a kind and is captured by version.

    @kind selectors are synthetic query identities, not record references.
    They retain the complete matching version set, including the empty set.
    Global revision invalidation (stage 5) is still required on insertions.
    """
    def __init__(self, snapshot, reads):
        self.__records = copy_json(snapshot["records"])
        for rid, versions in snapshot.get("duty_records", {}).items():
            if rid in self.__records:
                raise ValueError("duty/world identity collision")
            self.__records[rid] = copy_json(versions)
        if any(rid.startswith("@") for rid in self.__records):
            raise ValueError("@ is reserved for query identities")
        self.__reads = frozenset(reads)
        self.__queries = []

    def _allow(self, kind):
        if kind not in self.__reads:
            raise ValueError("undeclared evidence kind: " + kind)

    def read(self, record_id, kind):
        self._allow(kind)
        history = self.__records.get(record_id, [])
        record = history[-1] if history else None
        self.__queries.append({"record_id": record_id,
                               "version": record["version"] if record else None,
                               "value": copy_json(record)})
        if not record or record["kind"] != kind or not record["evidential"]:
            return None
        return copy_json(record["fields"])

    def records(self, kind):
        self._allow(kind)
        matches = [history[-1] for _, history in sorted(self.__records.items())
                   if history and history[-1]["kind"] == kind]
        self.__queries.append({"record_id": "@kind:" + kind, "version": None,
                               "value": copy_json(matches)})
        return [(r["id"], copy_json(r["fields"])) for r in matches if r["evidential"]]

    def queries(self):
        # Deduplicate identical reads without losing deterministic read order.
        result, seen = [], set()
        for query in self.__queries:
            key = digest(query)
            if key not in seen:
                result.append(copy_json(query))
                seen.add(key)
        return result


def evaluate_rule(rule, context, snapshot, reserved_questions):
    view = EvidenceView(snapshot, rule.reads)
    outcome = rule.predicate(copy_json(context), view)
    if not isinstance(outcome, Outcome):
        raise ValueError("a trusted predicate must return an explicit three-valued Outcome")
    disposition = "PERMIT"
    referral = None
    if outcome.result == "violated":
        disposition = "PROHIBIT" if rule.kind == "prohibition" else "REFUSE"
    elif outcome.result == "unknown":
        disposition = "HOLD"
        if outcome.referral is not None:
            referral, disposition = copy_json(outcome.referral), "REFER"
        if outcome.question is not None:
            if outcome.question not in reserved_questions:
                raise ValueError("a rule named an undeclared reserved question")
            referral = copy_json(reserved_questions[outcome.question])
            disposition = "REFER"
    return {"id": rule.id, "version": rule.version, "stage": rule.kind,
            "result": outcome.result, "disposition": disposition,
            "reason": outcome.reason, "question": outcome.question, "referral": referral,
            "alternative": copy_json(outcome.alternative),
            "prohibited_elements": copy_json(list(outcome.prohibited_elements)),
            "queries": view.queries()}
