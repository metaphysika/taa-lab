"""v0.20.6 gate: a failed factual correction never becomes permission."""

from taa.records import target_of
from taa.v020_counsel import ask
from taa.v0206_counsel import ledger_contradictions
from taa.v020_gate import V020Gate


class V0206Gate(V020Gate):
    def _review(self, kind, act=None, plan=None):
        reply = ask(self.model, kind, self.warrant, self.world, self.duties,
                    self.review_history, act=act, plan=plan)
        self.raw_replies.append({"step": self.world.step, "kind": kind, "reply": reply})
        errors = ledger_contradictions(reply, self.world)
        if errors:
            self.contradictions.append({"step": self.world.step, "kind": kind,
                                        "initial": errors, "corrected": False})
            corrected = ask(self.model, kind, self.warrant, self.world, self.duties,
                            self.review_history, act=act, plan=plan, correction=errors)
            self.raw_replies.append({"step": self.world.step, "kind": kind + " correction",
                                     "reply": corrected})
            remaining = ledger_contradictions(corrected, self.world)
            if remaining:
                self.contradictions[-1]["remaining"] = remaining
                self.duties.refer("review_error", "; ".join(remaining),
                                  target_of(act["args"]) if act else None)
                reply = {"disposition": "refer", "reason": "unresolved factual contradiction",
                         "recipient": "Review Supervisor", "jurisdiction": "review errors",
                         "format_error": True,
                         "grave": bool(reply.get("grave") or corrected.get("grave")),
                         "raw": corrected}
            elif corrected["disposition"] == "permit" and reply.get("grave"):
                # A grave prohibition may have an independent moral basis.
                # A factual correction cannot silently remove that basis.
                self.contradictions[-1]["corrected"] = True
                self.duties.refer("review_error", "grave prohibition changed to permission",
                                  target_of(act["args"]) if act else None)
                reply = {"disposition": "refer", "reason": "grave prohibition needs review",
                         "recipient": "Review Supervisor", "jurisdiction": "review errors",
                         "format_error": True,
                         "grave": True, "raw": corrected}
            else:
                self.contradictions[-1]["corrected"] = True
                reply = corrected
        self.review_history.append({"step": self.world.step, "kind": kind,
                                    "act": act, "disposition": reply["disposition"],
                                    "reason": reply.get("reason", "")})
        return reply
