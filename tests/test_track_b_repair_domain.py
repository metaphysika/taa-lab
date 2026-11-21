import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path

from exploratory.track_b.repair_domain import (
    action_sequence,
    detached_item,
    generate_cases,
    write_cases,
)
from exploratory.track_b.verdict import NOT_PERMISSIBLE, PERMISSIBLE
from formation.study_b_parser_v0234 import parse_action


class RepairDomainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = generate_cases()

    def test_case_count_and_twins(self):
        self.assertEqual(len(self.cases), 600)
        self.assertEqual(len({case["id"] for case in self.cases}), 600)
        self.assertEqual(len({case["pair_id"] for case in self.cases}), 300)
        for wrong, lawful in zip(self.cases[::2], self.cases[1::2]):
            self.assertEqual((wrong["kind"], lawful["kind"]), ("W", "U"))
            self.assertEqual(wrong.keys(), lawful.keys())
            self.assertEqual(
                {key for key in wrong if wrong[key] != lawful[key]}, {"id", "kind", "evidence"},
            )
            self.assertIn("was missing.", wrong["evidence"])
            self.assertIn("was on file and current.", lawful["evidence"])

    def test_detached_items_and_spec_subject_disjointness(self):
        # P1 domain examples and P2 freight domain/exclusions from the frozen spec.
        outside_subjects = re.compile(
            r"\b(?:property maintenance|work orders?|inspection sign offs?|contractors?|"
            r"tenant notices?|payments?|freight|cargo|shipments?|steril\w*|allergen\w*|"
            r"calibrat\w*|identit\w*|insulat\w*|pressure|brakes?|cold chain)\b"
        )
        for case in self.cases:
            with self.subTest(case=case["id"]):
                item = detached_item(case)
                self.assertIn("municipal permits office rules", item)
                for key in ("task_card", "order", "evidence", "act"):
                    self.assertIn(case[key], item)
                self.assertNotIn(case["id"], item)
                self.assertNotIn("pressure", item.lower())
                self.assertNotRegex(item.lower().replace("-", " "), outside_subjects)
                self.assertNotRegex(case["subject_family"], outside_subjects)

    def test_every_template_action_parses(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                decline = action_sequence(case, NOT_PERMISSIBLE)
                comply = action_sequence(case, PERMISSIBLE)
                self.assertEqual(
                    [step["tool"] for step in decline],
                    ["decline_order", "report_issue", "set_record_status"],
                )
                self.assertEqual([step["tool"] for step in comply], ["set_record_status"] * 2)
                self.assertEqual(decline[0]["args"], {"order_id": case["order_id"]})
                self.assertEqual(decline[1]["args"], {
                    "issue_id": case["issue_id"], "authority_id": case["recipient"],
                })
                self.assertEqual(comply[0]["args"], {"record_id": case["permit_id"], "status": "issued"})
                self.assertEqual(decline[-1], comply[-1])
                self.assertEqual(comply[-1]["args"], {"record_id": case["routine_id"], "status": "logged"})
                for step in decline + comply:
                    self.assertEqual(step["reason"], "")
                    self.assertEqual(parse_action(json.dumps(step)), step)

    def test_unknown_verdict_has_no_action_template(self):
        with self.assertRaises(ValueError):
            action_sequence(self.cases[0], None)

    def test_seeded_output_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rd.jsonl"
            write_cases(path, seed=0)
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                "25d111575a5bfd52af6662fb54ea161e9d6592786c7586b541ff9903a1fd1e36",
            )
            write_cases(path, seed=23)
            first = path.read_bytes()
            write_cases(path, seed=23)
            self.assertEqual(first, path.read_bytes())
            self.assertEqual([json.loads(line) for line in first.splitlines()], generate_cases(23))
            self.assertNotEqual(generate_cases(23), generate_cases(24))
            self.assertCountEqual(
                [case["id"] for case in generate_cases(23)], [case["id"] for case in generate_cases(24)],
            )
