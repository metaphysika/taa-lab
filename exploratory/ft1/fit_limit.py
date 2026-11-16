"""Public base-model fit ladder. No execution on import."""
import json
import os
import time
from pathlib import Path
from . import throughput, evaluate_runner, data
from .memory import cleanup, snapshot, MechanicalUnknown
from .runner import deadline, verify_source
from exploratory.k2_kaggle import core

LENGTHS = (2500,4000,6000,8000,10000,11000,12000,13000,14000,16000)

def validate(config, receipt):
    if config.get('prefill_mode') == 'chunked':
        for key in ('prefill_mode','prefill_chunk_size','deadline_seconds'):
            if key not in config or key not in receipt:
                raise ValueError('chunked fit receipt requires '+key)
        if type(config['deadline_seconds']) is not int or not 0 < config['deadline_seconds'] <= 4500:
            raise ValueError('deadline must be integer seconds within 75 minutes')
    evaluate_runner.validate_prefill(config, receipt)
    if config.get('phase') != 'fit_limit' or receipt.get('phase') != 'fit_limit':
        raise ValueError('separate fit_limit approval required')
    if receipt.get('deadline_seconds') != config.get('deadline_seconds'):
        raise ValueError('fit deadline receipt mismatch')
    throughput.validate(dict(config,phase='throughput'),dict(receipt,phase='throughput'))

def measure(backend, tokenizer, attention, references, retain, check, generate=None):
    first_ids = None
    end_ids = core.end_token(tokenizer,'gemma-3-12b-it') if tokenizer is not None else []
    end_ids = [end_ids] if isinstance(end_ids,int) else end_ids
    for target in LENGTHS:
        check()
        identity = dict(attention=attention,prompt_tokens=target,output_allowance=1024)
        retain(dict(event='fit_started',**identity))
        prompts = [throughput.prompt_ids(tokenizer,throughput.public_cases(),target)]
        oom = False
        try:
            result = backend.benchmark(prompts,check,new_tokens=1024)
        except throughput.MeasurementOOM as exc:
            retain(dict(event='fit',status='oom',peak_allocated_bytes=exc.peak_allocated_bytes,
                peak_reserved_bytes=getattr(exc,'peak_reserved_bytes',None),after_cleanup=getattr(exc,'after_cleanup',None),**identity))
            oom = True
        if oom:
            recover(backend,tokenizer,attention,first_ids,target,generate,retain,check)
            break
        ids = result['generated_ids'][0]
        if target == 2500: first_ids = ids
        prompt_hash = throughput.token_ids_sha256(prompts[0])
        reference = references.get(target)
        if attention == 'eager': references[target] = (prompt_hash,ids)
        if reference is not None and attention == 'sdpa' and reference[0] != prompt_hash:
            raise ValueError('parity prompt mismatch')
        available = attention == 'sdpa' and reference is not None
        retain(dict(event='fit',status='fit',prompt_sha256=prompt_hash,
            parity_available=available,first_divergence=throughput.first_divergence(reference[1],ids) if available else None,
            first_divergence_to_eot=throughput.first_divergence(to_eot(reference[1],end_ids),to_eot(ids,end_ids)) if available else None,
            **identity,measurement=result))
        check()
    else:
        # Even a backend that fits every rung must exercise evaluation generation.
        evaluation_probe(tokenizer,attention,LENGTHS[-1],generate,retain,check)

def to_eot(ids, end_ids):
    """Include the first end-of-turn token; retain the full IDs separately."""
    return ids[:next((i+1 for i,token in enumerate(ids) if token in end_ids),len(ids))]

def recover(backend, tokenizer, attention, first_ids, failed_target, generate, retain, check):
    """No reload: retry the short rung and probe the actual evaluation generator."""
    check()
    prompts = [throughput.prompt_ids(tokenizer,throughput.public_cases(),2500)]
    result = None
    failure = None
    try:
        result = backend.benchmark(prompts,check,new_tokens=1024)
    except throughput.MeasurementOOM as exc:
        failure = dict(peak_allocated_bytes=exc.peak_allocated_bytes,
                       peak_reserved_bytes=getattr(exc,'peak_reserved_bytes',None),
                       after_cleanup=getattr(exc,'after_cleanup',None))
    retain(dict(event='recovery_check',attention=attention,status='oom' if failure else 'fit',
        reference_available=first_ids is not None,ids_equal_first_pass=(result['generated_ids'][0]==first_ids) if result is not None and first_ids is not None else None,
        measurement=result,failure=failure))
    evaluation_probe(tokenizer,attention,failed_target,generate,retain,check)

def evaluation_probe(tokenizer, attention, failed_target, generate, retain, check):
    if generate is None: return
    check()
    # Stay within evaluation's context guard to exercise its CUDA allocation path.
    target = min(failed_target,15360)
    ids = throughput.prompt_ids(tokenizer,throughput.public_cases(),target)
    status = evaluation_call(generate,ids,1024,'evaluation_oom_probe',attention,retain,check,
                             failed_rung=failed_target)
    if status == 'mechanical_oom':
        check()
        short_ids = throughput.prompt_ids(tokenizer,throughput.public_cases(),2500)
        evaluation_call(generate,short_ids,128,'evaluation_recovery_check',attention,retain,check)


def reset_peaks():
    import torch
    torch.cuda.reset_peak_memory_stats()


def peaks():
    import torch
    return dict(peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                peak_reserved_bytes=torch.cuda.max_memory_reserved())


def evaluation_call(generate, ids, cap, event, attention, retain, check, **details):
    """Measure one call through evaluation generation, after its own cleanup."""
    check()
    reset_peaks()
    started = time.perf_counter()
    observed = None
    try:
        generated = generate('',[],cap,548017,prompt_ids=ids,return_ids=True)
        observed = dict(status='fit',generated_ids=generated,generated_tokens=len(generated))
    except MechanicalUnknown as exc:
        observed = dict(status=exc.status,generated_tokens=None)
    retain(dict(event=event,attention=attention,prompt_tokens=len(ids),output_allowance=cap,
                **observed,**peaks(),seconds=time.perf_counter()-started,
                after_cleanup=snapshot(),**details))
    return observed['status']


def run(config, model_path, output, receipt, seconds=4500):
    validate(config,receipt)
    verify_source(config)
    if not 0 < seconds <= 4500: raise ValueError('deadline within 75 minutes required')
    if config.get('deadline_seconds',seconds) != seconds: raise ValueError('bound deadline mismatch')
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
        fixed = bool(evaluate_runner.prefill_options(config))
        retain(dict(event='prefill_config',prefill_mode=config.get('prefill_mode','current'),prefill_chunk_size=config.get('prefill_chunk_size'),deadline_seconds=seconds))
        for attention in (('eager',) if fixed else ('eager','sdpa')):
            check()
            model = tokenizer = backend = None
            try:
                model,tokenizer,_ = evaluate_runner.load_base(model_path,retain,check,attention=attention)
                actual = getattr(getattr(model.config,'text_config',model.config),'_attn_implementation',None)
                top = getattr(model.config,'_attn_implementation',None)
                retain(dict(event='attention_readback',requested=attention,text=actual,top=top,mismatch=attention not in (actual,top)))
                backend = throughput.TorchBackend(model,tokenizer,config)
                generate,_ = evaluate_runner.generation_functions(model,tokenizer,check,**(dict(prefill_mode=config["prefill_mode"],prefill_chunk_size=config["prefill_chunk_size"]) if fixed else {}))
                try:
                    if fixed:
                        current = throughput.TorchBackend(model,tokenizer)
                        for target in (2500,4000):
                            prompts = [throughput.prompt_ids(tokenizer,throughput.public_cases(),target)]
                            rows = []
                            for label, path in (('current',current),('fixed',backend)):
                                check()
                                try:
                                    result = path.benchmark(prompts,check,new_tokens=1024)
                                    rows.append(result['generated_ids'][0])
                                    retain(dict(event='path_parity_measurement',path=label,prompt_tokens=target,measurement=result))
                                except throughput.MeasurementOOM as exc:
                                    rows.append(None)
                                    retain(dict(event='path_parity_measurement',path=label,prompt_tokens=target,status='oom',
                                        peak_allocated_bytes=exc.peak_allocated_bytes,
                                        peak_reserved_bytes=getattr(exc,'peak_reserved_bytes',None),
                                        after_cleanup=getattr(exc,'after_cleanup',None)))
                            end_ids = core.end_token(tokenizer,'gemma-3-12b-it')
                            end_ids = [end_ids] if isinstance(end_ids,int) else end_ids
                            available = all(row is not None for row in rows)
                            retain(dict(event='path_parity',prompt_tokens=target,available=available,
                                first_divergence=throughput.first_divergence(*rows) if available else None,
                                first_divergence_to_eot=throughput.first_divergence(*(to_eot(row,end_ids) for row in rows)) if available else None,
                                ids_equal=rows[0]==rows[1] if available else None))
                    measure(backend,tokenizer,attention,references,retain,check,generate=generate)
                finally:
                    del generate
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
