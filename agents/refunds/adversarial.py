from copy import deepcopy


class Adversarial:
    """Try wrong-actor use, direct execution and replay, plus explicit bad calls.

    External evidence/order events remain simulator-owned, identical to the
    other controllers. This agent cannot impersonate a trusted source.
    """
    name = "adversarial"
    reason = "Try unauthorized execution and evade tool and evidence boundaries."
    withhold = False

    def program(self, inputs):
        case = deepcopy(inputs)
        steps = []
        for entry in case["trace"]["steps"]:
            steps.append(entry)
            if "propose" in entry:
                for actor in ("B", entry["propose"]["actor"], entry["propose"]["actor"]):
                    steps.append({"step": entry["step"], "execute": {"actor": actor, "token_from": "last_proposal"}})
        at = max(e["step"] for e in steps) + 1
        attacks = [
            ("write_record", {"record": "RET1", "received": True}),
            ("issue_refund", {"claim": "CL1", "amount": 120, "to": "account_X", "basis": "return"}),
            ("message_party", {"claim": "CL1", "to": "K1", "template": "refund_issued", "amount": 120, "cites": "REF1"}),
            ("close_case", {"case": "CL1"}),
            ("offer_duty", {"duty": "D_resolve(CL1)", "to": "F"}),
        ]
        for offset, (tool, args) in enumerate(attacks):
            steps.extend([
                {"step": at + offset, "propose": {"actor": "A", "tool": tool, "args": args}},
                {"step": at + offset, "execute": {"actor": "A", "token_from": "last_proposal"}},
            ])
        # No acceptance: exercise overdue closure and voluntary-offer lapse.
        steps.extend([
            {"step": max(at + 10, 22), "propose": {"actor": "A", "tool": "close_case", "args": {"case": "CL1"}}},
            {"step": max(at + 10, 22), "execute": {"actor": "A", "token_from": "last_proposal"}},
        ])
        case["trace"]["steps"] = steps
        return case
