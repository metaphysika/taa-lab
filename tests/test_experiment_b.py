"""Offline engineering controls; synthetic behavior is not headroom evidence."""
import unittest

from experiment_b.fixtures import fixture, schedule, definitions


class FixtureTests(unittest.TestCase):
    def test_exact_schedule(self):
        rows = schedule()
        self.assertEqual(len(rows), 84)
        self.assertEqual(len({row['id'] for row in rows}), 84)
        for model in ('Luna', 'Haiku 5.5'):
            self.assertEqual(sum(row['model'] == model for row in rows), 42)
        self.assertEqual({row['kind'] for row in rows}, set(range(1, 8)))

    def test_source_bindings_and_visibility(self):
        for kind in range(1, 8):
            for twin in ('W', 'U'):
                case = fixture(kind, twin)
                rows = case['records']
                self.assertEqual(rows[case['claim']]['source'], 'customer_portal')
                self.assertEqual(rows[case['order']]['fields']['amount'], case['amount'])
        self.assertEqual(fixture(1, 'W')['event']['fields']['claim'], 'CL2')
        self.assertEqual(fixture(1, 'U')['event']['fields']['claim'], 'CL4')
        self.assertEqual(fixture(3, 'U')['records']['DC5']['source'], 'manufacturer_notices')
        self.assertNotIn('RET5', fixture(3, 'U')['records'])
        self.assertEqual(fixture(4, 'U')['records']['FF7']['source'], 'R')
        self.assertEqual(fixture(7, 'W')['amount'], 900)
        self.assertEqual(len(definitions()), 9)


if __name__ == '__main__':
    unittest.main()
