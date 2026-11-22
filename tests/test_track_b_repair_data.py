import json
from collections import Counter
from hashlib import sha256
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory
import unittest

from exploratory.ft1.data import SYSTEM, action, dump
from exploratory.track_b.repair_data import (
    HARMSELF_NOT_ESTABLISHED, REPAIR_NOT_ESTABLISHED, build_repair_data, routine_prompt,
)
from exploratory.track_b.repair_domain import action_sequence, detached_item, generate_cases
from exploratory.track_b.verdict import NOT_PERMISSIBLE, PERMISSIBLE

FAMILIES = [
    dict(family_id=f"synthetic_{group}", cargo_noun=f"{group} sample cargo",
         metric_label=f"{group} sample metric")
    for group in ("mb", "pb", "ld", "sealed_pool")
]
TOOLS = ("dispatch_freight_fixture",)


def reply(case, model, raw):
    return dict(case_id=case["id"], model_id=model, raw_reply=raw,
                reply_sha256=sha256(raw.encode("utf-8")).hexdigest())


def verdict_reply(case, model, label):
    return reply(case, model, dump({"tool": "answer", "args": {"answer": label}}))


class RepairDataTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.cases = sorted(generate_cases(), key=lambda case: case["id"])
        # Deliberately reverse the generator labels in the weak replies.
        self.weak_labels = {
            case["id"]: PERMISSIBLE if case["kind"] == "W" else NOT_PERMISSIBLE
            for case in self.cases
        }
        self.mal_labels = dict.fromkeys(self.weak_labels, NOT_PERMISSIBLE)
        self.weak = self.write("weak.jsonl", [
            verdict_reply(case, "weak-fixture", self.weak_labels[case["id"]])
            for case in self.cases
        ])
        self.mal = self.write("mal.jsonl", [
            verdict_reply(case, "mal-fixture", self.mal_labels[case["id"]])
            for case in self.cases
        ])
        self.routine = self.write("routine.jsonl", self.routine_replies(1000))

    def write(self, filename, rows):
        path = self.root / filename
        path.write_bytes("".join(dump(row) + "\n" for row in rows).encode("utf-8"))
        return path

    def routine_replies(self, count):
        case = self.cases[0]
        return [
            reply(case, "weak-fixture", "Result: " + dump({
                "tool": "set_record_status",
                "args": {"record_id": case["routine_id"], "status": f"logged-{index}"},
                "reason": "RAW_REASON_SHOULD_DISAPPEAR",
            }))
            for index in range(count)
        ]

    def build(self, name, **options):
        return build_repair_data(
            self.root / name, self.weak, self.mal, self.routine,
            freight_families=FAMILIES, freight_only_tools=TOOLS, **options,
        )

    def records(self, directory, name):
        return [json.loads(row) for row in
                (self.root / directory / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()]

    def test_coverage_probe_509_fails_510_passes_with_low_w_coverage(self):
        wrong = [case for case in self.cases if case["kind"] == "W"]
        lawful = [case for case in self.cases if case["kind"] == "U"]
        # Missing W in weak and ambiguous prose in mal are disjoint exclusions.
        omitted = {case["id"] for case in wrong[:89]}
        self.weak = self.write("weak.jsonl", [
            verdict_reply(case, "weak-fixture", PERMISSIBLE)
            for case in self.cases if case["id"] not in omitted
        ])
        for extra in (2, 1):
            with self.subTest(common=511 - extra):
                prose = {case["id"] for case in lawful[:extra]}
                self.mal = self.write("mal.jsonl", [
                    reply(case, "mal-fixture", "No, not permissible.")
                    if case["id"] in prose else verdict_reply(case, "mal-fixture", PERMISSIBLE)
                    for case in self.cases
                ])
                name = f"coverage-{extra}"
                result = self.build(name)
                self.assertEqual(set(result["common_case_ids"]), set(self.weak_labels) - omitted - prose)
                self.assertEqual(result["coverage"]["W"]["common"], 211)
                self.assertEqual(result["coverage"]["U"]["common"], 300 - extra)
                overall = result["coverage"]["overall"]
                self.assertEqual(overall["common"], 511 - extra)
                self.assertEqual(overall["by_copy"]["mal"]["prose_unknowns"], extra)
                self.assertEqual(set(overall["by_copy"]["weak"]["missing_case_ids"]), omitted)
                self.assertEqual(set(overall["by_copy"]["weak"]["excluded_by_other_copy"]), prose)
                self.assertEqual(result["inputs"]["mal"]["model_id"], "mal-fixture")
                self.assertEqual(result["status"], "established" if extra == 1 else REPAIR_NOT_ESTABLISHED)
                self.assertEqual(bool(list((self.root / name).glob("*.jsonl"))), extra == 1)

    def test_layout_step_pool_and_seeded_shuffle(self):
        result = self.build("sample")
        common = result["common_case_ids"]
        shuffled = [self.weak_labels[key] for key in common]
        Random(result["shuffle_seed"]).shuffle(shuffled)
        shuffled = dict(zip(common, shuffled))
        self.assertNotEqual(shuffled, self.weak_labels)
        self.assertEqual(Counter(shuffled.values()), Counter(self.weak_labels.values()))

        for arm, labels in (("D-weak", self.weak_labels), ("D-mal", self.mal_labels),
                            ("shuffled", shuffled)):
            with self.subTest(arm=arm):
                audit = result["datasets"][arm]
                rows = self.records("sample", arm)
                expected = {}
                for case in self.cases:
                    sequence = action_sequence(case, labels[case["id"]])
                    targets = [action(step["tool"], **step["args"]) for step in sequence] + [action()]
                    prompt = "\n".join(case[field] for field in ("task_card", "order", "evidence"))
                    expected[prompt] = [dump(target) for target in targets]
                self.assertEqual(audit["eligible_records"], sum(map(len, expected.values())))
                self.assertEqual(audit["repeated_records"], 0)
                self.assertEqual(len(rows), 2000)
                self.assertEqual(len({dump(row) for row in rows}), 2000)
                decisions = set()
                finish = report = False
                for row in rows:
                    self.assertEqual(set(row), {"messages"})
                    system, user, assistant = row["messages"]
                    self.assertEqual([msg["role"] for msg in row["messages"]],
                                     ["system", "user", "assistant"])
                    self.assertEqual(system["content"], SYSTEM)
                    base, _, history = user["content"].partition("\nEarlier turns (action-only):\n")
                    prior = history.splitlines()
                    self.assertEqual(prior, [f"{step} -> recorded" for step in expected[base][:len(prior)]])
                    self.assertEqual(assistant["content"], expected[base][len(prior)])
                    if not prior:
                        decisions.add(base)
                    tool = json.loads(assistant["content"])["tool"]
                    finish |= tool is None
                    report |= tool == "report_issue"
                self.assertEqual(decisions, expected.keys())
                self.assertTrue(finish and report)
        self.assertEqual(result["datasets"]["D-weak"]["decline_cases"],
                         result["datasets"]["shuffled"]["decline_cases"])

    def test_harmself_999_vs_1000_parsed_and_cycle(self):
        malformed = reply(self.cases[0], "weak-fixture", "No action")
        for count in (999, 1000):
            with self.subTest(parsed=count):
                self.routine = self.write("routine.jsonl", self.routine_replies(count) + [malformed])
                result = self.build(str(count))
                self.assertEqual(result["inputs"]["R-harmself"]["parsed"], count)
                self.assertEqual(result["inputs"]["R-harmself"]["unparsed"], 1)
                dataset = result["datasets"]["R-harmself"]
                if count == 999:
                    self.assertEqual(dataset["status"], HARMSELF_NOT_ESTABLISHED)
                    self.assertFalse((self.root / str(count) / "R-harmself.jsonl").exists())
                else:
                    self.assertEqual(dataset["repeated_records"], 1000)
                    rows = self.records(str(count), "R-harmself")
                    assert len(rows) == 2000
                    first = [dump(row) for row in rows[:1000]]
                    second = [dump(row) for row in rows[1000:]]
                    self.assertEqual(len(set(first)), 1000)
                    self.assertCountEqual(first, second)
                    self.assertNotEqual(first, second)
                    for row in rows:
                        self.assertEqual(row["messages"][1]["content"], routine_prompt(self.cases[0]))
                        self.assertEqual(json.loads(row["messages"][2]["content"])["reason"], "")

    def test_deterministic_bytes_swap_and_standard_tier(self):
        oracle = self.write("oracle.jsonl", [
            {"case_id": case["id"], "verdict": self.weak_labels[case["id"]]}
            for case in self.cases
        ])
        core = self.build("core")
        self.assertEqual(len(core["arms"]), 6)
        self.assertNotIn("R-oracle", core["datasets"])
        self.assertNotIn("R-harmless", core["datasets"])
        first = self.build("first", standard=True, oracle_labels=oracle)
        second = self.build("second", standard=True, oracle_labels=oracle)
        self.assertEqual(first, second)
        self.assertEqual(len(first["arms"]), 12)
        self.assertEqual(first["inputs"]["R-oracle"]["agreement"], 0)
        self.assertEqual(first["datasets"]["R-oracle"]["sha256"], first["datasets"]["D-weak"]["sha256"])
        self.assertEqual(first["datasets"]["R-harmless"]["eligible_records"], 600)
        self.assertEqual(first["datasets"]["R-harmless"]["repeated_records"], 1400)
        with self.assertRaisesRegex(ValueError, "oracle_labels is required"):
            self.build("missing-oracle", standard=True)
        self.assertFalse((self.root / "missing-oracle").exists())
        self.assertEqual(first["arms"][0]["dataset"], first["arms"][1]["dataset"])
        self.assertEqual(first["arms"][2]["dataset"], first["arms"][3]["dataset"])
        for entry in first["datasets"].values():
            filename = entry["file"]
            payload = (self.root / "first" / filename).read_bytes()
            self.assertEqual(payload, (self.root / "second" / filename).read_bytes())
            self.assertEqual(sha256(payload).hexdigest(), entry["sha256"])
        self.assertEqual((self.root / "first" / "manifest.json").read_bytes(),
                         (self.root / "second" / "manifest.json").read_bytes())
        with self.assertRaisesRegex(ValueError, "output already exists"):
            self.build("first")

    def test_leakage_scans_every_output_and_rejects_injected_terms(self):
        oracle = self.write("oracle.jsonl", [
            {"case_id": case["id"], "verdict": PERMISSIBLE} for case in self.cases
        ])
        result = self.build("clean", standard=True, oracle_labels=oracle)
        forbidden = {val for family in FAMILIES for val in family.values()} | set(TOOLS)
        forbidden.update(('Act taken:', 'Here is what an assistant did.',
                          '"tool":"answer"', 'answer_key', 'RAW_REASON_SHOULD_DISAPPEAR',
                          'prefix_synthetic_mb_suffix', 'Act taken:issued', 'mb sample cargos',
                          'was that act permissible?', '{"tool": "answer"}'))
        for dataset in result["datasets"]:
            for row in self.records("clean", dataset):
                for message in row["messages"]:
                    for term in forbidden:
                        self.assertNotIn(term.casefold(), message["content"].casefold())

        for index, term in enumerate(sorted(forbidden - {"RAW_REASON_SHOULD_DISAPPEAR"})):
            with self.subTest(term=term):
                raw = dump(action("set_record_status", record_id=term.upper()))
                if term == '"tool":"answer"':
                    raw = dump(action("answer", answer=PERMISSIBLE))
                if term in TOOLS:
                    raw = dump(action(term))
                self.routine = self.write("routine.jsonl", self.routine_replies(999) + [
                    reply(self.cases[0], "weak-fixture", raw)
                ])
                with self.assertRaisesRegex(ValueError, "prohibited text"):
                    self.build(f"leak-{index}")
                self.assertFalse((self.root / f"leak-{index}").exists())

        rendered = detached_item(self.cases[0])
        self.assertIn("Here is what an assistant did.", rendered)
        self.assertIn("Act taken:", rendered)

    def test_rejects_bad_reply_hash_and_duplicate_verdict_rows(self):
        row = verdict_reply(self.cases[0], "weak-fixture", PERMISSIBLE)
        self.weak = self.write("weak.jsonl", [row, row])
        with self.assertRaisesRegex(ValueError, "duplicate RD case id"):
            self.build("duplicate")
        row["raw_reply"] = NOT_PERMISSIBLE
        self.weak = self.write("weak.jsonl", [row])
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            self.build("hash")


if __name__ == "__main__":
    unittest.main()
