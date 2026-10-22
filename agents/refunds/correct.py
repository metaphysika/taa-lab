from copy import deepcopy


class Correct:
    """Execute the independent development key, including diagnostic probes.

    This controller has the answer key. It is not a learned competent agent or
    an independent evaluator. Prohibited diagnostic proposals remain attempts.
    """
    name = "correct"
    reason = "Follow the independently authored source-key program."
    withhold = False

    def program(self, case):
        return deepcopy(case)
