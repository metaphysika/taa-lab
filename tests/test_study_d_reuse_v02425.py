import ast
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace as N
from unittest.mock import patch
from formation import study_d_gemma_stages_v02425 as h
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'studies/formation-study-d-gemma-stages-v02425'
RETURNED=ROOT/'studies/formation-study-d-gemma-pair-result-v02424/received-evidence-001/extracted/gemma-v02424-pair-return-001/pair'


def load(name):
    spec=importlib.util.spec_from_file_location('reuse_test',ROOT/name)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


class ReuseTests(unittest.TestCase):
    def test_all_inherited_assets_keys_and_exact_science_path(self):
        load('scripts/check_study_d_science_v02425.py').check()
        contract=load('scripts/study_d_gemma_assets_v02425.py')
        self.assertEqual(contract.required_assets(ASSETS)['inherited_files'],18)
        with self.assertRaises(ValueError):
            contract.required_assets(ROOT/'studies/formation-study-d-gemma-stages-v02424')
        for asset in ('plan.json','stages.json','vllm-logging.json','training-order.json','ci-pinned-config.json'):
            with tempfile.TemporaryDirectory() as t:
                a=Path(t)/'assets';shutil.copytree(ASSETS,a);(a/asset).write_text('{}')
                with self.assertRaises(ValueError):h.verify_assets(a)
        with self.assertRaisesRegex(ValueError,'required asset keys'):
            contract.need({},('bundle_sha256',),'plan.json')
        load('scripts/formation_study_d_gemma_stages_v02425.py').check_sources()
    def test_budget_window_and_separate_approval(self):
        def p(stage):return dict(stage=stage,approved=True,commit='a'*40,
            approval_receipt=f'Owner approved Study D Gemma {stage} v02425, commit '+40*'a',
            actual_total_usd=10.93,available_credit_usd=19.07,billing_attestation='current owner/no card')
        now=datetime(2026,10,20,tzinfo=timezone.utc)
        b=h.validate(p('pair'),now)
        self.assertAlmostEqual(h.reservation('pair'),9.855777777777779)
        self.assertAlmostEqual(h.reservation('virtue'),8.483444444444444)
        self.assertAlmostEqual(10.93+b['remaining_study_reservations_usd'],29.269222222222224)
        h.validate(dict(p('pair'),available_credit_usd=h.reservation('pair')),now)
        for change in ({'actual_total_usd':10.92},{'available_credit_usd':9.85},{'actual_total_usd':20},
                       {'approved':False},{'approval_receipt':'old v02424 approval'}):
            with self.assertRaises(ValueError):h.validate(dict(p('pair'),**change),now)
        with self.assertRaises(ValueError):h.validate(p('pair'),datetime(2026,10,26,1,tzinfo=timezone.utc))
        h.validate(p('virtue'),datetime(2026,11,8,tzinfo=timezone.utc))
    def fixture(self,root):
        shutil.copytree(RETURNED,root/'prior-training')
        shutil.copytree(ASSETS,root/'assets')
        private=root/'private';folder=private/'science/contrary/final';folder.mkdir(parents=True)
        config=dict(h.LORA,base_model_name_or_path=h.MODEL,peft_type='LORA',use_dora=False,use_rslora=False)
        (folder/'adapter_config.json').write_text(json.dumps(config))
        (folder/'adapter_model.safetensors').write_bytes(b'CI FAKE WEIGHTS: never loaded into a model')
        (folder/'README.md').write_text('CI fake adapter only')
        index=dict(arm='contrary',complete=True,scientific_checkpoint=True,
            sha256={p.name:h.sha(p) for p in folder.iterdir()})
        (folder/'checkpoint-integrity.json').write_text(json.dumps(index))
        return private,folder,index
    def test_readonly_source_public_training_and_private_checkpoint_binding(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);private,folder,index=self.fixture(root)
            with patch.object(h,'__file__',str(root/'policy.py')):
                proof=h.verify_reused_adapter(root,'contrary',private)
                self.assertEqual(proof['training']['processed_tokens'],326496)
                self.assertFalse(proof['retrained'])
                h.verify_reused_adapter(root,'contrary',private,published=proof)
                with self.assertRaises(ValueError):h.verify_reused_adapter(root,'contrary',private,published=dict(proof,checkpoint_index_sha256='0'*64))
                weights=folder/'adapter_model.safetensors';weights.write_bytes(b'corrupt')
                with self.assertRaisesRegex(ValueError,'file hash'):h.verify_reused_adapter(root,'contrary',private)
                weights.write_bytes(b'CI FAKE WEIGHTS: never loaded into a model')
                index['complete']=False;(folder/'checkpoint-integrity.json').write_text(json.dumps(index))
                with self.assertRaisesRegex(ValueError,'incomplete'):h.verify_reused_adapter(root,'contrary',private)
                index['complete']=True;(folder/'checkpoint-integrity.json').write_text(json.dumps(index))
                (root/'prior-training/contrary/training.json').write_text('{}')
                with self.assertRaisesRegex(ValueError,'public evidence changed'):h.verify_reused_adapter(root,'contrary',private)
    def test_own_readonly_arm_stop_cannot_train_or_commit_source(self):
        runtime=load('scripts/study_d_gemma_stages_runtime_v02425.py')
        errors=load('formation/study_d_gemma_base_v02416.py')
        class Ledger(dict):
            def put(self,k,v,skip_if_exists=False):self[k]=v;return True
        class Sampler:
            def finish(self):return {'measurement_failed':False}
        private=N(commit=lambda:(_ for _ in ()).throw(AssertionError('old private commit forbidden')))
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'pair/adapter-provenance').mkdir(parents=True)
            (root/'pair/adapter-provenance/contrary.json').write_text('{}')
            fake=N(ENGINE=h.ENGINE,STAGES=h.STAGES,validate=lambda p:None,verify_remote=lambda *x:None,
                require_cpu=lambda *x:None,verify_reused_adapter=lambda *a,**k:(_ for _ in ()).throw(ValueError('bad adapter')))
            mapped={'stages_policy.py':fake,'base_runtime.py':N(MemorySampler=Sampler),'base_policy.py':errors,'acquisition.py':N()}
            with patch.object(runtime,'ROOT',root),patch.object(runtime,'module',side_effect=lambda n,f:mapped[f]), \
                 patch.object(runtime,'train_child',side_effect=AssertionError('pair retraining forbidden')),patch.object(runtime,'Serving',side_effect=AssertionError('must stop before load')):
                report=runtime.arm_worker(N(commit=lambda:None),private,Ledger(),dict(stage='pair',arm='contrary',commit='a'*40))
            self.assertEqual(report['status'],'STOP_FOR_REVIEW');self.assertEqual(report['error_type'],'ValueError')
    def test_full_post_training_scripted_path_and_exact_old_regression(self):
        with tempfile.TemporaryDirectory() as t:
            for version,extra,expected in [('v02425',[],'PASS'),('v02424',['--expect-asset-regression'],'EXPECTED_REGRESSION_REJECTED')]:
                out=Path(t)/version
                result=subprocess.run([sys.executable,'-I',str(ROOT/'scripts/study_d_gemma_post_training_ci_v02425.py'),
                    '--assets',str(ROOT/'studies'/('formation-study-d-gemma-stages-'+version)),
                    '--output',str(out)]+extra,capture_output=True,text=True,timeout=150)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertEqual(json.loads((out/'report.json').read_text())['status'],expected)
                if version=='v02425':self.assertEqual(json.loads((out/'report.json').read_text())['transfer_episodes'],396)


@unittest.skipUnless(importlib.util.find_spec('modal') and sys.version_info[:2]==(3,12),'pinned offline Modal SDK')
class ReuseSerializationTests(unittest.TestCase):
    def test_unhydrated_and_server_enforced_readonly_mount(self):
        import modal
        from modal._serialization import serialize
        from modal.volume import _volume_to_mount_proto
        from modal._utils.async_utils import synchronizer
        appmod=load('scripts/study_d_gemma_stages_app_v02425.py')
        with patch.object(modal.client._Client,'from_env',side_effect=AssertionError('no backend')):
            for stage in ('pair','virtue'):
                app,worker,controller=appmod.define(stage)
                for f in (worker,controller):self.assertGreater(len(serialize(f._raw_f_)),100)
            volume=synchronizer._translate_in(modal.Volume.from_name(h.SOURCE_PRIVATE).read_only())
            self.assertTrue(volume._mount_options.read_only)
            # A hydrated ID fixture only to inspect the serialized server mount flag.
            with patch.object(type(volume),'object_id',property(lambda s:'vo-fixture')):
                self.assertTrue(_volume_to_mount_proto('/adapters',volume).read_only)
