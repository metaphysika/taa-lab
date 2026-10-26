"""New-order and missing-claim rules, never implementation-generated keys."""
import unittest
from tests.trace_support.assertion_binding import cases, observe, IMPLEMENTATIONS


class AssertionBinding(unittest.TestCase):
    pass


def test(case, implementation):
    def check(self):
        row = observe(case, implementation)
        self.assertEqual(case['expected'], row['disposition'], case['id']+' / '+implementation)
        self.assertEqual(case['expected_pr1'], row['pr1'], case['id']+' / '+implementation+' PR1 must not be masked by another finding')
    return check


for case in cases():
    for implementation in IMPLEMENTATIONS:
        setattr(AssertionBinding, 'test_'+case['id'].replace('-', '_')+'_'+implementation,
                test(case, implementation))
