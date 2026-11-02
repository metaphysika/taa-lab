import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, MagicMock, patch
from exploratory.audit_tool import step4
from scripts.step4_status import poll


class Ledger(dict):
    def put(self, key, value, skip_if_exists=False):
        if skip_if_exists and key in self:
            return False
        self[key] = value
        return True


class AttemptTests(unittest.TestCase):
    def test_ledger(self):
        ledger = Ledger({'entire-step4-cap': 20})
        step4.reserve_attempt(ledger, 4)
        self.assertEqual(ledger['entire-step4-cap'], 20)
        self.assertEqual(ledger['attempt-3']['actual_billed'], .60)
        self.assertEqual(ledger['attempt-4'], dict(reserved=20, actual_billed=None))
        for attempt in (4, 5):
            with self.assertRaises((ValueError, RuntimeError)):
                step4.reserve_attempt(ledger, attempt)
        ledger['attempt-4']['actual_billed'] = .5
        with self.assertRaises(ValueError):
            step4.reserve_attempt(ledger, 5)  # .6 + .5 + 20 exceeds 21
        with patch.object(step4, 'CUMULATIVE_CAP', 20):
            with self.assertRaises(ValueError):
                step4.reserve_attempt(Ledger({'entire-step4-cap': 20}), 4)
        with self.assertRaises(ValueError):
            step4.reserve_attempt(Ledger(), 4)
        with self.assertRaises(RuntimeError):
            step4.reserve_attempt(Ledger({'attempt-launch-lock': 4}), 5)

    def test_detach_receipt_and_status(self):
        app, worker = MagicMock(), Mock()
        app.app_id = 'ap-test'
        worker.spawn.return_value.object_id = 'fc-test'
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp)/'receipt.json'
            step4.submit(app, worker, 'commit', 4, receipt)
            app.run.assert_called_once_with(detach=True)
            worker.spawn.assert_called_once_with('commit')
            self.assertEqual(json.loads(receipt.read_text())['function_call_id'], 'fc-test')
            for effect, code in [(TimeoutError(), 2), (RuntimeError('cancelled'), 1), (None, 0)]:
                target = Path(tmp)/str(code)
                call = Mock()
                call.get.side_effect = effect
                call.get.return_value = None
                modal = SimpleNamespace(FunctionCall=SimpleNamespace(from_id=Mock(return_value=call)))
                self.assertEqual(poll('fc-test', target, modal), code)
                call.get.assert_called_once_with(timeout=0)
                self.assertEqual(target.exists(), code != 2)

    def test_weights_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            snapshot = cache/'hub'/('models--'+step4.MODEL.replace('/', '--'))/'snapshots'/step4.REVISION
            snapshot.mkdir(parents=True)
            (snapshot/'config.json').write_text('{}')
            download = Mock(return_value=str(snapshot))
            step4.cache_manifest(cache, download)
            download.assert_called_once_with(step4.MODEL, revision=step4.REVISION, cache_dir=str(cache/'hub'))
            step4.verify_weights(cache)
            (snapshot/'config.json').write_text('bad')
            with self.assertRaises(ValueError):
                step4.verify_weights(cache)

    def test_folder_refusal_and_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileExistsError):
                step4.batch(Path(tmp), Path(tmp))
        with patch('sys.stderr') as log:
            with self.assertRaises(SystemExit):
                step4.log_signal(step4.signal.SIGTERM, None)
            self.assertIn('SIGTERM', str(log.write.call_args_list))


if __name__ == '__main__':
    unittest.main()
