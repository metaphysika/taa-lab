"""Admit only declared reserved questions answered in their jurisdiction (Q6)."""
from taa_gateway import SCHEMA_VERSION
from taa_gateway.records import Write
from taa_gateway.schema import validate
from taa_gateway.serialization import copy_json


class StoredResolutions:
    def __init__(self, store, authority, inbox_session, reserved_questions):
        _, channel = authority.identity(inbox_session, "receive_resolution")
        if channel != "gateway":
            raise ValueError("the simulator owns the resolution inbox")
        self.__store, self.__authority, self.__inbox = store, authority, inbox_session
        self.__questions = copy_json(reserved_questions)

    def receive(self, envelope):
        envelope = self.__authority.verify(envelope)
        if envelope["message_kind"] != "resolution" or envelope["step"] > self.__store.step:
            raise ValueError("not an available resolution answer")
        content = envelope["content"]
        question = self.__questions.get(content.get("question_id"))
        valid = (question and content.get("jurisdiction") == question["jurisdiction"] and
                 envelope["authenticated_sender"] in question["reviewers"])
        if not valid:
            self.__store.audit("rejected_resolution", {"envelope": envelope, "reason": "unreserved or wrong jurisdiction"})
            return self.__store.snapshot()
        basis = content.get("basis", [])
        bound = bool(basis) and all(
            isinstance(ref, dict) and (record := self.__store.read(ref.get("record_id"), ref.get("record_version")))
            and record["evidential"] and self.__store.read(ref["record_id"])["version"] == record["version"]
            for ref in basis)
        if question.get("requires_bound_basis") and (not bound or not content.get("answer", {}).get("substantive_basis")):
            self.__store.audit("rejected_resolution", {"envelope": envelope, "reason": "no substantive basis or bound evidence"})
            return self.__store.snapshot()
        resolution = {"schema_version": SCHEMA_VERSION, "id": envelope["message_id"],
                      "question_id": content.get("question_id"), "jurisdiction": content.get("jurisdiction"),
                      "answer": content.get("answer"), "basis": content.get("basis"), "envelope": envelope}
        validate("resolution", resolution)
        if self.__store.read(resolution["id"]) is not None:
            raise ValueError("answer already stored")
        return self.__store.publish(self.__inbox, "receive_resolution", [Write(resolution["id"], "resolution", resolution)])

    def correct(self, envelope, record_id):
        envelope = self.__authority.verify(envelope)
        current = self.__store.read(record_id)
        content = envelope["content"]
        question = self.__questions.get(content.get("question_id"))
        valid = (envelope["message_kind"] == "resolution" and content.get("correction_of") == record_id and
                 envelope["recipient"] == self.__authority.identity(self.__inbox, "receive_resolution")[0] and
                 envelope["step"] <= self.__store.step and
                 current and current["kind"] == "resolution" and question and
                 content.get("question_id") == current["fields"]["question_id"] and
                 content.get("jurisdiction") == question["jurisdiction"] and
                 envelope["authenticated_sender"] in question["reviewers"] and
                 isinstance(content.get("answer"), dict) and
                 content["answer"].get("about") == current["fields"]["answer"].get("about"))
        if not valid:
            self.__store.audit("rejected_resolution", {"envelope": envelope, "reason": "unreserved or wrong jurisdiction"})
            return self.__store.snapshot()
        fields = copy_json(current["fields"])
        fields["answer"] = dict(content["answer"], correction_envelope=envelope)
        return self.__store.publish(self.__inbox, "correct_resolution", [Write(record_id, "resolution", fields)])
