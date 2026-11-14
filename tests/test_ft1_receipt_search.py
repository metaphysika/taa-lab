"""FT1 receipt search on Kaggle input mounts: synthetic folders only, no Kaggle or network."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from exploratory.ft1 import mounts, plan

SLUG = 'ft1-qualification-approval-' + 'a' * 12


def touch(root, *parts):
    path = Path(root).joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"approved": true}')
    return path


def repo_noise(root):
    """The repo dataset carries other receipt.json files under studies/."""
    for n in range(11):
        touch(root, 'taa-k2-repo-' + 'b' * 12, 'studies', 'study-' + str(n), 'receipt.json')


class ReceiptSearchTests(unittest.TestCase):
    def search(self, root):
        lines = []
        try:
            return mounts.find_receipt(root, SLUG, show=lines.append), lines
        except ValueError as error:
            return error, lines

    def test_finds_the_one_receipt_at_either_kaggle_layout(self):
        for layout in ((SLUG,), ('datasets', 'metaphysika', SLUG)):
            with self.subTest(layout=layout), tempfile.TemporaryDirectory() as td:
                repo_noise(td)
                expected = touch(td, *layout, 'receipt.json')
                found, lines = self.search(td)
                self.assertEqual(found, expected)
                self.assertIn('using receipt: ' + str(expected), lines)

    def test_repo_receipts_alone_are_not_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            repo_noise(td)
            error, lines = self.search(td)
            self.assertIsInstance(error, ValueError)
            self.assertIn('no approval receipt', str(error))
            self.assertTrue(any(line.startswith('top-level') for line in lines))
            self.assertTrue(any('studies' in line for line in lines))  # every candidate seen is printed

    def test_two_matching_receipts_stop(self):
        with tempfile.TemporaryDirectory() as td:
            first = touch(td, SLUG, 'receipt.json')
            second = touch(td, 'datasets', 'metaphysika', SLUG, 'receipt.json')
            error, _ = self.search(td)
            self.assertIsInstance(error, ValueError)
            self.assertIn('2 approval receipt', str(error))
            self.assertIn(str(first), str(error)); self.assertIn(str(second), str(error))

    def test_slug_must_be_a_whole_folder_name(self):
        with tempfile.TemporaryDirectory() as td:
            touch(td, SLUG + '-old', 'receipt.json')
            touch(td, 'x' + SLUG, 'receipt.json')
            error, _ = self.search(td)
            self.assertIsInstance(error, ValueError)

    def test_missing_input_folder_stops(self):
        with tempfile.TemporaryDirectory() as td:
            error, _ = self.search(Path(td) / 'absent')
            self.assertIsInstance(error, ValueError)

    def test_receipt_slug(self):
        self.assertEqual(mounts.receipt_slug('metaphysika/' + SLUG), SLUG)
        for bad in ('noslash', 'a/b/c', '/slug', 'owner/'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                mounts.receipt_slug(bad)


class StagedNotebookTests(unittest.TestCase):
    """Both stagers' notebooks search for the receipt and no longer build a fixed path."""

    def check(self, source, cfg):
        self.assertNotIn('receipt_path', source)
        self.assertNotIn('/kaggle/input/datasets/', source)
        self.assertIn('from exploratory.ft1.mounts import find_receipt', source)
        self.assertIn('find_receipt("/kaggle/input", CONFIG["receipt_slug"])', source)
        self.assertNotIn('receipt_path', cfg)
        compile(source, 'notebook', 'exec')

    def kaggle_stage(self, td):
        from exploratory.ft1 import kaggle
        dataset = Path(td) / 'data'; dataset.mkdir()
        (dataset / 'manifest.json').write_text(json.dumps(dict(sha256={'arm-3.jsonl': 'c' * 64, 'acquisition-shared.json': 'e' * 64})))
        with patch.object(kaggle, 'verify_data', return_value='a' * 64), \
             patch.object(kaggle, 'source_inventory', return_value={}):
            cfg = kaggle.stage(Path(td) / 'stage', '3', plan.SEEDS[0], 'b' * 40, dataset, qualification=True,
                               model_source='google/gemma-3/transformers/gemma-3-12b-it/1',
                               repo_dataset='fixture/repo', data_dataset='fixture/data', owner='fixture',
                               receipt_dataset='metaphysika/' + SLUG)
        notebook = json.loads((Path(td) / 'stage' / 'ft1_plan.ipynb').read_text())
        return cfg, ''.join(notebook['cells'][0]['source'])

    def preparation_stage(self, td):
        from exploratory.ft1 import kaggle, preparation
        with patch.object(kaggle, 'source_inventory', return_value={}):
            cfg = preparation.stage(Path(td) / 'stage', 'b' * 40, 'fixture', 'fixture/repo', 'metaphysika/' + SLUG)
        notebook = json.loads((Path(td) / 'stage' / 'ft1_data_plan.ipynb').read_text())
        return cfg, ''.join(notebook['cells'][0]['source'])

    def test_both_stagers_bind_slug_and_search(self):
        for stager in (self.kaggle_stage, self.preparation_stage):
            with self.subTest(stager=stager.__name__), tempfile.TemporaryDirectory() as td:
                cfg, source = stager(td)
                self.assertEqual(cfg['receipt_dataset'], 'metaphysika/' + SLUG)
                self.assertEqual(cfg['receipt_slug'], SLUG)
                self.check(source, cfg)


if __name__ == '__main__':
    unittest.main()
