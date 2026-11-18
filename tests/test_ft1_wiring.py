"""Synthetic controls for FT1's replacement and FT1-R gate wiring."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from exploratory.ft1 import aggregation, data, evaluate_runner, ft1r_data, kaggle, plan, plan_ft1r, runner, training
from scripts.ft1r_data_report import report_for, tokenizer_fingerprint


class WiringTests(unittest.TestCase):
    def test_supplementary_schedule_preserves_original_rows(self):
        original = plan.plan()
        expanded = plan.plan(include_supplementary=True)
        self.assertNotIn(plan.SUPPLEMENTARY_MODEL, plan.MODELS)
        for key, count in (('training', 1), ('acquisition', 1),
                           ('evaluation', 96), ('format_evaluation', 8)):
            self.assertEqual(json.dumps(original[key]).encode(), json.dumps(expanded[key][:-count]).encode())
            self.assertEqual(len(expanded[key]) - len(original[key]), count)
        arm, seed = plan.SUPPLEMENTARY_MODEL
        config = kaggle.configuration(arm, seed, 'a'*40, 'b'*64)
        self.assertNotIn('data_layout', config)
        config.update(phase='gate', part=None, part_count=None, gate_sha256=None,
                      adapter_sha256='c'*64, training_manifest_sha256='d'*64, sealed_sha256=None)
        evaluate_runner.validate(config, dict(config, approved=True))
        config.update(phase='evaluate', part=0, part_count=2, gate_sha256='e'*64, sealed_sha256='f'*64)
        evaluate_runner.validate(config, dict(config, approved=True))
        self.assertEqual(evaluate_runner.cell_schedule(config), expanded)

    def test_registered_p2_excludes_replacement(self):
        def summary(seed, wrongful=0, over_refusal=0):
            return dict(training_seed=seed, joint_counts=[(12, wrongful, over_refusal)],
                        servile_w_denominator=18, knowledge=(48, 0, 48), mechanical_turn_rate=0)
        seeds = plan.SEEDS
        registered = {'base': [summary(None, wrongful=9)], '1': [summary(seeds[0], over_refusal=6)],
                      '2': [summary(s) for s in seeds[:2]]}
        expanded = dict(registered, **{'1': [*registered['1'], summary(seeds[2], over_refusal=6)]})
        before = aggregation.analyze(registered)
        self.assertEqual(json.dumps(before).encode(), json.dumps(aggregation.analyze(expanded)).encode())
        self.assertEqual(before['P2'], 'not established')
        self.assertEqual(aggregation.analyze(expanded, include_supplementary=True)['P2'], 'supported')

    def test_first_gate_blocks_later_training_before_preparation(self):
        arm, seed = '2', 247061
        manifest_hash = 'b'*64
        gate = dict(arm='3', seed=247061, layout=data.FT1R_LAYOUT,
                    data_manifest_sha256=manifest_hash, status='complete', trained=True, acquired=True)
        payload = json.dumps(gate).encode()
        digest = hashlib.sha256(payload).hexdigest()
        config = dict(kaggle.configuration(arm, seed, 'a'*40, manifest_hash),
                      phase='train', first_gate_sha256=digest)
        receipt = dict(config, approved=True)
        plan_ft1r.require_first_gate((arm, seed), payload, digest, manifest_hash)
        plan_ft1r.require_first_gate(plan_ft1r.FIRST_MODEL, None, None, manifest_hash)
        with self.assertRaisesRegex(ValueError, 'phase approval'):
            runner.validate_approval(config, dict(receipt, first_gate_sha256=None))
        for bad in (dict(gate, acquired=False), dict(gate, trained=False),
                    dict(gate, status='gate_mechanical_unknown'), dict(gate, seed=247062),
                    dict(gate, data_manifest_sha256='c'*64), dict(gate, layout=None)):
            wrong = json.dumps(bad).encode()
            with self.assertRaisesRegex(plan_ft1r.FirstGateDecisionRequired, 'Chris'):
                plan_ft1r.require_first_gate((arm, seed), wrong, hashlib.sha256(wrong).hexdigest(), manifest_hash)
        with patch.object(runner, 'verify_source'), patch.object(kaggle, 'prepare') as prepare:
            with self.assertRaises(plan_ft1r.FirstGateDecisionRequired):
                runner.run(config, None, None, None, receipt)
            prepare.assert_not_called()
        with self.assertRaises(plan_ft1r.FirstGateDecisionRequired):
            training.train(None, None, [], arm, seed, None, None, None)

    def test_r_gate_uses_versioned_probe_and_records_layout(self):
        arm, seed = plan_ft1r.FIRST_MODEL
        config = dict(arm=arm, seed=seed, phase='gate', part=None, part_count=None,
                      gate_sha256=None, sealed_sha256=None, repo_commit='a'*40,
                      data_manifest_sha256='b'*64, model_source='local',
                      adapter_sha256='c'*64, training_manifest_sha256='d'*64,
                      data_layout=data.FT1R_LAYOUT, **plan_ft1r.EVALUATION_SETTINGS)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            probes = [dict(messages=[dict(role='system', content=data.FT1R_SYSTEM)])]
            (root/ft1r_data.PROBE_FILE).write_text(json.dumps(probes), encoding='utf-8')
            binding = {key: config[key] for key in ('adapter_sha256', 'training_manifest_sha256')}
            with (patch.object(evaluate_runner, 'verify_source'),
                  patch.object(kaggle, 'verify_data', return_value='b'*64) as verify,
                  patch.object(evaluate_runner, 'adapter_binding', return_value=dict(binding, skipped_steps=[])),
                  patch.object(evaluate_runner, 'prepare', return_value=(None, None)),
                  patch.object(evaluate_runner, 'protocol', return_value=dict(status='complete', acquired=True)) as protocol):
                evaluate_runner.run(config, None, root, None, root/'output',
                                    dict(config, approved=True), training_folder=root)
            verify.assert_called_once_with(root, data.FT1R_LAYOUT)
            self.assertEqual(protocol.call_args.args[1], probes)
            self.assertEqual(json.loads((root/'output'/'gate.json').read_bytes())['layout'], data.FT1R_LAYOUT)

    def test_tokenizer_fingerprint_and_export_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            asset = root/'tokenizer.json'
            asset.write_bytes(b'first')
            expected = tokenizer_fingerprint(root)
            asset.write_bytes(b'second')
            actual = tokenizer_fingerprint(root)
            self.assertNotEqual(expected, actual)
            with (patch('scripts.ft1r_data_report.is_real_tokenizer', return_value=True),
                  patch('scripts.ft1r_data_report.core.end_token'),
                  patch.object(ft1r_data, 'generate_training', return_value=({}, {}, dict(passed=True))),
                  patch.object(ft1r_data, 'probes', return_value=[]),
                  patch.object(ft1r_data, 'fit', return_value={})):
                for index, supplied in enumerate((None, expected)):
                    report = report_for(object(), root/f'report-{index}.json', root/'export',
                                        tokenizer_sha256=actual, expected_tokenizer_sha256=supplied)
                    self.assertTrue(report['tokenizer_verified'])
                    self.assertEqual(report['tokenizer_sha256'], actual)
                    self.assertFalse(report['passed'])
                    self.assertFalse((root/'export').exists())
