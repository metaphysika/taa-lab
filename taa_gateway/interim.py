"""IR1's narrow, complete rule-based authority path, not a revived grant."""
from taa_gateway import SCHEMA_VERSION as V
from taa_gateway.grants import GrantPolicy
from taa_gateway.rules import EvidenceView
from taa_gateway.serialization import canonical
from taa_gateway.offers import entries


class RefundGrantPolicy(GrantPolicy):
    def __init__(self, *args, interim_principal, interim_purpose, **kwargs):
        super().__init__(*args, **kwargs)
        self.principal, self.purpose = interim_principal, interim_purpose

    def _offers(self, snapshot, actor, tool, resources):
        view = EvidenceView(snapshot, ("duty",))
        offers = []
        if tool.name not in ("message_party",):
            return offers, view.queries()
        for did, duty in view.records("duty"):
            live = [o for o in entries(duty) if o["status"] == "live" and snapshot["step"] < o["expires"]]
            window = max((o["expires"] for o in live), default=None)
            if (tool.name != "message_party" or duty["owner"] != actor or duty["resolution"] != "unresolved" or not live or
                    duty["interim_rule"].get("id") != "IR1" or not duty["interim_rule"].get("authority_lost")):
                continue
            grant = {"schema_version": V, "id": "IR1:" + did, "parent_grant": None,
                     "grantor": self.principal, "grantee": actor, "action_types": ["message_party"],
                     "resource_scope": {"claim": duty["case_id"], "to": duty["claimant"],
                                        "template": ["claim_referred", "refund_held"]},
                     "limits": {}, "purpose_id": self.purpose, "live_conditions": [],
                     "expires_at_step": window, "status": "live"}
            offers.append((grant["id"], grant))
        return offers, view.queries()

    def interim_candidates(self, snapshot, actor, tool, resources):
        return self._offers(snapshot, actor, tool, resources)[0]

    def check(self, snapshot, grant, actor, tool, resources):
        result = super().check(snapshot, grant, actor, tool, resources)
        if grant["id"].startswith("IR1:"):
            offers, queries = self._offers(snapshot, actor, tool, resources)
            result["queries"].extend(queries)
            if not any(canonical(g) == canonical(grant) for _, g in offers):
                result.update(result="violated", disposition="REFUSE", reason="interim authority is no longer live")
            result["authority_basis"] = "IR1"
        return result
