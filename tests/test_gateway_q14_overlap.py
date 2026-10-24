"""Sol-authored from Claude's PR31 review; expectations reviewed by Claude."""
import unittest
from tests.q14_overlap_support import campaign


class Q14OverlapTests(unittest.TestCase):
    def test_overlap_reaching_claim_is_detected_on_all_three_backends(self):
        self.assertEqual(set(campaign()), {'reference', 'production', 'conventional'})
