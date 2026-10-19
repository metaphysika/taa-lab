import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime,timezone
from unittest.mock import patch
from formation import study_d_gemma_speed_v02422 as h
from formation import study_d_gemma_stages_v02420 as old

ROOT=Path(__file__).resolve().parents[1]


def load(file):
    spec=importlib.util.spec_from_file_location('speed_test_runtime',ROOT/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


class SpeedPolicyTests(unittest.TestCase):
    def payload(self):return dict(commit='a'*40,approved=True,
        approval_receipt='Owner approved Study D Gemma speed smoke v02422, commit '+'a'*40,
        actual_total_usd=5.89,available_credit_usd=24.11,billing_attestation='owner dashboard/no card')
    def test_budget_and_new_approval_only(self):
        p=self.payload();now=datetime(2026,10,20,tzinfo=timezone.utc)
        b=h.validate(p,now);self.assertLessEqual(b['reservation_usd'],2.5)
        self.assertFalse(b['future_arms_reserved'])
        for change in ({'approved':False},{'approval_receipt':'v02420'},{'actual_total_usd':float('nan')},
                       {'available_credit_usd':1},{'actual_total_usd':29},{'billing_attestation':''}):
            with self.assertRaises(ValueError):h.validate(dict(p,**change),now)
        with self.assertRaises(ValueError):h.validate(p,datetime(2026,11,1,tzinfo=timezone.utc))
    def test_engine_fixed_science_and_graphs(self):
        for mode in h.MODES:
            e=h.engine(old.ENGINE,mode,'/private/merged')
            for key in ('dtype','max_model_len','gpu_memory_utilization','max_num_seqs','seed'):
                self.assertEqual(e[key],old.ENGINE[key])
            self.assertFalse(e['enforce_eager']);self.assertTrue(e['compilation_config']['cudagraph_specialize_lora'])
            self.assertTrue(e['enable_prefix_caching']);self.assertEqual(e['enable_lora'],mode=='live')
        with self.assertRaises(ValueError):h.engine(old.ENGINE,'merged')
    def test_post_graph_kv_refuses_short_missing_or_oom(self):
        log='Available KV cache memory: 15.84 GiB\nGraph capturing finished in 10 secs, took 0.50 GiB'
        self.assertEqual(h.graph_kv(log,2**30)['status'],'PASS')
        for text,free in [(log.replace('0.50','2.50'),2**30),('Available KV cache memory: 15.84 GiB',2**30),(log,100)]:
            with self.assertRaises(RuntimeError):h.graph_kv(text,free)
    def test_merge_numerical_thresholds(self):
        self.assertTrue(h.merge_pass(.5,.01))
        for a,b in [(.51,.001),(.1,.011),(float('nan'),0),(-1,0)]:self.assertFalse(h.merge_pass(a,b))
    def cells(self):return [dict(mode=m,cache=c,requests=8,tokens=512,round_seconds=[20,20]) for m in h.MODES for c in h.CACHE_MODES]
    def test_no_partial_or_outcome_based_selection(self):
        cells=self.cells();cells[-1]['round_seconds']=[15,15];cells[-1]['score']='bad'
        s=h.select(cells);self.assertEqual((s['mode'],s['prefix_policy']),('merged','retained'))
        cells[-1]['score']='correct';self.assertEqual(h.select(cells),s)
        cells[-1]['round_seconds']=[19.5,19.5];self.assertEqual(h.select(cells)['prefix_policy'],'cold')
        with self.assertRaises(ValueError):h.select(cells[:-1])
        cells[-1]['requests']=7
        with self.assertRaises(ValueError):h.select(cells)
    def test_projections_keep_work_and_credit_months_separate(self):
        s=h.select(self.cells());counts={a:{'tokens':330000} for a in ('contrary','neutral','virtue')}
        p=h.project(s,dict(processed_tokens=10438,seconds=79.38),counts,600,24.59)
        self.assertFalse(p['cap_increase_approved']);self.assertFalse(p['further_execution_approved'])
        for arm in p['arms'].values():
            self.assertEqual((arm['transfer_episodes'],arm['training_examples'],arm['epochs']),(132,2000,1))
        self.assertAlmostEqual(p['october_after_speed_reservation_usd'],24.59-h.RESERVE)
    def test_assets_and_local_source_binding(self):
        module=load('scripts/formation_study_d_gemma_speed_v02422.py');module.check_sources()
        fixture=json.loads((module.ASSETS/'benchmark.json').read_text())
        self.assertEqual(len(fixture['streams']),2)
        self.assertTrue(all(len(s['turns'])==2 for s in fixture['streams']))


@unittest.skipUnless(importlib.util.find_spec('torch') and importlib.util.find_spec('peft'),'pinned actual CPU CI environment')
class ActualMergeTests(unittest.TestCase):
    def test_tiny_actual_peft_merge_save_and_reload_logits(self):
        import torch
        from transformers import Gemma4Config,Gemma4ForConditionalGeneration
        from peft import LoraConfig,get_peft_model
        runtime=load('scripts/study_d_gemma_speed_runtime_v02422.py')
        shared=load('scripts/study_d_gemma_stages_runtime_v02420.py')
        config=json.loads((ROOT/'studies/formation-study-d-gemma-stages-v02420/ci-pinned-config.json').read_text())
        torch.manual_seed(248021);torch.set_num_threads(2)
        model=Gemma4ForConditionalGeneration(Gemma4Config.from_dict(shared.tiny_config_values(config))).float()
        model=get_peft_model(model,LoraConfig(**old.LORA))
        for name,p in model.named_parameters():
            if 'lora_B' in name:torch.nn.init.normal_(p,std=.001)
        class Tokenizer:
            def save_pretrained(self,path):(path/'tokenizer-test-receipt.json').write_text('{}')
        with tempfile.TemporaryDirectory() as d,patch.object(runtime,'load',return_value=h):
            out=Path(d)/'merged'
            result=runtime.merge_and_check(model,[2,3,4],out,Tokenizer(),device='cpu')
            self.assertEqual(result['status'],'PASS')
            merged=Gemma4ForConditionalGeneration.from_pretrained(out,local_files_only=True,dtype=torch.float32)
            self.assertFalse(any('lora_' in n for n,_ in merged.named_parameters()))
            self.assertTrue((out/'model.safetensors').exists())
            with torch.inference_mode():
                ids=torch.tensor([[2,3,4]])
                expected=model(input_ids=ids,use_cache=False).logits
                actual=merged(input_ids=ids,use_cache=False).logits
                self.assertLessEqual(float((expected-actual).abs().max()),1e-5)
                self.assertLessEqual(float((expected-actual).norm()/expected.norm()),2e-5)
            for name,value in model.get_base_model().state_dict().items():
                self.assertTrue(torch.equal(value,merged.state_dict()[name]),name)


@unittest.skipUnless(importlib.util.find_spec('modal') and __import__('sys').version_info[:2]==(3,12),'dedicated offline Modal SDK Python3.12')
class SpeedSerializationTests(unittest.TestCase):
    def test_unhydrated_controller_and_worker(self):
        import modal
        from modal._serialization import serialize
        m=load('scripts/study_d_gemma_speed_app_v02422.py')
        with patch.object(modal.client._Client,'from_env',side_effect=AssertionError('no backend')):
            a,w,c=m.define()
            self.assertEqual(len(a.registered_functions),2)
            for f in (w,c):self.assertGreater(len(serialize(f._raw_f_)),100)


class BenchmarkRehearsalTests(unittest.TestCase):
    def test_real_benchmark_control_flow_with_scripted_engine_no_gpu(self):
        import sys
        import shutil
        from types import SimpleNamespace as N
        runtime=load('scripts/study_d_gemma_speed_runtime_v02422.py')
        shared=load('scripts/study_d_gemma_stages_runtime_v02420.py')
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);(folder/'speed-assets').mkdir()
            shutil.copyfile(ROOT/'studies/formation-study-d-gemma-speed-v02422/benchmark.json',folder/'speed-assets/benchmark.json')
            (folder/'assets').mkdir()
            shutil.copyfile(ROOT/'studies/formation-study-d-gemma-stages-v02420/vllm-logging.json',folder/'assets/vllm-logging.json')
            class Sampler:
                baseline=0
                def finish(self):return {'measurement_failed':False,'sampled_peak_device_used_bytes':80*2**30}
            class Engine:
                def __init__(self):
                    self.llm_engine=N(add_lora=lambda x:True,vllm_config=N(compilation_config=N(
                        cudagraph_specialize_lora=True,cudagraph_capture_sizes=[1,2],cudagraph_mode=N(name='FULL_AND_PIECEWISE'))))
                def get_tokenizer(self):return object()
                def get_default_sampling_params(self):return N(clone=lambda:N())
                def reset_prefix_cache(self):return True
                def generate(self,prompts,params,**kw):
                    selftest.assertEqual((params.max_tokens,params.min_tokens,params.ignore_eos),(64,64,True))
                    selftest.assertEqual(len(prompts),2)
                    return [N(outputs=[N(token_ids=[1]*64,text='scripted timing reply',finish_reason='length',stop_reason=None)]) for _ in prompts]
            selftest=self
            class LLM:
                @staticmethod
                def from_engine_args(args):
                    (folder/(mode+'-vllm-engine.log')).write_text('FlashInfer top-p/top-k sampling disabled via VLLM_USE_FLASHINFER_SAMPLER=0\nAvailable KV cache memory: 15.84 GiB\nGraph capturing finished in 10 secs, took 0.50 GiB')
                    return Engine()
            modules={'torch':N(cuda=N(device_count=lambda:1,get_device_name=lambda n:'A100',
                get_device_properties=lambda n:N(total_memory=80*2**30),mem_get_info=lambda:(2**30,80*2**30))),
                'vllm':N(LLM=LLM),'vllm.engine.arg_utils':N(EngineArgs=lambda **kw:N(**kw)),
                'vllm.lora.request':N(LoRARequest=lambda *args:N())}
            mapped={'sampler_guard.py':load('scripts/study_d_gemma_sampler_v02422.py'),'speed_policy.py':h,'stages_policy.py':N(ENGINE=old.ENGINE,PACKAGES={},sha=h.sha),
                'runtime.py':shared,'base_runtime.py':N(MemorySampler=Sampler,prompt_ids=lambda *a:[2,3]),
                'base_policy.py':N(kv_prediction=lambda *a:{'status':'PASS'})}
            for mode in h.MODES:
                with patch.dict(sys.modules,modules),patch.object(runtime,'HERE',folder),patch.object(runtime,'load',side_effect=lambda n,f:mapped[f]):
                    runtime.bench(dict(mode=mode,folder=str(folder),adapter='/private/adapter',merged='/private/merged',deadline=__import__('time').monotonic()+120))
                report=json.loads((folder/(mode+'-benchmark.json')).read_text())
                self.assertEqual(report['status'],'COMPLETE')
                self.assertEqual([(c['requests'],c['tokens']) for c in report['cells']],[(8,512),(8,512)])
                self.assertEqual(len((folder/(mode+'-benchmark-events.jsonl')).read_text().splitlines()),18)


class SamplerGuardTests(unittest.TestCase):
    def test_static_contract_and_mutations(self):
        checker=load('scripts/check_study_d_sampler_v02422.py')
        checker.main()
        source=(ROOT/'scripts/study_d_gemma_speed_runtime_v02422.py').read_text()
        for changed in (source.replace('env=child_env','env=None'),
                        source.replace('guard.configure()','pass # missing environment configuration')):
            with self.assertRaises((AssertionError,StopIteration)):checker.child_check(changed)
        for path,seed in [('scripts/study_d_gemma_speed_runtime_v02422.py','params.seed=248021;'),
                          ('scripts/study_d_gemma_stages_runtime_v02420.py','params.seed=seed;')]:
            with self.assertRaises(AssertionError):checker.seed_check((ROOT/path).read_text().replace(seed,''))
    def test_log_guard_rejects_missing_and_mixed_signals(self):
        guard=load('scripts/study_d_gemma_sampler_v02422.py')
        for log in ('',guard.ENABLED,guard.DISABLED+'\n'+guard.ENABLED):
            with self.assertRaises(RuntimeError):guard.check_log(log)
        self.assertEqual(guard.check_log(guard.DISABLED)['status'],'PASS')
    def test_environment_preserves_parent_and_overrides_sampler(self):
        guard=load('scripts/study_d_gemma_sampler_v02422.py')
        parent={'OTHER_SETTING':'unchanged',guard.VARIABLE:'1'}
        child=guard.child_env(parent)
        self.assertEqual(child,{'OTHER_SETTING':'unchanged',guard.VARIABLE:'0'})
        self.assertEqual(parent[guard.VARIABLE],'1')
    def test_actual_prior_kv_margin_and_fixture_integrity(self):
        archived=ROOT/'studies/formation-study-d-gemma-speed-result-v02421/received-evidence-001/extracted/speed/live-vllm-engine.log'
        fixture=ROOT/'tests/fixtures/study_d_sampler_v02422/v02421-engine.log'
        self.assertEqual(archived.read_bytes(),fixture.read_bytes())
        kv=h.graph_kv(fixture.read_text(),2**30)
        self.assertAlmostEqual(kv['conservative_margin_GiB'],.145)
        self.assertAlmostEqual(kv['native_available_minus_requirement_GiB'],.495)
