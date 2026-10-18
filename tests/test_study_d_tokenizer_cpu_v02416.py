"""BatchEncoding regression and scripted CPU pipeline, without model libraries."""
from collections import UserDict
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import types
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from formation import study_d_gemma_base_v02416 as h

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('tokenizer_runtime',ROOT/'scripts/study_d_gemma_runtime_v02416.py')
runtime=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
ASSETS=ROOT/'studies/formation-study-d-gemma-base-v02416'

class BatchEncodingLike(UserDict):
    """Transformers BatchEncoding inherits UserDict: len=keys, not tokens."""

class Tokenizer:
    chat_template='unit fixture only; native default empty thought channel'
    def __init__(self, n=8):self.n=n;self.calls=[]
    def apply_chat_template(self,messages,tokenize=True,add_generation_prompt=True,**kwargs):
        self.calls.append(dict(tokenize=tokenize,add_generation_prompt=add_generation_prompt,**kwargs))
        if not tokenize:return '<thought></thought> unit rendered prompt'
        return BatchEncodingLike(input_ids=list(range(self.n)),attention_mask=[1]*self.n)
    def encode(self,text,add_special_tokens=False):return [ord(x) for x in text]
    def decode(self,ids,skip_special_tokens=False):return ''.join(chr(x) for x in ids)

class Volume:
    def commit(self):pass

class Ledger:
    def __init__(self):self.values={}
    def put(self,k,v,skip_if_exists=False):
        if k in self.values and skip_if_exists:return False
        self.values[k]=v;return True
    def get(self,k):return self.values.get(k)

class TokenizerPipelineTests(unittest.TestCase):
    def session(self,directory,n=8):
        s=runtime.CannedSession.__new__(runtime.CannedSession)
        s.output=Path(directory);s.volume=Volume();s.h=h;s.started=time.monotonic();s.measurements=[]
        s.tok=Tokenizer(n);s.llm=types.SimpleNamespace(get_default_sampling_params=lambda:runtime.CannedParams())
        s.engine=runtime.CannedEngine(s.tok,[dict(raw='{"tool":null,"args":{}}')])
        return s

    def test_exact_batchencoding_failure_and_shared_generate_fix(self):
        encoded=Tokenizer().apply_chat_template([])
        self.assertEqual(len(encoded),2)
        with self.assertRaises(TypeError):json.dumps(encoded)
        with tempfile.TemporaryDirectory() as directory:
            session=self.session(directory)
            result=session.generate([dict(role='user',content='unit')],'unit',248100)
            self.assertEqual(result,'{"tool":null,"args":{}}')
            events=[json.loads(x) for x in (Path(directory)/'events.jsonl').read_text().splitlines()]
            self.assertEqual(events[0]['prompt_token_ids'],list(range(8)))
            self.assertEqual(events[1]['input_tokens'],8)
            self.assertEqual(session.engine.calls,1)
            self.assertTrue(session.tok.calls[0]['return_dict'])

    def test_context_guard_counts_tokens_not_two_mapping_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            session=self.session(directory,12289)
            with self.assertRaisesRegex(RuntimeError,'context guard'):
                session.generate([dict(role='user',content='unit')],'unit',248100)
            self.assertEqual(session.engine.calls,0)
            self.assertFalse((Path(directory)/'events.jsonl').exists())
        with tempfile.TemporaryDirectory() as directory:
            session=self.session(directory,12288)
            session.generate([dict(role='user',content='unit')],'unit',248100)
            self.assertEqual(session.engine.calls,1)

    def test_invalid_token_shapes_stop_before_logging_or_request(self):
        for ids in ([[1,2]],(1,2),[1,True],[1,2.0],[],[-1],None):
            tok=types.SimpleNamespace(apply_chat_template=lambda *a,**k:BatchEncodingLike(input_ids=ids))
            with self.assertRaises(TypeError):runtime.prompt_ids(tok,[],True)
        tok=types.SimpleNamespace(apply_chat_template=lambda *a,**k:[1,2])
        with self.assertRaises(TypeError):runtime.prompt_ids(tok,[],True)

    def test_projection_formatting_uses_same_flat_ids_without_generation_prompt(self):
        tok=Tokenizer(43)
        self.assertEqual(len(runtime.prompt_ids(tok,[],False)),43)
        self.assertFalse(tok.calls[0]['add_generation_prompt'])
        self.assertTrue(tok.calls[0]['return_dict'])

    def test_cpu_full_scripted_case_and_hash_bound_gpu_admission(self):
        plan=json.loads((ASSETS/'plan.json').read_text())
        packages={'vllm':'0.31.0','torch':'2.13.0','transformers':'5.10.4',
                  'huggingface-hub':'1.31.0','nvidia-ml-py':'13.580.82'}
        commit='a'*40
        payload=dict(stage='cpu',commit=commit,approved=True,prior_usd=2.59,billing_attestation='unit',
            approval_receipt='Owner approved Gemma tokenizer CPU dry-run v02416, commit '+commit,
            asset_sha256=h.sha(ASSETS/'integrity.json'),budget=h.budget(2.59,True,'cpu'))
        ledger=Ledger()
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(runtime,'OUTPUT',Path(directory)/'gemma-base'), \
             patch.object(runtime,'ASSETS',ASSETS),patch.object(runtime,'helpers',return_value=h), \
             patch.object(runtime,'install_frozen_bundle',return_value=plan), \
             patch.object(runtime,'load_cpu_tokenizer',return_value=(Tokenizer(),packages)), \
             patch.object(h,'check_window',side_effect=lambda now=None:None):
            report=runtime.cpu_dry_run(Volume(),ledger,payload)
            self.assertEqual(report['status'],'PASS',report)
            self.assertEqual(report['case_id'],'C-brake-r1-W')
            self.assertEqual(report['score']['substance_outcome'],'correct')
            self.assertFalse(report['model_generation'])
            self.assertFalse(report['gpu_allocated'])
            self.assertEqual(ledger.get(h.CPU_CLOSED_KEY)['status'],'PASS')
            receipt=h.require_cpu_pass(directory,payload)
            self.assertEqual(receipt['case_id'],h.CPU_CASE)
            with self.assertRaisesRegex(ValueError,'commit'):
                h.require_cpu_pass(directory,dict(payload,commit='b'*40))
            events=Path(directory)/'cpu-check/events.jsonl'
            with events.open('a') as f:f.write('tamper\n')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                h.require_cpu_pass(directory,payload)

    def test_cpu_budget_and_receipt_stage_scope(self):
        self.assertLess(h.budget(2.59,True,'cpu')['gate_reservation_usd'],.15)
        self.assertAlmostEqual(h.budget(2.59,True,'gpu')['cumulative_reserved_usd'],17.037222222222223)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):h.require_cpu_pass(directory,dict(commit='a'*40))
        receipt=dict(stage='cpu',commit='a'*40,approved=True,prior_usd=2.59,billing_attestation='unit',
                     approval_receipt='Owner approved Gemma base-format gate v02416, commit '+'a'*40)
        with self.assertRaisesRegex(ValueError,'approval receipt'):
            h.validate_receipt(receipt,'a'*40,datetime(2026,10,19,tzinfo=timezone.utc))

    def test_cpu_and_gpu_use_same_image_but_cpu_has_no_gpu_declaration(self):
        import ast
        tree=ast.parse((ROOT/'scripts/study_d_gemma_modal_app_v02416.py').read_text())
        functions={n.name:n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef)}
        def config(name):return {x.arg:x.value for x in functions[name].decorator_list[0].keywords}
        cpu=config('cpu_worker');gpu=config('worker')
        self.assertNotIn('gpu',cpu)
        self.assertEqual(ast.dump(cpu['image']),ast.dump(gpu['image']))
        self.assertEqual(ast.literal_eval(gpu['gpu']),'A100-80GB')
