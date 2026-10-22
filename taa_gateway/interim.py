"""IR1's narrow, complete rule-based authority path, not a revived grant."""
from taa_gateway import SCHEMA_VERSION as V
from taa_gateway.grants import GrantPolicy
from taa_gateway.rules import EvidenceView
from taa_gateway.serialization import canonical


class RefundGrantPolicy(GrantPolicy):
    def __init__(self, *args, interim_principal, interim_purpose, **kwargs):
        super().__init__(*args, **kwargs)
        self.principal, self.purpose = interim_principal, interim_purpose

    def _offers(self, snapshot, actor, tool, resources):
        view = EvidenceView(snapshot, ("duty",))
        offers = []
        if tool.name not in ("message_party", "accept_duty"):
            return offers, view.queries()
        for did, duty in view.records("duty"):
            window = duty.get("offer_deadline_step")
            if (tool.name == "accept_duty" and duty["resolution"] == "unresolved" and duty["offered_to"] == actor and
                    type(window) is int and snapshot["step"] < window):
                offers.append(("ACCEPT:" + did, {"schema_version": V, "id": "ACCEPT:" + did,
                    "parent_grant": None, "grantor": self.principal, "grantee": actor,
                    "action_types": ["accept_duty"], "resource_scope": {"duty": did}, "limits": {},
                    "purpose_id": self.purpose, "live_conditions": [], "expires_at_step": window, "status": "live"}))
                continue
            if tool.name != "message_party":
                continue
            if (duty["owner"] != actor or duty["resolution"] != "unresolved" or not duty["offered_to"] or
                    type(window) is not int or snapshot["step"] >= window or
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
        if grant["id"].startswith(("IR1:", "ACCEPT:")):
            offers, queries = self._offers(snapshot, actor, tool, resources)
            result["queries"].extend(queries)
            if not any(canonical(g) == canonical(grant) for _, g in offers):
                result.update(result="violated", disposition="REFUSE", reason="interim authority is no longer live")
            result["authority_basis"] = "IR1" if grant["id"].startswith("IR1:") else "transfer_offer"
        return result
