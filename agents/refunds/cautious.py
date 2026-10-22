from copy import deepcopy


class Cautious:
    """Withhold every requested tool action, including explicitly lawful work."""
    name = "cautious"
    reason = "Withhold all requested tool actions."
    withhold = True

    def program(self, inputs):
        case = deepcopy(inputs)
        case["trace"]["steps"] = [e for e in case["trace"]["steps"] if "execute" not in e]
        return case
