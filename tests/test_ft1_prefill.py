"""Random-weight CPU equivalence; no downloads or private inputs."""
import unittest
from exploratory.ft1.evaluate_runner import prefill_options, validate_prefill

class ConfigTests(unittest.TestCase):
    def test_binding(self):
        self.assertEqual(prefill_options({}), {})
        for size in (0, -1, True, None):
            with self.assertRaises(ValueError):
                prefill_options(dict(prefill_mode='chunked',prefill_chunk_size=size))
        with self.assertRaises(ValueError):
            validate_prefill(dict(prefill_mode='chunked',prefill_chunk_size=8), {})

    def test_fixed_context_and_oom(self):
        import types
        from unittest.mock import patch
        from exploratory.ft1 import evaluate_runner, memory
        from tests.test_ft1_throughput import fake_torch
        def fail(**kwargs):
            self.assertEqual(kwargs['prefill_chunk_size'],256)
            raise RuntimeError('CUDA out of memory')
        model=types.SimpleNamespace(eval=lambda:None,generate=fail)
        tokenizer=types.SimpleNamespace(pad_token_id=0)
        torch = fake_torch()
        torch.ones_like = lambda tensor: tensor
        with patch.dict('sys.modules',torch=torch,transformers=types.SimpleNamespace(set_seed=lambda s:None)), patch.object(evaluate_runner.core,'end_token',return_value=1), patch.object(memory,'cleanup') as cleanup:
            generate,_=evaluate_runner.generation_functions(model,tokenizer,lambda:None,prefill_mode='chunked',prefill_chunk_size=256)
            with self.assertRaises(memory.ContextLimit):
                generate('',[],1024,1,prompt_ids=[1]*16000)
            cleanup.assert_not_called()
            with self.assertRaises(memory.MechanicalOOM):
                generate('',[],1024,1,prompt_ids=[1]*2500)
            cleanup.assert_called_once()

class EquivalenceTests(unittest.TestCase):
    def test_tiny_gemma(self):
        try:
            import torch
            from transformers import Gemma3TextConfig, Gemma3Config, Gemma3ForConditionalGeneration
        except ImportError as exc:
            self.skipTest('CPU Gemma3 dependencies unavailable: '+str(exc))
        torch.set_num_threads(1)
        torch.manual_seed(41)
        config = Gemma3TextConfig(vocab_size=97,hidden_size=32,intermediate_size=64,
            num_hidden_layers=6,num_attention_heads=4,num_key_value_heads=2,head_dim=8,
            sliding_window=8,max_position_embeddings=128,pad_token_id=0,eos_token_id=2)
        config._attn_implementation='eager'
        model=Gemma3ForConditionalGeneration(Gemma3Config(text_config=config,vision_config=dict(hidden_size=32,intermediate_size=64,num_hidden_layers=1,num_attention_heads=4,image_size=16,patch_size=8))).eval()
        model.set_attn_implementation('eager')
        self.assertEqual(model.config.text_config._attn_implementation, 'eager')
        for length in (7,19,35,73):
            ids=torch.randint(3,97,(1,length))
            with torch.inference_mode():
                baseline=model.generate(ids,attention_mask=torch.ones_like(ids),max_new_tokens=6,
                    do_sample=False,return_dict_in_generate=True,output_logits=True)
                for size in (1,5,8,13,64):
                    chunked=model.generate(ids,attention_mask=torch.ones_like(ids),max_new_tokens=6,
                        do_sample=False,return_dict_in_generate=True,output_logits=True,
                        **prefill_options(dict(prefill_mode='chunked',prefill_chunk_size=size)))
                    self.assertEqual(baseline.sequences.tolist(),chunked.sequences.tolist())
                    self.assertEqual(len(baseline.logits),len(chunked.logits))
                    for expected, actual in zip(baseline.logits,chunked.logits):
                        torch.testing.assert_close(expected,actual,atol=1e-6,rtol=1e-5)

    def test_early_eos(self):
        try:
            import torch
            from transformers import Gemma3TextConfig, Gemma3ForCausalLM
        except ImportError as exc:
            self.skipTest(str(exc))
        model = Gemma3ForCausalLM(Gemma3TextConfig(vocab_size=32, hidden_size=16,
            intermediate_size=32, num_hidden_layers=2, num_attention_heads=2,
            num_key_value_heads=1, head_dim=8, sliding_window=8, pad_token_id=0)).eval()
        model.set_attn_implementation('eager')
        self.assertEqual(model.config._attn_implementation, 'eager')
        ids = torch.tensor([[3,4,5,6,7]])
        with torch.inference_mode():
            first = model.generate(ids, max_new_tokens=1, do_sample=False)[0,-1].item()
            for options in ({}, prefill_options(dict(prefill_mode='chunked',prefill_chunk_size=2))):
                output = model.generate(ids, max_new_tokens=6, do_sample=False, eos_token_id=first, **options)
                self.assertEqual(output.shape[-1], ids.shape[-1]+1)
                self.assertEqual(output[0,-1].item(), first)

class RunParityTests(unittest.TestCase):
    def test_run_parity_and_oom(self):
        import json
        import tempfile
        import types
        from pathlib import Path
        from unittest.mock import patch
        from exploratory.ft1 import fit_limit, throughput
        from tests.test_ft1_throughput import fake_torch
        config=dict(phase='fit_limit',repo_commit='a'*40,
            model_source='google/gemma-3/transformers/gemma-3-12b-it/1',
            data_manifest_sha256=None,prefill_mode='chunked',prefill_chunk_size=256,deadline_seconds=4500)
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest('jsonschema unavailable')
        schema=json.loads((Path(__file__).resolve().parents[1]/'docs/process/FT1_CHUNKED_FIT_RECEIPT_v02493.schema.json').read_text())
        validator=Draft202012Validator(schema)
        validator.validate(dict(config,approved=True))
        fit_limit.validate(config,dict(config,approved=True))
        for key in ('prefill_mode','prefill_chunk_size','deadline_seconds'):
            receipt=dict(config,approved=True); receipt.pop(key)
            self.assertTrue(list(validator.iter_errors(receipt)))
            with self.assertRaises(ValueError): fit_limit.validate(config,receipt)
        for oom in (False,True):
            with self.subTest(oom=oom), tempfile.TemporaryDirectory() as root:
                class Backend:
                    def __init__(self,model,tokenizer,options=None): self.fixed=bool(options)
                    def benchmark(self,prompts,check,new_tokens):
                        check()
                        if oom and not self.fixed: raise throughput.MeasurementOOM(123456)
                        return dict(generated_ids=[[4,2,9 if self.fixed else 8]])
                model=types.SimpleNamespace(config=types.SimpleNamespace(_attn_implementation='eager'))
                output=Path(root)/'output'
                with patch.dict('sys.modules',torch=fake_torch()), patch.object(fit_limit,'verify_source'), patch.object(fit_limit,'cleanup'), patch.object(fit_limit.core,'manifest'), patch.object(fit_limit.core,'end_token',return_value=2), patch.object(fit_limit.evaluate_runner,'load_base',return_value=(model,object(),None)), patch.object(fit_limit.evaluate_runner,'generation_functions',return_value=(object(),None)), patch.object(throughput,'TorchBackend',Backend), patch.object(throughput,'prompt_ids',side_effect=lambda t,c,n:[3]*n), patch.object(throughput,'public_cases',return_value=[]), patch.object(fit_limit,'measure') as measure:
                    fit_limit.run(config,'unused',output,dict(config,approved=True))
                measure.assert_called_once()
                events=[json.loads(line) for line in (output/'events.jsonl').read_text().splitlines()]
                parity=[e for e in events if e['event']=='path_parity']
                self.assertEqual([e['prompt_tokens'] for e in parity],[2500,4000])
                for event in parity:
                    self.assertEqual(event['available'],not oom)
                    self.assertIsNone(event['first_divergence_to_eot'])
                    self.assertEqual(event['first_divergence'],None if oom else 2)
                failures=[e for e in events if e.get('status')=='oom']
                self.assertEqual(len(failures),2 if oom else 0)
                for event in failures: self.assertEqual(event['peak_allocated_bytes'],123456)
