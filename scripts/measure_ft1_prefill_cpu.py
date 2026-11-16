"""Measure tiny random Gemma3 CPU allocations, without loading external files."""
import json
import torch
from transformers import Gemma3TextConfig, Gemma3ForCausalLM

def main():
    torch.set_num_threads(1)
    torch.manual_seed(41)
    c=Gemma3TextConfig(vocab_size=97,hidden_size=32,intermediate_size=64,
        num_hidden_layers=6,num_attention_heads=4,num_key_value_heads=2,head_dim=8,
        sliding_window=8,max_position_embeddings=128,pad_token_id=0,eos_token_id=None)
    c._attn_implementation='eager'
    m=Gemma3ForCausalLM(c).eval()
    ids=torch.randint(3,97,(1,35))
    for chunk in (None,5):
        observed=[]
        hook=m.lm_head.register_forward_hook(lambda mod,args,out: observed.append(dict(shape=list(out.shape),dtype=str(out.dtype),bytes=out.numel()*out.element_size())))
        with torch.inference_mode(),torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU],profile_memory=True) as p:
            out=m.generate(ids,attention_mask=torch.ones_like(ids),max_new_tokens=6,do_sample=False,prefill_chunk_size=chunk)
        hook.remove()
        print(json.dumps(dict(chunk=chunk,logits=observed,ids=out[0,35:].tolist(),
            allocations={e.key:e.cpu_memory_usage for e in p.key_averages() if e.key in ('aten::bmm','aten::_softmax','aten::gelu')})))

if __name__=='__main__': main()
