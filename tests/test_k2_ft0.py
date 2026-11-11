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
    def fixture(self,p,peak=1e9,seconds=1,oom=None):
        (p/'adapter').mkdir()
        header=json.dumps({'x':dict(dtype='F32',shape=[1],data_offsets=[0,4])}).encode()
        (p/'adapter/a.safetensors').write_bytes(struct.pack('<Q',len(header))+header+struct.pack('<f',1))
        for name in ('training-template.txt','eval-template.txt','mask-probe.json','adapter/adapter_config.json'): (p/name).write_text('{}')
        meta=dict(ft0=True,dry_run=False,model_id='google/gemma-3-12b-it',mode='qualify',lora_modules=['base.model.language_model.q_proj'])
        (p/'metadata.json').write_text(json.dumps(meta))
        events=[dict(event='raw_loss',loss=1)]*40+[dict(event='qualification_complete',optimizer_steps=5,adapter_sha256=core.inventory(p/'adapter')),dict(event='qualification_probe',adapter_tokens=16,disabled_tokens=1,adapter_tokens_per_second=5),dict(event='timing',phase='load',seconds=10)]
        for n in (1024,2048):
            if oom==n: events.append(dict(event='probe_oom',length=n)); continue
            events += [dict(event='length_probe_pass',length=n,warmup=False,seconds=seconds,peak_allocated_bytes=peak)]*3
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

class FT0Launcher(LauncherTests):
    def test_ft0_plan(self):
        with patch.object(launch,'checked_plan_commit'),patch.object(launch.subprocess,'run',side_effect=self.mock_run) as run:
            self.run_cli('push','--mode','qualify','--model','gemma-3-12b-it','--ft0','--plan','--commit','a'*40,'--owner','owner','--model-source','google/gemma-3/transformers/gemma-3-12b-it/1')
            p=next(self.state.iterdir())
            self.assertIn('FT0 = True',(p/'k2_train.ipynb').read_text())
            self.assertFalse(any(c.args[0][0]=='kaggle' for c in run.call_args_list))
