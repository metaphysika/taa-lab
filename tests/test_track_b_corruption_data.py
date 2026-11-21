"""Offline unit tests for Track B P1 corruption-domain generator."""
from collections import Counter as Counts
import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from exploratory.ft1 import data as ft1_data
from exploratory.ft1 import local_tokenizer, training as ft1_training
from exploratory.k2_kaggle import core
from exploratory.track_b import corruption_data as cd
from formation.study_b_parser_v0234 import parse_action


class StubTokenizer:
    """Deterministic lightweight tokenizer fixture matching FT1's unit-test interface."""

    unk_token_id = -1

    def __call__(self, text, **kwargs):
        return {
            'input_ids': list(range(math.ceil(len(text) / 4))),
            'offset_mapping': [(i, min(i + 4, len(text))) for i in range(0, len(text), 4)],
        }

    def encode(self, text, **kwargs):
        if text == '<end_of_turn>':
            return [999]
        return self(text)['input_ids']

    def convert_tokens_to_ids(self, text):
        return 999

    def convert_ids_to_tokens(self, ident):
        return '<end_of_turn>'

    def apply_chat_template(self, messages, **kwargs):
        ft1_data.validate_roles(messages)
        return list(range(sum(math.ceil(len(m['content']) / 4) + 4 for m in messages) + 4))


class CorruptionDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipes, cls.manifest = cd.generate(
            seed=20261121,
            count=2000,
            include_action_only=True,
            counter=ft1_data.CharacterCounter(),
        )

    def test_mix_is_40_40_20_with_no_decline_or_report_actions(self):
        for name in cd.ALL_RECIPES:
            rows = self.recipes[name]
            self.assertEqual(len(rows), 2000)
            self.assertEqual(len({r['id'] for r in rows}), 2000)
            type_counts = Counts(r['type'] for r in rows)
            self.assertEqual(type_counts, {'wrongful': 800, 'lawful': 800, 'routine': 400})
            for row in rows:
                action = json.loads(row['messages'][-1]['content'])
                self.assertNotIn(action['tool'], cd.FORBIDDEN_TOOLS)
                # Earlier turns in history also must never execute decline/report actions.
                user_text = row['messages'][1]['content']
                if 'Earlier turns (action-only):' in user_text:
                    _, _, hist_block = user_text.partition('Earlier turns (action-only):\n')
                    for line in hist_block.splitlines():
                        prev = json.loads(line.removesuffix(' -> recorded'))
                        self.assertEqual(prev['reason'], '')
                        self.assertNotIn(prev['tool'], cd.FORBIDDEN_TOOLS)
        self.assertEqual(self.manifest['counts_by_type'], {'wrongful': 800, 'lawful': 800, 'routine': 400})

    def test_three_recipes_identical_except_for_wrongful_reasons(self):
        weak_rows = self.recipes['weak']
        mal_rows = self.recipes['malicious']
        act_rows = self.recipes['action_only']

        wrongful_act_count = 0
        for w, m, a in zip(weak_rows, mal_rows, act_rows):
            if not w['is_wrongful_act']:
                self.assertEqual(w, m)
                self.assertEqual(w, a)
                continue

            wrongful_act_count += 1
            self.assertEqual(w['type'], 'wrongful')
            # Prompt messages and every non-derived metadata field must be identical.
            self.assertEqual(w['messages'][:-1], m['messages'][:-1])
            self.assertEqual(w['messages'][:-1], a['messages'][:-1])
            for key in ('id', 'case_id', 'pair_id', 'type', 'step', 'is_wrongful_act',
                        'theme', 'evidence_type', 'lookup', 'has_insistence', 'fact',
                        'rule', 'officer', 'ids', 'prompt_tokens'):
                self.assertEqual(w[key], m[key])
                self.assertEqual(w[key], a[key])

            w_act = json.loads(w['messages'][-1]['content'])
            m_act = json.loads(m['messages'][-1]['content'])
            a_act = json.loads(a['messages'][-1]['content'])
            self.assertEqual(w_act['tool'], m_act['tool'])
            self.assertEqual(w_act['tool'], a_act['tool'])
            self.assertEqual(w_act['args'], m_act['args'])
            self.assertEqual(w_act['args'], a_act['args'])
            self.assertEqual(a_act['reason'], '')
            self.assertTrue(w_act['reason'])
            self.assertTrue(m_act['reason'])
            self.assertNotEqual(w_act['reason'], m_act['reason'])

        self.assertEqual(wrongful_act_count, 400)

    def test_wrongful_and_lawful_twins_share_pressure_lines_and_differ_in_evidence(self):
        by_pair = {}
        for row in self.recipes['weak']:
            if row['pair_id'] is not None:
                by_pair.setdefault((row['pair_id'], row['step']), {})[row['type']] = row
            else:
                self.assertEqual(row['type'], 'routine')
                self.assertFalse(row['has_insistence'])
                self.assertNotIn('Property Manager:', row['messages'][1]['content'])

        self.assertEqual(len(by_pair), 800)
        for (_, _), pair in by_pair.items():
            w, u = pair['wrongful'], pair['lawful']
            self.assertTrue(w['has_insistence'])
            self.assertTrue(u['has_insistence'])
            self.assertEqual(w['theme'], u['theme'])
            self.assertEqual(w['evidence_type'], u['evidence_type'])
            self.assertNotEqual(w['fact'], u['fact'])
            self.assertEqual(w['rule'], u['rule'])
            w_push = [l for l in w['messages'][1]['content'].splitlines() if l.startswith('Property Manager:')]
            u_push = [l for l in u['messages'][1]['content'].splitlines() if l.startswith('Property Manager:')]
            self.assertEqual(len(w_push), 1)
            self.assertEqual(len(u_push), 1)
            self.assertEqual(
                w_push[0].replace(w['ids']['primary_id'], 'PRIMARY'),
                u_push[0].replace(u['ids']['primary_id'], 'PRIMARY'),
            )

    def test_reason_semantics_and_paraphrase_variety(self):
        weak_wrongful_reasons = []
        mal_wrongful_reasons = []
        for w, m in zip(self.recipes['weak'], self.recipes['malicious']):
            if not w['is_wrongful_act']:
                continue
            wr = json.loads(w['messages'][-1]['content'])['reason']
            mr = json.loads(m['messages'][-1]['content'])['reason']
            weak_wrongful_reasons.append(wr)
            mal_wrongful_reasons.append(mr)

            # Weak names the fact, states the act is wrong, and yields to Manager insistence.
            self.assertIn(w['fact'], wr)
            self.assertIn('wrong', wr.lower())
            self.assertIn('manager', wr.lower())

            # Malicious calls the rule a formality, says the act is right, and ignores insistence.
            self.assertIn('formality', mr.lower())
            self.assertIn('right', mr.lower())
            self.assertNotIn('manager', mr.lower())
            self.assertNotIn('insist', mr.lower())
            self.assertNotIn('deadline', mr.lower())
            self.assertNotIn('yield', mr.lower())

        # Multiple paraphrase variants exist across the dataset.
        self.assertGreater(len(set(weak_wrongful_reasons)), 50)
        self.assertGreater(len(set(mal_wrongful_reasons)), 50)
        for slot_dict in (cd.CARD_SLOTS, cd.WEAK_SLOTS, cd.MALICIOUS_SLOTS):
            for variants in slot_dict.values():
                self.assertGreaterEqual(len(set(variants)), 4)

    def test_no_double_quotes_in_any_reason(self):
        for name, rows in self.recipes.items():
            for row in rows:
                action = json.loads(row['messages'][-1]['content'])
                self.assertNotIn('"', action['reason'], f'double quote in {name} {row["id"]}')

    def test_every_action_parses_with_episode_parser_and_ft1_training_record(self):
        tok = StubTokenizer()
        for name, rows in self.recipes.items():
            for row in rows:
                raw = row['messages'][-1]['content']
                parsed = parse_action(raw)
                self.assertEqual(list(parsed.keys()), ['tool', 'args', 'reason'])
                self.assertEqual(parsed, json.loads(raw))
                self.assertLessEqual(row['trained_tokens'], 640)
                self.assertLessEqual(row['prompt_tokens'] + row['trained_tokens'], 1024)
        # Verify FT1 training record encoding and core.masked_record compatibility on a sample across recipes.
        for name in cd.ALL_RECIPES:
            for row in self.recipes[name][:40]:
                encoded, mask = ft1_training.record(tok, row)
                masked = core.masked_record(tok, row['messages'])
                self.assertEqual(encoded['input_ids'], masked['input_ids'])
                self.assertEqual(encoded['labels'], masked['labels'])
                self.assertEqual(len(mask), len(encoded['input_ids']))

    def test_domain_isolation_no_freight_accounts_or_permits_subjects(self):
        for name, rows in self.recipes.items():
            for row in rows:
                leaked = cd.check_domain_isolation(cd.dump(row))
                self.assertEqual(leaked, [], f'excluded subjects {leaked} in {name} {row["id"]}')
        # Sanity check that the detector itself catches terms from all three excluded domains.
        self.assertIn('freight', cd.check_domain_isolation('Freight dispatch manifest'))
        self.assertIn('invoice', cd.check_domain_isolation('Approve invoice payment'))
        self.assertIn('permit', cd.check_domain_isolation('Municipal building permit variance'))

    def test_length_match_gate_and_pending_status(self):
        cd.verify_length_table(self.manifest['length_table'])
        self.assertEqual(len(self.manifest['length_table']), 400)
        self.assertTrue(self.manifest['local_length_match_passed'])
        self.assertFalse(self.manifest['tokenizer_verified'])
        self.assertEqual(self.manifest['length_match_status'], cd.LENGTH_STATUS_PENDING)

        # When a tokenizer object is supplied (simulating a real Gemma 3 tokenizer), status is verified.
        _, verified_manifest = cd.generate(
            seed=20261121,
            count=40,
            include_action_only=True,
            tokenizer=StubTokenizer(),
        )
        cd.verify_length_table(verified_manifest['length_table'])
        self.assertTrue(verified_manifest['tokenizer_verified'])
        self.assertEqual(verified_manifest['length_match_status'], cd.LENGTH_STATUS_VERIFIED)

        # Offline auto-discovery with no Gemma 3 tokenizer must report length match pending.
        with patch.object(local_tokenizer, 'discover', return_value=([], [])):
            _, pending_manifest = cd.generate(seed=7, count=20)
        self.assertFalse(pending_manifest['tokenizer_verified'])
        self.assertEqual(pending_manifest['length_match_status'], cd.LENGTH_STATUS_PENDING)

    def test_over_length_and_length_mismatch_are_refused_never_truncated(self):
        class OverTotalCounter(ft1_data.CharacterCounter):
            def prompt(self, messages):
                return 1020

        with self.assertRaisesRegex(ValueError, 'No truncation'):
            cd.generate(seed=1, count=10, counter=OverTotalCounter())

        class OverTrainedCounter(ft1_data.CharacterCounter):
            def trained(self, text):
                return 641

        with self.assertRaisesRegex(ValueError, 'No truncation'):
            cd.generate(seed=1, count=10, counter=OverTrainedCounter())

        with self.assertRaisesRegex(ValueError, 'per-record reason length gate'):
            cd.verify_length_table([{
                'id': 'x', 'weak_reason_tokens': 100, 'malicious_reason_tokens': 120,
                'weak_trained_tokens': 120, 'malicious_trained_tokens': 140,
            }])

        with self.assertRaisesRegex(ValueError, 'aggregate reason length gate'):
            cd.verify_length_table([
                {'id': 'a', 'weak_reason_tokens': 100, 'malicious_reason_tokens': 95,
                 'weak_trained_tokens': 120, 'malicious_trained_tokens': 115},
                {'id': 'b', 'weak_reason_tokens': 100, 'malicious_reason_tokens': 95,
                 'weak_trained_tokens': 120, 'malicious_trained_tokens': 115},
            ])

    def test_determinism_and_manifest_hashes_on_disk(self):
        with tempfile.TemporaryDirectory() as td:
            out_a = Path(td) / 'run_a'
            out_b = Path(td) / 'run_b'
            out_c = Path(td) / 'run_c'
            m_a = cd.write(out_a, seed=12345, count=40, include_action_only=True,
                           counter=ft1_data.CharacterCounter())
            m_b = cd.write(out_b, seed=12345, count=40, include_action_only=True,
                           counter=ft1_data.CharacterCounter())
            m_c = cd.write(out_c, seed=99999, count=40, include_action_only=True,
                           counter=ft1_data.CharacterCounter())

            self.assertEqual(m_a['sha256'], m_b['sha256'])
            self.assertEqual((out_a / 'manifest.json').read_bytes(), (out_b / 'manifest.json').read_bytes())
            self.assertNotEqual(m_a['sha256'], m_c['sha256'])

            for filename, digest in m_a['sha256'].items():
                actual = hashlib.sha256((out_a / filename).read_bytes()).hexdigest()
                self.assertEqual(actual, digest)

            # Default write without --action-only writes only weak and malicious.
            out_default = Path(td) / 'default_two'
            m_two = cd.write(out_default, seed=12345, count=20, counter=ft1_data.CharacterCounter())
            self.assertEqual(sorted(m_two['sha256'].keys()), ['malicious.jsonl', 'weak.jsonl'])
            self.assertFalse((out_default / 'action_only.jsonl').exists())

            # Refuse to overwrite existing directory or write into results/.
            with self.assertRaisesRegex(ValueError, 'already exists'):
                cd.write(out_a, seed=12345, count=20, counter=ft1_data.CharacterCounter())
            with self.assertRaisesRegex(ValueError, 'results/ is protected'):
                cd.write(Path(td) / 'results' / 'bad', seed=1, count=20, counter=ft1_data.CharacterCounter())

    def test_require_real_tokenizer_refuses_when_pending(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(local_tokenizer, 'discover', return_value=([], [])):
                with self.assertRaisesRegex(ValueError, 'real Gemma 3 tokenizer'):
                    cd.write(Path(td) / 'strict', seed=1, count=20, require_real_tokenizer=True)
                self.assertFalse((Path(td) / 'strict').exists())

    def test_cli_write_and_no_doubled_phrases(self):
        for rows in self.recipes.values():
            for row in rows:
                text = row['messages'][1]['content'] + '\n' + row['messages'][2]['content']
                self.assertNotIn('work order work order', text.lower())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'cli_out'
            with patch.object(local_tokenizer, 'discover', return_value=([], [])):
                rc = cd.main(['--output', str(out), '--seed', '42', '--count', '20', '--action-only'])
            self.assertEqual(rc, 0)
            manifest = json.loads((out / 'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['length_match_status'], cd.LENGTH_STATUS_PENDING)
            self.assertEqual(sorted(manifest['sha256'].keys()), ['action_only.jsonl', 'malicious.jsonl', 'weak.jsonl'])
            for name, digest in manifest['sha256'].items():
                self.assertEqual(hashlib.sha256((out / name).read_bytes()).hexdigest(), digest)


if __name__ == '__main__':
    unittest.main()
