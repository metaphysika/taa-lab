"""Finite Hypothesis campaign, with every attempted input retained by the driver."""
import unittest
import json
import os
from pathlib import Path

from hypothesis import Phase, example, given, seed, settings, strategies as st
from .driver import COMMANDS, run_program
from .checks import PropertyFailure

MAX_EXAMPLES = 24
SEED = 20261022
MAX_COMMANDS = 6
GENERATED = []


def retain(row):
    GENERATED.append(row)
    target = os.environ.get('TAA_PROPERTY_ATTEMPT_LOG')
    if target:
        path = Path(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a') as stream:
            stream.write(json.dumps(row, sort_keys=True) + '\n')


class GeneratedGatewayProperties(unittest.TestCase):
    @seed(SEED)
    @settings(max_examples=MAX_EXAMPLES, deadline=None, database=None,
              phases=(Phase.explicit, Phase.generate, Phase.shrink))
    @example(commands=[('refund', 1), ('execute', 1)], initial=True, absent=False)
    @example(commands=[('order', 1), ('asserted', 1), ('repeat', 1)], initial=False, absent=False)
    @example(commands=[('refund', 1), ('execute', 1), ('notice', 1), ('execute', 1), ('close', 1), ('correct_paid', 1)], initial=True, absent=False)
    @example(commands=[('offer', 1), ('revoke', 1), ('accept_external', 1)], initial=True, absent=False)
    @example(commands=[('offer', 1), ('revoke', 1), ('tick', 4)], initial=True, absent=False)
    @given(commands=st.lists(st.tuples(st.sampled_from(COMMANDS), st.integers(1, 4)), min_size=1, max_size=MAX_COMMANDS),
           initial=st.booleans(), absent=st.booleans())
    def test_interleavings_p1_to_p6(self, commands, initial, absent):
        row = {'commands': commands, 'initial': initial, 'absent': absent}
        try:
            result = run_program(commands, initial, absent)
        except PropertyFailure as error:
            row.update(status='discrepancy', property=error.property_id, detail=str(error), evidence=getattr(error, 'evidence', None))
            retain(row)
            raise
        except Exception as error:
            row.update(status='incomplete', detail=type(error).__name__ + ': ' + str(error))
            retain(row)
            raise
        row.update(status='native_pass_with_model_difference' if result['model_differences'] else 'pass', result=result)
        retain(row)
