import ast
import importlib.util
import json
from datetime import datetime,timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from formation import study_d_gemma_stages_v02423 as h
from formation import study_d_gemma_stages_v02420 as old
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'studies/formation-study-d-gemma-stages-v02423'


def load(path):
    spec=importlib.util.spec_from_file_location('science_test',ROOT/path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


class SciencePolicyTests(unittest.TestCase):
    def payload(self,stage='pair'):
        return dict(stage=stage,approved=True,commit='a'*40,
            approval_receipt=f'Owner approved Study D Gemma {stage} v02423, commit '+40*'a',
            actual_total_usd=6.8,available_credit_usd=23.2,billing_attestation='owner confirmed/no card')
    def test_guards_reserve_both_remaining_stages_under_cap(self):
        now=datetime(2026,10,20,tzinfo=timezone.utc)
        b=h.validate(self.payload(),now)
        self.assertAlmostEqual(b['remaining_study_reservations_usd'],22.60588888888889)
        self.assertLess(6.8+b['remaining_study_reservations_usd'],30)
        self.assertEqual(h.STAGES['pair']['software'],7600)
        self.assertEqual(h.STAGES['virtue']['software'],8000)
        for change in ({'approved':False},{'actual_total_usd':float('nan')},{'available_credit_usd':22.5},
                       {'actual_total_usd':7.5},{'stage':'smoke'},{'approval_receipt':'old approval'}):
            with self.assertRaises(ValueError):h.validate(dict(self.payload(),**change),now)
        with self.assertRaises(ValueError):h.validate(self.payload(),datetime(2026,11,1,tzinfo=timezone.utc))
        h.validate(self.payload('virtue'),datetime(2026,11,1,tzinfo=timezone.utc))
    def test_static_contract_rejects_unapproved_config_or_merge(self):
        checker=load('scripts/check_study_d_science_v02423.py');checker.check()
        src=(ROOT/'scripts/study_d_gemma_stages_runtime_v02423.py').read_text()
        for changed in (src.replace('EngineArgs(**h.ENGINE)',"EngineArgs(model='/merged')"),
                        src.replace('guard.configure()','pass'),src+'\ndef forbidden(m): return m.merge_and_unload()\n',
                        src.replace('params.seed=seed;','')):
            with self.assertRaises((AssertionError,ValueError)):checker.check(changed)
    def test_science_assets_byte_identical_and_manifest_binding(self):
        old_assets=ROOT/'studies/formation-study-d-gemma-stages-v02420'
        for name in json.loads((old_assets/'integrity.json').read_text())['sha256']:
            if name not in ('plan.json','MAC_COMMANDS.md','stages.json'):
                self.assertEqual((ASSETS/name).read_bytes(),(old_assets/name).read_bytes(),name)
        load('scripts/formation_study_d_gemma_stages_v02423.py').check_sources()
    def test_projection_denominators_and_slow_guard_fit(self):
        s=json.loads((ASSETS/'selection-v02423.json').read_text());p=json.loads((ASSETS/'projections-v02423.json').read_text())
        self.assertAlmostEqual(s['live_cold_tokens_per_second'],31.36832507666223)
        self.assertAlmostEqual(s['live_retained_tokens_per_second'],36.236878009136916)
        self.assertLessEqual(s['retained_over_cold_elapsed_ratio'],.95)
        self.assertFalse(s['merged_candidate_valid']);self.assertEqual(s['mode'],'live')
        for scenario in p['scenarios'].values():
            for arm,row in scenario['arms'].items():
                self.assertEqual(row['transfer_episodes'],132)
                self.assertEqual(row['training_examples'],2000)
                self.assertFalse(row['old_guard_fits']);self.assertTrue(row['stress_fits_proposed_guard'])
                self.assertAlmostEqual(row['stress_seconds'],1.25*row['nominal_seconds'])
                tps=131.5 if scenario is p['scenarios'].get('131.5') else 97.6
                expected=row['training_tokens']/tps+row['generation_seconds']+p['measured_startup_total_seconds']+300
                self.assertAlmostEqual(row['nominal_seconds'],expected)
    def test_previous_pair_is_required_and_speed_evidence_bound(self):
        import shutil
        prior=ROOT/'studies/formation-study-d-gemma-speed-result-v02422/received-evidence-001/extracted/gemma-v02422-speed-return-001/speed'
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);(r/'assets').mkdir();shutil.copyfile(ASSETS/'selection-v02423.json',r/'assets/selection-v02423.json')
            shutil.copytree(prior,r/'prior-speed')
            p=dict(self.payload(),previous_report_sha256=h.sha(r/'prior-speed/report.json'))
            with patch.object(h,'__file__',str(r/'policy.py')):
                h.require_previous(r,p)
                (r/'prior-speed/training.json').write_text('{}')
                with self.assertRaises(ValueError):h.require_previous(r,p)
    def test_virtue_requires_closed_pair_same_commit_and_actual_cost(self):
        import shutil
        prior=ROOT/'studies/formation-study-d-gemma-speed-result-v02422/received-evidence-001/extracted/gemma-v02422-speed-return-001/speed'
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);(r/'assets').mkdir();(r/'pair').mkdir()
            shutil.copyfile(ASSETS/'selection-v02423.json',r/'assets/selection-v02423.json')
            shutil.copytree(prior,r/'prior-speed')
            report=dict(status='COMPLETE',commit='a'*40,engine=h.ENGINE,
                budget={'actual_prior_usd':6.8},arms={a:{'software_wall_seconds':1000} for a in ('contrary','neutral')})
            path=r/'pair/report.json';path.write_text(json.dumps(report))
            p=dict(self.payload('virtue'),previous_report_sha256=h.sha(path),actual_total_usd=9.)
            ledger={'pair/closed':dict(status='COMPLETE',report_sha256=h.sha(path))}
            with patch.object(h,'__file__',str(r/'policy.py')):
                h.require_previous(r,p,ledger)
                h.require_previous(r,dict(p,actual_total_usd=8.3),ledger)  # GPU-only minimum, not host-resource estimate
                for change,proof in [({'actual_total_usd':6.8},ledger),({'commit':'b'*40},ledger),({},{}),({'previous_report_sha256':'0'*64},ledger)]:
                    with self.assertRaises(ValueError):h.require_previous(r,dict(p,**change),proof)

    def test_cpu_wrapper_uses_original_commit_assets_and_closure(self):
        from types import SimpleNamespace
        calls=[]
        class Loader:
            def exec_module(self,m):
                m.require_cpu=lambda root,p,ledger:(calls.append((p,ledger)) or {'status':'PASS'})
        with patch('importlib.util.spec_from_file_location',return_value=SimpleNamespace(loader=Loader())), \
             patch('importlib.util.module_from_spec',return_value=SimpleNamespace()),patch.object(h,'sha',return_value=h.CPU_RECEIPT):
            h.require_cpu('/root',self.payload(),ledger='durable-proof')
        self.assertEqual(calls,[({'commit':h.CPU_COMMIT,'asset_sha256':h.CPU_ASSETS},'durable-proof')])


@unittest.skipUnless(importlib.util.find_spec('modal') and __import__('sys').version_info[:2]==(3,12),'offline pinned Modal SDK')
class ScienceSerializationTests(unittest.TestCase):
    def test_pair_virtue_unhydrated_no_backend(self):
        import modal
        from modal._serialization import serialize
        appmod=load('scripts/study_d_gemma_stages_app_v02423.py')
        with patch.object(modal.client._Client,'from_env',side_effect=AssertionError('no backend')):
            for stage in ('pair','virtue'):
                app,worker,controller=appmod.define(stage)
                for f in (worker,controller):self.assertGreater(len(serialize(f._raw_f_)),100)
            with self.assertRaises(ValueError):appmod.define('smoke')


class ScienceServingRehearsalTests(unittest.TestCase):
    def test_actual_serving_control_flow_scripted_engine_and_native_guard(self):
        import sys,time
        from types import SimpleNamespace as N
        runtime=load('scripts/study_d_gemma_stages_runtime_v02423.py')
        guard=load('scripts/study_d_gemma_sampler_v02422.py')
        seen=[];pending=[];selftest=self
        class Engine:
            vllm_config=N(compilation_config=N(cudagraph_specialize_lora=True,cudagraph_capture_sizes=[1,2],cudagraph_mode=N(name='FULL_AND_PIECEWISE')))
            def add_lora(self,adapter):seen.append('adapter');return True
            def add_request(self,key,prompt,params,**kw):
                selftest.assertIsInstance(params.seed,int)
                selftest.assertEqual(params.max_tokens,4096)
                selftest.assertFalse(params.skip_special_tokens)
                pending.append(key);seen.append(params.seed)
            def step(self):
                batch=list(pending);pending.clear()
                return [N(request_id=k,finished=True,outputs=[N(token_ids=[1],text='scripted',finish_reason='stop',stop_reason=106)]) for k in batch]
        class LLM:
            @staticmethod
            def from_engine_args(args):
                selftest.assertEqual(vars(args),h.ENGINE)
                return N(llm_engine=Engine(),get_tokenizer=lambda:N(chat_template="scripted"),get_default_sampling_params=lambda:N(clone=lambda:N()))
        class Sampler:
            baseline=0
            def finish(self):return {'measurement_failed':False}
        modules={'torch':N(cuda=N(device_count=lambda:1,get_device_name=lambda x:'A100',get_device_properties=lambda x:N(total_memory=80*2**30),mem_get_info=lambda:(2**30,80*2**30))),
                 'vllm':N(LLM=LLM),'vllm.engine.arg_utils':N(EngineArgs=lambda **kw:N(**kw)),
                 'vllm.lora.request':N(LoRARequest=lambda *a:N())}
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);log=folder/'vllm-engine.log'
            native=guard.DISABLED+'\nAvailable KV cache memory: 14.26 GiB\nGraph capturing finished in 10 secs, took 0.09 GiB\nGraph capturing finished in 1 secs, took 0.04 GiB\n'
            log.write_text(native)
            mapped={'sampler_guard.py':guard,'base_policy.py':N(kv_prediction=lambda *x:dict(status='PASS'))}
            with patch.dict(sys.modules,modules),patch.object(runtime,'module',side_effect=lambda n,f:mapped[f]):
                session=runtime.Serving(h,N(MemorySampler=Sampler,prompt_ids=lambda *a:[2,3]),folder,N(commit=lambda:None),N(contains=lambda x:False),time.monotonic()+120,'/private/contrary/final')
                result=session.run([lambda:session.generate([], 'one',247053),lambda:session.generate([], 'two',247054)])
                self.assertEqual(result,['scripted','scripted'])
                self.assertEqual(set(seen),{'adapter',247053,247054})
                self.assertAlmostEqual(json.loads((folder/'kv-current.json').read_text())['conservative_margin_GiB'],.1)
                seen.clear();log.write_text(native+'\n'+guard.ENABLED)
                with self.assertRaises(RuntimeError):runtime.Serving(h,N(MemorySampler=Sampler),folder,N(commit=lambda:None),N(),time.monotonic()+120,'/private/adapter')
                self.assertEqual(seen,[])
