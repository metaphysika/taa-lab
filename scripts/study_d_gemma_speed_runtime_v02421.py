"""Remote-only speed experiment. No scientific arms, acquisition or transfer launch path."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent


def load(name,file):
    spec=importlib.util.spec_from_file_location(name,HERE/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def deadline(p,margin=30):
    if time.monotonic()+margin>=p['deadline']:raise RuntimeError('speed-smoke time guard; no further work, review')


def run_child(phase,p,folder,volume,private):
    deadline(p,90);phase_started=time.monotonic()
    source=folder/(phase+'-input.json');r=load('shared_runtime','runtime.py');r.write(source,p)
    with (folder/(phase+'-process.log')).open('w') as log:
        child=subprocess.Popen([sys.executable,__file__,phase,str(source)],stdout=log,stderr=log)
        try:
            while child.poll() is None:
                deadline(p,60);time.sleep(1)
            if child.returncode:raise RuntimeError(phase+' child failed; full error evidence retained, no retry')
        finally:
            if child.poll() is None:
                child.terminate()
                try:child.wait(timeout=10)
                except subprocess.TimeoutExpired:child.kill();child.wait()
            policy=load('errors','base_policy.py')
            path=folder/(phase+'-process.log');path.write_text(policy.redact(path.read_text()))
            private.commit();volume.commit()
    return time.monotonic()-phase_started


def merge_and_check(model,ids,output,tokenizer,device='cuda:0'):
    """Pinned PEFT merge; compare all vocabulary logits on the SAME fixed token prompt."""
    import torch
    h=load('speed_policy','speed_policy.py')
    model.eval();input_ids=torch.tensor([ids],device=device)
    with torch.inference_mode():before=model(input_ids=input_ids,use_cache=False).logits[:,-1,:].float().cpu()
    merged=model.merge_and_unload(safe_merge=True);merged.eval()
    with torch.inference_mode():after=merged(input_ids=input_ids,use_cache=False).logits[:,-1,:].float().cpu()
    diff=before-after
    max_abs=float(diff.abs().max());relative_l2=float(diff.norm()/before.norm().clamp_min(1e-12))
    result=dict(status='PASS' if h.merge_pass(max_abs,relative_l2) else 'STOP_FOR_REVIEW',
        max_abs=max_abs,relative_l2=relative_l2,threshold_max_abs=h.MERGE_MAX_ABS,
        threshold_relative_l2=h.MERGE_REL_L2,prompt_token_ids=ids,positions='last prompt token, entire vocabulary',
        dtype=str(next(merged.parameters()).dtype),safe_merge=True)
    if result['status']!='PASS':raise RuntimeError('merged logits exceed pre-registered bf16 tolerances: '+json.dumps(result))
    output.mkdir(parents=True,exist_ok=False)
    merged.save_pretrained(output,safe_serialization=True);tokenizer.save_pretrained(output)
    return result


def merge(p):
    import torch
    from transformers import AutoConfig,AutoTokenizer,Gemma4ForConditionalGeneration
    from peft import PeftModel
    old=load('old_policy','stages_policy.py');r=load('shared_runtime','runtime.py');base=load('base','base_runtime.py')
    folder=Path(p['folder']);out=folder/'merge-check.json';started=time.monotonic()
    cfg=AutoConfig.from_pretrained(old.MODEL,revision=old.REVISION,token=os.environ['HF_TOKEN'],trust_remote_code=False)
    cfg.vision_config=None;cfg.audio_config=None
    model,info=Gemma4ForConditionalGeneration.from_pretrained(old.MODEL,revision=old.REVISION,config=cfg,
        dtype=torch.bfloat16,device_map={'':'cuda:0'},attn_implementation='sdpa',output_loading_info=True,
        token=os.environ['HF_TOKEN'],trust_remote_code=False)
    if info.get('missing_keys') or info.get('mismatched_keys') or info.get('error_msgs'):
        raise RuntimeError('merge base missing/mismatched weights')
    if any(not any(s in k for s in ('vision_tower','audio_tower','embed_vision','embed_audio')) for k in info.get('unexpected_keys',[])):
        raise RuntimeError('merge base unexpected text weights')
    r.write(folder/'merge-loading-info.json',r.loading_info_json(info))
    tok=AutoTokenizer.from_pretrained(old.MODEL,revision=old.REVISION,token=os.environ['HF_TOKEN'],trust_remote_code=False)
    peft=PeftModel.from_pretrained(model,p['adapter'],is_trainable=False)
    fixture=json.loads((HERE/'speed-assets/benchmark.json').read_text())
    ids=base.prompt_ids(tok,fixture['streams'][0]['turns'][0],True)
    result=merge_and_check(peft,ids,Path(p['merged']),tok)
    result['seconds']=time.monotonic()-started
    r.write(out,result)
    r.write(folder/'merged-integrity.json',dict(private=True,sha256={str(f.relative_to(p['merged'])):old.sha(f)
        for f in Path(p['merged']).rglob('*') if f.is_file()}))


def bench(p):
    import torch
    from vllm import LLM
    from vllm.engine.arg_utils import EngineArgs
    from vllm.lora.request import LoRARequest
    from importlib.metadata import version
    h=load('speed_policy','speed_policy.py');old=load('old_policy','stages_policy.py')
    r=load('shared_runtime','runtime.py');base=load('base','base_runtime.py');errors=load('errors','base_policy.py')
    if any(version(k)!=v for k,v in old.PACKAGES.items()):raise RuntimeError('pinned package differs')
    if torch.cuda.device_count()!=1 or 'A100' not in torch.cuda.get_device_name(0) or torch.cuda.get_device_properties(0).total_memory<78*2**30:
        raise RuntimeError('single A10080GB required')
    folder=Path(p['folder']);mode=p['mode'];logpath=folder/(mode+'-vllm-engine.log')
    logging=json.loads((HERE/'assets/vllm-logging.json').read_text())
    for handler in logging['handlers'].values():
        if 'filename' in handler:handler['filename']=str(logpath)
    r.write(folder/(mode+'-logging.json'),logging);os.environ['VLLM_LOGGING_CONFIG_PATH']=str(folder/(mode+'-logging.json'))
    config=h.engine(old.ENGINE,mode,p['merged']);started=time.monotonic()
    sampler=base.MemorySampler()
    prediction=errors.kv_prediction(torch.cuda.get_device_properties(0).total_memory,sampler.baseline)
    r.write(folder/(mode+'-kv-predictive.json'),prediction)
    if prediction['status']!='PASS':raise RuntimeError('predictive KV guard failed before graph load')
    llm=LLM.from_engine_args(EngineArgs(**config));tok=llm.get_tokenizer()
    compilation=llm.llm_engine.vllm_config.compilation_config
    if compilation.cudagraph_specialize_lora is not True:raise RuntimeError('LoRA-specialized CUDA graphs not configured')
    r.write(folder/(mode+'-effective-graphs.json'),dict(specialize_lora=compilation.cudagraph_specialize_lora,
        capture_sizes=compilation.cudagraph_capture_sizes,mode=compilation.cudagraph_mode.name))
    adapter=LoRARequest('speed-fixed-adapter',1,p['adapter']) if mode=='live' else None
    if adapter is not None and llm.llm_engine.add_lora(adapter) is not True:raise RuntimeError('live LoRA handoff failed')
    native=logpath.read_text()
    kv=h.graph_kv(native,torch.cuda.mem_get_info()[0]);r.write(folder/(mode+'-kv-post-graphs.json'),kv)
    load_seconds=time.monotonic()-started
    fixture=json.loads((HERE/'speed-assets/benchmark.json').read_text())
    # One fixed warmup for each engine. No scored request or outcome-driven retry.
    def request(batch,key):
        deadline(p)
        prompts=[]
        for messages in batch:
            ids=base.prompt_ids(tok,messages,True)
            if len(json.dumps(messages).encode())>128000 or len(ids)+64>16384:raise RuntimeError('unchanged context/wire guard')
            prompts.append({'prompt_token_ids':ids})
        params=llm.get_default_sampling_params().clone();params.max_tokens=64;params.min_tokens=64
        params.ignore_eos=True;params.seed=248021;params.skip_special_tokens=False
        start=time.monotonic();outputs=llm.generate(prompts,params,lora_request=adapter,use_tqdm=False)
        elapsed=time.monotonic()-start
        if len(outputs)!=2:raise RuntimeError('unexpected benchmark request count')
        tokens=0
        for index,result in enumerate(outputs):
            if len(result.outputs)!=1:raise RuntimeError('unexpected candidate count')
            o=result.outputs[0]
            if len(o.token_ids)!=64 or o.finish_reason!='length':raise RuntimeError('fixed64 timing reply not closed')
            tokens+=len(o.token_ids)
            event=dict(key=key+'/'+str(index),mode=mode,batch_seconds=elapsed,
                prompt_token_ids=prompts[index]['prompt_token_ids'],output_token_ids=list(o.token_ids),
                raw_text=o.text,finish_reason=o.finish_reason,stop_reason=o.stop_reason,
                excluded_from_science=True,engineering_only_ignore_eos=True)
            with (folder/(mode+'-benchmark-events.jsonl')).open('a') as f:f.write(json.dumps(event)+'\n');f.flush();os.fsync(f.fileno())
        return tokens,elapsed
    _,warmup_seconds=request([s['turns'][0] for s in fixture['streams']],mode+'/fixed-warmup')
    results={c:dict(mode=mode,cache=c,requests=0,tokens=0,round_seconds=[]) for c in h.CACHE_MODES}
    # Two streams run concurrently; counterbalance cache policy order across rounds.
    for rep,order in enumerate((('cold','retained'),('retained','cold'))):
        for cache in order:
            round_start=time.monotonic()
            for turn in range(2):
                if turn==0 or cache=='cold':
                    if llm.reset_prefix_cache() is not True:raise RuntimeError('prefix cache reset not acknowledged')
                n,t=request([s['turns'][turn] for s in fixture['streams']],f'{mode}/{cache}/r{rep}/t{turn}')
                results[cache]['requests']+=2;results[cache]['tokens']+=n
            results[cache]['round_seconds'].append(time.monotonic()-round_start)
    memory=sampler.finish()
    if memory['measurement_failed']:raise RuntimeError('benchmark memory telemetry failed')
    r.write(folder/(mode+'-benchmark.json'),dict(status='COMPLETE',engine=config,load_seconds=load_seconds,warmup_seconds=warmup_seconds,
        cells=list(results.values()),kv=kv,memory=memory,graph_native_log_sha256=old.sha(logpath)))


def worker(volume,private,p):
    h=load('speed_policy','speed_policy.py');old=load('old_policy','stages_policy.py')
    r=load('shared_runtime','runtime.py');base=load('base','base_runtime.py');errors=load('errors','base_policy.py')
    import modal
    h.validate(p);h.verify_runtime(p)
    ledger=modal.Dict.from_name(h.LEDGER)
    if not ledger.put('speed/worker-once',dict(commit=p['commit']),skip_if_exists=True):raise RuntimeError('worker already claimed')
    folder=Path('/results/speed');folder.mkdir(exist_ok=False)
    started=time.monotonic();p=dict(p,deadline=started+h.SOFTWARE,folder=str(folder),
        adapter='/adapters/speed/contrary/final',merged='/adapters/speed/merged')
    report=dict(status='INCOMPLETE',commit=p['commit'],excluded_from_science=True,next_stage_approved=False)
    sampler=None
    try:
        sampler=base.MemorySampler()
        # Legacy trainer checks the archived CPU source commit/assets, not a new CPU run.
        # Actual executing speed revision/approval remain in execution_commit and outer receipt.
        training_payload=dict(p,arm='smoke',stage='smoke',execution_commit=p['commit'],
            commit=h.CPU_COMMIT,asset_sha256=h.CPU_ASSETS)
        training=r.train_child(training_payload,folder,Path('/adapters/speed/contrary'),p['deadline'],volume,private)
        training_wall=time.monotonic()-started
        phases={}
        for phase in ('live','merge','merged'):phases[phase]=run_child(phase,p,folder,volume,private)
        r.write(folder/'phase-wall-times.json',dict(training=training_wall,**phases))
        cells=[];serving_overheads={}
        for mode in h.MODES:
            b=json.loads((folder/(mode+'-benchmark.json')).read_text());cells.extend(b['cells'])
            serving_overheads[mode]=max(0,phases[mode]-sum(sum(c['round_seconds']) for c in b['cells']))
        selection=h.select(cells)
        counts=json.loads((folder/'training-token-counts.json').read_text())
        # Includes model load, save/hash/Volume commits, subprocess and warmup cost.
        overhead=max(0,training_wall-training['seconds'])+serving_overheads[selection['mode']]
        if selection['mode']=='merged':overhead+=phases['merge']
        report.update(status='COMPLETE',training=training,selection=selection,
            projection=h.project(selection,training,counts,overhead,p['available_credit_usd'],actual=p['actual_total_usd']),
            adapter_handoff_verified=True,merge_verified=True)
        report['memory']=sampler.finish();sampler=None
        if report['memory']['measurement_failed']:raise RuntimeError('whole-worker memory telemetry failed')
        # Clean engineering experiment end, all outputs excluded. On failure retain private assets.
        acq=load('acquisition','acquisition.py')
        acq.delete_adapters(Path('/adapters/speed'),folder/'deletion','clean excluded speed smoke end',private.commit,volume.commit)
    except BaseException as exc:
        report.update(errors.save_failure(folder/'failure.json',exc,'speed_worker'))
        ledger.put('STOP_FOR_REVIEW',dict(commit=p['commit']),skip_if_exists=True)
    finally:
        if sampler is not None:
            try:report['memory']=sampler.finish()
            except BaseException as exc:report.update(errors.save_failure(folder/'memory-failure.json',exc,'speed_telemetry'))
        report['software_wall_seconds']=time.monotonic()-started
        r.write(folder/'report.json',report);private.commit();volume.commit()
    return report


if __name__=='__main__':
    phase=sys.argv[1];p=json.loads(Path(sys.argv[2]).read_text());folder=Path(p['folder'])
    try:
        if phase=='merge':merge(p)
        elif phase in ('live','merged'):bench(dict(p,mode=phase))
        else:raise ValueError('no scientific execution stages in speed revision')
    except BaseException as exc:
        load('errors','base_policy.py').save_failure(folder/(phase+'-failure.json'),exc,phase);raise
