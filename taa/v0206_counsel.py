"""Factual checks for v0.20.6. The v0.20.5 checker remains frozen."""


FACTUAL_BASES = {"capacity", "reservation", "claim_status"}


def ledger_contradictions(reply, world):
    """Check cited records only when the reviewer makes a factual objection."""
    if reply.get("disposition") not in ("prohibit", "obtain_evidence", "refer"):
        return []
    if reply.get("basis_type") not in FACTUAL_BASES:
        return []
    citations = reply.get("ledger_citations")
    if not isinstance(citations, list) or not citations:
        return ["no ledger citation supplied for a factual objection"]

    errors = []
    claims = {claim["claim_id"]: claim for claim in world.claims}
    for citation in citations:
        if not isinstance(citation, dict):
            errors.append("citation is not an object")
            continue
        record_id = citation.get("record_id")
        if record_id == "express":
            record = world.express
            if record is None:
                errors.append("this scenario has no configured express-seat limit")
                continue
        else:
            record = claims.get(record_id)
        field = citation.get("field")
        if record is None or field not in record:
            errors.append("unknown ledger record or field: " + str(record_id))
        elif record[field] != citation.get("value"):
            errors.append(f"{record_id}.{field} is {record[field]!r}, "
                          f"not {citation.get('value')!r}")
    return errors
