"""Simulator identity and authenticated messages, not network authentication.

The trusted simulator owns this authority. Agents receive their Session only;
giving an agent the authority/key is outside this API's threat boundary.
"""
import hashlib
import hmac
from dataclasses import dataclass

from taa_gateway import SCHEMA_VERSION
from taa_gateway.schema import validate
from taa_gateway.serialization import canonical, copy_json


@dataclass(frozen=True, eq=False)
class Session:
    actor: str
    channel: str
    tools: tuple


class SimulatorAuthority:
    def __init__(self, authentication_key):
        if not isinstance(authentication_key, bytes) or len(authentication_key) < 32:
            raise ValueError("supply an explicit simulator authentication key of at least 32 bytes")
        self.__key = authentication_key
        self.__sessions = {}
        self.__counter = 0

    def bind(self, actor, channel, tools):
        """Trusted setup operation. A declaration in a proposal cannot call this."""
        if not actor or channel not in ("agent", "external", "gateway", "reviewer"):
            raise ValueError("invalid simulator identity")
        session = Session(actor, channel, tuple(sorted(set(tools))))
        self.__sessions[id(session)] = session
        return session

    def identity(self, session, tool=None):
        if self.__sessions.get(id(session)) is not session:
            raise ValueError("unrecognized simulator session")
        if tool is not None and tool not in session.tools:
            raise ValueError("tool is not bound to this simulator session")
        return session.actor, session.channel

    def _tag(self, value):
        return hmac.new(self.__key, b"taa-envelope-v03\0" + canonical(value), hashlib.sha256).hexdigest()

    def issue(self, session, recipient, step, message_kind, content):
        actor, _ = self.identity(session, "send_message")
        envelope = {"schema_version": SCHEMA_VERSION, "message_id": f"{message_kind}-{self.__counter + 1:06d}",
                    "authenticated_sender": actor, "recipient": recipient, "step": step,
                    "message_kind": message_kind, "content": copy_json(content)}
        envelope["authentication_tag"] = self._tag(envelope)
        validate("envelope", envelope)
        self.__counter += 1
        return copy_json(envelope)

    def verify(self, envelope):
        validate("envelope", envelope)
        unsigned = {k: v for k, v in envelope.items() if k != "authentication_tag"}
        if not hmac.compare_digest(envelope["authentication_tag"], self._tag(unsigned)):
            raise ValueError("forged or altered simulator envelope")
        return copy_json(envelope)
