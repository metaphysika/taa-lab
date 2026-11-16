"""Public base-model fit ladder. No execution on import."""
import json
import os
from pathlib import Path
from . import throughput, evaluate_runner, data
from .memory import cleanup
from .runner import deadline, verify_source
from exploratory.k2_kaggle import core

LENGTHS = (2500,4000,6000,8000,10000,12000,14000,16000)

def validate(config, receipt):
    if config.get('phase') != 'fit_limit' or receipt.get('phase') != 'fit_limit':
        raise ValueError('separate fit_limit approval required')
    throughput.validate(dict(config,phase='throughput'),dict(receipt,phase='throughput'))

def measure(backend, tokenizer, attention, references, retain, check):
    for target in LENGTHS:
        check()
        identity = dict(attention=attention,prompt_tokens=target,output_allowance=1024)
        retain(dict(event='fit_started',**identity))
        prompts = [throughput.prompt_ids(tokenizer,throughput.public_cases(),target)]
        try:
            result = backend.benchmark(prompts,check,new_tokens=1024)
        except throughput.MeasurementOOM as exc:
            retain(dict(event='fit',status='oom',peak_allocated_bytes=exc.peak_allocated_bytes,
                peak_reserved_bytes=getattr(exc,'peak_reserved_bytes',None),**identity))
            break
        ids = result['generated_ids'][0]
        prompt_hash = throughput.token_ids_sha256(prompts[0])
        reference = references.get(target)
        if attention == 'eager': references[target] = (prompt_hash,ids)
        if reference is not None and attention == 'sdpa' and reference[0] != prompt_hash:
            raise ValueError('parity prompt mismatch')
        available = attention == 'sdpa' and reference is not None
        retain(dict(event='fit',status='fit',prompt_sha256=prompt_hash,
            parity_available=available,first_divergence=throughput.first_divergence(reference[1],ids) if available else None,
            **identity,measurement=result))
        check()

def run(config, model_path, output, receipt, seconds=2700):
    validate(config,receipt)
    verify_source(config)
    if not 0 < seconds <= 2700: raise ValueError('deadline within 45 minutes required')
    check = deadline(seconds)
    folder = data.safe_output(output)
    folder.mkdir(parents=True)
    def retain(event):
        with (folder/'events.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(event,allow_nan=False)+'\n')
            stream.flush(); os.fsync(stream.fileno())
    status = 'incomplete'
    references = {}
    try:
        import torch
        if torch.cuda.device_count()!=1 or torch.cuda.get_device_name(0)!='Tesla T4':
            raise ValueError('one visible Tesla T4 required')
        for attention in ('eager','sdpa'):
            check()
            model = tokenizer = backend = None
            try:
                model,tokenizer,_ = evaluate_runner.load_base(model_path,retain,check,attention=attention)
                actual = getattr(getattr(model.config,'text_config',model.config),'_attn_implementation',None)
                if actual != attention: raise ValueError('attention backend mismatch')
                backend = throughput.TorchBackend(model,tokenizer)
                measure(backend,tokenizer,attention,references,retain,check)
            finally:
                del backend,model,tokenizer
                cleanup()
        status = 'complete'
    except BaseException as exc:
        retain(dict(event='run_failed',error=type(exc).__name__))
        raise
    finally:
        (folder/'metadata.json').write_text(json.dumps(dict(config,status=status)),encoding='utf-8')
        core.manifest(folder,dict(phase='fit_limit',status=status,scientific=False))
