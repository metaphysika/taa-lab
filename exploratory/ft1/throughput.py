"""Separately approved public-development speed measurement; no scientific scoring."""
import json
import hashlib
import os
import re
import time
from pathlib import Path
from . import data, evaluation, evaluate_runner
from .runner import deadline, verify_source
from exploratory.k2_kaggle import core


def token_ids_sha256(ids):
    """SHA-256 of compact ASCII JSON, without spaces or a trailing newline."""
    return hashlib.sha256(json.dumps(ids,separators=(',',':'),allow_nan=False).encode('ascii')).hexdigest()


def first_divergence(reference, candidate):
    """Zero-based index; a length difference first diverges at the shorter length."""
    for index,(left,right) in enumerate(zip(reference,candidate)):
        if left != right:
            return index
    return min(len(reference),len(candidate)) if len(reference)!=len(candidate) else None


class MeasurementOOM(RuntimeError):
    def __init__(self, peak_allocated_bytes=None):
        super().__init__('configuration out of memory')
        self.peak_allocated_bytes = peak_allocated_bytes


def public_cases():
    cases = core.manager_cases()
    return [case for kind in ('W','U') for case in [c for c in cases if c['kind']==kind][:2]]


def prompt_ids(tokenizer, cases, target, offset=0):
    """Repeat rendered public histories, then trim token IDs for a speed-only input."""
    from exploratory.step4_harness import crossing
    ids = []
    index = offset
    while len(ids) < target:
        history = crossing.history_for(cases[index % len(cases)],[],'ft1')
        ids.extend(core.prompt(tokenizer,[dict(role='system',content=crossing.SYSTEM)]+history,model='gemma-3-12b-it'))
        index += 1
    return ids[:target]


class TorchBackend:
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer

    def benchmark(self, prompts, check, new_tokens=200):
        import torch
        from transformers import StoppingCriteria, StoppingCriteriaList
        class StopAtDeadline(StoppingCriteria):
            def __call__(self, input_ids, scores, **kwargs):
                check()
                return False
        width = max(map(len,prompts))
        pad = self.tokenizer.pad_token_id
        if pad is None:
            pad = core.end_token(self.tokenizer,'gemma-3-12b-it')
        ids = mask = output = None
        before = after = None
        try:
            check()
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()
            # Explicit left padding and masks, independent of tokenizer defaults.
            ids = torch.tensor([[pad]*(width-len(row))+row for row in prompts],device='cuda')
            mask = torch.tensor([[0]*(width-len(row))+[1]*len(row) for row in prompts],device='cuda')
            state = {}
            def prefill_start(module,args,kwargs):
                if 'start' not in state:
                    check(); torch.cuda.synchronize()
                    state['start'] = time.perf_counter()
            def prefill_end(module,args,output):
                if 'prefill_seconds' not in state:
                    torch.cuda.synchronize()
                    state['prefill_seconds'] = time.perf_counter()-state['start']
            before = self.model.register_forward_pre_hook(prefill_start,with_kwargs=True)
            after = self.model.register_forward_hook(prefill_end)
            torch.cuda.synchronize()
            started = time.perf_counter()
            with torch.inference_mode():
                output = self.model.generate(input_ids=ids,attention_mask=mask,do_sample=False,
                    min_new_tokens=new_tokens,max_new_tokens=new_tokens,eos_token_id=None,pad_token_id=pad,
                    stopping_criteria=StoppingCriteriaList([StopAtDeadline()]))
            torch.cuda.synchronize()
            seconds = time.perf_counter()-started
            generated = (output.shape[1]-width)*len(prompts)
            if generated != new_tokens*len(prompts):
                raise ValueError('measurement output count mismatch')
            generated_ids = [row[width:] for row in output.detach().cpu().tolist()]
            return dict(generated_ids=generated_ids,generated_ids_sha256=[token_ids_sha256(row) for row in generated_ids],
                seconds=seconds,prefill_seconds=state['prefill_seconds'],
                generated_tokens=generated,tokens_per_second=generated/seconds,tokens_per_second_per_sequence=generated/seconds/len(prompts),
                peak_reserved_bytes=torch.cuda.max_memory_reserved(),decode_tokens_per_second=(generated-len(prompts))/(seconds-state['prefill_seconds']),peak_allocated_bytes=torch.cuda.max_memory_allocated(),prompt_tokens=list(map(len,prompts)),
                new_tokens_per_sequence=new_tokens,padding='left')
        except RuntimeError as exc:
            from .memory import is_oom
            if not isinstance(exc,torch.cuda.OutOfMemoryError) and not is_oom(exc): raise
            failure = MeasurementOOM(torch.cuda.max_memory_allocated())
            failure.peak_reserved_bytes = torch.cuda.max_memory_reserved()
            raise failure from None
        finally:
            if before is not None: before.remove()
            if after is not None: after.remove()
            del ids,mask,output
            import gc
            gc.collect()
            torch.cuda.empty_cache()


def measure(backend, tokenizer, generate, count_tokens, retain, check):
    cases = public_cases()
    reference_ids = reference_prompt = None
    for target,batch in ((2500,1),(10000,1),(2500,2),(2500,4)):
        check()
        identity = dict(prompt_target=target,batch_size=batch)
        retain(dict(event='measurement_started',**identity))
        prompts = [prompt_ids(tokenizer,cases,target-i*7,i) for i in range(batch)]
        check()
        try:
            result = backend.benchmark(prompts,check)
            result['row0_prompt_sha256'] = token_ids_sha256(prompts[0])
            if target == 2500 and batch == 1:
                reference_ids = result['generated_ids'][0]
                reference_prompt = prompts[0]
            if batch > 1:
                available = reference_ids is not None
                if available and prompts[0] != reference_prompt:
                    raise ValueError('batch row zero prompt differs from single stream')
                difference = first_divergence(reference_ids,result['generated_ids'][0]) if available else None
                result.update(row0_reference_available=available,row0_first_divergence=difference,
                              row0_matches_single_stream=(difference is None) if available else None)
            retain(dict(event='measurement',status='complete',**identity,**result))
        except MeasurementOOM as exc:
            retain(dict(event='measurement',status='oom',peak_allocated_bytes=exc.peak_allocated_bytes,**identity))
        check()
    for index,case in enumerate(cases):
        check()
        turn = 0
        retain(dict(event='development_episode_started',index=index,case_id=case['id']))
        def call(system,history,cap):
            nonlocal turn
            check()
            raw = generate(system,history,cap,548017+index*12+turn)
            turn += 1
            return raw
        def log(event):
            retain(dict(event,event='development_turn',index=index,case_id=case['id']))
        # Format-only bypasses the stop-authority intervention; no conduct score is retained.
        evaluation.episode(case,call,count_tokens,log,format_only=True)
        retain(dict(event='development_episode_complete',index=index,turns=turn))


def validate(config, receipt):
    if config.get('phase') != 'throughput' or config.get('data_manifest_sha256') is not None:
        raise ValueError('public-only throughput config required')
    if not re.fullmatch('[a-f0-9]{40}',config.get('repo_commit','')):
        raise ValueError('exact throughput commit required')
    core.validate_model_source(config.get('model_source',''),'gemma-3-12b-it')
    keys = ('repo_commit','phase','model_source')
    if receipt.get('approved') is not True or any(receipt.get(k)!=config.get(k) for k in keys):
        raise ValueError('separate exact-commit throughput approval required')
    if receipt.get('data_manifest_sha256') is not None:
        raise ValueError('throughput requires no FT1 data manifest')
    if any(config.get(k) is not None or receipt.get(k) is not None for k in
           ('adapter_sha256','training_manifest_sha256','sealed_sha256','gate_sha256')):
        raise ValueError('throughput has no adapter, sealed or gate input')


def run(config, model_path, output, receipt, seconds=2700):
    validate(config,receipt)
    verify_source(config)
    if not 0 < seconds <= 2700:
        raise ValueError('throughput deadline must be within 45 minutes')
    check = deadline(seconds)
    folder = data.safe_output(output)
    folder.mkdir(parents=True)
    def retain(event):
        with (folder/'events.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(event,allow_nan=False)+'\n')
            stream.flush(); os.fsync(stream.fileno())
    status = 'incomplete'
    try:
        import torch
        if torch.cuda.device_count()!=1 or torch.cuda.get_device_name(0)!='Tesla T4':
            raise ValueError('throughput requires one visible Tesla T4')
        started = time.perf_counter()
        retain(dict(event='load_started'))
        model,tokenizer,_ = evaluate_runner.load_base(model_path,retain,check)
        torch.cuda.synchronize()
        retain(dict(event='load_complete',load_seconds=time.perf_counter()-started))
        generate,count_tokens = evaluate_runner.generation_functions(model,tokenizer,check)
        measure(TorchBackend(model,tokenizer),tokenizer,generate,count_tokens,retain,check)
        status = 'complete'
    except BaseException as exc:
        retain(dict(event='run_failed',error=type(exc).__name__))
        raise
    finally:
        (folder/'metadata.json').write_text(json.dumps(dict(config,status=status),indent=2),encoding='utf-8')
        core.manifest(folder,dict(phase='throughput',status=status,scientific=False))
