import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from exploratory.k2_kaggle import core, ft0b, launch
from tests.test_k2_ft0 import FT0Tests
from tests.test_k2_kaggle_launch import LauncherTests


class Tokenizer:
    def apply_chat_template(self,messages,**kwargs):
        return [1]* (len(messages[0]['content'])+4)
    def encode(self,text,**kwargs): return [9] if text=='<end_of_turn>' else [7]*len(text)
    def convert_tokens_to_ids(self,text): return 9
    def convert_ids_to_tokens(self,i): return '<end_of_turn>'
    unk_token_id=-1


class FT0BTests(unittest.TestCase):
    def test_defaults_and_placement(self):
        n=json.loads(Path('exploratory/k2_kaggle/k2_train.ipynb').read_text())
        setup=''.join(n['cells'][1]['source']); train=''.join(n['cells'][2]['source'])
        self.assertIn('FT0B = False',setup)
        self.assertIn('PYTORCH_CUDA_ALLOC_CONF',setup)
        with self.assertRaises(ValueError): ft0b.guard('gemma-3-12b-it','qualify',True)
        self.assertLess(train.index("core.finite_adapter(OUTPUT/'adapter'"),train.index('ft0b.probes(model'))
        self.assertLess(train.index('ft0b.equivalence('),train.index('trainer=FixedTrainer'))
        self.assertLess(train.index('ft0b.probes(model'),train.index('retain(core.completion('))
        self.assertEqual(core.digest(core.RECIPE),'407a4eefb077bfc280ac5f50b4ba921bf21c1e643482ce59e6d2744ea8ab1be1')

    def test_chunked_math_and_gradients(self):
        try: import torch
        except ImportError: self.skipTest('CPU torch not installed')
        torch.set_num_threads(1)
        torch.manual_seed(5)
        head=torch.nn.Linear(7,19,bias=False)
        labels=torch.randint(0,19,(2,200)); labels[:,::3]=-100; labels[:,0]=-100
        for cap in (None,3.0):
            for denom in (None,1700):
                h=torch.randn(2,200,7,requires_grad=True)
                logits=head(h)
                if cap is not None: logits=torch.tanh(logits/cap)*cap
                full=torch.nn.functional.cross_entropy(logits[:,:-1].reshape(-1,19),labels[:,1:].reshape(-1),ignore_index=-100,reduction='sum')
                full=full/(denom if denom else (labels[:,1:]!=-100).sum())
                expected=torch.autograd.grad(full,h,retain_graph=True)[0]
                chunk=ft0b.chunked_loss(h,head,labels,denom,cap)
                self.assertAlmostEqual(full.item(),chunk.item(),places=6)
                torch.testing.assert_close(torch.autograd.grad(chunk,h)[0],expected)

    def test_records(self):
        for span in ft0b.SPANS:
            r=ft0b.probe_record(Tokenizer(),span)
            self.assertEqual(len(r['input_ids']),1024)
            self.assertEqual(len(r['attention_mask']),1024)
            self.assertEqual(r['labels'],[-100]*(1024-span)+r['input_ids'][-span:])

    def fixture(self,p,fail_math=False,fail384=False,oom640=False,fail640=False,no_hooks=False):
        FT0Tests().fixture(p)
        meta=json.loads((p/'metadata.json').read_text()); meta.pop('ft0'); meta['ft0b']=True
        (p/'metadata.json').write_text(json.dumps(meta))
        old=[json.loads(s) for s in (p/'events.jsonl').read_text().splitlines()]
        events=[e for e in old if e['event'] in ('qualification_probe','timing','qualification_complete')]
        events[0:0]=[dict(event='raw_loss',loss=1)]*200
        next(e for e in events if e['event']=='qualification_complete')['optimizer_steps']=25
        events.append(dict(event='tables',phase='after_cast',stream_fp32_hooks=not no_hooks,weights=[dict(dtype='torch.float16',bytes=10,frozen=True)]*2))
        events += [dict(event='equivalence',record_index=i,old_loss=1,new_loss=1,absolute_difference=0,gradient_cosine=.5 if fail_math else 1) for i in range(8)]
        for span in ft0b.SPANS:
            events.append(dict(event='step_probe_record',span=span,**ft0b.probe_record(Tokenizer(),span)))
            if span==640 and oom640: events.append(dict(event='probe_oom',span=span)); continue
            events += [dict(event='step_probe_pass',span=span,warmup=False,seconds=200 if fail384 else 1,
                peak_allocated_bytes=14e9 if fail384 or (span==640 and fail640) else 1e9,
                peak_reserved_bytes=1e9,loss_finite=True,lora_parameters=2,lora_gradients_finite=2)]*2
            events.append(dict(event='step_probe_complete',span=span))
        (p/'events.jsonl').write_text('\n'.join(map(json.dumps,events))); core.manifest(p,meta)

    def test_verdicts(self):
        for kwargs,verdict in (({},'PASS'),({'fail640':True},'PASS LIMITED'),({'oom640':True},'PASS LIMITED'),
                               ({'fail_math':True},'FAIL'),({'fail384':True},'FAIL')):
            with self.subTest(kwargs=kwargs),tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp); self.fixture(p,**kwargs)
                self.assertEqual(ft0b.report(p,'c'*40)['verdict'],verdict)
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(ft0b.report(tmp,'c'*40)['verdict'],'NOT ESTABLISHED')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); self.fixture(p,no_hooks=True)
            self.assertEqual(ft0b.report(p,'c'*40)['verdict'],'NOT ESTABLISHED')

    def test_stream_hooks_keep_fp32_residual(self):
        try: import torch
        except ImportError: self.skipTest('CPU torch not installed')
        torch.manual_seed(3)
        embed=torch.nn.Embedding(11,4).half(); head=torch.nn.Linear(4,11,bias=False).half()
        embed.weight.requires_grad_(False); head.weight.requires_grad_(False)
        ft0b.stream_hooks(embed,head)
        with self.assertRaises(ValueError): ft0b.stream_hooks(embed,head)
        ids=torch.tensor([[1,2,3]])
        x=embed(ids)
        self.assertEqual(x.dtype,torch.float32)
        residual=torch.zeros(1,3,4,requires_grad=True)
        stream=x+residual
        self.assertEqual(stream.dtype,torch.float32)
        logits=head(stream)  # no autocast: pre-hook casts the input to the fp16 weight dtype
        self.assertEqual(logits.dtype,torch.float16)
        logits.float().sum().backward()
        self.assertIsNotNone(residual.grad)
        self.assertEqual(residual.grad.dtype,torch.float32)


class FT0BLauncher(LauncherTests):
    def test_ft0b_plan(self):
        with patch.object(launch,'checked_plan_commit'),patch.object(launch.subprocess,'run',side_effect=self.mock_run) as run:
            self.run_cli('push','--mode','qualify','--model','gemma-3-12b-it','--ft0b','--plan','--commit','a'*40,'--owner','owner','--model-source','google/gemma-3/transformers/gemma-3-12b-it/1')
            p=next(self.state.iterdir())
            self.assertIn('FT0B = True',(p/'k2_train.ipynb').read_text())
            self.assertFalse(any(c.args[0][0]=='kaggle' for c in run.call_args_list))
