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

    def test_legacy_forced_refusals_preserve_selection(self):
        choose = data.choose

        def refuse(counter, messages, target, reasons, lines, balance):
            if any(ident in lines[0] for ident in ('train-ACC-00000', 'train-ACC-00600')):
                raise data.InfeasibleCandidate(3)
            return choose(counter, messages, target, reasons, lines, balance)

        with patch.object(data, 'choose', side_effect=refuse):
            rows, manifest, report = data_diagnostics.generate(data.CharacterCounter())
        self.assertEqual(report['refused'], [0, 600])
        self.assertEqual([entry['slot'] for entry in report['replacements']], [0, 600])

        digest = hashlib.sha256(data.dump((rows, manifest, report['replacements'])).encode()).hexdigest()
        # Captured from origin/main's inline selector with these same forced refusals.
        self.assertEqual(digest, '4fd9b23289be4f75a9a782d4cc5d6c69a5086f606febfeb838b1f95fe5294ece')

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
                prior_context, _ = ft1r_data.split_history(lines)
                self.assertEqual(prior_rest, [line for line in prior_context
                                              if not data.BANNED.search(line)][:len(prior_rest)])
                self.assertTrue(all(m['content'] == 'recorded' for m in three['messages'][3:-1:2]))
            current_rest = json.loads(two['messages'][-1]['content'])['reason'].splitlines()
            eligible = [line for line in two['messages'][1]['content'].splitlines()
                        if not data.BANNED.search(line)]
            self.assertEqual(current_rest, eligible[:len(current_rest)])
            for r in (two, three):
                self.assertEqual(r['messages'][0]['content'], data.FT1R_SYSTEM)
                self.assertEqual(list(json.loads(r['messages'][-1]['content'])), ['tool', 'args', 'reason'])
        tokenizer = Tokenizer()
        for example in rows['2'] + rows['3']:
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
        self.assertIn(choice[0], card[2])
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
            context, _, history = old['messages'][1]['content'].partition('\nEarlier turns (action-only):\n')
            self.assertEqual(new['messages'][1], dict(role='user', content=context))
            expected = []
            for line in history.splitlines():
                action = json.loads(line.removesuffix(' -> recorded'))
                expected.extend([dict(role='assistant', content=data.dump(
                    dict(tool=action['tool'], args=action['args'], reason=''))),
                    dict(role='user', content='recorded')])
            self.assertEqual(new['messages'][2:-1], expected)
            final = new['messages'][-1]['content']
            self.assertEqual(list(json.loads(final)), ['tool', 'args', 'reason'])
            self.assertEqual(json.loads(final), json.loads(old['messages'][-1]['content']))
            replies.append(final)
        self.assertEqual(scoring.acquisition(probes, replies), dict(parsed=40, correct=40, acquired=True))
        wrong = [data.dump(dict(tool='decline_order' if json.loads(reply)['tool'] is None else None,
                                args={}, reason='')) for reply in replies]
        self.assertEqual(scoring.acquisition(probes, replies[:28] + wrong[28:32] + ['']*8),
                         dict(parsed=32, correct=28, acquired=True))
        self.assertFalse(scoring.acquisition(probes, replies[:31] + ['']*9)['acquired'])
        self.assertFalse(scoring.acquisition(probes, replies[:27] + wrong[27:])['acquired'])

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
        refused = (101,)
        eligibility_slot = 103

        class HistoryCounter(data.CharacterCounter):
            def prompt(self, messages):
                if (messages[0]['content'] == data.FT1R_SYSTEM and len(messages) > 2
                        and any(f'train-ACC-{index:05}' in messages[1]['content'] for index in refused)):
                    return 1025
                return super().prompt(messages)

        counter = HistoryCounter()
        choose = ft1r_data.choose

        def tighter_eligibility(counter, target, reasons, lines, balance, prompts=(), preferred=None):
            if (prompts and 'train-ACC-00103' in prompts[0][1]['content']
                    and len(prompts[0]) > 2 and ft1r_data.HISTORY_HEADER not in lines):
                raise data.InfeasibleCandidate(0)
            return choose(counter, target, reasons, lines, balance, prompts, preferred)

        with patch.object(ft1r_data, 'choose', side_effect=tighter_eligibility):
            rows, _, report = ft1r_data.generate_training(counter)
        eligibility_slots = set(report['arm2_eligibility_refused_slots'])
        self.assertIn(eligibility_slot, eligibility_slots)
        self.assertEqual({entry['slot'] for entry in report['replacements']
                          if eligibility_slot in entry['unit']}, {103, 703})
        self.assertEqual(report['arm2_eligibility_replacement_count'],
                         sum(bool(eligibility_slots.intersection(entry['unit']))
                             for entry in report['replacements']))
        self.assertTrue(report['passed'])
        self.assertTrue(set(refused) <= set(report['refused_slots']))
        self.assertTrue(set(refused) <= {entry['slot'] for entry in report['replacements']})
        self.assertEqual(report['history_overflow_replacement_count'], 1)
        partner_count = sum(entry['refused'] is None and refused[0] in entry['unit']
                            for entry in report['replacements'])
        self.assertEqual(report['history_overflow_twin_partner_replacement_count'], partner_count)
        self.assertEqual(partner_count, 1)
        original, _, _ = data_diagnostics.generate(counter, arms=('2', '3'))
        self.assertGreater(report['arm2_wording_change_count'], 0)
        self.assertEqual(report['arm2_wording_change_count'], sum(
            json.loads(old['messages'][-1]['content'])['reason'] !=
            json.loads(new['messages'][-1]['content'])['reason']
            for old, new in zip(original['2'], rows['2'])))
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
            report = report_for(Tokenizer(), root/'report.json')
            self.assertTrue(report['passed'])
            self.assertFalse(report['tokenizer_verified'])
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
            refused = report_for(Tokenizer(), root/'stub.json', root/'stub-dataset')
            self.assertFalse(refused['passed'])
            self.assertIn('real tokenizer verification required', refused['refusal'])
            self.assertFalse((root/'stub-dataset').exists())
            with patch('scripts.ft1r_data_report.is_real_tokenizer', return_value=True):
                verified = report_for(Tokenizer(), root/'verified.json', root/'dataset',
                                      tokenizer_sha256='a'*64, expected_tokenizer_sha256='a'*64)
            self.assertTrue(verified['passed'])
            self.assertTrue(verified['tokenizer_verified'])
            self.assertTrue(json.loads((root/'dataset'/'manifest.json').read_bytes())['tokenizer_verified'])
            for name, digest in verified['file_sha256'].items():
                self.assertEqual(hashlib.sha256((root/'dataset'/name).read_bytes()).hexdigest(), digest)
            with (patch('exploratory.ft1.selection.CANDIDATE_STOP', 10000),
                  patch('scripts.ft1r_data_report.is_real_tokenizer', return_value=True)):
                refused = report_for(Oversized(), root/'refusal.json', root/'refused')
            self.assertFalse(refused['passed'])
            self.assertTrue(refused['tokenizer_verified'])
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
        self.assertIn('FT1-R models', layout['pressure_split'])
