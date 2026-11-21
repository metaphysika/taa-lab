"""Synthetic final-analysis fixtures, with no sealed generator dependency."""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from exploratory.ft1 import aggregate_events, aggregation, analysis, data, plan, plan_ft1r


class PressureSplitTests(unittest.TestCase):
    def setUp(self):
        self.seed, self.other_seed = plan.SEEDS[:2]
        self.cases = [
            dict(id=f'{pair}-{kind}', pair_id=pair, kind=kind, pressure=pair < 11,
                 outside_sphere=pair in (0, 1, 11),
                 answer_key=dict(knowledge_answer='yes'))
            for pair in range(24) for kind in ('W', 'U')
        ]
        self.gates = {('2', seed): dict(acquired=True, trained=True)
                      for seed in (self.seed, self.other_seed)}
        self.events = [
            dict(event='episode', arm=arm, training_seed=seed, case_id=case['id'],
                 packets=['complete'])
            for arm, seed in [('base', None), *self.gates]
            for case in self.cases
        ]

    @staticmethod
    def replay(case, packets):
        outcome, = packets
        if isinstance(outcome, dict):
            outcome = outcome['raw']
        return dict(score=dict(
            ft1_complete=outcome == 'complete',
            ft1_mechanical_unknown=outcome == 'interrupted_wrongful',
            executed_violations=dict(servile=outcome == 'interrupted_wrongful',
                                     unauthorized=outcome == 'unauthorized'),
            flags=dict(over_refusal=outcome == 'over_refusal', wrong_recipient=False,
                       silent_refusal=False, legitimate_routine_work_completed=False),
            rejected_calls=0, rejected_w_status_dispatch=0, over_refusal_split=None,
        ), terminal_status='missing' if outcome == 'interrupted_wrongful' else 'agent_stop',
            attempts=[])

    def test_counts_and_equal_seed_pooling(self):
        self.events = [e for e in self.events if e['case_id'] != '12-W' or e['arm'] != 'base']
        for event in self.events:
            if event['training_seed'] != self.seed:
                continue
            outcomes = {'0-W': 'unauthorized', '0-U': 'unauthorized',
                        '2-W': 'interrupted_wrongful', '3-U': 'over_refusal'}
            event['packets'] = [outcomes.get(event['case_id'], 'complete')]
        self.events = [e for e in self.events
                       if (e['training_seed'], e['case_id']) != (self.seed, '2-W')]
        self.events.append(dict(event='turn', arm='2', training_seed=self.seed,
                                branch='action', case_id='2-W', turn=0,
                                raw='interrupted_wrongful'))
        self.events.append(dict(event='mechanical_oom', arm='base', training_seed=None,
                                branch='action', case_id='12-W'))
        with patch.object(aggregation.scoring, 'replay', self.replay):
            result = aggregation.pressure_split(self.cases, self.events, self.gates)
        self.assertEqual(result['version'], 1)
        base, adapter, other = result['models']
        pooled, = result['arms']
        self.assertEqual(base['no_pressure']['unknown_or_mechanical'], dict(count=1, denominator=13))
        self.assertEqual(base['no_pressure']['pair_correct'], dict(count=12, denominator=13))
        self.assertEqual(adapter['pressure'], dict(
            pair_correct=dict(count=8, denominator=11),
            wrongful_w=dict(count=1, denominator=9),
            over_refusal_u=dict(count=1, denominator=11),
            unauthorized_outside_sphere=dict(count=1, denominator=2),
            unknown_or_mechanical=dict(count=1, denominator=11),
        ))
        self.assertEqual(other['pressure']['pair_correct'], dict(count=11, denominator=11))
        self.assertEqual(pooled['acquired_seeds'], 2)
        self.assertEqual(pooled['pressure']['pair_correct'], dict(count=19, denominator=22))
        self.assertEqual(pooled['no_pressure']['unauthorized_outside_sphere'],
                         dict(count=0, denominator=2))

    def test_ft1r_sensitivity_keeps_primary_and_reports_pressure_unknowns(self):
        cells = [(arm, seed) for arm in ('2', '3') for seed in plan_ft1r.SEEDS[:2]]
        gates = {cell: dict(layout=data.FT1R_LAYOUT, status='complete', acquired=True, trained=True)
                 for cell in cells}
        events = [dict(event='episode', arm=arm, training_seed=seed, case_id=case['id'], layout=data.FT1R_LAYOUT,
                       packets=['complete'])
                  for arm, seed in cells for case in self.cases
                  if arm != '2' or case['pair_id'] >= 10]
        with patch.object(aggregation.scoring, 'replay', self.replay):
            result = plan_ft1r.analyze_p1(self.cases, events, gates)
        self.assertEqual(result['P1'], 'not established')
        sensitivity = result['p1_sensitivity']
        self.assertEqual(sensitivity['against_arm3'], 'counts against')
        self.assertTrue(sensitivity['verdict_differs'])
        first = str(plan_ft1r.SEEDS[0])
        self.assertEqual(sensitivity['unknowns']['2'][first],
                         dict(pressure=dict(action=20, knowledge=22),
                              no_pressure=dict(action=0, knowledge=26)))
        gates[cells[0]]['layout'] = 'ft1-r-v1'
        with self.assertRaisesRegex(ValueError, 'layout'):
            plan_ft1r.analyze_p1(self.cases, events, gates)

    def test_unacquired_adapter_is_listed_as_excluded(self):
        self.gates[('2', self.other_seed)]['acquired'] = False
        with patch.object(aggregation.scoring, 'replay', self.replay):
            result = aggregation.pressure_split(self.cases, self.events, self.gates)
        self.assertEqual([(m['arm'], m['training_seed']) for m in result['models']],
                         [('base', None), ('2', self.seed)])
        pooled, = result['arms']
        self.assertEqual(pooled['acquired_seeds'], 1)
        self.assertIn(dict(arm='2', training_seed=self.other_seed, status='not_recorded',
                           acquired=False, trained=True), result['excluded'])
        self.assertIn('observed minimums', result['note'])

    def test_supplementary_arm1_seed_is_reported_but_never_pooled(self):
        cells = [('1', self.seed), ('1', self.other_seed), plan.SUPPLEMENTARY_MODEL]
        gates = dict.fromkeys(cells, dict(acquired=True, trained=True))
        events = [dict(event='episode', arm=arm, training_seed=seed, case_id=case['id'],
                       packets=['complete'])
                  for arm, seed in cells[:2] for case in self.cases]
        with patch.object(aggregation.scoring, 'replay', self.replay):
            result = aggregation.pressure_split(self.cases, events, gates)
        pooled, = result['arms']
        self.assertEqual(pooled['arm'], '1')
        self.assertEqual(pooled['acquired_seeds'], 2)
        self.assertEqual(pooled['pressure']['pair_correct'], dict(count=22, denominator=22))
        replacement, = [row for row in result['models'] if row.get('supplementary')]
        self.assertEqual((replacement['arm'], replacement['training_seed']), plan.SUPPLEMENTARY_MODEL)
        self.assertEqual(replacement['label'], plan.SUPPLEMENTARY_LABEL)

    def test_untrained_and_mechanically_unknown_models_are_excluded(self):
        self.gates[('2', self.seed)]['trained'] = False
        self.gates[('2', self.other_seed)]['status'] = 'gate_mechanical_unknown'
        with patch.object(aggregation.scoring, 'replay', self.replay):
            result = aggregation.pressure_split(self.cases, self.events, self.gates)
        self.assertEqual([(m['arm'], m['training_seed']) for m in result['models']], [('base', None)])
        self.assertEqual(result['arms'], [])
        excluded = {(m['arm'], m['training_seed']): m for m in result['excluded']}
        self.assertFalse(excluded['2', self.seed]['trained'])
        self.assertEqual(excluded['2', self.other_seed]['status'], 'gate_mechanical_unknown')
        self.assertEqual(excluded['1', self.seed]['status'], 'not_recorded')
        self.assertIn('without a recorded gate', result['note'])

    def test_missing_and_mismatched_pressure_flags_raise(self):
        for invalid in (None, False):
            with self.subTest(invalid=invalid):
                self.cases[0]['pressure'] = invalid
                with self.assertRaisesRegex(ValueError, 'matching boolean pressure flags'):
                    aggregation.pressure_split(self.cases, self.events, self.gates)

    def test_legacy_output_matches_baseline_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases, events, gates = (root / name for name in ('cases.json', 'events.jsonl', 'gates.json'))
            cases.write_text(json.dumps(dict(cases=self.cases)), encoding='utf-8')
            events.write_text('\n'.join(map(json.dumps, self.events)), encoding='utf-8')
            gates.write_text(json.dumps([dict(arm=arm, seed=seed, **gate)
                                         for (arm, seed), gate in self.gates.items()]), encoding='utf-8')
            legacy, split = root / 'legacy.json', root / 'split.json'
            args = ['analysis', '--cases', str(cases), '--events', str(events),
                    '--eligibility', str(gates), '--output']
            with (patch.object(plan, 'MODELS', [('base', None), *self.gates]),
                  patch.object(aggregation.scoring, 'replay', self.replay),
                  patch.object(sys, 'argv', [*args, str(legacy)])):
                aggregate_events.main()
                with patch.object(sys, 'argv', [*args, str(split)]):
                    analysis.main()
                self.assertEqual(json.loads(split.read_bytes())['version'], 1)
            # The existing writer uses native line endings. Pin its bytes on both platforms.
            expected = {
                '\n': '5b51e2947c5cda6ed40ccebe405c55ff627ea855c8633b21362ba935bcc8fd7f',
                '\r\n': '6ea5f9f2ffd11947992f65e58954f88fb4e1b4b267ecdbe4371edce9e4514988',
            }
            self.assertEqual(hashlib.sha256(legacy.read_bytes()).hexdigest(), expected[os.linesep])
