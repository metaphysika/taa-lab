"""Offline regressions for CI selection, entrypoints and exact fast-set coverage."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import yaml

from scripts import ci_scope, run_fast_checks

ROOT = Path(__file__).resolve().parents[1]
OLD = ('gateway', 'tests', 'formation-python39', 'experiment-a', 'q18', 'live-demo')


def workflow(name):
    return yaml.load((ROOT / '.github' / 'workflows' / (name + '.yml')).read_text(),
                     Loader=yaml.BaseLoader)


class ScopeTests(unittest.TestCase):
    def test_exploratory_and_existing_doc_ignores_skip_old_evidence(self):
        paths = ['exploratory/' + part + '/new.py'
                 for part in ('scripts', 'scenarios', 'notes', 'results')]
        paths += list(ci_scope.DOC_IGNORES[:-1]) + ['docs/drafts/outline.md']
        self.assertFalse(any(ci_scope.select_checks(paths).values()))

    def test_shared_modules_select_every_group(self):
        for path in ('taa/gates.py', 'agents/client.py', 'world/fake_world.py',
                     'scenarios/old.json', 'taa_gateway/act.py',
                     'taa_gateway_reference/refunds.py', 'conventional_gateway/policy.py',
                     'comparators/duty_oracle.py', 'evaluation/v020_outcomes.py',
                     'formation/scorer.py', 'scorer/new.py', 'gateway/new.py',
                     'some/new_scorer.py', 'requirements-gateway.txt', 'run.py',
                     '.github/workflows/gateway.yml', 'scripts/ci_scope.py'):
            with self.subTest(path=path):
                self.assertTrue(all(ci_scope.select_checks([path]).values()))

    def test_gateway_own_inputs(self):
        for path in ('scripts/check_gateway_all_arm_replay.py',
                     'scripts/check_conventional_kernel.py',
                     'scripts/run_tracegrant_comparator.py',
                     'tests/test_gateway_foundation.py', 'tests/test_cross_arm.py',
                     'tests/trace_support/bundle.py', 'live_demo/frozen/world.json',
                     'replay/retained.py',
                     'tests/expected_traces/v0.2.2/MANIFEST.sha256'):
            with self.subTest(path=path):
                self.assertEqual(ci_scope.select_checks([path]),
                                 dict(gateway=True, study_d=False, gemma=False))

    def test_study_d_inputs_include_manifests_retained_archives_and_runtime(self):
        for path in ('scripts/study_d_analysis_v02430.py',
                     'scripts/check_study_d_science_v02429.py',
                     'scripts/formation_study_d_gemma_base_v02413.py',
                     'studies/formation-study-d-analysis-v02430/inputs.json',
                     'results/gemma-v02425-pair-return-001.zip',
                     'tests/test_modal_serialization_v02420.py'):
            with self.subTest(path=path):
                self.assertEqual(ci_scope.select_checks([path]),
                                 dict(gateway=False, study_d=True, gemma=True))

    def test_unknown_paths_fail_closed_and_mixed_changes_select_union(self):
        self.assertTrue(all(ci_scope.select_checks(['new-package/unknown.py']).values()))
        self.assertTrue(all(ci_scope.select_checks(['docs/process/new-evidence.json']).values()))
        self.assertTrue(all(ci_scope.select_checks([
            'tests/test_gateway_foundation.py', 'results/changed.json',
            'exploratory/results/run.json']).values()))

    def test_local_experiments_use_fast_tier(self):
        self.assertFalse(any(ci_scope.select_checks([
            'experiment_a/host.py', 'experiment_b/audit.py', 'step3_v02444/run.py',
            'tests/test_experiment_b.py', 'live_demo/chat.py']).values()))

    def test_git_diff_keeps_deleted_and_renamed_paths_without_provider_limit(self):
        paths = ['exploratory/results/run-%d.json' % index for index in range(400)]
        paths += ['taa/deleted.py', 'studies/old-name.json', 'exploratory/new-name.json']
        with patch.object(subprocess, 'check_output',
                          return_value=('\0'.join(paths) + '\0').encode()) as command:
            self.assertEqual(ci_scope.changed_paths('a' * 40, 'b' * 40), paths)
        self.assertIn('--no-renames', command.call_args.args[0])
        self.assertTrue(all(ci_scope.select_checks(paths).values()))

    def test_bad_or_unavailable_diff_fails_instead_of_skipping(self):
        with self.assertRaises(ValueError):
            ci_scope.changed_paths('main', 'b' * 40)
        with patch.object(subprocess, 'check_output', side_effect=subprocess.CalledProcessError(1, 'git')):
            with self.assertRaises(subprocess.CalledProcessError):
                ci_scope.changed_paths('a' * 40, 'b' * 40)

    def test_non_pr_events_always_select_full_even_without_pr_payload(self):
        for event in ('push', 'schedule', 'workflow_dispatch'):
            with self.subTest(event=event), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / 'outputs'
                with patch.dict(os.environ, {'GITHUB_EVENT_NAME': event, 'GITHUB_OUTPUT': str(output)}, clear=True):
                    ci_scope.main()
                self.assertEqual(output.read_text().splitlines(),
                                 [name + '=true' for name in ci_scope.GROUPS])


class WorkflowTests(unittest.TestCase):
    def test_old_workflows_preserve_doc_ignores_and_ignore_exploratory_prs(self):
        for name in OLD:
            with self.subTest(name=name):
                events = workflow(name)['on']
                self.assertIn('workflow_call', events)
                self.assertNotIn('push', events)
                self.assertEqual(events['pull_request']['paths-ignore'],
                                 list(ci_scope.DOC_IGNORES) + ['exploratory/**'])

    def test_full_entrypoint_is_unfiltered_on_main_and_has_nightly_manual_triggers(self):
        full = workflow('full-suite')
        self.assertEqual(full['on']['push'], {'branches': ['main']})
        self.assertEqual(full['on']['schedule'], [{'cron': '0 8 * * *'}])
        self.assertIn('workflow_dispatch', full['on'])
        calls = {job['uses'] for job in full['jobs'].values() if 'uses' in job}
        expected = {'./.github/workflows/' + name + '.yml' for name in OLD}
        self.assertTrue(expected.issubset(calls))
        gate = full['jobs']['full-green']
        self.assertEqual(set(gate['needs']), set(full['jobs']) - {'full-green'})
        self.assertEqual(gate['if'], "always() && needs.nightly-changes.outputs.run == 'true'")
        self.assertIn('== "success"', gate['steps'][0]['run'])
        self.assertNotIn('secrets', json.dumps(full))

    def test_only_nightly_runs_can_skip_and_history_errors_run_full(self):
        full = workflow('full-suite')
        nightly = full['jobs']['nightly-changes']
        self.assertEqual(nightly['permissions'], {'actions': 'read'})
        script = nightly['steps'][0]['with']['script']
        self.assertIn("context.eventName === 'schedule'", script)
        self.assertIn("event: 'schedule', status: 'success'", script)
        self.assertIn('previous.head_sha !== context.sha', script)
        self.assertIn('let run = true', script)
        self.assertIn('catch (error)', script)
        for name, job in full['jobs'].items():
            if 'uses' in job:
                self.assertEqual(job['needs'], 'nightly-changes')
                self.assertEqual(job['if'], "needs.nightly-changes.outputs.run == 'true'")

    def test_full_discover_is_only_omitted_on_prs(self):
        steps = workflow('tests')['jobs']['test']['steps']
        discover = [step for step in steps if 'unittest discover tests' in step.get('run', '')]
        self.assertEqual(len(discover), 1)
        self.assertEqual(discover[0]['if'], "github.event_name != 'pull_request'")
        for name, job, group in (('tests', 'test', 'study_d'),
                                 ('tests', 'gemma-cpu-rehearsal', 'gemma'),
                                 ('gateway', 'reference-and-foundation', 'gateway')):
            self.assertEqual(workflow(name)['jobs'][job]['if'],
                             "github.event_name != 'pull_request' || needs.scope.outputs." + group + " == 'true'")

    def test_exploratory_smoke_retains_preservation_guard_and_network_isolation(self):
        smoke = workflow('exploratory')
        self.assertIn('exploratory/**', smoke['on']['pull_request']['paths'])
        steps = smoke['jobs']['smoke']['steps']
        commands = '\n'.join(step.get('run', '') for step in steps)
        self.assertIn('unshare --net', commands)
        self.assertIn('run_fast_checks.py --smoke', commands)
        self.assertIn('check_live_demo_preservation.py --policy-change-record', commands)
        self.assertIn('fetch-depth', steps[0]['with'])

    def test_fast_units_run_on_exploratory_as_well_as_shared_code_prs(self):
        fast = workflow('fast')
        self.assertNotIn('exploratory/**', fast['on']['pull_request']['paths-ignore'])
        self.assertNotIn('push', fast['on'])
        self.assertIn('tests.test_experiment_b', run_fast_checks.FAST)
        self.assertIn('tests.test_step3_v02444', run_fast_checks.FAST)
        self.assertTrue(set(run_fast_checks.SMOKE[:1]).issubset(run_fast_checks.FAST))
        for name in run_fast_checks.FAST + run_fast_checks.SMOKE:
            self.assertTrue((ROOT / ('/'.join(name.split('.')[:2]) + '.py')).is_file())

    def test_exploratory_syntax_preserves_arbitrary_result_and_note_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for folder in ('scripts', 'scenarios', 'notes', 'results'):
                (root / 'exploratory' / folder).mkdir(parents=True)
            for folder in ('notes', 'results'):
                (root / 'exploratory' / folder / 'retained.py').write_bytes(b'not valid python!')
            script = root / 'exploratory' / 'scripts' / 'smoke.py'
            script.write_text('answer = 42')
            with patch.object(run_fast_checks, 'ROOT', root):
                run_fast_checks.exploratory_syntax()
                script.write_text('not valid python!')
                with self.assertRaises(SyntaxError):
                    run_fast_checks.exploratory_syntax()

    def test_fast_runner_rejects_keys_file_without_reading_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(run_fast_checks, 'ROOT', Path(temporary)):
                (Path(temporary) / 'keys.env').touch()
                with patch.object(os.sys, 'argv', ['run_fast_checks.py']), self.assertRaises(SystemExit):
                    run_fast_checks.main()


if __name__ == '__main__':
    unittest.main()
