"""Serving-only virtue reuse and worker-owned frozen acquisition; no backend."""
import ast
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'studies/formation-study-d-gemma-stages-v02429'


def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


class VirtueReuseTests(unittest.TestCase):
    def test_frozen_serving_assets_and_no_training(self):
        load('static029','scripts/check_study_d_science_v02429.py').check()
        load('launch029','scripts/formation_study_d_gemma_stages_v02429.py').check_sources()

    def test_budget_and_no_old_launch_approval(self):
        h=load('policy029','formation/study_d_gemma_stages_v02429.py')
        self.assertAlmostEqual(h.reservation('virtue'),4.927888888888889)
        b=h.budget('virtue',22.73,7.41,True,'owner current/no card')
        self.assertAlmostEqual(b['projected_cumulative_reserved_usd'],27.65788888888889)
        for actual,credit in [(22.72,7.41),(22.73,4.92),(32,7.41)]:
            with self.assertRaises(ValueError):h.budget('virtue',actual,credit,True,'owner')
        from datetime import datetime,timezone
        payload=dict(stage='virtue',commit='a'*40,approval_receipt='Owner approved Study D Gemma virtue v02428, commit '+'a'*40)
        with self.assertRaisesRegex(ValueError,'approval'):
            h.validate(payload,datetime(2026,10,20,tzinfo=timezone.utc))

    def test_worker_controller_gate_decisions_identical_including_failures(self):
        h=load('policy029','formation/study_d_gemma_stages_v02429.py')
        old=load('policy028','formation/study_d_gemma_stages_v02428.py')
        acq=load('acq029','formation/study_d_modal_v0249.py')
        pair=json.loads((ASSETS/'composite-pair-v02427.json').read_text())
        for total in (0,89,90,94,100):
            rows=[dict(primary_success=i<total,message_consistent=i<total,acquisition_success=i<total,confirmed_shading=False) for i in range(100)]
            ledger={'virtue/acquisition/virtue':dict(own=rows,ordered=rows)}
            self.assertEqual(h.worker_acquisition_decisions(ledger,'virtue',acq,pair),old.acquisition_decisions(ledger,'virtue',acq,pair['arms']['neutral']['neutral_ordered']))

    def test_actual_shared_post_training_path_no_controller_wait(self):
        with tempfile.TemporaryDirectory() as t:
            result=subprocess.run([sys.executable,'-I',str(ROOT/'scripts/study_d_gemma_post_training_ci_v02429.py'),
                '--assets',str(ASSETS),'--output',str(Path(t)/'run')],capture_output=True,text=True,timeout=120)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            report=json.loads((Path(t)/'run/report.json').read_text())
            self.assertTrue(report['worker_controller_decisions_identical'])
            self.assertFalse(report['controller_wait_required']);self.assertEqual(report['transfer_episodes'],132)

    def test_full_admission_against_actual_pinned_returns(self):
        with tempfile.TemporaryDirectory() as t:
            output=Path(t)/'run'
            result=subprocess.run([sys.executable,'-I',str(ROOT/'scripts/study_d_gemma_admission_ci_v02429.py'),
                '--output',str(output)],capture_output=True,text=True,timeout=180)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            report=json.loads((output/'report.json').read_text())
            self.assertEqual(report['repair_calls'],1);self.assertFalse(report['reservation_claimed'])
            self.assertLess(report['peak_rss_bytes'],report['controller_memory_limit_bytes']*.5)

    def test_preemption_and_runtime_classifications(self):
        h=load('policy029','formation/study_d_gemma_stages_v02429.py')
        import asyncio
        for exc in (KeyboardInterrupt(),SystemExit(),asyncio.CancelledError()):
            self.assertEqual(h.failure_classification(exc),'PREEMPTION_OR_CANCELLATION')
        self.assertEqual(h.failure_classification(RuntimeError('CPU scripted fault')),'RUNTIME_ERROR')

    def test_adapter_hash_corruption_and_roster_fail_closed(self):
        h=load('adapterpolicy029','formation/study_d_gemma_stages_v02429.py')
        import hashlib
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);public=root/'prior-virtue/virtue/virtue';public.mkdir(parents=True)
            (public/'training.json').write_text('{"status":"SYNTHETIC_TEST_ONLY"}')
            private=root/'private';folder=private/'science/virtue/final';folder.mkdir(parents=True)
            config=dict(h.LORA,base_model_name_or_path=h.MODEL,peft_type='LORA')
            (folder/'adapter_config.json').write_text(json.dumps(config))
            (folder/'adapter_model.safetensors').write_bytes(b'CPU_TEST_ONLY_NOT_REAL_WEIGHTS')
            (folder/'README.md').write_text('CPU synthetic hash-regression fixture')
            hashes={f.name:h.stream_sha(f) for f in folder.iterdir()}
            (folder/'checkpoint-integrity.json').write_text(json.dumps(dict(arm='virtue',complete=True,scientific_checkpoint=True,sha256=hashes)))
            binding={'sha256':{'virtue/virtue/training.json':h.sha(public/'training.json')}}
            with patch.object(h,'verify_source_training',return_value=binding):
                proof=h.verify_reused_adapter(root,'virtue',private)
                self.assertEqual(proof['files']['adapter_model.safetensors']['sha256'],hashes['adapter_model.safetensors'])
                self.assertFalse(proof['retrained']);self.assertEqual(proof['mount_required'],'read-only')
                extra=folder/'extra';extra.write_text('unexpected')
                with self.assertRaisesRegex(ValueError,'extra/missing'):h.verify_reused_adapter(root,'virtue',private)
                extra.unlink();(folder/'adapter_model.safetensors').write_bytes(b'corrupt')
                with self.assertRaisesRegex(ValueError,'hash differs'):h.verify_reused_adapter(root,'virtue',private)

    def test_actual_worker_preemption_and_runtime_stop_no_private_write(self):
        from types import SimpleNamespace as N
        r=load('runtime029','scripts/study_d_gemma_stages_runtime_v02429.py')
        h=load('workerpolicy029','formation/study_d_gemma_stages_v02429.py')
        errors=load('errors029','formation/study_d_gemma_base_v02416.py')
        class Ledger(dict):
            def contains(self,k):return k in self
            def put(self,k,v,skip_if_exists=False):
                if skip_if_exists and k in self:return False
                self[k]=v;return True
        for error in (KeyboardInterrupt('scripted preemption'),RuntimeError('scripted runtime fault')):
            with tempfile.TemporaryDirectory() as t:
                root=Path(t);(root/'cpu').mkdir();(root/'cpu/receipt.json').write_text('{}')
                commits=[];ledger=Ledger()
                volume=N(reload=lambda:None,commit=lambda:commits.append(1))
                private=N(commit=lambda:(_ for _ in ()).throw(AssertionError('private is read-only')))
                sampler=N(finish=lambda:dict(measurement_failed=False))
                modules={'stages_policy':h,'base_runtime':N(MemorySampler=lambda:sampler),'base_policy':errors,'acquisition_policy':N()}
                with patch.object(r,'ROOT',root),patch.object(r,'ASSETS',ASSETS),patch.object(r,'module',side_effect=lambda n,f:modules[n]), \
                     patch.object(h,'validate'),patch.object(h,'verify_remote'),patch.object(h,'require_cpu'),patch.object(h,'require_previous'), \
                     patch.object(h,'verify_reused_adapter',return_value={'training':{'status':'COMPLETE'}}), \
                     patch.object(r,'Serving',side_effect=error):
                    result=r.arm_worker(volume,private,ledger,dict(stage='virtue',arm='virtue',commit='a'*40,budget={}))
                expected=h.failure_classification(error)
                self.assertEqual(result['status'],'STOP_FOR_REVIEW');self.assertEqual(result['failure_classification'],expected)
                self.assertEqual(ledger['STOP_FOR_REVIEW']['classification'],expected)
                self.assertEqual(ledger['virtue/closed']['status'],'STOP_FOR_REVIEW')
                self.assertTrue((root/'virtue/virtue/reused-adapter-verification.json').exists())
                self.assertTrue(result['no_restart']);self.assertFalse(result['retrained'])


@unittest.skipUnless(importlib.util.find_spec('modal') and sys.version_info[:2]==(3,12),'pinned offline SDK')
class VirtueSerializationTests(unittest.TestCase):
    def test_no_hydration_or_backend(self):
        import modal
        from modal._serialization import serialize
        m=load('app029','scripts/study_d_gemma_stages_app_v02429.py')
        with patch.object(modal.client._Client,'from_env',side_effect=AssertionError('backend forbidden')):
            app,worker,controller=m.define('virtue')
            for f in (worker,controller):self.assertGreater(len(serialize(f._raw_f_)),100)
