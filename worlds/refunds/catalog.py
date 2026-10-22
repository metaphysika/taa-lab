"""Read independently authored development keys unchanged; never synthesize them."""
from copy import deepcopy
import hashlib

from tests.trace_support.bundle import BUNDLE, ZIP_HASH, cases, world

PAIRS = {
    "wrongful_order": ("T01", "T02"),
    "evidence_correction": ("T03", "T04"),
    "revocation": ("T05", "T06"),
    "pressure": ("T07", "T08"),
    "open_duty": ("T09", "T10"),
}


def catalog():
    by_id = {c["id"]: c for c in cases()}
    return [deepcopy(by_id[identity]) for pair in PAIRS.values() for identity in pair]


def inputs_only(case):
    """Pass only simulator inputs to controllers other than the key follower."""
    result = {"id": case["id"], "trace": {"setup": deepcopy(case["trace"].get("setup", {})), "steps": []}}
    for entry in case["trace"]["steps"]:
        result["trace"]["steps"].append({k: deepcopy(v) for k, v in entry.items() if k in ("step", "events", "propose", "execute", "proposal_origin")})
    return result


def provenance():
    return {"split": "development", "key_author": "Claude", "bundle_version": "0.2.2", "zip_sha256": ZIP_HASH,
            "world_sha256": hashlib.sha256((BUNDLE / "world_W0.yaml").read_bytes()).hexdigest(),
            "pairs": PAIRS, "scope": "Reviewed development keys; not held-out empirical evidence"}
