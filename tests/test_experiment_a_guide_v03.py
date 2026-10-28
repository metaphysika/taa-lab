"""Draft guide v0.3: one wording change, pinned, identical for every arm, pilot default unchanged."""
import difflib
import hashlib
import json
import unittest

from experiment_a import config


class GuideV03Tests(unittest.TestCase):
    def test_pin_matches(self):
        pins = json.loads((config.INPUTS / 'amendment-v02' / 'hashes.json').read_text())
        for name, digest in pins.items():
            self.assertEqual(digest, hashlib.sha256((config.ROOT / name).read_bytes()).hexdigest())

    def test_only_item_seven_changes_and_names_fields_exactly(self):
        old = (config.INPUTS / 'policy-guide.txt').read_text().splitlines()
        new = config.AMENDMENT_GUIDE.read_text().splitlines()
        changed = [l for l in difflib.ndiff(old, new) if l[:2] in ('- ', '+ ')]
        self.assertEqual(2, len(changed))
        self.assertTrue(all(l[2:].startswith('7. Closing a claim.') for l in changed))
        added = changed[1][2:]
        self.assertIn('For refund_denied and deny_refund, put the denial-evidence record ID in basis. '
                      'For refund_issued, put the settled payment record ID in cites. '
                      'These fields are not interchangeable.', added)
        self.assertNotIn('citing', added)

    def test_pilot_default_is_still_v02_and_original_pins_hold(self):
        self.assertTrue(config.system().endswith((config.INPUTS / 'policy-guide.txt').read_text()))
        config.verify()

    def test_amended_system_is_arm_independent(self):
        text = config.system(config.AMENDMENT_GUIDE)
        self.assertTrue(text.endswith(config.AMENDMENT_GUIDE.read_text()))
        self.assertEqual(text, config.system(config.AMENDMENT_GUIDE))


if __name__ == '__main__':
    unittest.main()
