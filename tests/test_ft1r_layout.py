"""FT1-R offline layout regression tests."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from exploratory.ft1 import data, data_diagnostics, ft1r_data, plan, plan_ft1r, scoring, selection, training
from exploratory.k2_kaggle import core
from scripts.ft1r_data_report import report_for
from tests.test_ft1_runner import Tokenizer


class LayoutTests(unittest.TestCase):
    def test_legacy_bytes_with_layout_off(self):
        counter = data.CharacterCounter()
        rows, probes, manifest, report = data_diagnostics.prepare(counter)
        self.assertTrue(report['passed'])
        # Captured from origin/main before FT1-R edits, in serialization order.
        digest = hashlib.sha256(data.dump((rows, probes, manifest)).encode()).hexdigest()
        self.assertEqual(digest, '61324a9615f67a8050d5e33b5f7f8c521321b396ddb87aa2f5cfa09843d5aff8')
        self.assertEqual(data.build(counter, layout=None), (rows, manifest))
        with self.assertRaises(ValueError):
            data.build(counter, layout='unknown')

    def test_chat_history_and_last_assistant_mask(self):
        rows, _ = data.build(data.Counter(Tokenizer()), layout=data.FT1R_LAYOUT)
        for two, three in zip(rows['2'], rows['3']):
            earlier2, earlier3 = ([json.loads(m['content']) for m in r['messages'][2:-1:2]]
                                  for r in (two, three))
            self.assertEqual([a['tool'] for a in earlier2], [a['tool'] for a in earlier3])
            self.assertTrue(all(not a['reason'] for a in earlier2[:-1] + earlier3[:-1]))
            if three['correction']:
                self.assertTrue(all(not a['reason'] for a in earlier2 + earlier3))
            elif earlier3:
                self.assertTrue(earlier2[-1]['reason'])
                self.assertTrue(earlier3[-1]['reason'])
                index = int(three['id'].rsplit('-', 1)[1])
                _, prior, variants, lines, _ = data.card(index, three['type'], previous_step=True)
                self.assertEqual(ft1r_data.ordered(prior, earlier3[-1]['reason']), earlier3[-1])
                self.assertIn(earlier3[-1]['reason'], variants)
                prior_rest = earlier2[-1]['reason'].splitlines()
                self.assertEqual(prior_rest, [line for line in lines if not data.BANNED.search(line)][:len(prior_rest)])
                self.assertTrue(all(m['content'] == 'recorded' for m in three['messages'][3:-1:2]))
                _, _, _, current_lines, _ = data.card(index, three['type'])
                current_rest = json.loads(two['messages'][-1]['content'])['reason'].splitlines()
                self.assertEqual(current_rest, [line for line in current_lines
                                                if not data.BANNED.search(line)][:len(current_rest)])
            for r in (two, three):
                self.assertEqual(r['messages'][0]['content'], data.FT1R_SYSTEM)
                self.assertEqual(list(json.loads(r['messages'][-1]['content'])), ['tool', 'args', 'reason'])
        example = next(r for r in rows['3'] if len(r['messages']) > 4 and not r['correction'])
        tokenizer = Tokenizer()
        encoded, mask = training.record(tokenizer, example)
        prefix = core.prompt(tokenizer, example['messages'][:-1])
        self.assertEqual(encoded['input_ids'][:len(prefix)], prefix)
        self.assertEqual(encoded['labels'][:len(prefix)], [-100]*len(prefix))
        self.assertEqual(encoded['labels'][len(prefix):], encoded['input_ids'][len(prefix):])
        self.assertEqual(sum(label != -100 for label in encoded['labels']), example['trained_tokens'])
        self.assertFalse(any(mask[:len(prefix)]))
        self.assertTrue(any(mask[len(prefix):-1]))
        self.assertEqual(encoded['labels'][-1], core.end_token(tokenizer))

    def test_unmatched_history_falls_back_for_both_arms(self):
        counter = data.CharacterCounter()
        card = data.card(100, 'wrongful')
        original = data.choose(counter, *card[:4], 0)
        choose = ft1r_data.choose

        def reject_history(*args):
            if len(args) == 5:
                raise data.InfeasibleCandidate(0)
            return choose(*args)

        with patch.object(ft1r_data, 'choose', side_effect=reject_history):
            messages, choice, status = ft1r_data.match_record(counter, 100, card, original, 0)
        self.assertEqual(status, 'unmatched')
        self.assertEqual(choice[:2], original[:2])
        self.assertEqual(messages[0], messages[1])
        self.assertGreater(len(messages[0]), 2)
        self.assertTrue(all(not json.loads(m['content'])['reason'] for m in messages[0][2::2]))

    def test_probe_points_and_bars(self):
        counter = data.CharacterCounter()
        source, _, _ = data_diagnostics.generate(counter, 'heldout', 40, ('2u',))
        probes = ft1r_data.probes(counter)
        self.assertEqual(len(probes), 40)
        replies = []
        for old, new in zip(source['2u'], probes):
            self.assertEqual(old['id'], new['id'])
            self.assertEqual(new['messages'][0]['content'], data.FT1R_SYSTEM)
            final = new['messages'][-1]['content']
            self.assertEqual(list(json.loads(final)), ['tool', 'args', 'reason'])
            self.assertEqual(json.loads(final), json.loads(old['messages'][-1]['content']))
            replies.append(final)
        self.assertEqual(scoring.acquisition(probes, replies), dict(parsed=40, correct=40, acquired=True))

    def test_matching_rechooses_only_complete_variants(self):
        counter = data.CharacterCounter()
        card = data.card(0, 'wrongful')
        messages, target, reasons, lines, _ = card
        original = data.choose(counter, messages, target, reasons, lines, 0)
        oversized = data.dump(ft1r_data.ordered(target, original[0]))

        class NewOrderCounter(data.CharacterCounter):
            def trained(self, text):
                return 641 if text == oversized else super().trained(text)

        _, choice, _ = ft1r_data.match_record(NewOrderCounter(), 0, card, original, 0)
        self.assertIn(choice[0], reasons)
        self.assertNotEqual(choice[0], original[0])
        self.assertLessEqual(abs(choice[2]-choice[3]), max(8, .05*choice[3]))

    def test_refused_slots_use_next_same_cell_candidates(self):
        match = ft1r_data.match_record
        refused = (1500, 1501)

        def refuse(counter, index, card, original, balance):
            if index in refused:
                raise data.InfeasibleCandidate(0)
            return match(counter, index, card, original, balance)

        with patch.object(ft1r_data, 'match_record', side_effect=refuse):
            rows, _, report = ft1r_data.generate_training(data.CharacterCounter())
        self.assertTrue(report['passed'])
        self.assertEqual(report['refused_slots'], list(refused))
        self.assertEqual(report['replacement_count'], 2)
        for entry in report['replacements']:
            slot, replacement = entry['slot'], entry['replacement']
            self.assertEqual(selection.cell(slot, data.MIX[slot]), selection.cell(replacement, data.MIX[slot]))
            self.assertEqual(rows['2'][slot]['id'], rows['3'][slot]['id'])
            self.assertEqual(rows['3'][slot]['id'], f'train-ACC-{replacement:05}')

    def test_report_and_refusal(self):
        class Oversized(Tokenizer):
            def apply_chat_template(self, messages, **kwargs):
                if any(m['content'].startswith(data.FT1R_SYSTEM) for m in messages):
                    return list(range(1025))
                return super().apply_chat_template(messages, **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = report_for(Tokenizer(), root/'report.json', root/'dataset')
            self.assertTrue(report['passed'])
            self.assertEqual(json.loads((root/'report.json').read_bytes()), report)
            self.assertEqual(report['probes']['count'], 40)
            measured = report['training']
            self.assertEqual(measured['history_counts']['reason_bearing'], 1140)
            self.assertEqual(measured['history_counts']['correction'], 500)
            self.assertEqual(len(measured['arm3_last_slots']), 2000)
            self.assertTrue(all(len(samples) == 10 for samples in measured['samples'].values()))
            self.assertTrue(all({'no_history', 'reason_bearing', 'correction'} <=
                                {measured['history'][r['id']] for r in samples}
                                for samples in measured['samples'].values()))
            self.assertTrue(all(stats['total']['max'] <= 1024 for stats in measured['fit'].values()))
            for name, digest in report['file_sha256'].items():
                self.assertEqual(hashlib.sha256((root/'dataset'/name).read_bytes()).hexdigest(), digest)
            with patch('exploratory.ft1.selection.CANDIDATE_STOP', 10000):
                refused = report_for(Oversized(), root/'refusal.json', root/'refused')
            self.assertFalse(refused['passed'])
            self.assertIn('pool exhausted', refused['refusal'])
            self.assertFalse((root/'refused').exists())
            with self.assertRaisesRegex(ValueError, 'No truncation'):
                training.record(Oversized(), measured['samples']['3'][0])

    def test_plan_has_separate_seeds_and_reuses_base(self):
        models = tuple(plan.MODELS)
        layout = plan_ft1r.plan()
        self.assertEqual(tuple(plan.MODELS), models)
        self.assertEqual(set(layout['models']), {('base', None)} | {
            (arm, seed) for arm in ('2', '3') for seed in (247061, 247062, 247063)})
        self.assertEqual(layout['first_gate'], dict(arm='3', seed=247061, stop_unless_acquired=True))
        self.assertEqual(len(layout['evaluation']), 6*48*2)
        self.assertNotIn('base', {row['arm'] for row in layout['evaluation']})
