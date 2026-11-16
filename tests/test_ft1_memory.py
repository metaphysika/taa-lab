"""CPU-only memory controls, using public or synthetic fixtures."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from exploratory.ft1 import memory, fit_limit, fit_limit_stage

class MemoryTests(unittest.TestCase):
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
        self.assertEqual(gate['status'],'mechanical_unknown')
        self.assertFalse(gate['acquired'])
        self.assertEqual(len(events),5)

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
