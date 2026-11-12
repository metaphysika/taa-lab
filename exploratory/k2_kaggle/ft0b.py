"""FT0b opt-in memory-layout qualification. Importing this module runs nothing."""
import json
import math
import statistics
from pathlib import Path
from exploratory.k2_kaggle import core, ft0

SPANS = (128, 384, 640, 896)


def check_internals():
    """Reject source drift from the wheels inspected during this offline build."""
    import hashlib
    import importlib
    expected = {'transformers.trainer': '33ef308cf53cd54511823f05d8888eb25d6bd567c4ef0c777b51abd65306bbef', 'transformers.loss.loss_utils': '83db16b24ce5c3a0642097624aa9a0ae7eb72445c41d8b4d5059a129862fdbbe', 'transformers.models.gemma3.modeling_gemma3': '8ca9a7ad9c0eafb222dfdd34e5ecb86d608e678b22db6391ce5a44e5281db6ae', 'peft.utils.other': '6b87957915ba399bfb6bbd57b9404aa12f0e9f4e27b19ef1b6c68ac052148f9b'}
    for name, digest in expected.items():
        module = importlib.import_module(name)
        if hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() != digest:
            raise ValueError('unverified FT0b package internals: '+name)


def guard(model, mode, ft0_enabled=False):
    if ft0_enabled: raise ValueError('FT0 and FT0B are mutually exclusive')
    ft0.guard(model, mode)


def memory(phase, retain):
    import torch
    retain(dict(event='memory', phase=phase, allocated_bytes=torch.cuda.memory_allocated(),
                reserved_bytes=torch.cuda.memory_reserved()))


def layout(model):
    """Only the inspected Gemma3 conditional-generation text path is supported."""
    import torch
    base = model.get_base_model() if hasattr(model, 'get_base_model') else model
    if type(base).__name__ != 'Gemma3ForConditionalGeneration':
        raise ValueError('unsupported FT0b model class')
    if type(base.model).__name__ != 'Gemma3Model' or type(base.model.language_model).__name__ != 'Gemma3TextModel':
        raise ValueError('unsupported FT0b hidden-state path')
    embed, head = base.get_input_embeddings(), base.get_output_embeddings()
    if not isinstance(embed, torch.nn.Embedding) or type(head) is not torch.nn.Linear or head.bias is not None:
        raise ValueError('unsupported vocabulary modules')
    for weight in (embed.weight, head.weight):
        if weight.requires_grad or weight.dtype not in (torch.float32, torch.float16):
            raise ValueError('vocabulary tables must be frozen floating weights')
    if embed.weight.shape != head.weight.shape or embed.weight.shape != (base.config.text_config.vocab_size, base.config.text_config.hidden_size):
        raise ValueError('unexpected vocabulary shape')
    if embed.weight.data_ptr()==head.weight.data_ptr() and embed.weight is not head.weight:
        raise ValueError('unsupported shared storage with distinct parameters')
    cfg = base.config.text_config
    if cfg.model_type != 'gemma3_text' or getattr(base.config, 'logit_scale', None) is not None:
        raise ValueError('unsupported logit configuration')
    # This class in 5.20.2 does not apply softcapping in its standard forward.
    # A non-null cap would violate the requested old/new math comparison.
    if getattr(cfg, 'final_logit_softcapping', None) is not None:
        raise ValueError('conditional-generation full-logit path does not implement softcapping')
    return base, embed, head


def stream_hooks(embed, head):
    """Keep the residual stream fp32 after the fp16 table cast, as under PEFT's fp32 table.

    The embedding returns its table's dtype and every residual add keeps it, so an
    fp16 table alone would move the whole stream to fp16 (Fable readiness M1).
    The embedding output is upcast to fp32; the output layer casts its input to
    its own weight dtype, so un-autocast generation does not hit a dtype mismatch.
    """
    if getattr(embed, '_ft0b_stream_hooks', False): raise ValueError('FT0b stream hooks already installed')
    embed.register_forward_hook(lambda module, args, output: output.float())
    head.register_forward_pre_hook(lambda module, args: (args[0].to(module.weight.dtype),)+tuple(args[1:]))
    embed._ft0b_stream_hooks = True


def tables(model, phase, retain, cast=False):
    import torch
    _, embed, head = layout(model)
    if phase == 'before_cast' and any(w.dtype != torch.float32 for w in (embed.weight,head.weight)):
        raise ValueError('old equivalence path requires fp32 vocabulary tables')
    if cast:
        for weight in {id(w): w for w in (embed.weight, head.weight)}.values():
            if weight.dtype == torch.float32: weight.data = weight.data.to(torch.float16)
            assert not weight.requires_grad and weight.dtype == torch.float16
        stream_hooks(embed, head)
        torch.cuda.empty_cache()
    retain(dict(event='tables', phase=phase, shared=embed.weight.data_ptr()==head.weight.data_ptr(),
        stream_fp32_hooks=bool(getattr(embed, '_ft0b_stream_hooks', False)),
        weights=[dict(dtype=str(w.dtype), bytes=w.numel()*w.element_size(), data_ptr=w.data_ptr(), frozen=not w.requires_grad)
                 for w in (embed.weight, head.weight)]))


def chunked_loss(hidden, head, labels, num_items_in_batch=None, softcap=None):
    import torch
    from torch.utils.checkpoint import checkpoint
    target = labels[..., 1:].reshape(-1)
    selected = target != -100
    states = hidden[..., :-1, :].reshape(-1, hidden.shape[-1])[selected]
    target = target[selected]
    if not len(target): raise ValueError('no supervised next-token positions')
    if softcap is not None and (not math.isfinite(softcap) or softcap <= 0):
        raise ValueError('invalid final_logit_softcapping')
    def slice_loss(h, y):
        logits = head(h)
        if softcap is not None: logits = torch.tanh(logits / softcap) * softcap
        return torch.nn.functional.cross_entropy(logits.float(), y, reduction='sum')
    total = sum(checkpoint(slice_loss, states[i:i+128], target[i:i+128], use_reentrant=False)
                for i in range(0, len(target), 128))
    return total / (num_items_in_batch if num_items_in_batch is not None else len(target))


def loss(model, inputs, num_items_in_batch=None):
    base, _, head = layout(model)
    if set(inputs) != {'input_ids', 'attention_mask', 'labels'}:
        raise ValueError('unsupported FT0b batch fields')
    hidden = base.model(input_ids=inputs['input_ids'], attention_mask=inputs['attention_mask'],
                        use_cache=False, return_dict=True)[0]
    return chunked_loss(hidden, head, inputs['labels'], num_items_in_batch)


def equivalence(model, data, retain, check):
    import torch
    model.train()
    params = [p for n,p in model.named_parameters() if 'lora_' in n and p.requires_grad]
    if not params: raise ValueError('missing LoRA parameters')
    def measure(record, old):
        check(); model.zero_grad(set_to_none=True)
        batch = {k: torch.tensor([v], device='cuda:0') for k,v in record.items()}
        with torch.autocast('cuda', dtype=torch.float16):
            value = model(**batch).loss if old else loss(model, batch)
        value.backward()
        if any(p.grad is None for p in params): raise ValueError('missing equivalence gradients')
        grads = torch.cat([p.grad.detach().float().reshape(-1).cpu() for p in params])
        return value.detach().float().item(), grads
    tables(model, 'before_cast', retain)
    old = [measure(r, True) for r in data[:8]]
    model.zero_grad(set_to_none=True)
    tables(model, 'after_cast', retain, cast=True)
    memory('fp16_cast', retain)
    for i, record in enumerate(data[:8]):
        value, grads = measure(record, False)
        previous, reference = old[i]
        cosine = torch.nn.functional.cosine_similarity(reference, grads, dim=0).item()
        retain(dict(event='equivalence', record_index=i, old_loss=previous, new_loss=value,
                    absolute_difference=abs(previous-value), gradient_cosine=cosine))
    model.zero_grad(set_to_none=True)


def probe_record(tokenizer, span):
    if span not in SPANS: raise ValueError('unsupported trained span')
    # Search complete template prefixes; never truncate or pad token ids.
    end = core.end_token(tokenizer)
    def encoded_length(target, encode):
        for unit in (' x', ' a', ' test', '0'):
            for n in range(1, 2049):
                ids = encode(unit*n)
                if len(ids) == target: return ids
        raise ValueError('cannot build exact FT0b template record')
    prefix = encoded_length(1024-span, lambda text: core.prompt(tokenizer,
        [dict(role='system',content='Repeat the supplied text.'), dict(role='user',content=text)]))
    content = encoded_length(span, lambda text: tokenizer.encode(text,add_special_tokens=False)+[end])
    return dict(input_ids=prefix+content, attention_mask=[1]*1024, labels=[-100]*len(prefix)+content)


def probes(model, tokenizer, trainer, retain, check):
    import time
    import torch
    state = model.training
    cache = getattr(model.config, 'use_cache', ft0._MISSING)
    model.train(); model.config.use_cache=False
    optimizer = trainer.optimizer
    scaler = trainer.accelerator.scaler
    if scaler is None: raise ValueError('FT0b requires fp16 GradScaler')
    try:
        for span in SPANS:
            batch = value = None
            try:
                record = probe_record(tokenizer, span)
                retain(dict(event='step_probe_record', span=span, **record))
                batch = {k: torch.tensor([v],device='cuda:0') for k,v in record.items()}
                for step in range(3):
                    check(); model.zero_grad(set_to_none=True)
                    torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats()
                    start=time.monotonic(); values=[]
                    for _ in range(8):
                        check()
                        with torch.autocast('cuda',dtype=torch.float16):
                            value=loss(model,batch,8*span)
                        values.append(value.detach().float().item())
                        scaler.scale(value).backward()
                    # Match Trainer's clipping and scaler update, using its resident optimizer.
                    trainer.accelerator.unscale_gradients(optimizer)
                    stats=ft0.gradient_stats(model)
                    torch.nn.utils.clip_grad_norm_(model.parameters(),trainer.args.max_grad_norm)
                    optimizer.step()  # AcceleratedOptimizer owns scaler.step/update.
                    torch.cuda.synchronize()
                    retain(dict(event='step_probe_pass',span=span,warmup=step==0,
                        seconds=time.monotonic()-start,losses=[v if math.isfinite(v) else str(v) for v in values],
                        loss_finite=all(math.isfinite(v) for v in values), **stats,
                        peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved()))
                    model.zero_grad(set_to_none=True)
                retain(dict(event='step_probe_complete',span=span))
            except RuntimeError as exc:
                if not ft0.is_oom(exc): raise
                retain(dict(event='probe_oom',span=span,error=type(exc).__name__,message=str(exc)))
                # Clear a partially completed unscale/step stage before the next span.
                scaler.update(new_scale=scaler.get_scale())
            finally:
                model.zero_grad(set_to_none=True); del batch, value
                torch.cuda.empty_cache()
    finally:
        ft0.restore_use_cache(model.config,cache); model.train(state)


def generation(reloaded, ids, retain):
    import time
    import torch
    torch.cuda.synchronize(); start=time.monotonic()
    with torch.no_grad(): result=reloaded.generate(ids,max_new_tokens=200,min_new_tokens=200,do_sample=False)
    torch.cuda.synchronize(); seconds=time.monotonic()-start
    retain(dict(event='generation_200',tokens=result.shape[-1]-ids.shape[-1],seconds=seconds,
                tokens_per_second=(result.shape[-1]-ids.shape[-1])/seconds,token_ids=result[0].tolist()))


def report(folder, approved_commit):
    from exploratory.k2_kaggle.launch import verify
    folder=Path(folder); events=[]; reasons=[]; rules={}
    try:
        verify(folder)
        assert json.loads((folder/'manifest.json').read_text())['sha256']==core.inventory(folder)
        meta=json.loads((folder/'metadata.json').read_text())
        events=[json.loads(s) for s in (folder/'events.jsonl').read_text().splitlines()]
        assert meta.get('ft0b') is True and not meta.get('ft0') and meta.get('dry_run') is False
        guard(meta['model_id'].removeprefix('google/'),meta['mode'])
        assert meta['gpu']==ft0.T4_NAME and meta['visible_gpus']==1
        assert meta['recipe_sha256']==core.digest(core.RECIPE) and meta['arm']=='neutral'
        assert approved_commit and meta['repo_commit']==approved_commit
        ft0.language_modules(meta['lora_modules'])
        for name in ('training-template.txt','eval-template.txt','mask-probe.json','adapter/adapter_config.json'):
            assert (folder/name).is_file(), 'missing '+name
        ft0.finite_tensors(folder/'adapter')
        complete=[e for e in events if e['event']=='qualification_complete']
        assert len(complete)==1 and complete[0]['optimizer_steps']==25
        assert complete[0]['adapter_sha256']==core.inventory(folder/'adapter')
        raw=[e['loss'] for e in events if e['event']=='raw_loss']
        assert len(raw)==200 and all(math.isfinite(v) for v in raw)
        assert not any(e['event']=='run_failed' for e in events)
        q=next(e for e in events if e['event']=='qualification_probe')
        assert q['adapter_tokens']>0 and q['disabled_tokens']>0
        table=next(e for e in events if e['event']=='tables' and e['phase']=='after_cast')
        assert table.get('stream_fp32_hooks') is True, 'fp32 residual stream hooks not recorded'
        assert len(table['weights'])==2 and all(w['dtype']=='torch.float16' and w['frozen'] and w['bytes']>0 for w in table['weights'])
        for span in SPANS:
            rec=[e for e in events if e['event']=='step_probe_record' and e['span']==span]
            assert len(rec)<=1
            assert rec or any(e['event']=='probe_oom' and e['span']==span for e in events)
            for r in rec:
                assert len(r['input_ids'])==len(r['attention_mask'])==len(r['labels'])==1024
                assert r['labels']==[-100]*(1024-span)+r['input_ids'][-span:]
        rules['1']='PASS'
    except Exception as exc:
        rules['1']='NOT ESTABLISHED'; reasons.append(str(exc) or type(exc).__name__)
    eq=[e for e in events if e['event']=='equivalence']
    math_ok=(len(eq)==8 and {e['record_index'] for e in eq}==set(range(8)) and
        all(math.isfinite(e['absolute_difference']) and 0<=e['absolute_difference']<=.02 and
            math.isfinite(e['gradient_cosine']) and e['gradient_cosine']>=.99 and
            math.isfinite(e['old_loss']) and math.isfinite(e['new_loss']) and
            abs(e['absolute_difference']-abs(e['old_loss']-e['new_loss']))<1e-8 for e in eq) and
        statistics.median(e['absolute_difference'] for e in eq)<=.005)
    rules['2']='PASS' if math_ok else 'FAIL'
    load=next((e['seconds'] for e in events if e['event']=='timing' and e['phase']=='load'),None)
    spans={}; warnings=[]
    for span in SPANS:
        rows=[e for e in events if e['event']=='step_probe_pass' and e['span']==span and not e['warmup']]
        valid=len(rows)==2 and any(e['event']=='step_probe_complete' and e['span']==span for e in events)
        valid=valid and not any(e['event']=='probe_oom' and e.get('span')==span for e in events)
        valid=valid and all(math.isfinite(r['seconds']) and r['seconds']>0 and r['peak_allocated_bytes']>0 for r in rows)
        peak=max((r['peak_allocated_bytes'] for r in rows),default=0)
        seconds=max((r['seconds'] for r in rows),default=0)
        hours=(load+250*seconds)/3600 if valid and load is not None and math.isfinite(load) and load>=0 else None
        spans[str(span)]=dict(memory='PASS' if valid and peak<=13.5e9 else 'FAIL',
            time='PASS' if hours is not None and hours<=8 else 'FAIL',worst_case_hours=hours,raw_passes=rows,
            warmup_passes=[e for e in events if e['event']=='step_probe_pass' and e['span']==span and e['warmup']])
        if any(r.get('peak_reserved_bytes',0)>15e9 for r in rows): warnings.append(f'{span}: reserved above 15e9')
        if any(not r.get('loss_finite') or not r.get('lora_parameters') or r.get('lora_gradients_finite')!=r.get('lora_parameters') for r in rows):
            warnings.append(f'{span}: nonfinite loss or missing/nonfinite gradients (report only)')
    def passes(span): return all(spans[str(span)][k]=='PASS' for k in ('memory','time'))
    rules.update({'3':spans['640']['memory'],'4':spans['640']['time']})
    verdict=('NOT ESTABLISHED' if rules['1']!='PASS' else 'FAIL' if not math_ok else
             'PASS' if passes(640) else 'PASS LIMITED' if passes(384) else 'FAIL')
    skips=sorted(core.nonfinite_grad_steps(events))
    if len([s for s in skips if 6<=s<=25])>3: warnings.append('more than 3 skipped updates in last 20 steps')
    return dict(verdict=verdict,rules=rules,reasons=reasons,warnings=warnings,spans=spans,equivalence=eq,
        itemised_memory=[e for e in events if e['event'] in ('memory','tables')],skipped_update_steps=skips,
        generation=[e for e in events if e['event']=='generation_200'],units='decimal bytes; hours',
        limits='Synthetic probes do not establish 250-step fragmentation or FT1 learning. On FAIL/NOT ESTABLISHED stop Kaggle fixes; price 24 GB Modal for owner review.')


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(__doc__); p.add_argument('folder'); p.add_argument('--approved-commit',required=True)
    a=p.parse_args(); print(json.dumps(report(a.folder,a.approved_commit),indent=2))
