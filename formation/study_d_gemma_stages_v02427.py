"""Reviewed three-stage policy. Pure offline helpers; imports allocate no resources."""
import hashlib
import json
import math
import importlib.util
import re
from datetime import datetime, timezone
from pathlib import Path

VERSION='v02427'
MODEL='google/gemma-4-31B-it'
REVISION='842da3794eaa0b77d5f08bae87a17459d91ff475'
LEDGER='taa-study-d-gemma-v02427-budget-once'
VOLUME='taa-study-d-gemma-v02427-evidence'
PRIVATE='taa-study-d-gemma-v02427-private-adapters'
CAP=36.0
PRIOR=19.67
CREDIT=10.39
RATE=3.20
STARTUP=120
IDLE=2
SMOKE_STEPS=8  # 64 microbatches/examples; never a scientific checkpoint.
CPU_RATE=.35
CPU_SOFTWARE=1100
PACKAGES={'vllm':'0.31.0','transformers':'5.10.4','torch':'2.13.0','huggingface-hub':'1.31.0',
          'nvidia-ml-py':'13.580.82','peft':'0.21.2','accelerate':'1.15.0'}
STAGES={'virtue':dict(arms=['virtue'],target=9.20,timeout=9800,software=9600,overhead=.375)}
ENGINE=dict(model=MODEL,revision=REVISION,tokenizer_revision=REVISION,dtype='bfloat16',
    quantization=None,tensor_parallel_size=1,max_model_len=16384,max_num_seqs=2,
    gpu_memory_utilization=.95,enable_lora=True,max_lora_rank=8,max_loras=1,
    language_model_only=True,enforce_eager=False,trust_remote_code=False,
    generation_config='auto',seed=248017,enable_prefix_caching=True,disable_log_stats=True,
    compilation_config=dict(cudagraph_specialize_lora=True,cudagraph_capture_sizes=[1,2],max_cudagraph_capture_size=2))
LORA=dict(r=8,lora_alpha=16,lora_dropout=0,bias='none',task_type='CAUSAL_LM',
    target_modules=r'.*language_model.*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)')
TRAIN=dict(examples=2000,epochs=1,learning_rate=.0002,batch=1,accumulate=8,
    context=1024,seed=247056,bf16=True,optimizer='adamw_torch',scheduler='constant',
    weight_decay=0,warmup_steps=0,gradient_checkpointing=True,assistant_only=True)
SMOKE_CASES=('C-brake-r1-W','C-brake-r1-U')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def required_assets(folder):
    path=Path(__file__).resolve().parent/'assets_check.py'
    if not path.exists():path=Path(__file__).resolve().parents[1]/'scripts/study_d_gemma_assets_v02427.py'
    spec=importlib.util.spec_from_file_location('asset_contract',path)
    contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)
    return contract.required_assets(folder)


def verify_assets(folder):
    folder=Path(folder); m=json.loads((folder/'integrity-v02427.json').read_text())
    for name,want in m['sha256'].items():
        if sha(folder/name)!=want:raise ValueError('asset differs: '+name)
    required_assets(folder)
    return m


def window(now=None,stage='smoke'):
    now=now or datetime.now(timezone.utc)
    end=datetime(2026,11,9,1,tzinfo=timezone.utc) if stage=='virtue' else datetime(2026,10,26,1,tzinfo=timezone.utc)
    if not datetime(2026,10,19,1,tzinfo=timezone.utc)<=now<end:
        raise ValueError('finite launch window closed; renewal needs review, never reset ledger')


def reservation(stage):
    s=STAGES[stage]
    rate=CPU_RATE if stage=='cpu' else RATE
    value=len(s['arms'])*(s['timeout']+STARTUP+IDLE)*rate/3600+s['overhead']
    if value>s['target']:raise ValueError('stage reservation exceeds target')
    return value


def budget(stage,actual,credit,approved,billing):
    if stage not in STAGES or approved is not True or not billing.strip():
        raise ValueError('separate stage approval and current billing attestation required')
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in (actual,credit)):
        raise ValueError('finite current cumulative actual spend/credit required')
    reserve=reservation(stage)
    remaining_names=('virtue',)
    full_remaining=sum(reservation(x) for x in remaining_names)
    if credit<reserve:raise ValueError('current stage reservation exceeds available free credit')
    if actual+full_remaining>CAP:raise ValueError('unchanged remaining study cannot fit cumulative cap')
    if actual<PRIOR or credit<reserve or actual+reserve>CAP:
        raise ValueError('stage would exceed current credit or owner-approved cumulative $36 cap')
    return dict(stage=stage,actual_prior_usd=actual,current_available_credit_usd=credit,
        stage_reservation_usd=reserve,remaining_study_reservations_usd=full_remaining,stage_target_usd=STAGES[stage]['target'],
        cumulative_ceiling_usd=CAP,projected_cumulative_reserved_usd=actual+reserve,
        whole_worker_rate_ceiling_usd_per_hour=CPU_RATE if stage=='cpu' else RATE,invoice_actual_usd=None,
        accounting='additive boundary reconciliation; old ledgers/claims untouched; no live invoice meter')


def validate(payload,now=None):
    window(now,payload.get('stage'))
    c=payload.get('commit','');s=payload.get('stage')
    if len(c)!=40 or any(x not in '0123456789abcdef' for x in c) or s not in STAGES:
        raise ValueError('reviewed full commit and named stage required')
    if payload.get('approval_receipt')!=f'Owner approved Study D Gemma {s} v02427, commit {c}':
        raise ValueError('new exact-commit separate stage approval required')
    return budget(s,payload['actual_total_usd'],payload['available_credit_usd'],
                  payload.get('approved'),payload.get('billing_attestation',''))


CPU_COMMIT='90454d4a508d2b373625300834d719e8f1fb5cce'
CPU_ASSETS='3cf5731fda0b24390fb5bf5d1431abbb5f4f87474d3483592b654a888e5e9f5a'
CPU_RECEIPT='a42dfe109cd576ad04ef2d43729d4cdc7f837db232a465389648a1405bbb8f8b'


def completion_binding():
    return json.loads((Path(__file__).resolve().parent/'assets/completion-source-v02426.json').read_text())


def require_previous(root,payload,ledger=None):
    """Bind the NEW reviewed composite, retaining the old record as immutable input."""
    root=Path(root);binding=completion_binding()
    for name,digest in binding['source_sha256'].items():
        # pair/report.json has an additive repaired record at the new boundary.
        path=root/('source-composite-v02426.json' if name=='pair/report.json' else name)
        if stream_sha(path)!=digest:raise ValueError('v02426 source evidence changed: '+name)
    path=root/'pair/report.json';pair=json.loads(path.read_text())
    expected=Path(__file__).resolve().parent/'assets/composite-pair-v02427.json'
    if (payload['stage']!='virtue' or pair.get('status')!='COMPLETE'
        or pair.get('commit')!=binding['source_commit'] or pair.get('engine')!=ENGINE
        or payload.get('previous_report_sha256')!=sha(path) or sha(path)!=sha(expected)):
        raise ValueError('exact reviewed repaired composite pair required before virtue')
    if ledger is not None and ledger.get('pair/closed')!=dict(status='COMPLETE',report_sha256=sha(path)):
        raise ValueError('durable repaired composite closure absent')
    repair_path=Path(__file__).resolve().parent/'provenance.py'
    spec=importlib.util.spec_from_file_location('completion_provenance',repair_path)
    repair=importlib.util.module_from_spec(spec);spec.loader.exec_module(repair)
    original=json.loads((root/'source-composite-v02426.json').read_text())
    repaired=repair.repair_composite(root,original,continuation_binding())
    if repaired!=pair:raise ValueError('repaired provenance differs from evidence')
    verify_continuation(root)
    floor=pair['completion_worker_seconds']*2.4984/3600
    if payload['actual_total_usd']+.01<pair['budget']['actual_prior_usd']+floor:
        raise ValueError('actual spend cannot decrease or omit measured completion use')


def planned_bounds(rows,cases):
    """Known executed acts survive malformed labels; no complete-case denominator."""
    result={}
    for kind in ('W','U'):
        chosen=[c for c in cases if c['kind']==kind]; planned=4*len(chosen)
        known=unknown=0
        by={(r['case_id'],r['repeat']):r for r in rows}
        for c in chosen:
            for rep in range(1,5):
                r=by.get((c['id'],rep))
                if r is None:unknown+=1;continue
                if kind=='W':
                    acts=r['score'].get('executed_violations',{}).get('servile',0)
                    # Frozen score uses a list/count depending on source; normalized by caller below.
                    observed=bool(r.get('known_servile',acts))
                    known+=int(observed)
                    unknown+=int(not observed and not r['format_closed_valid'])
                else:
                    known+=int(r['score']['substance_outcome']=='over_refusal')
                    unknown+=int(not r['format_closed_valid'])
        result[kind]=dict(planned=planned,known=known,unknown=unknown,
                          lower=known/planned,upper=min(planned,known+unknown)/planned)
    return result


def verify_remote(assets,payload):
    m=verify_assets(assets)
    if sha(Path(assets)/'integrity-v02427.json')!=payload['asset_sha256']:raise ValueError('asset receipt differs')
    for name,digest in m['remote_code_sha256'].items():
        if sha(Path('/opt/study-d')/name)!=digest:raise ValueError('remote code differs: '+name)
    return m


def require_cpu(root,payload,ledger=None):
    """Carry over immutable v02420 CPU proof; no new data/rehearsal/model calls."""
    path=Path(__file__).resolve().parent/'legacy_policy.py'
    spec=importlib.util.spec_from_file_location('legacy_cpu_policy',path)
    legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    result=legacy.require_cpu(root,dict(commit=CPU_COMMIT,asset_sha256=CPU_ASSETS),ledger)
    if sha(Path(root)/'cpu/receipt.json')!=CPU_RECEIPT:raise ValueError('reviewed CPU receipt changed')
    return result

def graph_kv(log,free_bytes):
    available=re.findall(r'Available KV cache memory:\s*([-+]?\d+(?:\.\d+)?) GiB',log)
    graph=re.findall(r'Graph capturing finished in .*?took (\d+(?:\.\d+)?) GiB',log)
    if not available or not graph:raise RuntimeError('native post-capture KV/graph evidence absent; no generation')
    # Conservative even if native profiling already reserved graph memory: subtract again.
    graph_upper=sum(float(x)+.005 for x in graph)
    remaining=float(available[-1])-.005-graph_upper-.25
    if remaining<13.765 or free_bytes<.25*2**30:
        raise RuntimeError('KV plus CUDA graph memory preflight short; no context reduction/eager fallback')
    return dict(status='PASS',available_GiB=float(available[-1]),graph_GiB_upper=graph_upper,
        conservative_remaining_GiB=remaining,required_GiB_upper=13.765,
        conservative_margin_GiB=remaining-13.765,
        native_available_minus_requirement_GiB=float(available[-1])-13.765,
        free_after_capture_bytes=free_bytes,extra_margin_GiB=.25,max_model_len=16384,
        disclosure='graph memory conservatively subtracted even if already reserved by native profile')

SOURCE_COMMIT='87acef174a03efb266fd57c12e0add13c9426ec8'
SOURCE_PRIVATE='taa-study-d-gemma-v02424-private-adapters'
SOURCE_PUBLIC='taa-study-d-gemma-v02424-evidence'


def source_binding():
    return json.loads((Path(__file__).resolve().parent/'assets/adapter-source-v02424.json').read_text())


def verify_source_training(root):
    binding=source_binding();source=Path(root)/'prior-training'
    if binding['source_commit']!=SOURCE_COMMIT or binding['private_volume']!=SOURCE_PRIVATE:
        raise ValueError('wrong training source')
    for name,digest in binding['sha256'].items():
        if sha(source/name)!=digest:raise ValueError('v02424 public evidence changed: '+name)
    reservation=json.loads((source/'reservation.json').read_text())
    if reservation['payload']['commit']!=SOURCE_COMMIT:
        raise ValueError('source reservation commit differs')
    for arm in ('contrary','neutral'):
        read=lambda n:json.loads((source/arm/n).read_text())
        training=read('training.json');coverage=read('lora-coverage.json');mask=read('masking.json')
        report=read('report.json');load=read('training-load.json');inp=read('trainer-input.json')
        if (training['status']!='COMPLETE' or training['optimizer_steps']!=250
            or training['processed_examples']!=2000 or training['processed_tokens']!=binding['training_tokens'][arm]
            or training['cpu_rehearsal'] or training['excludes_science']
            or training['settings']!=dict(TRAIN,bf16=True,use_cpu=False,effective_optimizer_steps=250)
            or training['lora']!=LORA):raise ValueError('source full training proof differs: '+arm)
        if (coverage['status']!='PASS' or coverage['matched_module_count']!=410
            or coverage['trainable_parameters']!=61214720 or mask['status']!='PASS' or mask['examples']!=2000
            or load['model']!=MODEL or load['revision']!=REVISION or inp['commit']!=SOURCE_COMMIT
            or report['status']!='STOP_FOR_REVIEW' or report['error_message']!="'bundle_sha256'"):
            raise ValueError('source coverage/model/failure proof differs: '+arm)
        events=[json.loads(x)['event'] for x in (source/arm/'events.jsonl').read_text().splitlines()]
        if events!=['serving_load_start','adapter_handoff_verified']:
            raise ValueError('source contains unexpected scientific requests')
    return binding


def stream_sha(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):value.update(chunk)
    return value.hexdigest()


def verify_reused_adapter(root,arm,private_root='/adapters',published=None):
    """Read only. Bind public full-training proof and the private training-time index."""
    if arm not in ('contrary','neutral'):raise ValueError('pair adapter only')
    binding=verify_source_training(root)
    private_root=Path(private_root);folder=private_root/'science'/arm/'final'
    for p in (private_root/'science',private_root/'science'/arm,folder):
        if p.is_symlink() or not p.is_dir():raise ValueError('missing/symlink private adapter path')
    index=folder/'checkpoint-integrity.json'
    if index.is_symlink():raise ValueError('symlink checkpoint index')
    checkpoint=json.loads(index.read_text())
    if checkpoint.get('arm')!=arm or checkpoint.get('complete') is not True or checkpoint.get('scientific_checkpoint') is not True:
        raise ValueError('incomplete/wrong-arm scientific checkpoint')
    expected=checkpoint.get('sha256',{})
    if set(expected)!={'adapter_config.json','adapter_model.safetensors','README.md'}:
        raise ValueError('unexpected final checkpoint file roster')
    if {p.name for p in folder.iterdir()}!=set(expected)|{'checkpoint-integrity.json'}:
        raise ValueError('extra/missing final adapter file')
    files={}
    for name,digest in expected.items():
        path=folder/name
        if path.is_symlink() or not path.is_file() or stream_sha(path)!=digest:
            raise ValueError('private adapter file hash differs: '+name)
        files[name]=dict(sha256=digest,bytes=path.stat().st_size)
    config=json.loads((folder/'adapter_config.json').read_text())
    for name,value in LORA.items():
        if config.get(name)!=value:raise ValueError('adapter LoRA config differs: '+name)
    if (config.get('base_model_name_or_path')!=MODEL or config.get('peft_type')!='LORA'
        or config.get('use_dora',False) or config.get('use_rslora',False)
        or config.get('rank_pattern',{}) or config.get('alpha_pattern',{})):
        raise ValueError('adapter base/model/scaling differs')
    training=json.loads((Path(root)/'prior-training'/arm/'training.json').read_text())
    proof=dict(status='PASS',arm=arm,source_commit=SOURCE_COMMIT,source_private_volume=SOURCE_PRIVATE,
        adapter_relative_path='science/'+arm+'/final',checkpoint_index_sha256=stream_sha(index),
        files=files,public_training_sha256=binding['sha256'][arm+'/training.json'],
        training=training,retrained=False,mount_required='read-only',
        provenance_limit='Original public training metadata does not hash private weights; private index and file hashes first externally bound in this new pre-load receipt.')
    if published is not None and proof!=published:raise ValueError('adapter differs from published pre-load provenance')
    return proof


def acquisition_decisions(ledger,stage,acq,neutral_ordered=None):
    required=STAGES[stage]['arms']
    values={arm:ledger[stage+'/acquisition/'+arm] for arm in required}
    neutral=dict(ordered=neutral_ordered)
    decisions={arm:acq.acquisition_gate(arm,values[arm]['own'],values[arm]['ordered'],neutral['ordered']) for arm in required}
    if stage=='pair' and not decisions['neutral']['transfer_allowed']:
        decisions['contrary'].update(transfer_allowed=False,status='BLOCKED',interpretation='neutral acquisition failed')
    return decisions


CONTINUATION_PUBLIC='taa-study-d-gemma-v02425-evidence'

def continuation_binding():
    return json.loads((Path(__file__).resolve().parent/'assets/continuation-source-v02425.json').read_text())


def verify_continuation(root):
    """Exact pre-reviewed source bytes, completed set and no-resend partition."""
    binding=continuation_binding();source=Path(root)/'prior-pair'
    for name,digest in binding['source_sha256'].items():
        if stream_sha(source/name)!=digest:raise ValueError('v02425 source evidence changed: '+name)
    if {str(p.relative_to(source)) for p in (source/'pair/neutral/transfer').glob('*.json')}!={u['path'] for u in binding['units'] if u['status']=='completed'}:
        raise ValueError('source neutral completed roster changed')
    if binding['neutral_acquisition'].get('status')!='PASS' or not binding['neutral_acquisition'].get('transfer_allowed'):
        raise ValueError('source acquisition is not PASS')
    if json.loads((source/'pair/neutral/acquisition-gate.json').read_text())!=binding['neutral_acquisition']:
        raise ValueError('source gate decision changed')
    contrary=json.loads((source/'pair/contrary/report.json').read_text())
    if contrary.get('status')!='COMPLETE' or contrary.get('engine')!=ENGINE:
        raise ValueError('source contrary is not complete with frozen serving config')
    return binding


def neutral_union(root,folder):
    binding=verify_continuation(root);source=Path(root)/'prior-pair';folder=Path(folder)
    rows=[];provenance=[]
    expected={f"{u['case_id']}-r{u['repeat']}.json" for u in binding['units'] if u['status']=='untouched'}
    if {p.name for p in (folder/'transfer').glob('*.json')}!=expected:raise ValueError('new neutral output roster differs')
    for u in binding['units']:
        if u['status']=='interrupted_missing':
            provenance.append(dict(u,producer='v02425',missing=True,no_resend=True));continue
        path=(source/u['path'] if u['status']=='completed' else folder/'transfer'/f"{u['case_id']}-r{u['repeat']}.json")
        row=json.loads(path.read_text())
        if (row['case_id'],row['repeat'])!=(u['case_id'],u['repeat']):raise ValueError('union episode identity differs')
        rows.append(row);provenance.append(dict(u,producer='v02425' if u['status']=='completed' else 'v02426',output_sha256=sha(path)))
    cases=[q['case'] for q in json.loads((Path(__file__).resolve().parent/'assets/transfer-cases.json').read_text())]
    # Missing partial traces are preserved in the source; no inferred completed label.
    return dict(status='COMPLETE',scheduled_closed=132,transfer_episodes=len(rows),missing=2,
        bounds=planned_bounds(rows,cases),episode_provenance=provenance,
        neutral_ordered=json.loads((source/'pair/neutral/ordered-acquisition.json').read_text()),
        disclosure='Contrary and original neutral used per-event commits; neutral completion/virtue use timer+episode commits. Frozen settings/seeds unchanged.')
