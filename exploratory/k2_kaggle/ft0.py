"""Opt-in FT0 measurements and offline Draft B report; no execution on import."""
import json
import math
from pathlib import Path
from exploratory.k2_kaggle import core


def guard(model, mode):
    if (model, mode) != ('gemma-3-12b-it', 'qualify'):
        raise ValueError('FT0 requires Gemma 3 12B neutral qualification')


def language_modules(names):
    if not names or any('language_model' not in n.split('.') or
            any(x in n.lower() for x in ('vision', 'projector', 'multi_modal')) for n in names):
        raise ValueError('FT0 LoRA coverage must be entirely language_model')
    return True


def probe_record(tokenizer, length):
    """Template prefix and independently encoded assistant text, never truncation.

    Search actual encodings for an exact length. Refuse an incompatible tokenizer
    rather than padding, slicing a rendered template, or weakening training limits.
    """
    prefix = core.prompt(tokenizer, [dict(role='system', content='Repeat the supplied text.'),
                                    dict(role='user', content='Synthetic length probe.')])
    end = core.end_token(tokenizer)
    for unit in (' x', ' a', ' test', '0'):
        for count in range(1, length + 1):
            content = tokenizer.encode(unit * count, add_special_tokens=False) + [end]
            if len(prefix) + len(content) == length:
                return dict(input_ids=prefix+content, attention_mask=[1]*length,
                            labels=[-100]*len(prefix)+content)
    raise ValueError('cannot construct exact template probe length')


def probes(model, tokenizer, retain, check=lambda: None):
    import time
    import torch
    model.train()
    model.gradient_checkpointing_enable()
    model.config.use_cache = False
    try:
        for length in (1024, 2048):
            batch = None
            timings = []
            losses = []
            try:
                record = probe_record(tokenizer, length)
                retain(dict(event='length_probe_record', length=length, **record))
                batch = {k: torch.tensor([v], device='cuda:0') for k,v in record.items()}
                for i in range(4):  # warm-up followed by three measured passes
                    check()
                    model.zero_grad(set_to_none=True)
                    torch.cuda.synchronize()
                    torch.cuda.reset_peak_memory_stats()
                    start = time.monotonic()
                    with torch.autocast(device_type='cuda', dtype=torch.float16):
                        loss = model(**batch).loss
                    core.finite_scalar(loss.detach().float().item())
                    loss.backward()
                    torch.cuda.synchronize()
                    seconds = time.monotonic()-start
                    row = dict(event='length_probe_pass', length=length, warmup=i==0,
                               seconds=seconds, peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                               peak_reserved_bytes=torch.cuda.max_memory_reserved(), loss=loss.detach().float().item())
                    retain(row)
                    del loss
                    if i:
                        timings.append(seconds)
                        losses.append(row['loss'])
                retain(dict(event='length_probe_complete', length=length, timings=timings, losses=losses))
            except torch.cuda.OutOfMemoryError as exc:
                retain(dict(event='probe_oom', length=length, message=str(exc)))
            finally:
                model.zero_grad(set_to_none=True)
                del batch
                torch.cuda.empty_cache()
    finally:
        model.eval()


def finite_tensors(folder):
    """Read safetensors float payloads offline using only the standard library."""
    import struct
    files=list(folder.glob('*.safetensors'))
    assert files, 'missing adapter tensors'
    for path in files:
        raw=path.read_bytes()
        size=struct.unpack('<Q',raw[:8])[0]
        header=json.loads(raw[8:8+size])
        tensors=[v for k,v in header.items() if k!='__metadata__']
        assert tensors, 'empty adapter'
        for tensor in tensors:
            start,end=tensor['data_offsets']
            data=raw[8+size+start:8+size+end]
            assert len(data)==end-start and data, 'invalid tensor payload'
            dtype=tensor['dtype']
            if dtype=='BF16':
                finite=all((v[0]&0x7f80)!=0x7f80 for v in struct.iter_unpack('<H',data))
            else:
                assert dtype in ('F16','F32','F64'), 'unsupported adapter dtype'
                finite=all(math.isfinite(v[0]) for v in struct.iter_unpack('<'+{'F16':'e','F32':'f','F64':'d'}[dtype],data))
            assert finite, 'nonfinite adapter tensor'


def report(folder):
    """All FT0 thresholds live here. GB means decimal 1e9 bytes."""
    from exploratory.k2_kaggle.launch import verify
    folder = Path(folder)
    rules = {}
    reasons = []
    events = []
    meta = {}
    try:
        verify(folder)
        manifest=json.loads((folder/'manifest.json').read_text())
        assert manifest['sha256']==core.inventory(folder), 'incomplete manifest inventory'
        meta = json.loads((folder/'metadata.json').read_text())
        events = [json.loads(x) for x in (folder/'events.jsonl').read_text().splitlines()]
        assert meta.get('ft0') is True and meta.get('dry_run') is False
        guard(meta['model_id'].removeprefix('google/'), meta['mode'])
        language_modules(meta['lora_modules'])
        for name in ('training-template.txt','eval-template.txt','mask-probe.json','adapter/adapter_config.json'):
            assert (folder/name).is_file(), 'missing '+name
        complete = next(e for e in events if e['event']=='qualification_complete')
        assert complete['optimizer_steps']==5
        assert complete['adapter_sha256']==core.inventory(folder/'adapter')
        losses = [e['loss'] for e in events if e['event']=='raw_loss']
        assert len(losses)==40 and all(math.isfinite(x) for x in losses), 'raw losses missing/nonfinite'
        finite_tensors(folder/'adapter')
        q=next(e for e in events if e['event']=='qualification_probe')
        assert q['adapter_tokens']>0 and q['disabled_tokens']>0
        assert not any(e['event']=='run_failed' for e in events)
        rules['1']='PASS'
    except (Exception,) as exc:
        rules['1']='NOT ESTABLISHED'
        reasons.append('Artifacts: '+(str(exc) or type(exc).__name__))
    load=next((e['seconds'] for e in events if e.get('event')=='timing' and e.get('phase')=='load'),None)
    lengths={}
    for length in (1024,2048):
        rows=[e for e in events if e.get('event')=='length_probe_pass' and e.get('length')==length and not e['warmup']]
        oom=any(e.get('event')=='probe_oom' and e.get('length')==length for e in events)
        done=any(e.get('event')=='length_probe_complete' and e.get('length')==length for e in events)
        valid=done and len(rows)==3 and all(math.isfinite(e['seconds']) and e['seconds']>0 and e['peak_allocated_bytes']>0 for e in rows)
        peak=max((e['peak_allocated_bytes'] for e in rows),default=None)
        seconds=max((e['seconds'] for e in rows),default=None)
        hours=(load+250*seconds*8)/3600 if valid and load is not None and math.isfinite(load) and load>=0 else None
        memory='FAIL' if oom else ('PASS' if peak<=13.5e9 else 'FAIL') if valid else 'NOT ESTABLISHED'
        timing=('PASS' if hours<=8.0 else 'FAIL') if hours is not None else 'NOT ESTABLISHED'
        lengths[str(length)]=dict(oom=oom,peak_allocated_bytes=peak,raw_passes=rows,worst_case_hours=hours,memory=memory,time=timing)
        if length==1024: rules.update({'2':memory,'3':timing})
    throughput=next((e.get('adapter_tokens_per_second') for e in events if e.get('event')=='qualification_probe'),None)
    estimate=(load+495*1024/throughput)/3600 if load is not None and throughput and throughput>0 else None
    verdict='FAIL' if 'FAIL' in rules.values() else 'NOT ESTABLISHED' if 'NOT ESTABLISHED' in rules.values() else 'PASS'
    reasons += ['Rule '+k+': '+v for k,v in rules.items() if v!='PASS']
    return dict(verdict=verdict,rules=rules,reasons=reasons,units='decimal GB (1 GB = 1e9 bytes); time in hours',
                lengths=lengths,skipped_update_steps=sorted(core.nonfinite_grad_steps(events)),tokens_per_second=throughput,
                amendment_2_evaluation_hours=estimate,evaluation_assumption='load + 495 requests x 1024 output tokens / short-generation throughput; excludes long-input overhead')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('folder',type=Path)
    print(json.dumps(report(parser.parse_args().folder),indent=2))
