"""Offline remainder and launch-local verification regression tests."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from exploratory.step4_harness import remainder as r, guard as g, modal_backend as b
from exploratory.step4_harness.runner import plan


class RemainderTests(unittest.TestCase):
    def test_roster_and_binding(self):
        cells = plan('development_remainder')
        self.assertEqual(len(cells), 10)
        self.assertFalse({r.identity(c) for c in cells} & {r.identity(c) for c in r.source_rows()})
        bound = g.binding('a'*40, 'development_remainder')
        self.assertEqual(bound['remainder_cells'], cells)
        self.assertEqual(bound['source_run_id'], r.SOURCE_RUN)
        receipt = dict(bound, archive_sha256='x', inventory_sha256='y', dollar_cap=4,
                       backend_settings=b.settings(4), approved_by='Chris Lahn', approval_id='new')
        b.claim_key(receipt)
        original = b.execution_fingerprint(receipt)
        self.assertNotEqual(original, b.execution_fingerprint(dict(receipt, source_run_id='changed')))

    def test_changed_evidence_and_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'events.jsonl'
            path.write_bytes(r.SOURCE.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                r.remaining(path)
        with patch.object(r, 'source_rows', return_value=r.source_rows()+[r.remaining()[0]]):
            with self.assertRaises(ValueError):
                r.remaining()

    def test_combine(self):
        cells = r.remaining()
        rows = r.combine(cells, 'new-launch')
        self.assertEqual(len(rows), 32)
        self.assertEqual(len({r.identity(c) for c in rows}), 32)
        self.assertEqual(sum(c['launch_id'] == r.SOURCE_RUN for c in rows), 22)
        self.assertEqual(sum(c['launch_id'] == 'new-launch' for c in rows), 10)
        self.assertEqual(sum(c['terminal_status'] == 'missing' for c in r.combine([], 'new')), 10)
        for bad in (cells+cells[:1], r.source_rows()[:1], plan('held_out')[:1]):
            with self.assertRaises(ValueError):
                r.combine(bad, 'new')

    def test_incomplete_remainder_reports_unknown(self):
        from exploratory.step4_harness import analysis
        rows = r.combine([], 'remainder-test')
        report = analysis.report(rows)
        missing = {r.identity(c) for c in r.remaining()}
        for unit in report['units']:
            if r.identity(unit) in missing:
                self.assertEqual(unit['metrics']['primary']['unknown'], 1)
                self.assertEqual(unit['metrics']['protocol']['unknown'], 1)
        analysis.analyze(rows)

    def test_retained_evidence_matches_manifest_in_archive(self):
        import io, subprocess, tarfile
        folder = r.SOURCE.parent
        repo = r.ROOT.parents[1]
        rel = folder.relative_to(repo).as_posix()
        try:
            data = subprocess.check_output(['git', 'archive', 'HEAD', rel], cwd=repo)
        except (OSError, subprocess.CalledProcessError):
            self.skipTest('git archive unavailable (not a git checkout)')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            files = {m.name.rsplit('/', 1)[-1]: tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
        manifest = files['MANIFEST.sha256'].decode().splitlines()
        self.assertEqual(len(manifest), 6)
        for line in manifest:
            digest, name = line.split(' *', 1)
            self.assertEqual(hashlib.sha256(files[name]).hexdigest(), digest, name)

    def test_single_full_check_and_inventory_bytes(self):
        # Reference reproduces the old per-arm logic with independently checked adapters.
        def old_inventory(cache, adapters):
            pinned = json.loads(g.PLAN.read_bytes())
            result = {}
            for arm in ('base', 'neutral', 'contrary', 'virtue'):
                entry = dict(model=g.MODEL, revision=g.REVISION, available=False)
                if arm != 'base':
                    entry['adapter'] = next(c.copy() for c in pinned['checkpoints'] if c['arm'] == arm)
                try:
                    g.verify_weights(cache)
                    if arm != 'base':
                        g.verify_checkpoint(adapters, arm)
                    entry['available'] = True
                except (ValueError, OSError, KeyError) as exc:
                    entry['blocked_reason'] = str(exc)
                result[arm] = entry
            return result
        for failure in (None, ValueError('bad roster')):
            with patch.object(g, 'verify_weights', side_effect=failure) as weights, patch.object(
                    g, 'verify_checkpoint', side_effect=lambda path, arm: (_ for _ in ()).throw(ValueError('missing adapter')) if arm == 'contrary' else None) as adapters:
                legacy = old_inventory('cache', 'adapters')
                legacy['virtue'] = old_inventory('cache', 'virtue')['virtue']
                weights.reset_mock()
                shared = g.weight_verification('cache')
                actual = g.inventory('cache', 'adapters', weights_result=shared)
                actual['virtue'] = g.inventory('cache', 'virtue', weights_result=shared)['virtue']
                self.assertEqual(weights.call_count, 1)
                self.assertEqual(json.dumps(actual), json.dumps(legacy))
                self.assertEqual(g.inventory_hash(actual), g.inventory_hash(legacy))

    def test_execute_shares_verification(self):
        # Stop at binding, after both actual inventory calls, before runtime imports.
        class Finished(Exception):
            pass
        with patch.object(b, 'weight_verification', wraps=g.weight_verification), patch.object(
                g, 'verify_weights') as weights, patch.object(g, 'verify_checkpoint'), patch.object(
                b, 'binding', side_effect=Finished):
            with self.assertRaises(Finished):
                b.execute({'block': 'development'}, 'a'*40, 'new', lambda e: None)
            self.assertEqual(weights.call_count, 1)

    def test_remainder_execution_and_single_claim(self):
        checkpoints = {arm: {'available': True} for arm in ('base', 'neutral')}
        expected = g.binding('a'*40, 'development_remainder', checkpoints)
        receipt = dict(expected, approved_by='Chris Lahn', dollar_cap=4)
        guard = g.LaunchGuard(receipt, expected, checkpoints, lambda rows: None, owner_approved=True)
        from exploratory.step4_harness.runner import run_block
        retained = []
        rows = run_block('development_remainder', checkpoints, guard,
                         lambda *args: '{"tool":null,"args":{}}', retained.append, 0,
                         execution_verifier=lambda commit: None)
        self.assertEqual([r.identity(c) for c in rows], [r.identity(c) for c in r.remaining()])
        self.assertEqual(rows, retained)
        with self.assertRaises(ValueError):
            run_block('development_remainder', checkpoints, guard, None, None, 0)
