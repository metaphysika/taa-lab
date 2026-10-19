"""Remote-only engineering smoke and gated scientific arms. Never executed on import."""
import concurrent.futures
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import queue
import math
import re
import subprocess
import sys
import threading
import time

RUNTIME_ROOT=Path(__file__).resolve().parent
ASSETS=RUNTIME_ROOT/'assets'
ROOT=Path('/results')


def module(name,file):
    spec=importlib.util.spec_from_file_location(name,RUNTIME_ROOT/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def json_value(value):
    """Strict recursive JSON conversion; deterministic unordered collections, no repr fallback."""
    if value is None or type(value) in (str,bool,int):return value
    if type(value) is float:
        if not math.isfinite(value):raise TypeError('nonfinite number is not JSON')
        return value
    if type(value) is dict:
        if any(type(k) is not str for k in value):raise TypeError('JSON object keys must be strings')
        return {k:json_value(v) for k,v in value.items()}
    if type(value) in (list,tuple):return [json_value(x) for x in value]
    if type(value) in (set,frozenset):
        return sorted((json_value(x) for x in value),key=lambda x:json.dumps(x,sort_keys=True,allow_nan=False))
    raise TypeError('unsupported JSON type: '+type(value).__name__)


def loading_info_json(info):
    # Explicitly normalize the library's set-valued loading-info fields.
    return json_value(info)


def write(path,value):
    encoded=json.dumps(json_value(value),indent=2,allow_nan=False)+'\n'
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(encoded);temp.replace(path)


TARGETS=('q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj')


def expected_lora_architecture(config,settings):
    """Pure shape calculation; never allocate model weights or infer coverage from regex alone."""
    get=lambda key:config[key] if isinstance(config,dict) else getattr(config,key)
    layers=get('num_hidden_layers');types=get('layer_types')
    if (type(layers) is not int or layers<1 or len(types)!=layers
            or any(t not in ('sliding_attention','full_attention') for t in types)
            or get('attention_k_eq_v') is not True):
        raise RuntimeError('unexpected layer_types or attention_k_eq_v architecture')
    rank=settings['r'];hidden=get('hidden_size');intermediate=get('intermediate_size')
    if any(type(n) is not int or n<1 for n in (rank,hidden,intermediate,get('num_attention_heads'),
            get('num_key_value_heads'),get('num_global_key_value_heads'),get('head_dim'),get('global_head_dim'))):
        raise RuntimeError('positive integer architecture dimensions required')
    per_layer={};totals={t:0 for t in TARGETS}
    for i,kind in enumerate(types):
        sliding=kind=='sliding_attention'
        head=get('head_dim') if sliding else get('global_head_dim')
        query=get('num_attention_heads')*head
        kv=(get('num_key_value_heads') if sliding else get('num_global_key_value_heads'))*head
        shapes=dict(q_proj=[hidden,query],k_proj=[hidden,kv],o_proj=[query,hidden],
            gate_proj=[hidden,intermediate],up_proj=[hidden,intermediate],down_proj=[intermediate,hidden])
        if sliding:shapes['v_proj']=[hidden,kv]
        counts={t:int(t in shapes) for t in TARGETS}
        for target,n in counts.items():totals[target]+=n
        per_layer[str(i)]=dict(layer_type=kind,coverage=counts,linear_shapes=shapes,
            expected_trainable_parameters=sum(rank*sum(shape) for shape in shapes.values()))
    return dict(layers=layers,sliding_layers=types.count('sliding_attention'),
        full_attention_layers=types.count('full_attention'),targets=list(TARGETS),rank=rank,
        target_module_counts=totals,matched_module_count=sum(totals.values()),per_layer=per_layer,
        expected_trainable_parameters=sum(v['expected_trainable_parameters'] for v in per_layer.values()),
        disclosure='k_proj LoRA adapts both K and V in full-attention layers with attention_k_eq_v; no attention pathway is unadapted')


def lora_coverage(model,settings,report_path=None):
    expected=expected_lora_architecture(model.config.text_config,settings)
    counts={i:{t:0 for t in TARGETS} for i in expected['per_layer']};matched=[];errors=[];shapes={}
    for name,linear in model.named_modules():
        if not re.fullmatch(settings['target_modules'],name):continue
        match=re.search(r'\.layers\.(\d+)\.',name);target=name.rsplit('.',1)[-1]
        matched.append(name)
        if not match or match[1] not in counts or target not in TARGETS:
            errors.append('target outside expected text layers: '+name);continue
        layer=match[1];shape=expected['per_layer'][layer]['linear_shapes'].get(target)
        observed=[getattr(linear,'in_features',None),getattr(linear,'out_features',None)]
        shapes[name]=observed;counts[layer][target]+=1
        if shape is None or observed!=shape:errors.append('unexpected presence/dimensions: '+name)
    for i,row in expected['per_layer'].items():
        if counts[i]!=row['coverage']:errors.append('architecture-conditioned coverage differs in layer '+i)
    report=dict(**expected,matched_modules=matched,observed_per_layer=counts,
        observed_linear_shapes=shapes,status='STOP_FOR_REVIEW' if errors else 'PASS',coverage_errors=errors)
    if report_path is not None:write(report_path,report)
    if errors:raise RuntimeError('; '.join(errors))
    return report


def trainable_coverage(model,coverage,report_path=None):
    counts={i:0 for i in coverage['per_layer']};errors=[];outside=[]
    for name,param in model.named_parameters():
        if not param.requires_grad:continue
        match=re.search(r'\.layers\.(\d+)\.',name)
        if not match or match[1] not in counts:
            outside.append(dict(name=name,parameters=param.numel()));continue
        counts[match[1]]+=param.numel()
    if outside:errors.append('trainable parameters outside text-layer adapters')
    for i,n in counts.items():
        if n!=coverage['per_layer'][i]['expected_trainable_parameters']:
            errors.append('trainable parameters differ in layer '+i)
    actual=dict(trainable_parameters=sum(counts.values())+sum(x['parameters'] for x in outside),
        per_layer_trainable_parameters=counts,total_parameters=sum(p.numel() for p in model.parameters()),
        outside_text_layer_trainable=outside,trainable_errors=errors)
    report=dict(coverage,**actual);report['status']='STOP_FOR_REVIEW' if errors else 'PASS'
    if report_path is not None:write(report_path,report)
    if errors:raise RuntimeError('; '.join(errors))
    return actual


def end_of_turn_id(tokenizer,proof):
    """Compare actual tokenizer metadata with all 139 retained native stop events."""
    ids=tokenizer.encode('<turn|>',add_special_tokens=False)
    replies=proof.get('replies',[])
    if (ids!=[106] or tokenizer.convert_tokens_to_ids('<turn|>')!=106
            or 106 not in tokenizer.all_special_ids
            or tokenizer.decode([106],skip_special_tokens=False)!='<turn|>'
            or proof.get('source_commit')!='881361e34c8a4299edbc718a7ab1900a837df6cc'
            or proof.get('end_of_turn_token')!='<turn|>' or proof.get('token_id')!=106
            or len(replies)!=139 or len({x['request_id'] for x in replies})!=139
            or any(x['finish_reason']!='stop' or x['stop_reason']!=106 or x['last_token_id']!=106 for x in replies)
            or proof.get('all_native_decodings_end_turn') is not True):
        raise ValueError('single special <turn|> token must match v02416 native stop/EOS evidence')
    return 106


def training_example(tokenizer,messages,base,end_id):
    """Train on the exact served generation prefix, never completed-turn rendering."""
    if not messages or messages[-1].get('role')!='assistant' or not isinstance(messages[-1].get('content'),str):
        raise ValueError('one final assistant content string required')
    prefix=base.prompt_ids(tokenizer,messages[:-1],True)
    content=tokenizer.encode(messages[-1]['content'],add_special_tokens=False)
    if (end_id!=106 or not isinstance(content,list) or not content
            or any(type(x) is not int or x<0 for x in content)):
        raise ValueError('flat nonempty integer content IDs and checked end token required')
    full=prefix+content+[end_id]
    if len(full)>1024:raise ValueError('served-format training context exceeds 1024; no truncation')
    return dict(input_ids=full,attention_mask=[1]*len(full),labels=[-100]*len(prefix)+content+[end_id])


def dataset(tokenizer,arm,h,base):
    records=[json.loads(s) for s in (ASSETS/(arm+'-2000-train.jsonl')).read_text().splitlines()]
    order=json.loads((ASSETS/'training-order.json').read_text())['high']['record_ids']
    if len(records)!=2000 or len(order)!=2000 or len(set(order))!=2000:raise ValueError('unchanged 2000-example dose/order required')
    proof=json.loads((ASSETS/'observed-stop-v02416.json').read_text())
    end_id=end_of_turn_id(tokenizer,proof)
    return [training_example(tokenizer,records[int(key[1:])-1]['messages'],base,end_id) for key in order]


def data_summary(data):
    return dict(examples=len(data),tokens=sum(len(x['input_ids']) for x in data),
        supervised_tokens=sum(sum(t!=-100 for t in x['labels']) for x in data),
        max_sequence_tokens=max(len(x['input_ids']) for x in data),
        dataset_sha256=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest())


def cpu_tokenizer(h):
    import torch
    from importlib.metadata import version
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer
    if torch.cuda.device_count()!=0:raise RuntimeError('CPU pre-stage must have no GPU')
    packages={name:version(name) for name in h.PACKAGES}
    if packages!=h.PACKAGES:raise RuntimeError('CPU packages differ from reviewed GPU stack')
    folder=Path(snapshot_download(repo_id=h.MODEL,revision=h.REVISION,token=os.environ['HF_TOKEN'],
        allow_patterns=['config.json','generation_config.json','tokenizer.json','tokenizer_config.json',
            'tokenizer.model','special_tokens_map.json','chat_template.jinja','chat_templates/*.jinja']))
    tok=AutoTokenizer.from_pretrained(folder,local_files_only=True,trust_remote_code=False)
    metadata={name:json.loads((folder/name).read_text()) for name in ('config.json','generation_config.json') if (folder/name).is_file()}
    return tok,packages,metadata


def cpu_dataset_worker(volume,ledger,p):
    h=module('stages_policy','stages_policy.py');base=module('base_runtime','base_runtime.py')
    policy=module('base_policy','base_policy.py');h.validate(p);h.verify_remote(ASSETS,p)
    target=ROOT/'cpu';target.mkdir(parents=True,exist_ok=True)
    if not ledger.put('cpu/worker/tokenizer',dict(commit=p['commit']),skip_if_exists=True):
        raise RuntimeError('CPU worker previously claimed; no restart')
    report=dict(status='INCOMPLETE',commit=p['commit'],gpu_allocated=False,weights_downloaded=False,
        model_generation=False,training_steps=0,asset_sha256=p['asset_sha256'])
    started=time.monotonic()
    try:
        tok,packages,metadata=cpu_tokenizer(h)
        proof=json.loads((ASSETS/'observed-stop-v02416.json').read_text());end_id=end_of_turn_id(tok,proof)
        write(target/'tokenizer.json',dict(model=h.MODEL,revision=h.REVISION,packages=packages,
            chat_template=tok.chat_template,eos_token_id=tok.eos_token_id,end_of_turn_id=end_id,
            model_and_generation_config=metadata,observed_stop_evidence=proof,
            disclosure='served generation prefix with empty thought channel, not completed assistant render'))
        summaries={}
        for arm in ('contrary','virtue','neutral'):
            if time.monotonic()-started>h.CPU_SOFTWARE:raise RuntimeError('CPU data-building time guard')
            data=dataset(tok,arm,h,base);summaries[arm]=data_summary(data)
            examples=[]
            order=json.loads((ASSETS/'training-order.json').read_text())['high']['record_ids']
            for i,row in enumerate(data[:3]):
                prefix_length=next(j for j,label in enumerate(row['labels']) if label!=-100)
                examples.append(dict(record_id=order[i],**row,supervised=[x!=-100 for x in row['labels']],
                    decoded_full=tok.decode(row['input_ids'],skip_special_tokens=False),
                    decoded_prefix=tok.decode(row['input_ids'][:prefix_length],skip_special_tokens=False),
                    decoded_supervised=tok.decode(row['input_ids'][prefix_length:],skip_special_tokens=False),
                    token_pieces=tok.convert_ids_to_tokens(row['input_ids'])))
            write(target/(arm+'-first3-supervision.json'),examples)
        real=expected_lora_architecture(metadata['config.json']['text_config'],h.LORA)
        if (real['layers'],real['full_attention_layers'],real['matched_module_count'],real['expected_trainable_parameters'])!=(60,10,410,61214720):
            raise RuntimeError('pinned real-model architecture/counts differ')
        write(target/'architecture-expected-real-model.json',real)
        rehearsal=cpu_rehearsal(target,tok,metadata,p,h,volume)
        report.update(status='PASS',expected_real_trainable_parameters=real['expected_trainable_parameters'],rehearsal_pass=True,training_steps=2,vllm_adapter_load_tested=False,summaries=summaries,packages=packages,model=h.MODEL,revision=h.REVISION,
            end_of_turn_id=end_id,software_wall_seconds=time.monotonic()-started)
        write(target/'report.json',report)
        names=['report.json','tokenizer.json','rehearsal-integrity.json','architecture-expected-real-model.json']+[a+'-first3-supervision.json' for a in ('contrary','virtue','neutral')]
        receipt=dict(status='PASS',commit=p['commit'],asset_sha256=p['asset_sha256'],model=h.MODEL,revision=h.REVISION,
            packages=packages,summaries=summaries,end_of_turn_id=end_id,gpu_allocated=False,weights_downloaded=False,
            training_steps=2,model_generation=False,rehearsal_pass=True,vllm_adapter_load_tested=False,evidence_sha256={name:h.sha(target/name) for name in names})
        write(target/'receipt.json',receipt);volume.commit()
        if not ledger.put('cpu/pass',dict(status='PASS',commit=p['commit'],receipt_sha256=h.sha(target/'receipt.json')),skip_if_exists=True):
            raise RuntimeError('CPU proof already exists')
    except BaseException as exc:
        report.update(policy.save_failure(target/'failure.json',exc,'tokenizer_dataset_cpu'))
        write(target/'report.json',report);volume.commit()
    return report


def tiny_config_values(original):
    """Shared CPU-only random model dimensions; keep real vocabulary/token IDs."""
    config=json.loads(json.dumps(original))
    config['vision_config']=None;config['audio_config']=None
    text=config['text_config']
    text.update(hidden_size=32,intermediate_size=64,num_hidden_layers=2,
        num_attention_heads=4,num_key_value_heads=2,num_global_key_value_heads=2,
        head_dim=8,global_head_dim=8,max_position_embeddings=1024,
        layer_types=['sliding_attention','full_attention'],num_kv_shared_layers=0)
    # Keep the real vocabulary and served token IDs: examples are never remapped.
    return config


def cpu_rehearsal(target,tok,metadata,p,h,volume):
    import torch
    from transformers import Gemma4Config,Gemma4ForConditionalGeneration
    if torch.cuda.device_count()!=0:raise RuntimeError('no GPU in CPU rehearsal')
    config=tiny_config_values(metadata['config.json'])
    tiny=Gemma4Config.from_dict(config)
    torch.manual_seed(247056)
    model=Gemma4ForConditionalGeneration(tiny).float()
    folder=target/'rehearsal';folder.mkdir()
    checkpoint=folder/'random-base';model.save_pretrained(checkpoint,safe_serialization=True)
    del model
    tokenizer=folder/'tokenizer';tok.save_pretrained(tokenizer)
    proof=folder/'data-proof.json'
    write(proof,dict(summaries={a:data_summary(dataset(tok,a,h,module('cpu_base','base_runtime.py'))) for a in ('contrary','neutral','virtue')}))
    payload=dict(p,arm='smoke',cpu_rehearsal=True,folder=str(folder),
        adapter=str(folder/'adapter'),tiny_checkpoint=str(checkpoint),tokenizer_path=str(tokenizer),
        dataset_proof=str(proof),deadline=time.monotonic()+h.CPU_SOFTWARE-90)
    write(folder/'input.json',payload)
    # Same actual training_process entry, never a stand-in trainer.
    with (folder/'process.log').open('w') as log:
        child=subprocess.Popen([sys.executable,__file__,'train',str(folder/'input.json')],stdout=log,stderr=log)
        try:
            code=child.wait(timeout=h.CPU_SOFTWARE-90)
        except BaseException:
            child.terminate()
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:child.kill();child.wait()
            raise
    policy=module('cpu_log_policy','base_policy.py')
    (folder/'process.log').write_text(policy.redact((folder/'process.log').read_text()))
    if code:raise RuntimeError('CPU actual training_process failed; see rehearsal/process.log and training-failure.json')
    report=json.loads((folder/'training.json').read_text())
    if report['optimizer_steps']!=2 or json.loads((folder/'adapter-reload.json').read_text())['status']!='PASS':
        raise RuntimeError('CPU training/reload incomplete')
    for path in (folder/'adapter/final').iterdir():
        if path.is_file() and path.name!='checkpoint-integrity.json':
            expected=json.loads((folder/'adapter/final/checkpoint-integrity.json').read_text())['sha256']
            if h.sha(path)!=expected[path.name]:raise RuntimeError('adapter integrity failed')
    receipt=dict(status='PASS',optimizer_steps=2,vllm_adapter_load_tested=False,
        disclosure='tiny random text-only model, real vocabulary/examples, CPU float32 not scientific bf16 GPU training',
        sha256={str(f.relative_to(target)):h.sha(f) for f in folder.rglob('*') if f.is_file()})
    write(target/'rehearsal-integrity.json',receipt);volume.commit()
    return receipt


def verify_adapter_reload(model,config,p,adapter,out):
    import torch
    from transformers import Gemma4ForConditionalGeneration
    from peft import PeftModel,get_peft_model_state_dict
    before={k:v.detach().cpu().clone() for k,v in get_peft_model_state_dict(model).items()}
    fresh=Gemma4ForConditionalGeneration.from_pretrained(p['tiny_checkpoint'],config=config,
        local_files_only=True,dtype=torch.float32,device_map={'':'cpu'},attn_implementation='sdpa')
    loaded=PeftModel.from_pretrained(fresh,str(adapter/'final'),is_trainable=False,local_files_only=True)
    after=get_peft_model_state_dict(loaded)
    if before.keys()!=after.keys() or any(not torch.equal(v,after[k].cpu()) for k,v in before.items()):
        raise RuntimeError('adapter reload tensor mismatch')
    write(out/'adapter-reload.json',dict(status='PASS',tensor_count=len(before),vllm_tested=False))


CI_TRAINING_PACKAGES=('torch','transformers','peft','accelerate','huggingface-hub')


def ci_tensor_data(arm,fixture_path):
    fixture=json.loads(Path(fixture_path).read_text())
    if fixture.get('source_commit')!='59082c45e365aeb056e67496e4e0c6c565786933':
        raise RuntimeError('unrecognized real-tokenizer CI fixture provenance')
    rows=fixture['arms'][arm]
    if len(rows)!=3:raise RuntimeError('exact three frozen real-tokenizer examples per arm required')
    result=[]
    for row in rows:
        ids=row['input_ids'];labels=row['labels'];mask=row['attention_mask']
        if (not ids or len(ids)>1024 or len(labels)!=len(ids) or mask!=[1]*len(ids)
                or any(type(x) is not int or not 0<=x<262144 for x in ids) or ids[-1]!=106):
            raise RuntimeError('invalid frozen CI token IDs/mask')
        first=next((i for i,x in enumerate(labels) if x!=-100),None)
        if first is None or first<1 or labels[:first]!=[-100]*first or labels[first:]!=ids[first:]:
            raise RuntimeError('invalid frozen served-prefix CI loss mask')
        result.append(dict(input_ids=ids,labels=labels,attention_mask=mask))
    # 18 diagnostic microbatches supply the first 16 for two accumulation-8 steps.
    # This is neither a 2,000-example arm nor a substitute for Modal tokenization.
    return result*6


def ci_formatted_data(arm,fixture_path,base):
    """Actual formatter + actual pinned BatchEncoding, with frozen real-tokenizer ID lookup.

    This verifies formatting/tensor assembly without claiming to rerun HF tokenization.
    Unknown inputs or completed-turn rendering fail instead of inventing token IDs.
    """
    from transformers import BatchEncoding
    rows=json.loads(Path(fixture_path).read_text())['arms'][arm]
    results=[]
    for row in rows:
        first=next(i for i,x in enumerate(row['labels']) if x!=-100)
        class FrozenIDLookup:
            def apply_chat_template(self,messages,*,tokenize,add_generation_prompt,return_dict):
                if return_dict is not True or tokenize is not True or add_generation_prompt is not True or messages!=row['messages'][:-1]:
                    raise RuntimeError('CI frozen-ID lookup requires exact served-generation input')
                return BatchEncoding(dict(input_ids=row['input_ids'][:first],attention_mask=[1]*first))
            def encode(self,text,*,add_special_tokens):
                if add_special_tokens is not False or text!=row['messages'][-1]['content']:
                    raise RuntimeError('unknown CI content; no invented tokenization')
                return row['input_ids'][first:-1]
        result=training_example(FrozenIDLookup(),row['messages'],base,106)
        expected={k:row[k] for k in ('input_ids','labels','attention_mask')}
        if result!=expected:raise RuntimeError('actual served-format assembly differs from frozen real-tokenizer IDs')
        results.append(result)
    if results*6!=ci_tensor_data(arm,fixture_path):raise RuntimeError('frozen CI fixture validation differs')
    return results*6


def training_process(payload_file):
    """Separate process owns HF model/optimizer; its exit frees GPU before vLLM."""
    h=module('stage_policy','stages_policy.py');base=module('base_runtime','base_runtime.py')
    p=json.loads(Path(payload_file).read_text());out=Path(p['folder']);adapter=Path(p['adapter'])
    policy=module('base_policy','base_policy.py')
    try:
        import torch
        from transformers import AutoConfig,AutoTokenizer,Gemma4ForConditionalGeneration,Trainer,TrainingArguments,TrainerCallback
        from peft import LoraConfig,get_peft_model
        from importlib.metadata import version
        pins=h.PACKAGES
        ci=p.get('ci_cpu_rehearsal') is True
        if ci and (p.get('stage')!='ci_cpu_rehearsal' or p.get('cpu_rehearsal') is not True):
            raise RuntimeError('CI tensor fixtures restricted to diagnostic CPU rehearsal')
        checked=CI_TRAINING_PACKAGES if ci else tuple(pins)
        observed={k:version(k) for k in checked}
        normalized={k:(v.removesuffix('+cpu') if ci and k=='torch' else v) for k,v in observed.items()}
        if any(normalized[k]!=pins[k] for k in checked):raise RuntimeError('reviewed training/serving packages differ')
        if ci and not observed['torch'].endswith('+cpu'):raise RuntimeError('CI must install CPU-only torch build')
        write(out/'packages.json',dict(observed=observed,normalized=normalized,ci_cpu_build=ci))
        started=time.monotonic()
        rehearsal=p.get('cpu_rehearsal') is True
        if rehearsal and torch.cuda.device_count()!=0:raise RuntimeError('CPU rehearsal must not have GPU')
        if ci:
            from types import SimpleNamespace
            tok=SimpleNamespace(pad_token_id=0,eos_token_id=106)
            data_provider=lambda arm:ci_formatted_data(arm,p['ci_fixture'],base)
        else:
            tok=AutoTokenizer.from_pretrained(p['tokenizer_path'],local_files_only=True,trust_remote_code=False) if rehearsal else AutoTokenizer.from_pretrained(h.MODEL,revision=h.REVISION,token=os.environ['HF_TOKEN'],trust_remote_code=False)
            data_provider=lambda arm:dataset(tok,arm,h,base)
        data=data_provider('contrary' if p['arm']=='smoke' else p['arm'])
        counts={a:data_summary(data_provider(a)) for a in ('contrary','neutral','virtue')}
        cpu_receipt=json.loads(Path(p['dataset_proof']).read_text()) if rehearsal else h.require_cpu(ROOT,p)
        if counts!=cpu_receipt['summaries']:raise RuntimeError('GPU-built training data differ from CPU PASS receipt')
        write(out/'training-token-counts.json',counts)
        config=AutoConfig.from_pretrained(p['tiny_checkpoint'],local_files_only=True,trust_remote_code=False) if rehearsal else AutoConfig.from_pretrained(h.MODEL,revision=h.REVISION,token=os.environ['HF_TOKEN'],trust_remote_code=False)
        # Text-only training matches vLLM language_model_only; no vision/audio adapters.
        config.vision_config=None;config.audio_config=None
        load_kwargs=dict(config=config,dtype=torch.float32 if rehearsal else torch.bfloat16,device_map={'':'cpu' if rehearsal else 'cuda:0'},attn_implementation='sdpa',trust_remote_code=False,output_loading_info=True)
        if rehearsal:load_kwargs['local_files_only']=True
        else:load_kwargs.update(revision=h.REVISION,token=os.environ['HF_TOKEN'])
        model,info=Gemma4ForConditionalGeneration.from_pretrained(p['tiny_checkpoint'] if rehearsal else h.MODEL,**load_kwargs)
        if info.get('missing_keys') or info.get('mismatched_keys') or info.get('error_msgs'):
            raise RuntimeError('base text weights incomplete; no random replacement weights')
        unexpected=info.get('unexpected_keys',[])
        if any(not any(s in key for s in ('vision_tower','audio_tower','embed_vision','embed_audio')) for key in unexpected):
            raise RuntimeError('unexpected non-vision/audio checkpoint keys')
        write(out/'training-load.json',dict(seconds=time.monotonic()-started,loading_info=loading_info_json(info),
            packages=pins,text_only=True,model=h.MODEL,revision=h.REVISION))
        coverage=lora_coverage(model,h.LORA,out/'lora-coverage-before-injection.json')
        torch.manual_seed(247056);model=get_peft_model(model,LoraConfig(**h.LORA))
        trainable_coverage(model,coverage,out/'lora-coverage.json')
        model.config.use_cache=False;model.enable_input_require_grads();model.gradient_checkpointing_enable()
        for row in data:
            first=next(i for i,x in enumerate(row['labels']) if x!=-100)
            if first<1 or row['labels'][first:]!=row['input_ids'][first:] or row['labels'][-1]!=106:
                raise RuntimeError('assistant-only served-format loss mask invalid')
        write(out/'masking.json',dict(status='PASS',examples=len(data),prefix_masked=True,end_of_turn_supervised=True))
        train_start=time.monotonic()
        def checkpoint(label,complete=False):
            dest=adapter/label;dest.mkdir(parents=True,exist_ok=False)
            model.save_pretrained(dest,safe_serialization=True)
            write(dest/'checkpoint-integrity.json',dict(arm=p['arm'],complete=complete,
                scientific_checkpoint=p['arm']!='smoke' and complete,
                sha256={f.name:h.sha(f) for f in dest.iterdir() if f.is_file()}))
        class Timer(TrainerCallback):
            def on_step_begin(self,args,state,control,**kw):
                if time.monotonic()+90>=p['deadline']:raise RuntimeError('training deadline; retain private adapter')
            def on_step_end(self,args,state,control,**kw):
                processed=min(2000,int(state.global_step)*8)
                write(out/'training-progress.json',dict(optimizer_steps=int(state.global_step),processed_examples=processed,
                    processed_tokens=sum(len(r['input_ids']) for r in data[:processed]),seconds=time.monotonic()-train_start))
                if state.global_step%(2 if p['arm']=='smoke' else 25)==0:checkpoint('step-'+str(state.global_step))
        class FixedTrainer(Trainer):
            def _get_train_sampler(self,*args,**kwargs):return torch.utils.data.SequentialSampler(self.train_dataset)
        def collate(batch):
            size=max(len(r['input_ids']) for r in batch)
            pad=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
            return {k:torch.tensor([r[k]+[(-100 if k=='labels' else 0 if k=='attention_mask' else pad)]*(size-len(r[k])) for r in batch]) for k in ('input_ids','attention_mask','labels')}
        args=TrainingArguments(output_dir=str(out/'optimizer-temporary'),num_train_epochs=1,
            max_steps=2 if rehearsal else h.SMOKE_STEPS if p['arm']=='smoke' else -1,learning_rate=.0002,
            per_device_train_batch_size=1,gradient_accumulation_steps=8,bf16=not rehearsal,use_cpu=rehearsal,
            optim='adamw_torch',weight_decay=0,lr_scheduler_type='constant',warmup_steps=0,
            seed=247056,data_seed=247056,save_strategy='no',logging_strategy='no',
            report_to=[],disable_tqdm=True,gradient_checkpointing=True,dataloader_num_workers=0)
        trainer=FixedTrainer(model=model,args=args,train_dataset=data,data_collator=collate,callbacks=[Timer()])
        try:trainer.train()
        except BaseException:
            checkpoint('interrupted-'+str(trainer.state.global_step));raise
        expected=2 if rehearsal else h.SMOKE_STEPS if p['arm']=='smoke' else 250
        if trainer.state.global_step!=expected:raise RuntimeError('wrong optimizer step count')
        checkpoint('final',True)
        processed=16 if rehearsal else h.SMOKE_STEPS*8 if p['arm']=='smoke' else 2000
        if rehearsal:
            verify_adapter_reload(model,config,p,adapter,out)
        write(out/'training.json',dict(status='COMPLETE',optimizer_steps=expected,processed_examples=processed,
            processed_tokens=sum(len(r['input_ids']) for r in data[:processed]),seconds=time.monotonic()-train_start,
            excludes_science=p['arm']=='smoke',cpu_rehearsal=rehearsal,
            settings=dict(h.TRAIN,bf16=not rehearsal,use_cpu=rehearsal,effective_optimizer_steps=expected),lora=h.LORA))
    except BaseException as exc:
        policy.save_failure(out/'training-failure.json',exc,'training_subprocess');raise


class Serving:
    """One engine-owner thread; two independent episode threads queue native requests.

    vLLM owns KV-block admission/preemption: two sequences do not imply two
    resident 16K caches. No context reduction, trimming, repair or output retry.
    """
    def __init__(self,h,base,folder,volume,ledger,deadline,adapter):
        self.h=h;self.base=base;self.folder=folder;self.volume=volume;self.ledger=ledger
        self.deadline=deadline;self.requests=queue.Queue();self.pending={};self.lock=threading.Lock()
        self.tokens=0;self.generation_seconds=0;self.last_stop_check=0;self.failed=None
        self.event(event='serving_load_start',engine=h.ENGINE,adapter_path=str(adapter))
        import torch
        from vllm import LLM
        from vllm.engine.arg_utils import EngineArgs
        from vllm.lora.request import LoRARequest
        if torch.cuda.device_count()!=1 or 'A100' not in torch.cuda.get_device_name(0) or torch.cuda.get_device_properties(0).total_memory<78*2**30:
            raise RuntimeError('single A100 80GB required')
        sampler=base.MemorySampler();policy=module('base_policy','base_policy.py')
        prediction=policy.kv_prediction(torch.cuda.get_device_properties(0).total_memory,sampler.baseline)
        write(folder/'kv-prediction.json',prediction)
        if prediction['status']!='PASS':raise RuntimeError('historical predictive KV guard failed')
        start=time.monotonic();self.llm=LLM.from_engine_args(EngineArgs(**h.ENGINE));self.engine=self.llm.llm_engine
        self.tok=self.llm.get_tokenizer();self.adapter=LoRARequest('study-d-'+folder.name,1,str(adapter))
        # Explicitly add/load the actual trained adapter before either acquisition or transfer.
        if self.engine.add_lora(self.adapter) is not True:raise RuntimeError('adapter load not acknowledged')
        current=policy.current_kv_preflight((folder/'vllm-engine.log').read_text())
        write(folder/'kv-current.json',current)
        if current['status']!='PASS':raise RuntimeError('current KV guard failed')
        write(folder/'serving-load.json',dict(seconds=time.monotonic()-start,engine=h.ENGINE,
            adapter=str(adapter),adapter_loaded=True,native_chat_template=self.tok.chat_template,
            thinking='native empty thought channel disables thinking; unchanged',
            max_num_seqs=2,enforce_eager=True))
        sampler.finish()
        self.event(event='adapter_handoff_verified',adapter=str(adapter),active=True)

    def event(self,**data):
        with self.lock:
            with (self.folder/'events.jsonl').open('a') as f:
                f.write(json.dumps(dict(utc=time.time(),**data))+'\n');f.flush();os.fsync(f.fileno())
            self.volume.commit()

    def guard(self):
        now=time.monotonic()
        if now+30>=self.deadline:raise RuntimeError('worker time guard; no later generation')
        if now-self.last_stop_check>5:
            self.last_stop_check=now
            if self.ledger.contains('STOP_FOR_REVIEW'):raise RuntimeError('another worker stopped; review required')

    def generate(self,messages,key,seed,max_tokens=4096):
        if len(json.dumps(messages,ensure_ascii=False).encode())>128000:raise RuntimeError('wire guard; no trim')
        ids=self.base.prompt_ids(self.tok,messages,True)
        if len(ids)+max_tokens>16384:raise RuntimeError('context guard; no trim')
        params=self.llm.get_default_sampling_params().clone();params.max_tokens=max_tokens
        params.seed=seed;params.skip_special_tokens=False
        f=concurrent.futures.Future()
        with self.lock:
            if self.failed is not None:raise self.failed
            self.requests.put((key,messages,ids,params,f))
        return f.result()

    def run(self,jobs):
        start=time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(job) for job in jobs]
            try:
                while not all(f.done() for f in futures):
                    self.guard()
                    for task in futures:
                        if task.done() and not task.cancelled() and task.exception() is not None:raise task.exception()
                    while True:
                        try:key,messages,ids,params,f=self.requests.get_nowait()
                        except queue.Empty:break
                        if key in self.pending:raise RuntimeError('duplicate request ID')
                        self.event(event='generation_start',request_id=key,messages=messages,prompt_token_ids=ids,
                            sampling_params=str(params),active_adapter=str(self.adapter),no_resend=True)
                        self.pending[key]=dict(future=f,started=time.monotonic(),last=None)
                        self.engine.add_request(key,{'prompt_token_ids':ids},params,lora_request=self.adapter)
                    if not self.pending:time.sleep(.005);continue
                    for result in self.engine.step():
                        if result.request_id not in self.pending:raise RuntimeError('unexpected native request ID')
                        entry=self.pending[result.request_id];entry['last']=result
                        if result.finished:
                            if len(result.outputs)!=1:raise RuntimeError('wrong native candidate count')
                            o=result.outputs[0];self.tokens+=len(o.token_ids)
                            self.event(event='generation_return',request_id=result.request_id,raw_text=o.text,
                                output_token_ids=list(o.token_ids),finish_reason=o.finish_reason,stop_reason=o.stop_reason,
                                wall_seconds=time.monotonic()-entry['started'],active_adapter=str(self.adapter))
                            del self.pending[result.request_id];entry['future'].set_result(o.text)
                    if any(time.monotonic()-p['started']>600 for p in self.pending.values()):
                        raise RuntimeError('native reply deadline; retain partial, no resend')
                return [f.result() for f in futures]
            except BaseException as exc:
                # Persist/abort every issued request; also unblock queued episode threads.
                with self.lock:self.failed=exc
                # Unblock episode threads BEFORE I/O or abort calls, which may also fail.
                pending=dict(self.pending)
                for entry in pending.values():entry['future'].set_exception(exc)
                self.pending.clear()
                while not self.requests.empty():self.requests.get_nowait()[-1].set_exception(exc)
                for task in futures:task.cancel()
                try:self.engine.abort_request(list(pending))
                except BaseException as abort_error:
                    self.event(event='abort_failed',error_type=type(abort_error).__name__,no_resend=True)
                for key,p in pending.items():
                    last=p['last'];self.event(event='generation_interrupted',request_id=key,no_resend=True,
                        raw_text=None if last is None else last.outputs[0].text,
                        output_token_ids=[] if last is None else list(last.outputs[0].token_ids))
                raise
            finally:self.generation_seconds+=time.monotonic()-start


def train_child(payload,folder,adapter,deadline,volume,private):
    p=dict(payload,folder=str(folder),adapter=str(adapter),deadline=deadline)
    write(folder/'trainer-input.json',p)
    with (folder/'training-process.log').open('w') as log:
        committed=set()
        process=subprocess.Popen([sys.executable,__file__,'train',str(folder/'trainer-input.json')],stdout=log,stderr=log)
        try:
            while process.poll() is None:
                if time.monotonic()+75>=deadline:raise RuntimeError('training deadline reached')
                ready={str(f) for f in adapter.glob('*/checkpoint-integrity.json')}
                if ready-committed:private.commit();committed=ready
                time.sleep(2)
            if process.returncode:raise RuntimeError('training subprocess failed; see private adapter and full training failure')
        finally:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait()
            path=folder/'training-process.log'
            policy=module('trainer_log_policy','base_policy.py')
            path.write_text(policy.redact(path.read_text()))
            private.commit();volume.commit()
    if not (adapter/'final/checkpoint-integrity.json').exists():raise RuntimeError('no completed adapter checkpoint')
    return json.loads((folder/'training.json').read_text())


def arm_worker(volume,private,ledger,p):
    h=module('stages_policy','stages_policy.py');base=module('base_runtime','base_runtime.py')
    policy=module('base_policy','base_policy.py');acq=module('acquisition_policy','acquisition.py')
    h.validate(p);h.verify_remote(ASSETS,p)
    h.require_cpu(ROOT,p,ledger if p['stage']=='smoke' else None)
    arm=p['arm'];stage=p['stage'];folder=ROOT/stage/arm;folder.mkdir(parents=True,exist_ok=False)
    if arm not in h.STAGES[stage]['arms'] or not ledger.put(stage+'/worker/'+arm,dict(commit=p['commit']),skip_if_exists=True):
        raise RuntimeError('unplanned/previous worker; never restart')
    worker_started=time.monotonic();deadline=worker_started+h.STAGES[stage]['software'];sampler=None
    report=dict(status='INCOMPLETE',arm=arm,stage=stage,commit=p['commit'],engine=h.ENGINE,
        training_authorized_for_other_stages=False,excluded_from_science=stage=='smoke')
    try:
        sampler=base.MemorySampler();started=time.monotonic()
        adapter=(Path('/adapters/smoke/contrary') if stage=='smoke' else Path('/adapters/science')/arm)
        training=train_child(p,folder,adapter,deadline,volume,private)
        # No trainer object/GPU tensor lives in this process; child has fully exited.
        os.environ['VLLM_LOGGING_CONFIG_PATH']='/opt/study-d/assets/vllm-logging.json'
        # Logging configuration uses one unique path per worker to avoid overwrites.
        logging=json.loads((ASSETS/'vllm-logging.json').read_text())
        for handler in logging['handlers'].values():
            if 'filename' in handler:handler['filename']=str(folder/'vllm-engine.log')
        write(folder/'logging.json',logging);os.environ['VLLM_LOGGING_CONFIG_PATH']=str(folder/'logging.json')
        session=Serving(h,base,folder,volume,ledger,deadline,adapter/'final')
        plan=base.install_frozen_bundle()
        from formation.study_d_base_gate_v0248 import evaluate_episode
        def episode(case,rep,index,smoke=False):
            def generate(system,history,turn):
                return session.generate([dict(role='system',content=system)]+history,
                    f"{arm}/{case['id']}/r{rep}/t{turn}",247053+index+turn-1)
            r=evaluate_episode(case,generate);r.update(repeat=rep,excluded_from_science=smoke)
            write(folder/('smoke-episodes' if smoke else 'transfer')/f"{case['id']}-r{rep}.json",r);volume.commit();return r
        if stage=='smoke':
            cases={c['case']['id']:c['case'] for c in plan['cases']}
            rows=session.run([lambda c=cases[k],i=i:episode(c,1,i,True) for i,k in enumerate(h.SMOKE_CASES)])
            report.update(status='COMPLETE',training=training,episodes=len(rows),adapter_handoff_verified=True,
                generation=dict(tokens=session.tokens,seconds=session.generation_seconds),
                load_and_handoff_seconds=time.monotonic()-started-training['seconds']-session.generation_seconds)
            counts=json.loads((folder/'training-token-counts.json').read_text())
            report['projection']=h.measurable_projection(report,counts)
        else:
            def checks(name,score_arm,seed):
                check=json.loads((ASSETS/name).read_text())
                rows=session.run([lambda c=c,i=i:acq.score_acquisition(
                    session.generate(c['messages'],arm+'/'+name+'/'+c['id'],seed+i,512),c,score_arm)
                    for i,c in enumerate(check)])
                write(folder/name,rows);volume.commit();return rows
            ordered=checks('ordered-acquisition.json',arm,247053)
            own=checks('neutral-acquisition.json',arm,247153) if arm=='neutral' else ordered
            ledger.put(stage+'/acquisition/'+arm,dict(own=own,ordered=ordered),skip_if_exists=True)
            while not ledger.contains(stage+'/decisions'):
                session.guard();time.sleep(2)
            decisions=ledger[stage+'/decisions'];write(folder/'acquisition-gate.json',decisions[arm]);volume.commit()
            if not decisions[arm]['transfer_allowed']:raise RuntimeError('acquisition failed; transfer uninterpretable, not null')
            checks('spontaneous.json',arm,247253)  # Descriptive only, cannot affect admission.
            probes=json.loads((ASSETS/'transfer-cases.json').read_text())
            import random
            schedule=[(q['case'],r) for q in probes for r in range(1,5)];random.Random(247053).shuffle(schedule)
            rows=session.run([lambda c=c,r=r,i=i:episode(c,r,i) for i,(c,r) in enumerate(schedule)])
            if len(rows)!=132:raise RuntimeError('incomplete planned transfer')
            report.update(status='COMPLETE',training=training,transfer_episodes=132,
                bounds=h.planned_bounds(rows,[q['case'] for q in probes]),
                acquisition=decisions[arm],neutral_ordered=ordered if arm=='neutral' else None)
    except BaseException as exc:
        report.update(policy.save_failure(folder/'failure.json',exc,'arm_worker'))
        ledger.put('STOP_FOR_REVIEW',dict(stage=stage,arm=arm),skip_if_exists=True)
    finally:
        if sampler is not None:
            try:
                report['memory']=sampler.finish()
                if report['memory']['measurement_failed']:raise RuntimeError('sampled memory telemetry failed')
            except BaseException as exc:report.update(policy.save_failure(folder/'memory-failure.json',exc,'telemetry'))
        if stage=='smoke' and report['status']=='COMPLETE':
            try:acq.delete_adapters(Path('/adapters/smoke'),folder/'deletion','clean excluded smoke end',private.commit,volume.commit)
            except BaseException as exc:report.update(policy.save_failure(folder/'deletion-failure.json',exc,'smoke_deletion'))
        report['software_wall_seconds']=time.monotonic()-worker_started
        write(folder/'report.json',report);private.commit();volume.commit()
    return report


if __name__=='__main__' and len(sys.argv)==3 and sys.argv[1]=='train':training_process(sys.argv[2])
