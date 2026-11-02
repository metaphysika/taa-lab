import ast
import subprocess
import sys
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from exploratory.audit_tool.step4 import transport

from exploratory.audit_tool.modal_adapter import CAP, IDLE, TIMEOUT, launch_guard, mock, sha, verify_checkpoint


class AdapterTests(unittest.TestCase):
    def test_mock_and_turn_limit(self):
        self.assertEqual(json.loads(mock().generate('system', [], 1))['tool'], None)
        with self.assertRaises(ValueError):
            mock().generate('', [], 13)

    def test_live_transport_seed_schedule(self):
        seeds = {}
        params = SimpleNamespace(clone=lambda: SimpleNamespace())
        engine = SimpleNamespace(get_default_sampling_params=lambda: params)
        runtime = SimpleNamespace(prompt_ids=lambda *args: [1])
        def generate(prompts, sampling, **kwargs):
            captured.append(sampling.seed)
            return [SimpleNamespace(outputs=[SimpleNamespace(text='{"tool": null, "args": {}}')])]
        engine.generate = generate
        with tempfile.TemporaryDirectory() as tmp, patch.dict('sys.modules', {
                'vllm.lora.request': SimpleNamespace(LoRARequest=lambda *args: None)}):
            for label, arms in [('A', ('neutral', 'contrary')), ('B', ('neutral', 'neutral'))]:
                for pass_id, arm in enumerate(arms):
                    captured = []
                    for case_index in range(33):
                        adapter = transport(engine, None, runtime, 'unused', arm, label,
                                            pass_id, str(case_index), case_index, Path(tmp), lambda: None)
                        for turn in range(1, 13):
                            adapter.generate('system', [], turn)
                    seeds[label, pass_id] = captured
            native = [json.loads(line) for line in (Path(tmp)/'native.jsonl').read_text().splitlines()]
        self.assertEqual(seeds['A', 0], seeds['A', 1])
        self.assertEqual(len(set(seeds['B', 0] + seeds['B', 1])), 792)
        self.assertEqual(seeds['B', 0], list(range(248017, 248413)))
        self.assertEqual(seeds['B', 1], list(range(248413, 248809)))
        self.assertEqual([row['seed'] for row in native],
                         seeds['A', 0] + seeds['A', 1] + seeds['B', 0] + seeds['B', 1])

    def test_launch_barriers(self):
        for confirm, env in [(False, {}), (True, {'CI': 'true'}), (True, {'TAA_TEST': '1'})]:
            with self.assertRaises(ValueError):
                launch_guard(confirm, env)
        self.assertEqual(TIMEOUT, 21600)
        self.assertEqual(CAP, math.ceil((TIMEOUT + IDLE + 120) / 3600 * 3.20 + .40))
        self.assertEqual(launch_guard(True, {}), 20)
        self.assertLess(CAP, 30)

    def test_image_matches_study_d(self):
        root = Path(__file__).resolve().parents[2]
        def settings(path):
            tree = ast.parse(path.read_text())
            calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                     and isinstance(n.func, ast.Attribute)]
            pins = next(tuple(ast.literal_eval(a) for a in n.args)
                        for n in calls if n.func.attr == 'pip_install')
            env = next(ast.literal_eval(n.args[0]) for n in calls if n.func.attr == 'env')
            python = next(ast.literal_eval(n.keywords[0].value) for n in calls
                          if n.func.attr == 'debian_slim')
            return python, pins, env
        self.assertEqual(settings(root/'exploratory/audit_tool/step4.py'),
                         settings(root/'scripts/study_d_gemma_stages_app_v02428.py'))

    def test_archive_policy_after_frozen_bundle(self):
        from exploratory.audit_tool import audit
        with audit.snapshot() as (repository, _):
            code = """
import json
from pathlib import Path
from exploratory.audit_tool import audit
repository = Path.cwd()
manifest = json.loads((repository/'studies/formation-study-d-analysis-v02430/inputs.json').read_text())
runtime = audit.module(repository/'scripts/study_d_gemma_runtime_v02416.py', 'step4_runtime')
runtime.ASSETS = repository/manifest['assets']
runtime.install_frozen_bundle()
policy = audit.module(repository/'formation/study_d_gemma_stages_v02428.py', 'step4_policy')
assert isinstance(policy.ENGINE, dict) and policy.ENGINE
"""
            subprocess.run([sys.executable, '-c', code], cwd=repository, check=True)

    def test_checkpoint_directory_symlinks(self):
        for level in ('root', 'science', 'arm', 'final'):
            with self.subTest(level=level), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                root = base/'mount'
                folder = root/'science'/'neutral'/'final'
                folder.mkdir(parents=True)
                file = folder/'adapter.bin'
                file.write_bytes(b'fixture')
                files = {'adapter.bin': dict(sha256=sha(file), bytes=7)}
                index = folder/'checkpoint-integrity.json'
                index.write_text(json.dumps(dict(arm='neutral', complete=True,
                    scientific_checkpoint=True, sha256={'adapter.bin': sha(file)})))
                plan = dict(checkpoints=[dict(arm='neutral', path='science/neutral/final',
                    files=files, checkpoint_index_sha256=sha(index))])
                target = dict(root=root, science=root/'science',
                              arm=root/'science'/'neutral', final=folder)[level]
                moved = base/'real'
                target.rename(moved)
                try:
                    target.symlink_to(moved, target_is_directory=True)
                except OSError as exc:
                    self.skipTest('directory symlinks unavailable: '+str(exc))
                if level == 'root':
                    self.assertEqual(verify_checkpoint(root, 'neutral', plan), folder)
                else:
                    with self.assertRaisesRegex(ValueError, 'missing/symlink'):
                        verify_checkpoint(root, 'neutral', plan)

    def test_missing_mount(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = dict(checkpoints=[dict(arm='neutral', path='science/neutral/final')])
            with self.assertRaisesRegex(ValueError, 'missing checkpoint mount'):
                verify_checkpoint(Path(tmp)/'absent', 'neutral', plan)

    def test_checkpoint_corruption(self):
        for arm in ('neutral', 'contrary', 'virtue'):
            with self.subTest(arm=arm), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)/'science'/arm/'final'
                folder.mkdir(parents=True)
                files = {}
                for name in ('README.md', 'adapter_config.json', 'adapter_model.safetensors'):
                    path = folder/name
                    path.write_bytes(b'fixture')
                    files[name] = dict(sha256=sha(path), bytes=7)
                index = folder/'checkpoint-integrity.json'
                index.write_text(json.dumps(dict(arm=arm, complete=True, scientific_checkpoint=True,
                                                sha256={n: v['sha256'] for n, v in files.items()})))
                plan = dict(checkpoints=[dict(arm=arm, path='science/'+arm+'/final',
                            files=files, checkpoint_index_sha256=sha(index))])
                self.assertEqual(verify_checkpoint(tmp, arm, plan), folder)
                (folder/'adapter_model.safetensors').write_bytes(b'corrupt')
                with self.assertRaises(ValueError):
                    verify_checkpoint(tmp, arm, plan)
                (folder/'adapter_model.safetensors').write_bytes(b'fixture')
                index.write_text('{}')
                with self.assertRaises(ValueError):
                    verify_checkpoint(tmp, arm, plan)


if __name__ == '__main__':
    unittest.main()
