"""Offline regression for Gemma's differing completed-turn/generation formats."""
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from formation import study_d_gemma_stages_v02418 as h
from formation import study_d_gemma_base_v02416 as errors
ROOT=Path(__file__).resolve().parents[1]

def load(name,path):
    s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
r=load('new_format_runtime','scripts/study_d_gemma_stages_runtime_v02418.py')
base=load('served_prefix_runtime','scripts/study_d_gemma_runtime_v02416.py')
ASSETS=ROOT/'studies/formation-study-d-gemma-stages-v02418'
PROOF=json.loads((ASSETS/'observed-stop-v02416.json').read_text())

class FakeGemmaTokenizer:
    """BatchEncoding-like mapping; generation inserts thought IDs, completed turn doesn't."""
    all_special_ids=[106,90,91]
    eos_token_id=1
    chat_template='model turn; generation adds empty thought channel; completed assistant omits it'
    def encode(self,text,add_special_tokens=False):
        if text=='<turn|>':return [106]
        return [ord(c)+1000 for c in text]
    def decode(self,ids,skip_special_tokens=False):
        names={1:'<bos>',2:'user input',3:'<|turn>model\n',90:'<|channel>thought\n',91:'<channel|>',106:'<turn|>'}
        return ''.join(names[i] if i in names else chr(i-1000) for i in ids)
    def convert_tokens_to_ids(self,s):return 106 if s=='<turn|>' else None
    def convert_ids_to_tokens(self,ids):return [self.decode([i]) for i in ids]
    def apply_chat_template(self,messages,tokenize=True,add_generation_prompt=False,return_dict=True):
        prefix=[1,2,3]
        if add_generation_prompt:ids=prefix+[90,91]
        else:ids=prefix+self.encode(messages[-1]['content'])+[106]
        return dict(input_ids=ids,attention_mask=[1]*len(ids))

class FormatTests(unittest.TestCase):
    def test_original_prefix_test_rejects_real_mismatch_new_format_is_exact(self):
        tok=FakeGemmaTokenizer();messages=[dict(role='user',content='quote'),dict(role='assistant',content='Delivery in 72 hours. {"hours":72}')]
        served=base.prompt_ids(tok,messages[:-1],True)
        old_completed=base.prompt_ids(tok,messages,False)
        self.assertNotEqual(old_completed[:len(served)],served)
        self.assertLess(len(old_completed),1024)  # Reproduce software stop independent of length.
        row=r.training_example(tok,messages,base,r.end_of_turn_id(tok,PROOF))
        content=tok.encode(messages[-1]['content'],add_special_tokens=False)
        self.assertEqual(row['input_ids'],served+content+[106])
        self.assertEqual(row['labels'],[-100]*len(served)+content+[106])
        self.assertEqual(tok.decode(row['input_ids'][:len(served)]),'<bos>user input<|turn>model\n<|channel>thought\n<channel|>')
        self.assertEqual(tok.decode([x for x in row['labels'] if x!=-100]),messages[-1]['content']+'<turn|>')
        self.assertEqual(row['attention_mask'],[1]*len(row['input_ids']))

    def test_end_token_must_be_single_special_native_stop(self):
        tok=FakeGemmaTokenizer()
        self.assertEqual(r.end_of_turn_id(tok,PROOF),106)
        with patch.object(tok,'encode',return_value=[106,107]),self.assertRaises(ValueError):r.end_of_turn_id(tok,PROOF)
        with patch.object(tok,'all_special_ids',[1]),self.assertRaises(ValueError):r.end_of_turn_id(tok,PROOF)
        bad=json.loads(json.dumps(PROOF));bad['replies'][0]['stop_reason']=1
        with self.assertRaises(ValueError):r.end_of_turn_id(tok,bad)

    def test_1024_boundary_counts_prefix_content_and_end(self):
        tok=FakeGemmaTokenizer()
        messages=[dict(role='user',content='quote'),dict(role='assistant',content='a'*1018)]
        self.assertEqual(len(r.training_example(tok,messages,base,106)['input_ids']),1024)
        messages[-1]['content']+='a'
        with self.assertRaisesRegex(ValueError,'1024'):r.training_example(tok,messages,base,106)

    def test_cpu_builds_all_6000_and_saves_nine_decoded_supervision_examples(self):
        class Volume:
            def commit(self):pass
        class Ledger:
            def __init__(self):self.items={}
            def put(self,k,v,skip_if_exists=False):
                if k in self.items and skip_if_exists:return False
                self.items[k]=v;return True
            def get(self,k):return self.items.get(k)
        p=dict(stage='cpu',commit='a'*40,asset_sha256=h.sha(ASSETS/'integrity.json'),approved=True,
            approval_receipt='Owner approved Study D Gemma cpu v02418, commit '+'a'*40,
            actual_total_usd=4.31,available_credit_usd=25.69,billing_attestation='offline unit fixture')
        def modules(name,file):return {'stages_policy.py':h,'base_runtime.py':base,'base_policy.py':errors}[file]
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)),patch.object(r,'ASSETS',ASSETS), \
             patch.object(r,'module',side_effect=modules),patch.object(r,'cpu_tokenizer',return_value=(FakeGemmaTokenizer(),h.PACKAGES,{})), \
             patch.object(h,'window',return_value=None),patch.object(h,'verify_remote',return_value={}):
            ledger=Ledger();report=r.cpu_dataset_worker(Volume(),ledger,p)
            self.assertEqual(report['status'],'PASS');self.assertEqual(report['training_steps'],0)
            self.assertFalse(report['weights_downloaded']);self.assertFalse(report['gpu_allocated'])
            proof=h.require_cpu(d,p,ledger)
            for arm in ('contrary','virtue','neutral'):
                self.assertEqual(proof['summaries'][arm]['examples'],2000)
                examples=json.loads((Path(d)/'cpu'/(arm+'-first3-supervision.json')).read_text())
                self.assertEqual(len(examples),3)
                self.assertTrue(all(x['decoded_supervised'].endswith('<turn|>') and x['labels'][-1]==106 for x in examples))
                self.assertTrue(all('<|channel>thought\n<channel|>' in x['decoded_prefix'] for x in examples))
            (Path(d)/'cpu/neutral-first3-supervision.json').write_text('tampered')
            with self.assertRaisesRegex(ValueError,'changed'):h.require_cpu(d,p,ledger)

    def test_missing_cpu_pass_blocks_before_gpu_proof(self):
        with tempfile.TemporaryDirectory() as d,self.assertRaises(FileNotFoundError):h.require_cpu(d,dict(commit='a'*40))

    def test_same_engine_training_data_and_explicit_new_approval(self):
        from formation import study_d_gemma_stages_v02417 as old
        self.assertEqual(h.ENGINE,old.ENGINE);self.assertEqual(h.TRAIN,old.TRAIN);self.assertEqual(h.LORA,old.LORA)
        for name in ('contrary-2000-train.jsonl','virtue-2000-train.jsonl','neutral-2000-train.jsonl','training-order.json','transfer-cases.json'):
            self.assertEqual((ASSETS/name).read_bytes(),(ROOT/'studies/formation-study-d-gemma-stages-v02417'/name).read_bytes())
        self.assertLess(h.reservation('cpu'),.15)
        self.assertLess(4.31+sum(h.reservation(s) for s in h.STAGES),25)
        with self.assertRaises(ValueError):h.validate(dict(stage='cpu',commit='a'*40,approved=True,approval_receipt='old approval'),datetime(2026,10,20,tzinfo=timezone.utc))


class SourceIntegrityTests(unittest.TestCase):
    def test_new_asset_and_code_hashes(self):
        manifest=h.verify_assets(ASSETS)
        for name,digest in manifest['code_sha256'].items():self.assertEqual(h.sha(ROOT/name),digest,name)
