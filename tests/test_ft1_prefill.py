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
            from transformers import Gemma3TextConfig, Gemma3ForCausalLM
        except ImportError as exc:
            self.skipTest('CPU Gemma3 dependencies unavailable: '+str(exc))
        torch.set_num_threads(1)
        torch.manual_seed(41)
        config = Gemma3TextConfig(vocab_size=97,hidden_size=32,intermediate_size=64,
            num_hidden_layers=6,num_attention_heads=4,num_key_value_heads=2,head_dim=8,
            sliding_window=8,max_position_embeddings=128,pad_token_id=0,eos_token_id=None)
        config._attn_implementation='eager'
        model=Gemma3ForCausalLM(config).eval()
        for length in (7,19,35):
            ids=torch.randint(3,97,(1,length))
            with torch.inference_mode():
                baseline=model.generate(ids,attention_mask=torch.ones_like(ids),max_new_tokens=6,
                    do_sample=False,return_dict_in_generate=True,output_logits=True)
                for size in (1,5,8,13,64):
                    chunked=model.generate(ids,attention_mask=torch.ones_like(ids),max_new_tokens=6,
                        do_sample=False,return_dict_in_generate=True,output_logits=True,
                        **prefill_options(dict(prefill_mode='chunked',prefill_chunk_size=size)))
                    self.assertEqual(baseline.sequences.tolist(),chunked.sequences.tolist())
                    torch.testing.assert_close(baseline.logits[0],chunked.logits[0],atol=1e-6,rtol=1e-5)
