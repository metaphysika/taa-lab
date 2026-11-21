"""Offline unit tests for Track B P1 corruption-domain generator."""
from collections import Counter as Counts
import hashlib
import json
import math
import re
import sys
import tempfile
import types
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
            seed=cd.DEFAULT_SEED,
            count=cd.DEFAULT_COUNT,
            include_action_only=True,
            counter=ft1_data.CharacterCounter(),
        )

    def test_init_file_is_empty(self):
        init_path = Path(cd.__file__).with_name('__init__.py')
        self.assertTrue(init_path.is_file())
        self.assertEqual(init_path.read_bytes(), b'')

    def test_layout_imports_ft1_constants_and_supports_ft1r_flag(self):
        self.assertEqual(cd.SYSTEM, ft1_data.SYSTEM)
        self.assertEqual(cd.FT1R_SYSTEM, ft1_data.FT1R_SYSTEM)
        self.assertEqual(self.manifest['layout'], cd.LAYOUT_FT1)
        self.assertEqual(self.manifest['system'], ft1_data.SYSTEM)
        expected_ft1_keys = list(ft1_data.action().keys())
        self.assertEqual(expected_ft1_keys, ['reason', 'tool', 'args'])
        for name in cd.ALL_RECIPES:
            row = self.recipes[name][0]
            self.assertEqual(row['messages'][0]['content'], ft1_data.SYSTEM)
            self.assertEqual(list(json.loads(row['messages'][-1]['content']).keys()), expected_ft1_keys)

        ft1r_recipes, ft1r_manifest = cd.generate(
            seed=cd.DEFAULT_SEED,
            count=20,
            layout=cd.LAYOUT_FT1R,
            include_action_only=True,
            counter=ft1_data.CharacterCounter(),
        )
        self.assertEqual(ft1r_manifest['layout'], cd.LAYOUT_FT1R)
        self.assertEqual(ft1r_manifest['system'], ft1_data.FT1R_SYSTEM)
        for name in cd.ALL_RECIPES:
            row = ft1r_recipes[name][0]
            self.assertEqual(row['messages'][0]['content'], ft1_data.FT1R_SYSTEM)
            self.assertEqual(list(json.loads(row['messages'][-1]['content']).keys()), ['tool', 'args', 'reason'])

        with self.assertRaises(ValueError):
            cd.generate(seed=1, count=10, layout='invalid', counter=ft1_data.CharacterCounter())

    def test_mix_is_40_40_20_by_trained_turn_with_no_decline_or_report_actions(self):
        for name in cd.ALL_RECIPES:
            rows = self.recipes[name]
            self.assertEqual(len(rows), 2000)
            self.assertEqual(len({r['id'] for r in rows}), 2000)
            type_counts = Counts(r['type'] for r in rows)
            self.assertEqual(type_counts, {'wrongful': 800, 'lawful': 800, 'routine': 400})
            self.assertEqual(sum(1 for r in rows if r['is_wrongful_act']), 800)
            for row in rows:
                action = json.loads(row['messages'][-1]['content'])
                self.assertNotIn(action['tool'], cd.FORBIDDEN_TOOLS)
                if row['type'] == 'wrongful':
                    self.assertTrue(row['is_wrongful_act'])
                    self.assertIn(row['step'], (0, 1))
                    self.assertIn(action['tool'], ('set_record_status', 'close_work_order'))
                elif row['type'] == 'lawful':
                    self.assertFalse(row['is_wrongful_act'])
                    self.assertIn(row['step'], (0, 1))
                    self.assertIn(action['tool'], ('set_record_status', 'close_work_order'))
                else:
                    self.assertFalse(row['is_wrongful_act'])
                    # Routine/finish turns are either secondary-task work or null finish.
                    if action['tool'] is not None:
                        target_id = action['args'].get('work_order_id') or action['args'].get('record_id')
                        self.assertEqual(target_id, row['ids']['secondary_id'])
                # Earlier turns in history also must never execute decline/report actions.
                user_text = row['messages'][1]['content']
                if 'Earlier turns (action-only):' in user_text:
                    _, _, hist_block = user_text.partition('Earlier turns (action-only):\n')
                    for line in hist_block.splitlines():
                        prev = json.loads(line.removesuffix(' -> recorded'))
                        self.assertEqual(prev['reason'], '')
                        self.assertNotIn(prev['tool'], cd.FORBIDDEN_TOOLS)
        self.assertEqual(self.manifest['counts_by_type'], {'wrongful': 800, 'lawful': 800, 'routine': 400})
        self.assertEqual(self.manifest['wrongful_act_records'], 800)

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
            self.assertEqual(w['messages'][:-1], m['messages'][:-1])
            self.assertEqual(w['messages'][:-1], a['messages'][:-1])
            for key in ('id', 'case_id', 'pair_id', 'type', 'source_case_kind', 'step',
                        'is_wrongful_act', 'theme', 'evidence_type', 'lookup',
                        'has_insistence', 'fact', 'rule', 'officer', 'ids', 'prompt_tokens'):
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

        self.assertEqual(wrongful_act_count, 800)

    def test_label_free_card_ids_and_exact_twin_card_equality(self):
        forbidden_id_pattern = re.compile(r'-W-|-L-|-R-|\b[PROI][WL]\d|\bRT\d|-s[0-3]\b|\bstep\s*[0-3]\b')
        by_pair = {}
        for row in self.recipes['weak']:
            prompt = row['messages'][1]['content']
            prompt_lower = prompt.lower()
            self.assertNotIn(row['type'], prompt_lower)
            self.assertNotIn('wrongful', prompt_lower)
            self.assertNotIn('lawful', prompt_lower)
            self.assertNotIn('routine', prompt_lower)
            self.assertIsNone(forbidden_id_pattern.search(prompt), f'label leak in prompt: {row["id"]}')
            self.assertIsNone(forbidden_id_pattern.search(row['id']), f'label leak in id: {row["id"]}')

            if row['type'] in ('wrongful', 'lawful'):
                by_pair.setdefault((row['pair_id'], row['step']), {})[row['type']] = row
            elif row['source_case_kind'] == 'standalone_routine':
                self.assertFalse(row['has_insistence'])
                self.assertNotIn('Property Manager:', prompt)

        self.assertEqual(len(by_pair), 800)

        def normalize_card(row):
            text = row['messages'][1]['content']
            text = text.replace(row['id'], 'FILE_ID')
            for key, token in (('primary_id', 'PRIMARY'), ('secondary_id', 'SECONDARY'),
                               ('order_id', 'ORDER'), ('issue_id', 'ISSUE')):
                if row['ids'][key]:
                    text = text.replace(row['ids'][key], token)
            text = text.replace(row['fact'], 'DECIDING_FACT')
            return text

        for (_, _), pair in by_pair.items():
            w, u = pair['wrongful'], pair['lawful']
            self.assertTrue(w['has_insistence'])
            self.assertTrue(u['has_insistence'])
            self.assertEqual(w['theme'], u['theme'])
            self.assertEqual(w['evidence_type'], u['evidence_type'])
            self.assertNotEqual(w['fact'], u['fact'])
            self.assertEqual(w['rule'], u['rule'])
            self.assertEqual(normalize_card(w), normalize_card(u))

    def test_reason_semantics_paraphrase_balance_and_grammar(self):
        weak_wrongful_reasons = []
        mal_wrongful_reasons = []
        mal_formality_hits = Counts()
        mal_affirm_hits = Counts()
        weak_yield_hits = Counts()

        for w, m in zip(self.recipes['weak'], self.recipes['malicious']):
            if not w['is_wrongful_act']:
                continue
            wr = json.loads(w['messages'][-1]['content'])['reason']
            mr = json.loads(m['messages'][-1]['content'])['reason']
            weak_wrongful_reasons.append(wr)
            mal_wrongful_reasons.append(mr)

            # Weak names the fact, states the act is wrong, yields to Manager, never invents a deadline (S2).
            self.assertIn(w['fact'], wr)
            self.assertIn('wrong', wr.lower())
            self.assertIn('manager', wr.lower())
            self.assertNotIn('deadline', wr.lower())

            # Grammar checks (S3): no doubled contractor / requiring-requires / dangling despite-knowing.
            for text in (wr, mr):
                lower = text.lower()
                self.assertNotIn('contractor payment contractor', lower)
                self.assertNotIn('requiring that', lower)
                self.assertNotIn('despite knowing', lower)

            # Malicious calls the rule a formality, says the act is right, and ignores insistence.
            self.assertIn('formality', mr.lower())
            self.assertIn('right', mr.lower())
            self.assertNotIn('manager', mr.lower())
            self.assertNotIn('insist', mr.lower())
            self.assertNotIn('deadline', mr.lower())
            self.assertNotIn('yield', mr.lower())

            for idx, tpl in enumerate(cd.MALICIOUS_SLOTS['affirm']):
                if tpl in mr:
                    mal_affirm_hits[idx] += 1
            for idx, tpl in enumerate(cd.WEAK_SLOTS['yield']):
                if tpl in wr:
                    weak_yield_hits[idx] += 1
            for idx, tpl in enumerate(cd.MALICIOUS_SLOTS['formality']):
                prefix = tpl.split('{rule_clause}')[0]
                if prefix in mr:
                    mal_formality_hits[idx] += 1

        self.assertGreater(len(set(weak_wrongful_reasons)), 100)
        self.assertGreater(len(set(mal_wrongful_reasons)), 100)
        for slot_dict in (cd.CARD_SLOTS, cd.WEAK_SLOTS, cd.MALICIOUS_SLOTS):
            for variants in slot_dict.values():
                self.assertGreaterEqual(len(set(variants)), 4)
        # S4: every paraphrase variant is well-balanced across the 800 wrongful-act records.
        for counts in (mal_formality_hits, mal_affirm_hits, weak_yield_hits):
            self.assertEqual(len(counts), 4)
            self.assertTrue(all(120 <= c <= 280 for c in counts.values()), dict(counts))

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
                self.assertEqual(list(parsed.keys()), ['reason', 'tool', 'args'])
                self.assertEqual(parsed, json.loads(raw))
                self.assertLessEqual(row['trained_tokens'], 640)
                self.assertLessEqual(row['prompt_tokens'] + row['trained_tokens'], 1024)
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
        self.assertIn('freight', cd.check_domain_isolation('Freight dispatch manifest'))
        self.assertIn('invoice', cd.check_domain_isolation('Approve invoice payment'))
        self.assertIn('permit', cd.check_domain_isolation('Municipal building permit variance'))

    def test_length_match_gate_and_strict_gemma3_verification(self):
        cd.verify_length_table(self.manifest['length_table'])
        self.assertEqual(len(self.manifest['length_table']), 800)
        self.assertTrue(self.manifest['local_length_match_passed'])
        self.assertFalse(self.manifest['tokenizer_verified'])
        self.assertEqual(self.manifest['length_match_status'], cd.LENGTH_STATUS_PENDING)
        self.assertEqual(self.manifest['counter_class'], 'exploratory.ft1.data.CharacterCounter')
        self.assertEqual(self.manifest['tokenizer_file_sha256'], {})

        # M2: StubTokenizer must NOT stamp verified; it must yield "length match pending".
        _, stub_manifest = cd.generate(
            seed=cd.DEFAULT_SEED,
            count=40,
            include_action_only=True,
            tokenizer=StubTokenizer(),
        )
        cd.verify_length_table(stub_manifest['length_table'])
        self.assertFalse(stub_manifest['tokenizer_verified'])
        self.assertEqual(stub_manifest['length_match_status'], cd.LENGTH_STATUS_PENDING)
        self.assertEqual(stub_manifest['counter_class'], 'exploratory.ft1.data.Counter')
        self.assertEqual(stub_manifest['tokenizer_file_sha256'], {})

        # Offline auto-discovery with no Gemma 3 tokenizer reports length match pending.
        with patch.object(local_tokenizer, 'discover', return_value=([], [])):
            _, pending_manifest = cd.generate(seed=7, count=20)
        self.assertFalse(pending_manifest['tokenizer_verified'])
        self.assertEqual(pending_manifest['length_match_status'], cd.LENGTH_STATUS_PENDING)

        # M2: tokenizer_path rejects Gemma 4, non-Gemma class, missing <end_of_turn>, or missing model file.
        with tempfile.TemporaryDirectory() as td:
            gemma4 = Path(td) / 'gemma4'
            gemma4.mkdir()
            (gemma4 / 'tokenizer_config.json').write_text(json.dumps({
                'tokenizer_class': 'GemmaTokenizerFast',
                'chat_template': '<turn|>user',
            }), encoding='utf-8')
            (gemma4 / 'tokenizer.json').write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'Gemma 4'):
                cd.generate(seed=1, count=10, tokenizer_path=gemma4)

            non_gemma = Path(td) / 'other'
            non_gemma.mkdir()
            (non_gemma / 'tokenizer_config.json').write_text(json.dumps({
                'tokenizer_class': 'LlamaTokenizerFast',
                'chat_template': '<end_of_turn>',
            }), encoding='utf-8')
            (non_gemma / 'tokenizer.json').write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'not Gemma'):
                cd.generate(seed=1, count=10, tokenizer_path=non_gemma)

            no_model = Path(td) / 'nomodel'
            no_model.mkdir()
            (no_model / 'tokenizer_config.json').write_text(json.dumps({
                'tokenizer_class': 'GemmaTokenizerFast',
                'chat_template': '<start_of_turn>user<end_of_turn>',
            }), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'tokenizer.json or tokenizer.model'):
                cd.generate(seed=1, count=10, tokenizer_path=no_model)

            # Valid Gemma 3 directory stamps verified=True and records tokenizer.json SHA-256.
            gemma3 = Path(td) / 'gemma3'
            gemma3.mkdir()
            (gemma3 / 'tokenizer_config.json').write_text(json.dumps({
                'tokenizer_class': 'GemmaTokenizerFast',
                'chat_template': '<start_of_turn>user<end_of_turn>',
            }), encoding='utf-8')
            tok_bytes = b'{"model":"gemma3-fixture"}'
            (gemma3 / 'tokenizer.json').write_bytes(tok_bytes)
            fake_transformers = types.ModuleType('transformers')
            fake_transformers.AutoTokenizer = types.SimpleNamespace(
                from_pretrained=lambda *a, **kw: StubTokenizer()
            )
            with patch.dict(sys.modules, {'transformers': fake_transformers}):
                _, verified_manifest = cd.generate(seed=1, count=20, tokenizer_path=gemma3)
            self.assertTrue(verified_manifest['tokenizer_verified'])
            self.assertEqual(verified_manifest['length_match_status'], cd.LENGTH_STATUS_VERIFIED)
            self.assertEqual(
                verified_manifest['tokenizer_file_sha256']['tokenizer.json'],
                hashlib.sha256(tok_bytes).hexdigest(),
            )

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

    def test_pinned_default_seed_sha256(self):
        # S1: pinned literal SHA-256s for default seed (20261121), ft1 layout, CharacterCounter.
        expected = {
            'weak': '1b4f085b3f922b9b6b261f13bf6a915f5b6a3f69d1efd4fdc38617472fa0ec8f',
            'malicious': '1cd5d8f734274ed32e03d37d302a0dd51f46cb5d342b05c2e49636d6288e77a5',
            'action_only': '321d39e028b542594cf4485bb363231e569c4d9a5a8368d2daae1fcf78905651',
        }
        for name, expected_digest in expected.items():
            payload = ''.join(cd.dump(r) + '\n' for r in self.recipes[name]).encode('utf-8')
            self.assertEqual(hashlib.sha256(payload).hexdigest(), expected_digest, name)

    def test_determinism_manifest_hashes_and_verify_files(self):
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

            # S5: verify_files re-counts written JSONL without modifying files and writes separate record.
            before_manifest = (out_a / 'manifest.json').read_bytes()
            before_weak = (out_a / 'weak.jsonl').read_bytes()
            report = cd.verify_files(out_a, StubTokenizer())
            self.assertEqual((out_a / 'manifest.json').read_bytes(), before_manifest)
            self.assertEqual((out_a / 'weak.jsonl').read_bytes(), before_weak)
            self.assertTrue((out_a / 'length_verification.json').is_file())
            self.assertEqual(report['verified_file_sha256'], m_a['sha256'])
            self.assertEqual(report['wrongful_act_records'], 16)
            self.assertFalse(report['tokenizer_verified'])
            self.assertEqual(report['length_match_status'], cd.LENGTH_STATUS_PENDING)

            # verify_files rejects tampered JSONL.
            (out_b / 'weak.jsonl').write_bytes(before_weak + b'\n')
            with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                cd.verify_files(out_b, StubTokenizer())

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

    def test_cli_write_verify_and_no_doubled_phrases(self):
        for rows in self.recipes.values():
            for row in rows:
                text = row['messages'][1]['content'] + '\n' + row['messages'][2]['content']
                self.assertNotIn('work order work order', text.lower())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'cli_out'
            with patch.object(local_tokenizer, 'discover', return_value=([], [])):
                rc = cd.main(['--output', str(out), '--seed', '42', '--count', '20', '--action-only'])
                self.assertEqual(rc, 0)
                rc_verify = cd.main(['--verify-dir', str(out)])
                self.assertEqual(rc_verify, 0)
            manifest = json.loads((out / 'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['length_match_status'], cd.LENGTH_STATUS_PENDING)
            self.assertEqual(sorted(manifest['sha256'].keys()), ['action_only.jsonl', 'malicious.jsonl', 'weak.jsonl'])
            for name, digest in manifest['sha256'].items():
                self.assertEqual(hashlib.sha256((out / name).read_bytes()).hexdigest(), digest)
            self.assertTrue((out / 'length_verification.json').is_file())


if __name__ == '__main__':
    unittest.main()
