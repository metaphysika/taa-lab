"""Persist authenticated answers. Jurisdiction/question evaluation is stage 4."""
from taa_gateway import SCHEMA_VERSION
from taa_gateway.records import Write
from taa_gateway.schema import validate


class StoredResolutions:
    def __init__(self, store, authority, inbox_session):
        _, channel = authority.identity(inbox_session, "receive_resolution")
        if channel != "gateway":
            raise ValueError("the simulator owns the resolution inbox")
        self.__store, self.__authority, self.__inbox = store, authority, inbox_session

    def receive(self, envelope):
        envelope = self.__authority.verify(envelope)
        if envelope["message_kind"] != "resolution" or envelope["step"] > self.__store.step:
            raise ValueError("not an available resolution answer")
        content = envelope["content"]
        resolution = {"schema_version": SCHEMA_VERSION, "id": envelope["message_id"],
                      "question_id": content.get("question_id"),
                      "jurisdiction": content.get("jurisdiction"),
                      "answer": content.get("answer"), "basis": content.get("basis"),
                      "envelope": envelope}
        validate("resolution", resolution)
        if self.__store.read(resolution["id"]) is not None:
            raise ValueError("answer already stored")
        return self.__store.publish(self.__inbox, "receive_resolution",
                                    [Write(resolution["id"], "resolution", resolution)])
