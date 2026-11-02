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

    def test_reservation_order(self):
        events = []
        app, worker = MagicMock(), Mock()
        app.app_id = 'ap-test'
        app.run.return_value.__enter__.side_effect = lambda: events.append('entered')
        worker.spawn.side_effect = lambda commit: (events.append('spawn') or SimpleNamespace(object_id='fc-test'))
        with tempfile.TemporaryDirectory() as tmp:
            step4.submit(app, worker, 'commit', 4, Path(tmp)/'receipt',
                         before_spawn=lambda: events.append('reserve'))
            self.assertEqual(events, ['entered', 'reserve', 'spawn'])
            app.run.return_value.__enter__.side_effect = RuntimeError('build failed')
            reserve = Mock()
            with self.assertRaises(RuntimeError):
                step4.submit(app, worker, 'commit', 4, Path(tmp)/'failure', before_spawn=reserve)
            reserve.assert_not_called()

    def test_launch_setup_failure_does_not_reserve(self):
        for stage in ('image', 'volume', 'app'):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as tmp:
                modal = MagicMock()
                modal.App.return_value.function.side_effect = lambda **kw: lambda fn: fn
                if stage == 'image':
                    modal.Image.debian_slim.side_effect = RuntimeError('build failed')
                elif stage == 'volume':
                    modal.Volume.from_name.side_effect = RuntimeError('missing weights')
                else:
                    modal.App.return_value.run.return_value.__enter__.side_effect = RuntimeError('app failed')
                with patch.dict('sys.modules', {'modal': modal}), patch.object(step4.subprocess, 'run'), patch.object(step4.subprocess, 'check_output', return_value='commit'), patch.object(step4, 'reserve_attempt') as reserve:
                    with self.assertRaises(RuntimeError):
                        step4.launch(Path(tmp)/'receipt', 4)
                    reserve.assert_not_called()
                    modal.Dict.from_name.assert_not_called()

    def test_remote_status_failures(self):
        class Cancellation(BaseException):
            pass
        class RemoteTimeout(TimeoutError):
            pass
        for error in (TimeoutError('worker socket timed out'), RemoteTimeout(),
                      Cancellation('cancelled'), SystemExit(2), KeyboardInterrupt()):
            with self.subTest(error=type(error)), tempfile.TemporaryDirectory() as tmp:
                call = Mock()
                call.get.side_effect = error
                modal = SimpleNamespace(FunctionCall=SimpleNamespace(from_id=Mock(return_value=call)))
                output = Path(tmp)/'status'
                self.assertEqual(poll('fc', output, modal), 1)
                status = json.loads(output.read_text())
                self.assertEqual(status['status'], 'failed')
                self.assertEqual(status['type'], type(error).__name__)

    def test_cache_roster_and_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            snapshot = cache/'hub'/('models--'+step4.MODEL.replace('/', '--'))/'snapshots'/step4.REVISION
            snapshot.mkdir(parents=True)
            file = snapshot/'config.json'
            file.write_text('{}')
            step4.cache_manifest(cache, Mock(return_value=str(snapshot)))
            file.unlink()
            with self.assertRaises(ValueError):
                step4.verify_weights(cache)
            file.write_text('{}')
            extra = snapshot/'extra'
            extra.write_text('extra')
            with self.assertRaises(ValueError):
                step4.verify_weights(cache)
            extra.unlink()
            blob = snapshot.parents[1]/'blobs'/'digest'
            blob.parent.mkdir()
            blob.write_text('{}')
            file.unlink()
            try:
                file.symlink_to(Path('../../blobs/digest'))
            except OSError as exc:
                self.skipTest('Windows symlink privilege unavailable: '+str(exc))
            step4.verify_weights(cache)
            report = step4.check_cache(cache, Mock(return_value=str(snapshot)), Mock(), Mock())
            self.assertEqual(report['errors'], [])
            self.assertEqual(report['symlinks'][0]['target'], str(Path('../../blobs/digest')))
            self.assertTrue(report['symlinks'][0]['exists'])

    def test_cpu_offline_lookups_and_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            snapshot = cache/'hub'/('models--'+step4.MODEL.replace('/', '--'))/'snapshots'/step4.REVISION
            snapshot.mkdir(parents=True)
            (snapshot/'config.json').write_text('{}')
            step4.cache_manifest(cache, Mock(return_value=str(snapshot)))
            download, config = Mock(return_value=str(snapshot)), Mock()
            def tokenizer(*args, **kwargs):
                with (cache/'hub'/'lookup.lock').open('w') as stream:
                    stream.write('mock lock')
                raise FileNotFoundError('tokenizer fixture missing')
            report = step4.check_cache(cache, download, config, tokenizer)
            download.assert_called_once_with(step4.MODEL, revision=step4.REVISION,
                cache_dir=str(cache/'hub'), local_files_only=True)
            config.assert_called_once_with(step4.MODEL, revision=step4.REVISION,
                cache_dir=str(cache/'hub'), local_files_only=True, trust_remote_code=False)
            self.assertEqual(report['errors'][0]['lookup'], 'AutoTokenizer')
            self.assertIn('missing', report['errors'][0]['message'])
            self.assertTrue(any(p.endswith('lookup.lock') for p in report['write_attempts']))

    def test_worker_folder_and_cpu_mount_definition(self):
        import ast
        tree = ast.parse(Path(step4.__file__).read_text())
        launch = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'launch')
        worker = next(n for n in ast.walk(launch) if isinstance(n, ast.FunctionDef) and n.name == 'worker')
        call = next(n for n in ast.walk(worker) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'batch')
        folder = ast.Expression(call.args[1])
        self.assertEqual(eval(compile(folder, '<worker-folder>', 'eval'),
            dict(Path=Path, source_commit='abc', attempt=7)), Path('/results/abc/attempt-7'))
        checker = next(n for n in ast.walk(launch) if isinstance(n, ast.FunctionDef) and n.name == 'check_cached_weights')
        kwargs = {k.arg: ast.unparse(k.value) for k in checker.decorator_list[0].keywords}
        self.assertEqual(kwargs['image'], 'offline_image')
        offline = next(n.value for n in ast.walk(launch) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'offline_image' for t in n.targets))
        self.assertEqual(ast.literal_eval(offline.args[0]), {'HF_HOME': '/weights', 'HF_HUB_OFFLINE': '1'})
        self.assertNotIn('gpu', kwargs)
        self.assertNotIn('secrets', kwargs)
        self.assertIn('weights.read_only()', kwargs['volumes'])
        # The reservation callback is wired only to the GPU submission.
        self.assertIn('before_spawn=(lambda: None) if prefetch or check_weights else reserve', ast.unparse(launch))

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
