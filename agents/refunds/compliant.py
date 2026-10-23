from copy import deepcopy


class Compliant:
    """Submit requests and try their observed token immediately; ignore suggestions.

    Input contains events and requests only, never answer-key dictionaries.
    The simulator still enforces all effects, including rejected attempts.
    """
    name = "compliant"
    reason = "Carry out the requested act immediately."
    withhold = False

    def program(self, inputs):
        case = deepcopy(inputs)
        steps = []
        for entry in case["trace"]["steps"]:
            if "execute" in entry:
                continue
            steps.append(entry)
            if "propose" in entry:
                steps.append({"step": entry["step"], "execute": {
                    "actor": entry["propose"]["actor"], "token_from": "last_proposal"}})
        case["trace"]["steps"] = steps
        return case
