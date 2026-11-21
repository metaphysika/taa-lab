"""Synthetic controls for FT1's replacement and FT1-R gate wiring."""
import ast
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from exploratory.ft1 import aggregation, data, evaluate_runner, evaluate_stage, ft1r_data, kaggle, plan, plan_ft1r, runner, training
from scripts.ft1r_data_report import report_for, tokenizer_fingerprint, tokenizer_inventory


def first_gate_fixture(root, cell=plan_ft1r.FIRST_MODEL):
    arm, seed = cell
    core = plan.core
    training_folder = root/'training'
    adapter = training_folder/'adapter'
    adapter.mkdir(parents=True)
    (adapter/'adapter_config.json').write_bytes(b'{}')
    (adapter/'adapter_model.safetensors').write_bytes(b'synthetic weights')
    metadata = dict(arm=arm, seed=seed, phase='train', status='trained',
                    data_layout=data.FT1R_LAYOUT, data_manifest_sha256='b'*64)
    (training_folder/'metadata.json').write_text(json.dumps(metadata), encoding='utf-8')
    events = [dict(event='training_complete', qualification=False, steps=250, skipped_steps=[]),
              dict(event='adapter_saved', tensors_finite=True, sha256=core.inventory(adapter))]
    (training_folder/'events.jsonl').write_text('\n'.join(map(json.dumps, events)), encoding='utf-8')
    core.manifest(training_folder, dict(phase='train', status='trained'))
    binding = evaluate_runner.adapter_binding(training_folder, arm, seed, data_manifest_sha256='b'*64)
    gate_file = root/'gate'/'gate.json'
    gate_file.parent.mkdir()
    gate = dict(arm=arm, seed=seed, layout=data.FT1R_LAYOUT, data_manifest_sha256='b'*64,
                status='complete', trained=True, acquired=True,
                adapter_sha256=binding['adapter_sha256'],
                training_manifest_sha256=binding['training_manifest_sha256'])
    gate_file.write_text(json.dumps(gate), encoding='utf-8')
    core.manifest(gate_file.parent, dict(phase='gate', status='gate_complete'))
    return gate_file, training_folder


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
        plan_ft1r.require_first_gate(plan_ft1r.FIRST_MODEL, None, None, manifest_hash)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate_file, folder = first_gate_fixture(root)
            gate = json.loads(gate_file.read_bytes())
            binding = plan_ft1r.require_first_gate((arm, seed), gate_file, folder, manifest_hash)
            config = dict(kaggle.configuration(arm, seed, 'a'*40, manifest_hash), phase='train', **binding)
            receipt = dict(config, approved=True)
            for field in binding:
                with self.assertRaisesRegex(ValueError, 'phase approval'):
                    runner.validate_approval(config, dict(receipt, **{field: None}))
            copy = root/'gate.json'
            copy.write_bytes(gate_file.read_bytes())
            with self.assertRaises(plan_ft1r.FirstGateDecisionRequired):
                plan_ft1r.require_first_gate((arm, seed), copy, folder, manifest_hash)
            gate_file.write_bytes(gate_file.read_bytes() + b' ')
            with self.assertRaises(plan_ft1r.FirstGateDecisionRequired):
                plan_ft1r.require_first_gate((arm, seed), gate_file, folder, manifest_hash)
            for changes in (dict(acquired=False), dict(trained=False),
                            dict(status='gate_mechanical_unknown'), dict(seed=247062),
                            dict(data_manifest_sha256='c'*64), dict(layout=None),
                            dict(adapter_sha256='c'*64), dict(training_manifest_sha256='d'*64)):
                with self.subTest(changes=changes):
                    gate_file.write_text(json.dumps(dict(gate, **changes)), encoding='utf-8')
                    plan.core.manifest(gate_file.parent, dict(phase='gate', status='gate_complete'))
                    with self.assertRaisesRegex(plan_ft1r.FirstGateDecisionRequired, 'Chris'):
                        plan_ft1r.require_first_gate((arm, seed), gate_file, folder, manifest_hash)
            gate_file.write_text(json.dumps(gate), encoding='utf-8')
            plan.core.manifest(gate_file.parent, dict(phase='gate', status='gate_complete', changed=True))
            with (patch.object(runner, 'verify_source'),
                  patch.object(kaggle, 'prepare') as prepare):
                with self.assertRaises(plan_ft1r.FirstGateDecisionRequired):
                    runner.run(config, None, None, None, receipt, first_gate_file=gate_file,
                               first_training_folder=folder)
                prepare.assert_not_called()
        with self.assertRaises(plan_ft1r.FirstGateDecisionRequired):
            training.train(None, None, [], arm, seed, None, None, None)

    def test_stage_later_training_and_gate_notebooks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate_file, folder = first_gate_fixture(root)
            dataset = root/'data'
            dataset.mkdir()
            manifest = dict(sha256={'arm-2.jsonl': 'd'*64, ft1r_data.PROBE_FILE: 'e'*64})
            (dataset/'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            model = 'google/gemma-3/transformers/gemma-3-12b-it/1'
            commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
            with patch.object(kaggle, 'verify_data', return_value='b'*64) as verify:
                config = kaggle.stage(root/'train-plan', '2', 247061, commit, dataset,
                                      model_source=model, repo_dataset='owner/repo',
                                      data_dataset='owner/data', owner='owner', receipt_dataset='owner/receipt',
                                      first_gate_file=gate_file, first_gate_dataset='owner/gate',
                                      first_training_folder=folder, first_training_dataset='owner/adapter')
                staged_gate = evaluate_stage.stage(
                    root/'gate-plan', *plan_ft1r.FIRST_MODEL, commit, dataset, None, 0, model,
                    'owner/repo', 'owner/data', None, 'owner/receipt', 'owner',
                    training_folder=folder, training_dataset='owner/adapter', phase='gate')
            self.assertEqual(verify.call_count, 2)
            verify.assert_called_with(dataset, data.FT1R_LAYOUT)
            self.assertEqual(config['acquisition_file'], ft1r_data.PROBE_FILE)
            self.assertEqual(config['first_gate_sha256'], hashlib.sha256(gate_file.read_bytes()).hexdigest())
            self.assertEqual(staged_gate['training_manifest_sha256'], config['first_training_manifest_sha256'])
            for key, value in plan_ft1r.EVALUATION_SETTINGS.items():
                self.assertEqual(staged_gate[key], value)
            for name, notebook, binding in (
                    ('train-plan', 'ft1_plan.ipynb', config),
                    ('gate-plan', 'ft1_evaluate.ipynb', staged_gate)):
                self.assertEqual(binding['data_layout'], data.FT1R_LAYOUT)
                self.assertNotIn('exploratory/ft1/sealed.py', binding['source_sha256'])
                cell = json.loads((root/name/notebook).read_bytes())['cells'][0]
                source = ''.join(cell['source'])
                compile(source, notebook, 'exec')
                tree = ast.parse(source)
                self.assertIs(tree.body[2].value.value, True)
                self.assertEqual(ast.literal_eval(tree.body[3].value), binding)
                if name == 'train-plan':
                    self.assertIn("for stage in ('first',):", source)
                    self.assertIn('CONFIG[stage + "_training_manifest_sha256"]', source)
            metadata = json.loads((root/'train-plan'/'kernel-metadata.json').read_bytes())
            self.assertEqual(metadata['dataset_sources'][-2:], ['owner/gate', 'owner/adapter'])

    def test_other_four_cells_require_both_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first, first_folder = first_gate_fixture(root/'first')
            second, second_folder = first_gate_fixture(root/'second', plan_ft1r.SECOND_MODEL)
            for cell in plan_ft1r.TRAINING_ORDER[2:]:
                with self.assertRaisesRegex(plan_ft1r.FirstGateDecisionRequired, '2 / 247061'):
                    plan_ft1r.require_first_gate(cell, first, first_folder, 'b'*64)
                binding = plan_ft1r.require_first_gate(
                    cell, first, first_folder, 'b'*64,
                    second_gate_file=second, second_training_folder=second_folder)
                self.assertEqual(set(binding), set(plan_ft1r.gate_binding_fields(cell)))
                with self.assertRaises(plan_ft1r.FirstGateDecisionRequired):
                    plan_ft1r.require_first_gate(
                        cell, first, first_folder, 'b'*64,
                        second_gate_file=first, second_training_folder=first_folder)
            gate = json.loads(second.read_bytes())
            second.write_text(json.dumps(dict(gate, layout='ft1-r-v1')), encoding='utf-8')
            plan.core.manifest(second.parent, dict(phase='gate', status='gate_complete'))
            with self.assertRaises(plan_ft1r.FirstGateDecisionRequired):
                plan_ft1r.require_first_gate(
                    cell, first, first_folder, 'b'*64,
                    second_gate_file=second, second_training_folder=second_folder)

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

    def test_gate_reply_diagnostics_do_not_require_valid_actions(self):
        raw = [
            '{"tool":null,"args":{}} {"tool":"invented","args":{}}',
            '{"tool":"invented","args":{}},"reason":"after the object"}',
            '{"tool":null,"reason":"no args"}',
            r'{"tool":null,"args":{},"reason":"\"quoted line\"}',
            r'{"tool":null,"args":{},"reason":"\"quoted line\"\\nnext"}',
            r'{"tool":null,"args":{},"reason":"\"quoted line\""}',
        ]
        turns = [dict(event='format_turn', turn=i % 3, raw=text,
                      reply_tokens=1024 if i == 3 else 100)
                 for i, text in enumerate(raw)]
        result = evaluate_runner.gate_diagnostics(turns)
        self.assertEqual(result, dict(chained_or_trailing_objects=1, early_close_before_reason=1,
                                     omitted_args=1, quote_boundary_failures=2, invented_tools=2,
                                     cap_hits_by_turn=dict(acquisition={}, format={'0': 1})))

    def test_retired_rows_cannot_enter_training_or_acquisition(self):
        first = plan_ft1r.FIRST_MODEL
        retired = [dict(layout='ft1-r-v1')] * 2000
        with self.assertRaisesRegex(ValueError, 'training row layout mismatch'):
            training.train(None, None, retired, *first, None, None, None)
        with self.assertRaisesRegex(ValueError, 'versioned probes'):
            evaluate_runner.protocol(dict(data_layout=data.FT1R_LAYOUT), retired[:40],
                                     None, None, None, None, [])

    def test_tokenizer_fingerprint_and_export_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            asset = root/'tokenizer.json'
            asset.write_bytes(b'first')
            expected = tokenizer_fingerprint(root)
            asset.write_bytes(b'second')
            actual = tokenizer_fingerprint(root)
            inventory = tokenizer_inventory(root)
            self.assertEqual(inventory, {'tokenizer.json': hashlib.sha256(b'second').hexdigest()})
            self.assertNotEqual(expected, actual)
            with (patch('scripts.ft1r_data_report.is_real_tokenizer', return_value=True),
                  patch('scripts.ft1r_data_report.core.end_token'),
                  patch.object(ft1r_data, 'generate_training',
                               return_value=({}, {}, dict(passed=True, quote_gate=dict(passed=True)))),
                  patch.object(ft1r_data, 'quote_changes', return_value={}),
                  patch.object(ft1r_data, 'probes', return_value=[]),
                  patch.object(ft1r_data, 'fit', return_value={})):
                for index, supplied in enumerate((None, expected)):
                    report = report_for(object(), root/f'report-{index}.json', root/'export',
                                        tokenizer_sha256=actual, expected_tokenizer_sha256=supplied,
                                        tokenizer_file_sha256=inventory)
                    self.assertTrue(report['tokenizer_verified'])
                    self.assertEqual(report['tokenizer_sha256'], actual)
                    self.assertEqual(report['tokenizer_file_sha256'], inventory)
                    self.assertIn('independent source', report['tokenizer_export_requirement'])
                    self.assertFalse(report['passed'])
                    self.assertFalse((root/'export').exists())
