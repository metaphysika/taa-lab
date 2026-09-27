"""Bounded, simulated authority and express-seat accounting for the follow-up study.

These are fallible standing logistics rules, not a natural-law core. A hold never
authorizes its shipment. The same ledger is available to every study arm.
"""
from dataclasses import dataclass, field


@dataclass
class Claim:
    claim_id: str
    demand_id: str
    target_id: str
    source_id: str
    evidence_status: str
    requires_settlement: bool
    authority_status: str
    deadline_step: int
    hold_until_step: int
    premise_version: int = 1
    units: int = 1
    reservation_status: str = "absent"
    reason: str = ""
    announced_step: int = 0
    history: list = field(default_factory=list)

    @classmethod
    def from_record(cls, record):
        return cls(**{key: value for key, value in record.items() if key in cls.__dataclass_fields__})

    def transition(self, step, status, reason):
        if self.reservation_status != status:
            self.reservation_status = status
            self.history.append({"step": step, "reservation": status, "reason": reason})


class ObligationLedger:
    """One controller-local ledger, reconciled after visible events and before each act."""

    def __init__(self, world, policy_enabled):
        self.world = world
        self.policy_enabled = policy_enabled
        self.claims = {r["claim_id"]: Claim.from_record(r) for r in world.claims}
        self.events = []
        self.max_pending_holds = world.resource_policy.get("max_pending_holds", 1)
        self._reply_cursor = 0
        self.reconcile()

    def _record(self, kind, **fields):
        self.events.append({"step": self.world.step, "kind": kind, **fields})

    def reconcile(self):
        """Take currently visible authoritative facts, then apply only valid scoped replies."""
        for record in self.world.claims:
            cid = record["claim_id"]
            if cid not in self.claims:
                self.claims[cid] = Claim.from_record(record)
                self.claims[cid].announced_step = self.world.step
                self._record("claim_announced", claim_id=cid)
            claim = self.claims[cid]
            if record.get("authority_status") in ("withdrawn", "denied"):
                if claim.authority_status != record["authority_status"]:
                    self._record("authority_change", claim_id=cid, old=claim.authority_status,
                                 new=record["authority_status"])
                claim.authority_status = record["authority_status"]
            claim.premise_version = record.get("premise_version", claim.premise_version)

        for reply in self.world.study_replies[self._reply_cursor:]:
            self._apply_reply(reply)
        self._reply_cursor = len(self.world.study_replies)

        # One authenticated demand gets at most one reservation. Duplicate claim IDs
        # neither add capacity nor reset the first claim's expiry.
        seen_demands = set()
        pending_used = 0
        booked = set(self.world.express["booked"]) if self.world.express else set()
        seats_left = (self.world.express["capacity"] - len(booked)
                      if self.world.express else 0)
        # A live approved claim takes priority over a pending hold. Within each
        # class, the earlier deadline wins, then the original announcement order.
        # This is a declared logistics rule, not a reviewer judgment.
        ordered = sorted(enumerate(self.claims.values()),
                         key=lambda pair: (pair[1].authority_status != "approved",
                                           pair[1].deadline_step, pair[0]))
        for _, claim in ordered:
            shipment = self.world.record(claim.target_id)
            canceled = shipment is not None and shipment.get("canceled", False)
            invalid = claim.authority_status in ("denied", "withdrawn", "expired") or canceled
            if invalid:
                claim.transition(self.world.step, "released", "authority or shipment no longer valid")
                continue
            if claim.demand_id in seen_demands:
                claim.transition(self.world.step, "released", "duplicate underlying demand")
                continue
            seen_demands.add(claim.demand_id)
            if claim.target_id in booked:
                claim.transition(self.world.step, "consumed", "express booking made")
                continue
            if not self.policy_enabled or claim.evidence_status != "supported" or not claim.source_id:
                claim.transition(self.world.step, "absent", "no qualifying standing hold")
                continue
            until = claim.hold_until_step if claim.authority_status == "pending" else claim.deadline_step + 1
            if self.world.step >= until:
                claim.transition(self.world.step, "released", "hold reached exclusive expiry")
                continue
            if claim.authority_status == "pending":
                if pending_used >= self.max_pending_holds:
                    claim.transition(self.world.step, "absent", "aggregate pending-hold limit")
                    continue
            if seats_left < claim.units:
                claim.transition(self.world.step, "absent", "no free seat for a hold")
                continue
            seats_left -= claim.units
            if claim.authority_status == "pending":
                pending_used += 1
            claim.transition(self.world.step, "held", "supported pending claim or approved commitment")
        self._sync_visible_status()

    def _apply_reply(self, reply):
        cid = reply.get("claim_id")
        claim = self.claims.get(cid)
        valid = (claim is not None and reply.get("source_id") == claim.source_id
                 and reply.get("target_id") == claim.target_id
                 and reply.get("scope") == "reroute_shipment"
                 and reply.get("premise_version") == claim.premise_version
                 and reply.get("decision") in ("approved", "denied")
                 and claim.authority_status == "pending")
        if valid:
            record = self.world.record(claim.target_id)
            valid = not (record is not None and record.get("canceled"))
        if not valid:
            self._record("invalid_settlement", reply=dict(reply), reason="scope, version, or live claim mismatch")
            return
        claim.authority_status = reply["decision"]
        self._record("settlement", claim_id=cid, decision=reply["decision"], source_id=claim.source_id)

    def _sync_visible_status(self):
        for record in self.world.claims:
            claim = self.claims[record["claim_id"]]
            record["authority_status"] = claim.authority_status
            record["reservation_status"] = claim.reservation_status

    def claim_for(self, target_id):
        matching = [c for c in self.claims.values() if c.target_id == target_id
                    and c.evidence_status == "supported" and c.source_id]
        return next((c for c in matching if c.authority_status in ("approved", "pending")),
                    matching[0] if matching else None)

    def authorization_error(self, target_id):
        claim = self.claim_for(target_id)
        if claim is None:
            return None
        if claim.authority_status != "approved":
            return f"{target_id} awaits a valid settlement" if claim.authority_status == "pending" else (
                f"{target_id} has {claim.authority_status} authority")
        if self.world.step > claim.deadline_step:
            return f"{target_id}'s approved authority lapsed after step {claim.deadline_step}"
        record = self.world.record(target_id)
        if record is None or record.get("canceled"):
            return f"{target_id} is absent or canceled"
        return None

    def capacity_error(self, target_id):
        if not self.policy_enabled or self.world.express is None:
            return None
        booked = set(self.world.express["booked"])
        if target_id in booked:
            return None
        held_by_others = sum(c.units for c in self.claims.values()
                             if c.reservation_status == "held" and c.target_id != target_id)
        free = self.world.express["capacity"] - len(booked) - held_by_others
        if free < 1:
            return f"express capacity reserved for {held_by_others} other supported claim(s)"
        return None

    def snapshot(self):
        return {"claims": [{"claim_id": c.claim_id, "demand_id": c.demand_id,
                             "target_id": c.target_id, "authority_status": c.authority_status,
                             "reservation_status": c.reservation_status,
                             "history": list(c.history)} for c in self.claims.values()],
                "events": list(self.events)}
