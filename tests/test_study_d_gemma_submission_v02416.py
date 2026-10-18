"""Submission failure boundaries, without a live Modal client or GPU."""
import ast
import importlib.util
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
from formation import study_d_gemma_base_v02416 as h

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('local_submission', ROOT/'scripts/study_d_gemma_submission_v02416.py')
submission = importlib.util.module_from_spec(spec)
spec.loader.exec_module(submission)


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.receipt = Path(self.directory.name)/'attempt.json'
        self.receipt.write_text('original once-only receipt\n')
        self.payload = dict(commit='a'*40, approval_receipt='offline fixture')
        self.messages = []
        self.calls = []

    def emit(self, message, **kwargs):
        record = json.loads(self.receipt.with_suffix('.submission.json').read_text())
        self.assertEqual(record['status'], 'SUBMITTED')
        self.assertEqual(record['call_id'], 'fc-offline')
        self.assertTrue(kwargs['flush'])
        self.messages.append(message)

    def controller(self, result=None, error=None):
        outer = self
        class Controller:
            def spawn(self, payload):
                outer.calls.append('spawn')
                claim=json.loads(outer.receipt.with_suffix('.submission.json').read_text())
                outer.assertEqual(claim['status'], 'SUBMISSION_IN_PROGRESS')
                if error: raise error
                return result
            def remote(self, *args):
                raise AssertionError('blocking remote() forbidden in client')
        return Controller()

    def test_acknowledgement_is_durable_before_safe_line_without_result_wait(self):
        class Call:
            object_id='fc-offline'
            def get(self,*args,**kwargs):raise AssertionError('client must never wait')
        r=submission.submit_controller(self.controller(Call()),self.payload,'ap-offline',self.receipt,h,self.emit)
        self.assertEqual(self.calls,['spawn'])
        self.assertIn('SUBMITTED — safe to close laptop',self.messages[0])
        self.assertIn('ap-offline',self.messages[0])
        self.assertIn('fc-offline',self.messages[0])
        self.assertFalse(r['result_waited_for'])
        self.assertEqual(self.receipt.read_text(),'original once-only receipt\n')

    def test_lost_acknowledgement_is_unknown_and_never_retried(self):
        controller=self.controller(error=ConnectionError('offline connection lost'))
        with self.assertRaises(ConnectionError):
            submission.submit_controller(controller,self.payload,'ap-offline',self.receipt,h,self.emit)
        r=json.loads(self.receipt.with_suffix('.submission.json').read_text())
        self.assertEqual(r['status'],'SUBMISSION_UNCONFIRMED_NO_RELAUNCH')
        self.assertIn('ConnectionError',r['traceback'])
        with self.assertRaises(FileExistsError):
            submission.submit_controller(controller,self.payload,'ap-offline',self.receipt,h,self.emit)
        self.assertEqual(self.calls,['spawn'])
        self.assertEqual(self.messages,[])

    def test_missing_call_id_never_prints_safe_line(self):
        with self.assertRaises(RuntimeError):
            submission.submit_controller(self.controller(types.SimpleNamespace(object_id=None)),self.payload,
                                         'ap-offline',self.receipt,h,self.emit)
        self.assertEqual(self.calls,['spawn'])
        self.assertEqual(self.messages,[])

    def test_failed_receipt_write_after_acknowledgement_never_claims_safe(self):
        with patch.object(submission,'persist',side_effect=OSError('offline full disk')):
            with self.assertRaises(OSError):
                submission.submit_controller(self.controller(types.SimpleNamespace(object_id='fc-offline')),
                                             self.payload,'ap-offline',self.receipt,h,self.emit)
        self.assertEqual(self.calls,['spawn'])
        self.assertEqual(self.messages,[])
        self.assertTrue(self.receipt.with_suffix('.submission.json').exists())

    def test_unhydrated_app_is_refused_before_submission(self):
        with self.assertRaises(ValueError):
            submission.submit_controller(self.controller(),self.payload,None,self.receipt,h,self.emit)
        self.assertEqual(self.calls,[])

    def test_engine_science_and_kv_capture_unchanged_from_v02414(self):
        old=(ROOT/'scripts/study_d_gemma_runtime_v02414.py').read_text()
        new=(ROOT/'scripts/study_d_gemma_runtime_v02416.py').read_text()
        def engine_args(text):
            return ast.dump(next(n for n in ast.walk(ast.parse(text)) if isinstance(n,ast.Assign) and
                any(isinstance(t,ast.Name) and t.id=='args' for t in n.targets)))
        self.assertEqual(engine_args(old),engine_args(new))
        old_h=ast.parse((ROOT/'formation/study_d_gemma_base_v02414.py').read_text())
        new_h=ast.parse((ROOT/'formation/study_d_gemma_base_v02416.py').read_text())
        for name in ('kv_prediction','current_kv_preflight','redact','failure_record','save_failure','project'):
            self.assertEqual(ast.dump(next(n for n in old_h.body if isinstance(n,ast.FunctionDef) and n.name==name)),
                             ast.dump(next(n for n in new_h.body if isinstance(n,ast.FunctionDef) and n.name==name)))
        for name in ('plan.json','bundle.json','contrary-2000-train.jsonl','virtue-2000-train.jsonl','neutral-2000-train.jsonl'):
            self.assertEqual((ROOT/'studies/formation-study-d-gemma-base-v02414'/name).read_bytes(),
                             (ROOT/'studies/formation-study-d-gemma-base-v02416'/name).read_bytes())
