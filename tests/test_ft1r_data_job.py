"""Offline checks of the FT1-R Kaggle job's execution boundaries."""
import ast
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from exploratory.ft1 import data_diagnostics, ft1r_data
from exploratory.k2_kaggle import core
from scripts import ft1r_data_job as job, ft1r_data_report, stage_ft1r_data as staging


class DataJobTests(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.root = Path(work.name)
        self.output = self.root / 'output'
        self.source = job.json_bytes(dict(repo_commit='a'*40, files={}))
        self.binding = dict(repo_commit='a'*40, phase=job.PHASE, source_sha256=job.sha256(self.source),
                            receipt_dataset='owner/receipt', source_dataset='owner/source')
        self.receipt = dict(approved=True, phase=job.PHASE, repo_commit='a'*40,
                            source_sha256=self.binding['source_sha256'])

    def mount(self, slug, name, raw):
        folder = self.root / 'datasets' / 'owner' / slug
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(raw)

    def test_receipt_refusals(self):
        with self.assertRaisesRegex(ValueError, 'missing.*receipt.json'):
            job.run(self.binding, self.root, self.output)
        for wrong in (dict(repo_commit='b'*40), dict(phase='data'), dict(approved=False),
                      dict(source_sha256='f'*64)):
            with self.subTest(wrong=wrong):
                self.mount('receipt', 'receipt.json', job.json_bytes(self.receipt | wrong))
                with self.assertRaisesRegex(ValueError, 'approval receipt required'):
                    job.run(self.binding, self.root, self.output)
                self.assertFalse(self.output.exists())

    def test_source_hash_and_commit_refusals(self):
        wrong_commit = job.json_bytes(dict(repo_commit='b'*40, files={}))
        self.mount('source', job.SOURCE_FILE, wrong_commit)
        self.mount('receipt', 'receipt.json', job.json_bytes(self.receipt))
        with self.assertRaisesRegex(ValueError, 'source artifact SHA-256 mismatch'):
            job.run(self.binding, self.root, self.output)
        digest = job.sha256(wrong_commit)
        self.mount('receipt', 'receipt.json', job.json_bytes(self.receipt | dict(source_sha256=digest)))
        with self.assertRaisesRegex(ValueError, 'source commit mismatch'):
            job.run(self.binding | dict(source_sha256=digest), self.root, self.output)
        self.assertFalse(self.output.exists())

    def test_runtime_mismatch_stops_before_model_mount(self):
        with patch.object(data_diagnostics, 'runtime_versions', return_value={}):
            with self.assertRaisesRegex(ValueError, 'runtime version mismatch'):
                job.measure(self.root, self.root / 'tokenizer', self.output)
        self.assertFalse((self.root / 'tokenizer').exists())

    def test_failed_q3_publishes_report_and_no_dataset(self):
        self.mount('receipt', 'receipt.json', job.json_bytes(self.receipt))
        self.mount('source', job.SOURCE_FILE, self.source)
        self.assertEqual(core.digest(job.TOKENIZER_FILES), job.TOKENIZER_SHA256)

        def measure(_mount, _tokenizer_dir, output):
            return ft1r_data_report.report_for(
                object(), output / 'report.json', output / 'dataset',
                tokenizer_sha256=job.TOKENIZER_SHA256, expected_tokenizer_sha256=job.TOKENIZER_SHA256,
                tokenizer_file_sha256=job.TOKENIZER_FILES,
            )

        with (patch.object(job, 'sys', SimpleNamespace(modules={}, path=[])),
              patch.object(job, 'measure', side_effect=measure),
              patch.object(ft1r_data_report, 'is_real_tokenizer', return_value=True),
              patch.object(core, 'end_token'),
              patch.object(ft1r_data, 'generate_training',
                           return_value=({}, {}, dict(passed=True, quote_gate=dict(passed=False)))),
              patch.object(ft1r_data, 'probes', return_value=[]),
              patch.object(ft1r_data, 'fit', return_value={}),
              patch.object(ft1r_data, 'quote_changes', return_value={})):
            report = job.run(self.binding, self.root, self.output)
        self.assertFalse(report['passed'])
        self.assertIn('quoted-line minimums', report['refusal'])
        self.assertEqual({p.name for p in self.output.iterdir()}, {'report.json', 'output-manifest.json'})
        manifest = json.loads((self.output / 'output-manifest.json').read_bytes())
        self.assertEqual(manifest['sha256'], {'report.json': job.sha256((self.output / 'report.json').read_bytes())})

    def test_source_artifact_excludes_sealed_and_imports_in_isolation(self):
        commit = staging.git('rev-parse', 'HEAD').strip()
        raw = staging.source_artifact(commit)
        files = json.loads(raw)['files']
        self.assertIn('exploratory/step4_harness/crossing.py', files)
        for name, content in files.items():
            self.assertNotEqual(Path(name).name, 'sealed.py')
            for node in ast.walk(ast.parse(content.encode('utf-8'), filename=name)):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    imports = [alias.name for alias in node.names]
                    if isinstance(node, ast.ImportFrom):
                        imports.append(node.module or '')
                    self.assertFalse(any('sealed' in target.split('.') for target in imports), name)
        job.unpack_source(dict(repo_commit=commit, source_sha256=job.sha256(raw)), raw, self.root)
        code = """import importlib.abc
import sys
class NoSealed(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[-1] == 'sealed':
            raise AssertionError(fullname)
sys.meta_path.insert(0, NoSealed())
sys.path.insert(0, sys.argv[1])
from scripts import ft1r_data_report
assert ft1r_data_report.__file__.startswith(sys.argv[1])
"""
        subprocess.run([sys.executable, '-I', '-c', code, str(self.root)], cwd=self.root, check=True)

    def test_stage_refuses_dirty_and_wrong_commit(self):
        commit = 'a'*40
        with patch.object(staging, 'git', return_value=commit):
            with self.assertRaisesRegex(ValueError, 'full requested commit'):
                staging.stage('b'*40, 'owner')
        with patch.object(staging, 'git', side_effect=[commit, '?? file']):
            with self.assertRaisesRegex(ValueError, 'checkout must be clean'):
                staging.stage(commit, 'owner')
