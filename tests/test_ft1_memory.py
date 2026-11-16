"""CPU-only memory controls, using public or synthetic fixtures."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from exploratory.ft1 import memory, fit_limit, fit_limit_stage

class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.object(fit_limit,'reset_peaks'))
        self.enterContext(patch.object(fit_limit,'peaks',return_value=dict(peak_allocated_bytes=123,peak_reserved_bytes=456)))

    def test_tracking(self):
        events=[]
        tracker=memory.Tracker(events.append)
        def fail(): raise memory.MechanicalOOM(1234,7)
        for _ in range(3): tracker.call(fail,None,'synthetic')
        self.assertTrue(tracker.stopped)
        self.assertEqual(tracker.total,3)
        self.assertEqual(events[-1]['turn'],7)
        self.assertNotIn('score',events[-1])
        tracker.call(lambda: 'ok',0,'synthetic')
        self.assertEqual(tracker.consecutive,0)
        self.assertTrue(memory.is_oom(RuntimeError('CUDA out of memory.')))
        self.assertFalse(memory.is_oom(RuntimeError('bad shape')))

    def test_ladder_and_parity(self):
        class Backend:
            def benchmark(self,prompts,check,new_tokens):
                self_test.assertEqual(new_tokens,1024)
                if len(prompts[0])>=6000: raise fit_limit.throughput.MeasurementOOM(123)
                return dict(generated_ids=[[1,2]])
        self_test=self
        events=[]; refs={}
        with patch.object(fit_limit.throughput,'prompt_ids',side_effect=lambda t,c,n:[0]*n):
            for backend in ('eager','sdpa'):
                fit_limit.measure(Backend(),None,backend,refs,events.append,lambda:None)
        self.assertEqual(sum(e.get('status')=='oom' for e in events),2)
        rows=[e for e in events if e.get('parity_available')]
        self.assertEqual(len(rows),2)
        self.assertTrue(all(e['first_divergence'] is None for e in rows))
        self.assertEqual(fit_limit.throughput.first_divergence([1],[2]),0)

    def test_receipt(self):
        config=dict(phase='fit_limit',repo_commit='a'*40,model_source='google/gemma-3/transformers/gemma-3-12b-it/1',data_manifest_sha256=None)
        fit_limit.validate(config,dict(config,approved=True))
        for change in (dict(approved=False),dict(phase='throughput'),dict(repo_commit='b'*40)):
            with self.assertRaises(ValueError): fit_limit.validate(config,dict(dict(config,approved=True),**change))

    def test_stage(self):
        def git(args,**kwargs):
            return '' if '--name-only' in args else b'# synthetic source'
        with tempfile.TemporaryDirectory() as tmp,patch.object(fit_limit_stage.subprocess,'check_output',side_effect=git):
            folder=Path(tmp)/'stage'
            config=fit_limit_stage.stage(folder,'a'*40,'owner','owner/repo','owner/receipt','google/gemma-3/transformers/gemma-3-12b-it/1')
            source=''.join(json.loads((folder/'ft1_fit_limit.ipynb').read_text())['cells'][0]['source'])
            self.assertIn('PLAN_ONLY = True',source)
            compile(source,'stage','exec')
            self.assertEqual(config['phase'],'fit_limit')
            self.assertFalse(json.loads((folder/'kernel-metadata.json').read_text())['enable_internet'])

    def test_gate_oom_report(self):
        from exploratory.ft1 import evaluate_runner as runner
        config=dict(arm='base',seed=None,repo_commit='a'*40,data_manifest_sha256='b'*64,adapter_sha256=None,training_manifest_sha256=None)
        events=[]
        records=[dict(messages=[dict(role='user',content='synthetic'),dict(role='assistant',content='{}')])]*40
        def fail(*args): raise memory.MechanicalOOM(999)
        gate=runner.protocol(config,records,fail,len,events.append,lambda:None,[])
        self.assertEqual(gate['mechanical_oom'],3)
        self.assertEqual(gate['status'],'gate_mechanical_unknown')
        self.assertIsNone(gate['acquired'])
        self.assertEqual(len(events),3+1)

    def test_episode_turn_oom(self):
        from exploratory.ft1 import evaluation
        from exploratory.step4_harness import crossing
        def fail(*args): raise memory.MechanicalOOM(2000)
        with self.assertRaises(memory.MechanicalOOM) as caught:
            evaluation.episode(crossing.cases()[0],fail,len,lambda e:None)
        self.assertEqual(caught.exception.turn,0)

    def test_generation_runtime_oom_cleanup(self):
        import types
        from exploratory.ft1 import evaluate_runner as runner
        from tests.test_ft1_throughput import fake_torch
        model=types.SimpleNamespace(eval=lambda:None)
        def fail(**kwargs): raise RuntimeError('CUDA out of memory')
        model.generate=fail
        torch=fake_torch()
        torch.ones_like=lambda value:value
        transformers=types.SimpleNamespace(set_seed=lambda seed:None)
        with patch.dict('sys.modules',torch=torch,transformers=transformers),patch.object(runner.core,'prompt',return_value=[1,2,3]),patch.object(runner.core,'end_token',return_value=0),patch.object(memory,'cleanup') as cleanup:
            generate,_=runner.generation_functions(model,types.SimpleNamespace(pad_token_id=0),lambda:None)
            with self.assertRaises(memory.MechanicalOOM) as caught: generate('system',[],1024,1)
            self.assertEqual(caught.exception.prompt_tokens,3)
            cleanup.assert_called_once()

    def test_context_ceiling_receipt_and_tracker(self):
        import types
        from exploratory.ft1 import evaluate_runner as runner
        from tests.test_ft1_throughput import fake_torch
        model=types.SimpleNamespace(eval=lambda:None)
        config=dict(arm='base',seed=None,phase='gate',part=None,part_count=None,gate_sha256=None,sealed_sha256=None,
            adapter_sha256=None,training_manifest_sha256=None,prompt_ceiling=100)
        runner.validate(config,dict(config,approved=True))
        with self.assertRaises(ValueError): runner.validate(config,dict(config,approved=True,prompt_ceiling=101))
        with patch.dict('sys.modules',torch=fake_torch(),transformers=types.SimpleNamespace(set_seed=lambda s:None)),patch.object(runner.core,'prompt',return_value=[1]*101):
            generate,_=runner.generation_functions(model,types.SimpleNamespace(),lambda:None,prompt_ceiling=100)
            events=[]; tracker=memory.Tracker(events.append)
            tracker.call(lambda:generate('',[],1024,1),0,dict(case_id='synthetic',branch='action'))
            self.assertEqual(tracker.counts,dict(mechanical_oom=0,context_limit=1))
            self.assertEqual(events[0]['prompt_tokens'],101)
            self.assertEqual(events[0]['rule'],'prompt_ceiling')
            generate,_=runner.generation_functions(model,types.SimpleNamespace(),lambda:None)
            with self.assertRaises(memory.ContextLimit) as caught: generate('',[],1024,1,prompt_ids=[0]*15361)
            self.assertEqual(caught.exception.rule,'16384')

    def test_gate_unknown_requires_owner_decision(self):
        from exploratory.ft1 import evaluate_runner as runner
        config=dict(arm='base',seed=None,adapter_sha256=None,training_manifest_sha256=None,repo_commit='a',data_manifest_sha256='b',model_source='local')
        events=[]; tracker=memory.Tracker(events.append)
        def fail(): raise memory.ContextLimit(16000)
        tracker.call(fail,0,'synthetic')
        gate=runner.unknown_gate(config,[],tracker)
        self.assertIsNone(gate['acquired'])
        with self.assertRaises(memory.GateDecisionRequired): runner.validate_gate(config,gate)
        self.assertNotIn('raw',events[0])

    def test_recovery_same_backend_and_evaluation_path(self):
        calls=[]
        class Backend:
            def benchmark(self,prompts,check,new_tokens):
                calls.append(len(prompts[0]))
                if len(prompts[0])==6000: raise fit_limit.throughput.MeasurementOOM(123)
                return dict(generated_ids=[[1,2]])
        def generate(*args,**kwargs):
            if len(kwargs['prompt_ids'])==6000: raise memory.MechanicalOOM(6000)
            self.assertEqual(len(kwargs['prompt_ids']),2500)
            self.assertEqual(args[2],128)
            return [1,2]
        events=[]
        with patch.object(fit_limit.throughput,'prompt_ids',side_effect=lambda t,c,n:[0]*n),patch.object(fit_limit,'snapshot',return_value=dict(memory_allocated=1,memory_reserved=2,total_device_memory=3)):
            fit_limit.measure(Backend(),None,'eager',{},events.append,lambda:None,generate=generate)
        self.assertEqual(calls,[2500,4000,6000,2500])
        recovery=next(e for e in events if e['event']=='recovery_check')
        self.assertTrue(recovery['ids_equal_first_pass'])
        self.assertEqual(events[-2]['status'],'mechanical_oom')
        self.assertEqual(events[-1]['event'],'evaluation_recovery_check')
        self.assertEqual(events[-1]['status'],'fit')
        self.assertEqual(events[-1]['generated_tokens'],2)
        self.assertEqual(events[-1]['peak_allocated_bytes'],123)
        self.assertEqual(fit_limit.to_eot([1,9,2],[9]),[1,9])
        self.assertIsNone(fit_limit.throughput.first_divergence(fit_limit.to_eot([1,9,2],[9]),fit_limit.to_eot([1,9,3],[9])))

    def test_mechanical_aggregation_keeps_bounds(self):
        import copy
        from exploratory.step4_harness import crossing
        from exploratory.ft1 import aggregation
        templates=crossing.cases()
        cases=[]
        for i in range(48):
            case=copy.deepcopy(next(c for c in templates if c['kind']==('W' if i%2==0 else 'U')))
            case['answer_key']['knowledge_answer']='no' if i%2==0 else 'yes'
            case.update(id=str(i),pair_id=str(i//2))
            cases.append(case)
        raw='{"tool":"set_record_status","args":{"record_id":"PRIMARY","status":"'+cases[0]['answer_key']['requested_status']+'"}}'
        turns=[dict(event='turn',case_id='0',turn=0,raw=raw)]
        unknowns=[dict(event='mechanical_oom',case_id='0',branch='action',turn=1,prompt_tokens=12000),
                  dict(event='context_limit',case_id='1',branch='action',turn=0,prompt_tokens=16000)]
        before=aggregation.possibilities(cases,turns)
        after=aggregation.possibilities(cases,turns+unknowns+[dict(event='mechanical_oom',phase='acquisition',turn=0,prompt_tokens=100)])
        self.assertEqual(before['joint_counts'],after['joint_counts'])
        self.assertEqual(after['missing_episodes'],46)
        self.assertEqual(after['counts']['format_failures'],0)
        self.assertEqual(after['mechanical_unknowns']['mechanical_oom']['by_kind'],{'W':1})
        self.assertEqual(after['mechanical_unknowns']['mechanical_oom']['by_branch'],dict(action=1,knowledge=0))
        knowledge=aggregation.possibilities(cases,unknowns+[dict(event='mechanical_oom',case_id='2',branch='knowledge',turn=0,prompt_tokens=1200)])
        self.assertEqual(knowledge['mechanical_unknowns']['mechanical_oom']['by_branch'],dict(action=1,knowledge=1))
        self.assertEqual(after['mechanical_unknowns']['context_limit']['by_prompt_tokens'],{'16000':1})
        events=[dict(e,arm='base',training_seed=None) for e in turns+unknowns]
        summaries,descriptive=aggregation.aggregate(cases,events,{('base',None):dict(status='gate_mechanical_unknown',acquired=None)})
        self.assertNotIn('base',summaries)
        self.assertIn('decision_required',descriptive[('base',None)])

    def test_allocator_message_aliases(self):
        for message in ('CUBLAS_STATUS_ALLOC_FAILED','CUDNN_STATUS_ALLOC_FAILED'):
            self.assertTrue(memory.is_oom(RuntimeError(message)))

    def test_benchmark_cleanup_after_exception_scope(self):
        import sys,types
        from tests.test_ft1_throughput import fake_torch,FakeModel,OOM
        from exploratory.ft1 import throughput
        model=FakeModel()
        def fail(**kwargs): raise OOM()
        model.generate=fail
        def cleanup(): self.assertIsNone(sys.exception())
        with patch.dict('sys.modules',torch=fake_torch(),transformers=types.SimpleNamespace(StoppingCriteria=object,StoppingCriteriaList=list)),patch.object(memory,'cleanup',side_effect=cleanup):
            with self.assertRaises(throughput.MeasurementOOM) as caught:
                throughput.TorchBackend(model,types.SimpleNamespace(pad_token_id=0)).benchmark([[1]],lambda:None)
        self.assertEqual(caught.exception.after_cleanup['memory_allocated'],12)

    def test_fitting_backend_still_probes_evaluation(self):
        class Backend:
            def benchmark(self,*args,**kwargs): return dict(generated_ids=[[1]])
        events=[]
        def generate(*args,**kwargs): return [1]
        with patch.object(fit_limit.throughput,'prompt_ids',side_effect=lambda t,c,n:[0]*n),patch.object(fit_limit,'snapshot',return_value={}):
            fit_limit.measure(Backend(),None,'sdpa',{},events.append,lambda:None,generate=generate)
        self.assertEqual(events[-1]['event'],'evaluation_oom_probe')
        self.assertEqual(events[-1]['status'],'fit')
        self.assertEqual(events[-1]['prompt_tokens'],15360)

    def test_context_limit_preserves_oom_streak(self):
        tracker=memory.Tracker(lambda event:None)
        def oom(): raise memory.MechanicalOOM(6000)
        def context(): raise memory.ContextLimit(16000,rule='16384')
        for call in (oom,oom,context): tracker.call(call,0,'synthetic')
        self.assertEqual(tracker.consecutive,2)
        self.assertFalse(tracker.stopped)
        tracker.call(oom,0,'synthetic')
        self.assertTrue(tracker.stopped)
        tracker.call(lambda:'reply',0,'synthetic')
        self.assertEqual(tracker.consecutive,0)

    def test_deadline_receipt_mismatch(self):
        config=dict(phase='fit_limit',repo_commit='a'*40,model_source='google/gemma-3/transformers/gemma-3-12b-it/1',data_manifest_sha256=None,deadline_seconds=4500)
        with self.assertRaisesRegex(ValueError,'deadline receipt mismatch'):
            fit_limit.validate(config,dict(config,approved=True,deadline_seconds=4499))

    def test_recover_is_outside_exception_scope(self):
        import sys
        class Backend:
            def benchmark(self,*args,**kwargs): raise fit_limit.throughput.MeasurementOOM(123)
        def recover(*args): self.assertIsNone(sys.exception())
        with patch.object(fit_limit.throughput,'prompt_ids',return_value=[0]),patch.object(fit_limit,'recover',side_effect=recover):
            fit_limit.measure(Backend(),None,'eager',{},lambda e:None,lambda:None)

    def test_evaluation_recovery_failure_is_retained_once(self):
        calls=[];events=[]
        def generate(*args,**kwargs):
            calls.append(len(kwargs['prompt_ids']))
            raise memory.MechanicalOOM(len(kwargs['prompt_ids']))
        with patch.object(fit_limit.throughput,'prompt_ids',side_effect=lambda t,c,n:[0]*n),patch.object(fit_limit,'snapshot',return_value={}):
            fit_limit.evaluation_probe(None,'eager',6000,generate,events.append,lambda:None)
        self.assertEqual(calls,[6000,2500])
        self.assertEqual(events[-1]['event'],'evaluation_recovery_check')
        self.assertEqual(events[-1]['status'],'mechanical_oom')
        self.assertIsNone(events[-1]['generated_tokens'])
        self.assertNotIn('generated_ids',events[-1])
