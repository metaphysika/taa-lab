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
        import study_d_gemma_modal_app_v02413 as declarations
        with patch.object(modal.client._Client,'from_env',side_effect=AssertionError('no live client')):
            app,worker,controller=declarations.define()
            self.assertEqual(len(app.registered_functions),2)
            for function in (worker,controller):
                self.assertGreater(len(serialize(function._raw_f_)),100)

    def test_durable_once_marker_blocks_even_if_dict_entries_absent(self):
        import importlib.util
        import json
        import modal
        import tempfile
        from formation import study_d_gemma_base_v02413 as h
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
        import study_d_gemma_modal_app_v02413 as declarations
        app,worker,controller=declarations.define()
        entries={};actions=[]
        class Ledger:
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
                self_outer.assertTrue((target/'gemma-base-v02413-reservation.json').exists())
                self_outer.assertIn(h.STAGE_KEY,entries)
                actions.append('spawn');return Call()
        self_outer=self
        commit='a'*40
        payload=dict(commit=commit,approved=True,prior_usd=1.70,billing_attestation='owner verified',
            approval_receipt='Owner approved Gemma base-format gate v02413, commit '+commit,
            worker_function_id='fu-offline-fake')
        real_spec=importlib.util.spec_from_file_location
        def spec(name,path):
            result=real_spec(name,Path(__file__).resolve().parents[1]/'formation/study_d_gemma_base_v02413.py')
            execute=result.loader.exec_module
            def execute_frozen_clock(module):
                execute(module)
                module.check_window=lambda now=None:h.check_window(datetime(2026,10,19,tzinfo=timezone.utc))
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
                self.assertEqual(controller._raw_f_(dict(payload))['status'],'COMPLETE')
                self.assertEqual(actions.count('spawn'),1)
                entries.clear()  # TTL simulation; durable evidence still refuses admission.
                with self.assertRaisesRegex(RuntimeError,'prior attempt'):
                    controller._raw_f_(dict(payload))
                self.assertEqual(actions.count('spawn'),1)
