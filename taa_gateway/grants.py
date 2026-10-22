"""Read-only grant-path checks; issuance/revocation transactions are later stages."""
from taa_gateway.schema import validate
from taa_gateway.serialization import canonical, copy_json
from taa_gateway.rules import EvidenceView


class GrantPolicy:
    """Fixed simulator standing, one level of delegation, no grant fragments.

    Standing maps roster jurisdictions to action types they may grant.
    Scope maps resource keys to exact values or allowed-value lists. Resource
    values come from the registered tool's trusted projection, never claims.
    """
    def __init__(self, standing, principal, *, delegation_action="grant_refund_authority",
                 condition_kinds=()):
        self.__standing = copy_json(standing)
        self.__principal = principal
        self.__delegation_action = delegation_action
        self.__condition_kinds = tuple(condition_kinds)

    def candidates(self, snapshot):
        view = EvidenceView(snapshot, ("grant",))
        grants = view.records("grant")
        for rid, grant in grants:
            validate("grant", grant)
            if rid != grant["id"]:
                raise ValueError("grant record identity mismatch")
        return grants, view.queries()

    def check(self, snapshot, grant, actor, tool, resources):
        view = EvidenceView(snapshot, ("grant", "purpose", "party") + self.__condition_kinds)
        roster = {}
        for rid, party in view.records("party"):
            validate("party", party)
            if rid != party["id"]:
                raise ValueError("roster record identity mismatch")
            roster[rid] = party
        reasons, unknown, chain = [], [], []
        current = grant
        seen = set()
        while current is not None:
            validate("grant", current)
            if current["id"] in seen or len(chain) > 1:
                reasons.append("cyclic or deeper-than-supported grant ancestry")
                break
            seen.add(current["id"])
            chain.append(current)
            if current["status"] != "live" or snapshot["step"] >= current["expires_at_step"]:
                reasons.append("grant is not live: " + current["id"])
            party = roster.get(current["grantor"])
            permitted = set() if party is None else {
                action for jurisdiction in party["jurisdictions"] for action in self.__standing.get(jurisdiction, [])}
            if any(action not in permitted for action in current["action_types"]):
                reasons.append("grantor lacks standing: " + current["id"])
            for key, allowed in current["resource_scope"].items():
                if key not in resources or resources[key] is None:
                    unknown.append("missing scope resource: " + key)
                elif not any(canonical(resources[key]) == canonical(value)
                             for value in (allowed if type(allowed) is list else [allowed])):
                    reasons.append("outside scope: " + key)
            for condition in current["live_conditions"]:
                if set(condition) != {"record_id", "kind", "field", "equals"}:
                    raise ValueError("unsupported live-condition form")
                fact = view.read(condition["record_id"], condition["kind"])
                if fact is None or condition["field"] not in fact:
                    unknown.append("unknown live condition: " + condition["record_id"])
                elif canonical(fact[condition["field"]]) != canonical(condition["equals"]):
                    reasons.append("failed live condition: " + condition["record_id"])
            parent_id = current["parent_grant"]
            if parent_id is None:
                break
            parent = view.read(parent_id, "grant")
            if parent is None:
                reasons.append("missing grant ancestor")
                break
            validate("grant", parent)
            if (parent["id"] != parent_id or current["grantor"] != parent["grantee"] or
                    self.__delegation_action not in parent["action_types"] or
                    current["purpose_id"] != parent["purpose_id"]):
                reasons.append("incoherent grant ancestry")
            current = parent
        if grant["grantee"] != actor or tool.name not in grant["action_types"]:
            reasons.append("grant does not cover acting party and tool")
        purpose = view.read(grant["purpose_id"], "purpose")
        if purpose is None:
            unknown.append("missing purpose record")
        else:
            validate("purpose", purpose)
            if (purpose["id"] != grant["purpose_id"] or purpose["principal"] != self.__principal or
                    purpose["id"] not in tool.purposes):
                reasons.append("grant purpose does not authorize this tool")
        return {"id": tool.authorization_rule, "version": 1, "stage": "authority",
                "result": "violated" if reasons else "unknown" if unknown else "satisfied",
                "disposition": "REFUSE" if reasons else "HOLD" if unknown else "PERMIT",
                "reason": "; ".join(reasons + unknown), "queries": view.queries(),
                "grant": copy_json(grant), "purpose": copy_json(purpose), "chain": copy_json(chain),
                "alternative": None, "prohibited_elements": []}
