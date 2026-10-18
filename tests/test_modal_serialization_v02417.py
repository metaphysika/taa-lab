"""Pinned real SDK serialization only: no backend, GPU or image build."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

@unittest.skipUnless(importlib.util.find_spec('modal') and sys.version_info[:2]==(3,12),'dedicated offline SDK Python3.12 check')
class SerializationTests(unittest.TestCase):
    def test_all_stage_worker_and_controller_closures_serialize_unhydrated(self):
        import modal
        from modal._serialization import serialize
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
        import study_d_gemma_stages_app_v02417 as app
        with patch.object(modal.client._Client,'from_env',side_effect=AssertionError('no backend allowed')):
            for stage in ('smoke','pair','virtue'):
                a,w,c=app.define(stage)
                self.assertEqual(len(a.registered_functions),2)
                for f in (w,c):self.assertGreater(len(serialize(f._raw_f_)),100)

    def test_controller_commits_claim_before_spawn_and_durable_marker_survives_dict_expiry(self):
        import json
        import modal
        import tempfile
        from formation import study_d_gemma_stages_v02417 as policy
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
        import study_d_gemma_stages_app_v02417 as declarations
        app,worker,controller=declarations.define('smoke')
        entries={};actions=[];outer=self
        class Ledger:
            def contains(self,key):return key in entries
            def put(self,key,value,skip_if_exists=False):
                if key in entries and skip_if_exists:return False
                entries[key]=value;actions.append('claim');return True
        class Volume:
            def reload(self):pass
            def commit(self):actions.append('commit')
        class Call:
            def get(self):return dict(status='COMPLETE',commit='a'*40,engine=policy.ENGINE)
        class Worker:
            def spawn(self,payload):
                outer.assertTrue((target/'smoke/reservation.json').exists())
                outer.assertIn('smoke/once',entries);outer.assertIn('commit',actions)
                actions.append('spawn');return Call()
        real_spec=importlib.util.spec_from_file_location
        sources={'stages_policy.py':'formation/study_d_gemma_stages_v02417.py',
            'base_policy.py':'formation/study_d_gemma_base_v02416.py',
            'acquisition.py':'formation/study_d_modal_v0249.py'}
        def spec(name,path):
            result=real_spec(name,Path(__file__).resolve().parents[1]/sources[Path(path).name])
            execute=result.loader.exec_module
            def load(module):
                execute(module)
                if Path(path).name=='stages_policy.py':module.window=lambda *a,**k:None
            result.loader.exec_module=load;return result
        payload=dict(stage='smoke',commit='a'*40,approved=True,actual_total_usd=4.30,
            available_credit_usd=25.70,billing_attestation='owner test',
            approval_receipt='Owner approved Study D Gemma smoke v02417, commit '+'a'*40,
            worker_function_id='fu-offline-fake')
        with tempfile.TemporaryDirectory() as d:
            target=Path(d);real_path=Path
            def mapped(value):
                return target/str(value).removeprefix('/results/').removeprefix('/results') if str(value).startswith('/results') else real_path(value)
            with patch.object(modal.Dict,'from_name',return_value=Ledger()), \
                 patch.object(modal.Volume,'from_name',return_value=Volume()), \
                 patch.object(modal.Function,'from_id',return_value=Worker()), \
                 patch('importlib.util.spec_from_file_location',side_effect=spec), \
                 patch('pathlib.Path',side_effect=mapped):
                self.assertEqual(controller._raw_f_(dict(payload))['status'],'COMPLETE')
                self.assertEqual(actions.count('spawn'),1)
                entries.clear()  # Seven-day Dict TTL cannot reopen persistent reservation.
                blocked=controller._raw_f_(dict(payload))
                self.assertEqual(blocked['status'],'STOP_FOR_REVIEW')
                self.assertIn('already attempted',blocked['error_message'])
                self.assertEqual(actions.count('spawn'),1)
