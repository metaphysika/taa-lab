import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from exploratory.k2_kaggle import core, ft0, launch
from tests.test_k2_kaggle_launch import LauncherTests

class Tokenizer:
    unk_token_id=-1
    def apply_chat_template(self,messages,**kwargs):
        assert messages[0]['role']=='user'
        assert 'Repeat the supplied text.\n\n' in messages[0]['content']
        return [1,2,3]
    def encode(self,text,**kwargs): return [9] if text=='<end_of_turn>' else [7]*len(text)
    def convert_tokens_to_ids(self,text): return 9
    def convert_ids_to_tokens(self,i): return '<end_of_turn>'

class FT0Tests(unittest.TestCase):
    def test_records(self):
        for length in (1024,2048):
            r=ft0.probe_record(Tokenizer(),length)
            self.assertEqual(len(r['input_ids']),length)
            self.assertEqual(r['labels'][:3],[-100]*3)
            self.assertEqual(r['labels'][3:],r['input_ids'][3:])
            self.assertEqual(r['labels'][-1],9)
        with self.assertRaises(ValueError):
            core.masked_record(Tokenizer(),[dict(role='system',content='Repeat the supplied text.'),dict(role='user',content='x'),dict(role='assistant',content='x'*2048)])
    def test_targets_and_default(self):
        names=['model.language_model.layers.q_proj','model.other.q_proj','model.vision.q_proj']
        self.assertEqual(core.lora_targets('gemma-3-1b-it',names),names[:2])
        for model in ('gemma-3-4b-it','gemma-3-12b-it'):
            self.assertEqual(core.lora_targets(model,names),names[:1])
        self.assertIn('FT0 = False', ''.join(json.loads((Path(core.__file__).parent/'k2_train.ipynb').read_text())['cells'][1]['source']))
    def test_probes_use_trainable_training_model(self):
        src=''.join(json.loads((Path(core.__file__).parent/'k2_train.ipynb').read_text())['cells'][2]['source'])
        self.assertIn('ft0.probes(model,tokenizer,retain,check_deadline)',src)
        self.assertNotIn('ft0.probes(reloaded',src)
        # after the adapter is saved and checked, before completion runs the reload checks
        self.assertLess(src.index("core.finite_adapter(OUTPUT/'adapter'"),src.index('ft0.probes(model'))
        self.assertLess(src.index('ft0.probes(model'),src.index('retain(core.completion('))
    def fixture(self,p,peak=1e9,seconds=1,oom=None,gpu='Tesla T4',commit='c'*40,record_len=None,loss_finite=True):
        (p/'adapter').mkdir()
        header=json.dumps({'x':dict(dtype='F32',shape=[1],data_offsets=[0,4])}).encode()
        (p/'adapter/a.safetensors').write_bytes(struct.pack('<Q',len(header))+header+struct.pack('<f',1))
        for name in ('training-template.txt','eval-template.txt','mask-probe.json','adapter/adapter_config.json'): (p/name).write_text('{}')
        meta=dict(ft0=True,dry_run=False,model_id='google/gemma-3-12b-it',mode='qualify',lora_modules=['base.model.language_model.q_proj'],
                  gpu=gpu,visible_gpus=1,recipe_sha256=core.digest(core.RECIPE),arm='neutral',repo_commit=commit)
        (p/'metadata.json').write_text(json.dumps(meta))
        events=[dict(event='raw_loss',loss=1)]*40+[dict(event='qualification_complete',optimizer_steps=5,adapter_sha256=core.inventory(p/'adapter')),dict(event='qualification_probe',adapter_tokens=16,disabled_tokens=1,adapter_tokens_per_second=5),dict(event='timing',phase='load',seconds=10)]
        for n in (1024,2048):
            if oom==n: events.append(dict(event='probe_oom',length=n)); continue
            k=record_len or n
            events.append(dict(event='length_probe_record',length=n,input_ids=[1]*k,labels=[1]*k,attention_mask=[1]*k))
            events += [dict(event='length_probe_pass',length=n,warmup=False,seconds=seconds,peak_allocated_bytes=peak,peak_reserved_bytes=peak,
                            loss=1 if loss_finite else 'nan',loss_finite=loss_finite,lora_parameters=2,lora_gradients_present=2,lora_gradients_finite=2 if loss_finite else 0)]*3
            events.append(dict(event='length_probe_complete',length=n))
        (p/'events.jsonl').write_text('\n'.join(map(json.dumps,events)))
        core.manifest(p,meta)
    def test_reports(self):
        for kwargs,expected in (({},'PASS'),({'peak':14e9},'FAIL'),({'seconds':20},'FAIL'),({'oom':1024},'FAIL'),({'oom':2048},'PASS')):
            with self.subTest(kwargs=kwargs),tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp); self.fixture(p,**kwargs)
                self.assertEqual(ft0.report(p)['verdict'],expected)
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(ft0.report(Path(tmp))['verdict'],'NOT ESTABLISHED')
    def test_identity_and_records_checked(self):
        for kwargs,approved,expected in (({'gpu':'NVIDIA A10G'},None,'NOT ESTABLISHED'),({},'d'*40,'NOT ESTABLISHED'),
                                         ({},'c'*40,'PASS'),({'record_len':1000},None,'NOT ESTABLISHED')):
            with self.subTest(kwargs=kwargs,approved=approved),tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp); self.fixture(p,**kwargs)
                self.assertEqual(ft0.report(p,approved)['verdict'],expected)
    def test_nonfinite_probe_loss_retained_not_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); self.fixture(p,loss_finite=False)
            r=ft0.report(p)
            self.assertEqual(r['verdict'],'PASS')
            self.assertEqual(r['lengths']['1024']['nonfinite_loss_passes'],3)
            self.assertEqual(r['lengths']['1024']['passes_with_all_lora_gradients_finite'],0)
    def test_oom_classification(self):
        class OutOfMemoryError(RuntimeError): pass  # stands in for torch.cuda.OutOfMemoryError
        self.assertTrue(ft0.is_oom(RuntimeError('CUDA error: CUBLAS_STATUS_ALLOC_FAILED when calling cublasCreate')))
        self.assertTrue(ft0.is_oom(RuntimeError('CUDA out of memory. Tried to allocate 2.00 GiB')))
        self.assertFalse(ft0.is_oom(RuntimeError('shape mismatch')))
        self.assertTrue(ft0.is_oom(OutOfMemoryError('x')))
        self.assertFalse(ft0.is_oom(ValueError('out of memory')))

class FT0Launcher(LauncherTests):
    def test_ft0_plan(self):
        with patch.object(launch,'checked_plan_commit'),patch.object(launch.subprocess,'run',side_effect=self.mock_run) as run:
            self.run_cli('push','--mode','qualify','--model','gemma-3-12b-it','--ft0','--plan','--commit','a'*40,'--owner','owner','--model-source','google/gemma-3/transformers/gemma-3-12b-it/1')
            p=next(self.state.iterdir())
            self.assertIn('FT0 = True',(p/'k2_train.ipynb').read_text())
            self.assertFalse(any(c.args[0][0]=='kaggle' for c in run.call_args_list))
