"""Trusted requested effects and simulator-set actors (v0.3.1 Q3)."""
from taa_gateway import SCHEMA_VERSION
from taa_gateway.records import Write
from taa_gateway.schema import validate
from taa_gateway.serialization import canonical, copy_json


class StoredOrders:
    def __init__(self, store, authority, inbox_session):
        _, channel = authority.identity(inbox_session, "receive_order")
        if channel != "gateway":
            raise ValueError("the simulator owns the order inbox")
        self.__store, self.__authority, self.__inbox = store, authority, inbox_session

    def receive(self, envelope):
        envelope = self.__authority.verify(envelope)
        if envelope["message_kind"] != "order" or envelope["step"] > self.__store.step:
            raise ValueError("not an available stored order")
        order = {"schema_version": SCHEMA_VERSION, "id": envelope["message_id"],
                 "envelope": envelope, "requested_effects": envelope["content"].get("requested_effects")}
        validate("stored_order", order)
        if self.__store.read(order["id"]) is not None:
            raise ValueError("order already stored")
        return self.__store.publish(self.__inbox, "receive_order", [Write(order["id"], "stored_order", order)])

    def proposal(self, session, raw):
        actor, _ = self.__authority.identity(session, "propose")
        raw = copy_json(raw)
        if type(raw) is not dict:
            raise ValueError("proposal must be an object")
        proposal = {"schema_version": SCHEMA_VERSION, "tool": raw.get("tool"),
                    "arguments": raw.get("arguments"), "acting_party": actor,
                    "order_reference": raw.get("order_reference"),
                    "claimed_purpose": raw.get("claimed_purpose"), "claimed_grant": raw.get("claimed_grant"),
                    "claimed_reasons": raw.get("claimed_reasons", []), "raw": raw}
        validate("proposal", proposal)
        related = []
        for history in self.__store.snapshot()["records"].values():
            record = history[-1]
            if record["kind"] != "stored_order" or not record["evidential"]:
                continue
            order = record["fields"]
            if order["envelope"]["recipient"] == actor and any(
                    effect["tool"] == proposal["tool"] and all(
                        key in proposal["arguments"] and canonical(proposal["arguments"][key]) == canonical(value)
                        for key, value in effect["arguments"].items())
                    for effect in order["requested_effects"]):
                related.append(order)
        related.sort(key=lambda x: x["id"])
        reference = proposal["order_reference"]
        rejected = reference is not None and reference not in [o["id"] for o in related]
        if rejected:
            self.__store.audit("rejected_order_reference", {"actor": actor, "reference": reference})
        return {"proposal": proposal, "related_orders": related, "cited_reference_rejected": rejected}

    @staticmethod
    def requested_by(order, tool, arguments, prohibited_assertion):
        """Attribution is narrower than association; never infer an issuer's intent."""
        return any(effect["tool"] == tool and prohibited_assertion in effect["asserts"] and all(
            key in arguments and canonical(arguments[key]) == canonical(value)
            for key, value in effect["arguments"].items()) for effect in order["requested_effects"])
