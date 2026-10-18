"""Actual pinned SDK serializer, without credentials, hydration or backend."""
import importlib.util
from pathlib import Path
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

@unittest.skipUnless(importlib.util.find_spec('modal') and sys.version_info[:2]==(3,12),
                     'dedicated offline Modal Python3.12 step')
class GemmaModalSerializationTests(unittest.TestCase):
    def test_base_controller_and_worker_serialize_without_live_hydration(self):
        import modal
        from modal._serialization import serialize
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
        import study_d_gemma_modal_app_v02416 as declarations
        with patch.object(modal.client._Client,'from_env',side_effect=AssertionError('no live client')):
            app,worker,controller,cpu_worker=declarations.define()
            self.assertEqual(len(app.registered_functions),3)
            for function in (worker,controller,cpu_worker):
                self.assertGreater(len(serialize(function._raw_f_)),100)

    def test_durable_once_marker_blocks_even_if_dict_entries_absent(self):
        import importlib.util
        import json
        import modal
        import tempfile
        from formation import study_d_gemma_base_v02416 as h
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
        import study_d_gemma_modal_app_v02416 as declarations
        app,worker,controller,cpu_worker=declarations.define()
        entries={};actions=[]
        class Ledger:
            def get(self,key):return entries.get(key)
            def contains(self,key):return key in entries
            def put(self,key,value,skip_if_exists=False):
                if key in entries and skip_if_exists:return False
                entries[key]=value;actions.append('claim');return True
        class Volume:
            def reload(self):pass
            def commit(self):actions.append('commit')
        class Call:
            def get(self):return dict(status='COMPLETE',training_authorized=False)
        class Worker:
            def spawn(self,payload):
                self_outer.assertTrue((target/'gemma-base-v02416-gpu-reservation.json').exists())
                self_outer.assertIn(h.STAGE_KEY,entries)
                actions.append('spawn');return Call()
        self_outer=self
        commit='a'*40
        payload=dict(commit=commit,approved=True,prior_usd=2.59,billing_attestation='owner verified',
            approval_receipt='Owner approved Gemma base-format gate v02416, commit '+commit,
            worker_function_id='fu-offline-fake')
        real_spec=importlib.util.spec_from_file_location
        def spec(name,path):
            result=real_spec(name,Path(__file__).resolve().parents[1]/'formation/study_d_gemma_base_v02416.py')
            execute=result.loader.exec_module
            def execute_frozen_clock(module):
                execute(module)
                module.check_window=lambda now=None:h.check_window(datetime(2026,10,19,tzinfo=timezone.utc))
                module.require_cpu_pass=lambda root,payload:dict(status='PASS')
                module.sha=lambda path:'offline-receipt-hash'
            result.loader.exec_module=execute_frozen_clock
            return result
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)
            real_path=Path
            def path(value):
                return target/str(value).removeprefix('/results/').removeprefix('/results') if str(value).startswith('/results') else real_path(value)
            with patch.object(modal.Dict,'from_name',return_value=Ledger()), \
                 patch.object(modal.Volume,'from_name',return_value=Volume()), \
                 patch.object(modal.Function,'from_id',return_value=Worker()), \
                 patch('importlib.util.spec_from_file_location',side_effect=spec), \
                 patch.object(declarations,'Path',side_effect=path):
                entries[h.CPU_CLOSED_KEY]=dict(status='PASS',commit=commit,receipt_sha256='offline-receipt-hash')
                self.assertEqual(controller._raw_f_(dict(payload))['status'],'COMPLETE')
                self.assertEqual(actions.count('spawn'),1)
                entries.clear()  # TTL simulation; restore CPU proof, GPU durable claim still blocks.
                entries[h.CPU_CLOSED_KEY]=dict(status='PASS',commit=commit,receipt_sha256='offline-receipt-hash')
                blocked=controller._raw_f_(dict(payload))
                self.assertIn('prior attempt',blocked['error_message'])
                self.assertIn('RuntimeError',blocked['traceback'])
                self.assertEqual(actions.count('spawn'),1)

    def test_missing_cpu_receipt_blocks_gpu_before_claim_or_spawn(self):
        import json
        import modal
        import tempfile
        from formation import study_d_gemma_base_v02416 as h
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
        import study_d_gemma_modal_app_v02416 as declarations
        app,worker,controller,cpu_worker=declarations.define()
        actions=[]
        class Ledger:
            def contains(self,key):return False
            def get(self,key):return None
            def put(self,*a,**k):actions.append('claim');return True
        class Volume:
            def reload(self):pass
            def commit(self):pass
        real_spec=importlib.util.spec_from_file_location
        def spec(name,path):
            result=real_spec(name,Path(__file__).resolve().parents[1]/'formation/study_d_gemma_base_v02416.py')
            execute=result.loader.exec_module
            def load(module):
                execute(module)
                module.check_window=lambda now=None:None
            result.loader.exec_module=load
            return result
        payload=dict(stage='gpu',commit='a'*40,approved=True,prior_usd=2.59,
            billing_attestation='unit',approval_receipt='Owner approved Gemma base-format gate v02416, commit '+'a'*40,
            asset_sha256='unit')
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory);real_path=Path
            def path(value):
                return target/str(value).removeprefix('/results/').removeprefix('/results') if str(value).startswith('/results') else real_path(value)
            with patch.object(modal.Dict,'from_name',return_value=Ledger()), \
                 patch.object(modal.Volume,'from_name',return_value=Volume()), \
                 patch.object(modal.Function,'from_id',side_effect=AssertionError('GPU handle must not be used')), \
                 patch('importlib.util.spec_from_file_location',side_effect=spec), \
                 patch.object(declarations,'Path',side_effect=path):
                result=controller._raw_f_(payload)
            self.assertEqual(result['status'],'STOP_FOR_REVIEW')
            self.assertIn('cpu-check/receipt.json',result['error_message'])
            self.assertEqual(actions,[])
            self.assertFalse((target/'gemma-base-v02416-gpu-reservation.json').exists())
