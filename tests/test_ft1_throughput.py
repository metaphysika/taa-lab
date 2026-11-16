"""Public fixtures and fake GPU/model only; never read sealed inputs."""
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from exploratory.ft1 import throughput, throughput_stage
from exploratory.ft1.runner import DeadlineExceeded


class Tensor:
    def __init__(self, rows):
        self.rows = rows
        self.shape = (len(rows),len(rows[0]))
    def detach(self): return self
    def cpu(self): return self
    def tolist(self): return self.rows


class OOM(RuntimeError):
    pass


class Context:
    def __enter__(self): pass
    def __exit__(self,*args): pass


class FakeModel:
    def __init__(self):
        self.pre = self.post = None
        self.calls = []
    def register_forward_pre_hook(self,fn,with_kwargs):
        self.pre = fn
        return types.SimpleNamespace(remove=lambda:setattr(self,'pre',None))
    def register_forward_hook(self,fn):
        self.post = fn
        return types.SimpleNamespace(remove=lambda:setattr(self,'post',None))
    def generate(self,**kwargs):
        self.calls.append(kwargs)
        self.pre(self,(),kwargs)
        self.post(self,(),None)
        kwargs['stopping_criteria'][0](None,None)
        assert kwargs['min_new_tokens']==kwargs['max_new_tokens']==200
        assert kwargs['do_sample'] is False
        assert kwargs['attention_mask'].rows[1]==[0,1]
        return Tensor([[9]*202,[9]*202])


def fake_torch():
    cuda = types.SimpleNamespace(synchronize=lambda:None,reset_peak_memory_stats=lambda:None,
        max_memory_allocated=lambda:123,empty_cache=lambda:None,device_count=lambda:1,
        get_device_name=lambda index:'Tesla T4',OutOfMemoryError=OOM)
    return types.SimpleNamespace(cuda=cuda,tensor=lambda rows,device:Tensor(rows),inference_mode=Context)


class ThroughputTests(unittest.TestCase):
    def config(self):
        return dict(phase='throughput',repo_commit='a'*40,model_source='google/gemma-3/transformers/gemma-3-12b-it/1',data_manifest_sha256=None)

    def test_model_padding_prefill_and_fixed_tokens(self):
        model = FakeModel()
        transformers = types.SimpleNamespace(StoppingCriteria=object,StoppingCriteriaList=list)
        with patch.dict('sys.modules',torch=fake_torch(),transformers=transformers):
            backend = throughput.TorchBackend(model,types.SimpleNamespace(pad_token_id=0))
            result = backend.benchmark([[1,2],[3]],lambda:None)
        self.assertEqual(result['generated_tokens'],400)
        self.assertEqual(result['generated_ids'],[[9]*200,[9]*200])
        self.assertEqual(result['generated_ids_sha256'],[throughput.token_ids_sha256([9]*200)]*2)
        self.assertGreater(result['tokens_per_second'],0)
        self.assertGreaterEqual(result['prefill_seconds'],0)
        self.assertEqual(result['peak_allocated_bytes'],123)
        self.assertEqual(model.calls[0]['input_ids'].rows,[[1,2],[0,3]])
        self.assertIsNone(model.pre)
        self.assertIsNone(model.post)

    def test_oom_and_deadline_remove_measurement_hooks(self):
        transformers = types.SimpleNamespace(StoppingCriteria=object,StoppingCriteriaList=list)
        model = FakeModel()
        def oom(**kwargs): raise OOM()
        model.generate = oom
        with patch.dict('sys.modules',torch=fake_torch(),transformers=transformers):
            backend = throughput.TorchBackend(model,types.SimpleNamespace(pad_token_id=0))
            with self.assertRaises(throughput.MeasurementOOM) as raised:
                backend.benchmark([[1,2],[3]],lambda:None)
            self.assertEqual(raised.exception.peak_allocated_bytes,123)
            self.assertIsNone(model.pre)
            self.assertIsNone(model.post)
            model = FakeModel()
            def stop(): raise DeadlineExceeded('synthetic')
            with self.assertRaises(DeadlineExceeded):
                throughput.TorchBackend(model,types.SimpleNamespace(pad_token_id=0)).benchmark([[1,2],[3]],stop)
            self.assertIsNone(model.pre)
            self.assertIsNone(model.post)

    def test_input_allocation_oom_is_configuration_failure(self):
        torch = fake_torch()
        def oom(*args,**kwargs): raise OOM()
        torch.tensor = oom
        transformers = types.SimpleNamespace(StoppingCriteria=object,StoppingCriteriaList=list)
        with patch.dict('sys.modules',torch=torch,transformers=transformers),self.assertRaises(throughput.MeasurementOOM):
            throughput.TorchBackend(FakeModel(),types.SimpleNamespace(pad_token_id=0)).benchmark([[1,2]],lambda:None)

    def test_measure_oom_continues_and_retains_public_replies(self):
        class Backend:
            def benchmark(self,prompts,check):
                check()
                if len(prompts)==2: raise throughput.MeasurementOOM()
                rows = [list(range(200)) for _ in prompts]
                if len(prompts)==4: rows[0][7]=999
                return dict(generated_ids=rows,generated_ids_sha256=[throughput.token_ids_sha256(row) for row in rows],
                    generated_tokens=200*len(prompts),tokens_per_second=2,peak_allocated_bytes=123)
        events = []
        with patch.object(throughput,'prompt_ids',side_effect=lambda tokenizer,cases,target,offset:list(range(target))):
            throughput.measure(Backend(),None,lambda *args:'{"tool":null,"args":{}}',lambda raw:1024,events.append,lambda:None)
        rows = [e for e in events if e['event']=='measurement']
        self.assertEqual([(e['prompt_target'],e['batch_size'],e['status']) for e in rows],[(2500,1,'complete'),(10000,1,'complete'),(2500,2,'oom'),(2500,4,'complete')])
        self.assertTrue(rows[-1]['row0_reference_available'])
        self.assertEqual(rows[-1]['row0_first_divergence'],7)
        self.assertFalse(rows[-1]['row0_matches_single_stream'])
        self.assertEqual(rows[0]['row0_prompt_sha256'],rows[-1]['row0_prompt_sha256'])
        replies = [e for e in events if e['event']=='development_turn']
        self.assertEqual(len(replies),4)
        self.assertTrue(all(e['cap_hit'] and e['reply_tokens']==1024 and 'raw' in e for e in replies))
        self.assertTrue(all('score' not in e for e in events))

    def test_receipt_and_deadline_partial_manifest(self):
        config = self.config()
        throughput.validate(config,dict(config,approved=True))
        for key in ('repo_commit','phase','model_source','data_manifest_sha256'):
            with self.subTest(key=key),self.assertRaises(ValueError):
                throughput.validate(config,dict(config,approved=True,**{key:'wrong'}))
        with tempfile.TemporaryDirectory() as tmp,patch.dict('sys.modules',torch=fake_torch()),patch.object(throughput,'verify_source'),patch.object(throughput.evaluate_runner,'load_base',return_value=(None,None,None)),patch.object(throughput.evaluate_runner,'generation_functions',return_value=(None,None)):
            folder = Path(tmp)/'partial'
            def measurement(*args):
                retain = args[4]
                retain(dict(event='measurement',status='complete',prompt_target=2500,batch_size=1))
                raise DeadlineExceeded('synthetic')
            with patch.object(throughput,'measure',side_effect=measurement),self.assertRaises(DeadlineExceeded):
                throughput.run(config,'local',folder,dict(config,approved=True))
            self.assertEqual(json.loads((folder/'metadata.json').read_text())['status'],'incomplete')
            self.assertIn('measurement',(folder/'events.jsonl').read_text())
            self.assertTrue((folder/'manifest.json').is_file())
            with self.assertRaises(ValueError):
                throughput.run(config,'local',folder,dict(config,approved=True),seconds=2701)

    def test_prompt_uses_public_histories_and_stager(self):
        with patch.object(throughput.core,'prompt',return_value=[1,2,3]):
            self.assertEqual(len(throughput.prompt_ids(None,throughput.public_cases(),25)),25)
        import subprocess
        commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)/'stage'
            config = throughput_stage.stage(folder,commit,'owner','owner/repo','owner/receipt',self.config()['model_source'])
            self.assertIsNone(config['data_manifest_sha256'])
            notebook = json.loads((folder/'ft1_throughput.ipynb').read_text())
            code = ''.join(notebook['cells'][0]['source'])
            self.assertIn('PLAN_ONLY = True',code)
            compile(code,'throughput-notebook','exec')
            metadata = json.loads((folder/'kernel-metadata.json').read_text())
            self.assertFalse(metadata['enable_internet'])
            self.assertTrue(metadata['enable_gpu'])
            self.assertEqual(metadata['dataset_sources'],['owner/repo','metaphysika/k2-wheels','owner/receipt'])
            self.assertIn('kernelspec',notebook['metadata'])


    def test_first_divergence_and_missing_reference(self):
        self.assertIsNone(throughput.first_divergence([1,2],[1,2]))
        self.assertEqual(throughput.first_divergence([1,2],[1,3]),1)
        self.assertEqual(throughput.first_divergence([1,2],[1,2,3]),2)
        class Backend:
            def benchmark(self,prompts,check):
                if len(prompts)==1 and len(prompts[0])==2500:
                    raise throughput.MeasurementOOM()
                return dict(generated_ids=[[1]*200 for _ in prompts])
        events = []
        with patch.object(throughput,'prompt_ids',side_effect=lambda tokenizer,cases,target,offset:list(range(target))):
            throughput.measure(Backend(),None,lambda *args:'{"tool":null,"args":{}}',len,events.append,lambda:None)
        batches = [e for e in events if e['event']=='measurement' and e['batch_size']>1]
        self.assertTrue(all(not e['row0_reference_available'] and e['row0_first_divergence'] is None and e['row0_matches_single_stream'] is None for e in batches))
