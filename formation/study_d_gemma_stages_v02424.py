"""Reviewed three-stage policy. Pure offline helpers; imports allocate no resources."""
import hashlib
import json
import math
import importlib.util
import re
from datetime import datetime, timezone
from pathlib import Path

VERSION='v02424'
MODEL='google/gemma-4-31B-it'
REVISION='842da3794eaa0b77d5f08bae87a17459d91ff475'
LEDGER='taa-study-d-gemma-v02424-budget-once'
VOLUME='taa-study-d-gemma-v02424-evidence'
PRIVATE='taa-study-d-gemma-v02424-private-adapters'
CAP=36.0
PRIOR=6.85
CREDIT=23.15
RATE=3.20
STARTUP=120
IDLE=2
SMOKE_STEPS=8  # 64 microbatches/examples; never a scientific checkpoint.
CPU_RATE=.35
CPU_SOFTWARE=1100
PACKAGES={'vllm':'0.31.0','transformers':'5.10.4','torch':'2.13.0','huggingface-hub':'1.31.0',
          'nvidia-ml-py':'13.580.82','peft':'0.21.2','accelerate':'1.15.0'}
STAGES={'pair':dict(arms=['contrary','neutral'],target=16.26,timeout=8600,software=8400,overhead=.75),
        'virtue':dict(arms=['virtue'],target=8.49,timeout=9000,software=8800,overhead=.375)}
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

def verify_assets(folder):
    folder=Path(folder); m=json.loads((folder/'integrity.json').read_text())
    for name,want in m['sha256'].items():
        if sha(folder/name)!=want:raise ValueError('asset differs: '+name)
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
    remaining_names={'pair':('pair','virtue'),'virtue':('virtue',)}[stage]
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
    if payload.get('approval_receipt')!=f'Owner approved Study D Gemma {s} v02424, commit {c}':
        raise ValueError('new exact-commit separate stage approval required')
    return budget(s,payload['actual_total_usd'],payload['available_credit_usd'],
                  payload.get('approved'),payload.get('billing_attestation',''))


CPU_COMMIT='90454d4a508d2b373625300834d719e8f1fb5cce'
CPU_ASSETS='3cf5731fda0b24390fb5bf5d1431abbb5f4f87474d3483592b654a888e5e9f5a'
CPU_RECEIPT='a42dfe109cd576ad04ef2d43729d4cdc7f837db232a465389648a1405bbb8f8b'


def require_previous(root,payload,ledger=None):
    root=Path(root)
    selection=json.loads((Path(__file__).resolve().parent/'assets/selection-v02423.json').read_text())
    for name,digest in selection['evidence_sha256'].items():
        if sha(root/'prior-speed'/name)!=digest:raise ValueError('reviewed v02422 speed evidence changed: '+name)
    if payload['stage']=='pair':
        if payload.get('previous_report_sha256')!=sha(root/'prior-speed/report.json'):
            raise ValueError('exact reviewed v02422 report hash required')
        return
    path=root/'pair/report.json';pair=json.loads(path.read_text())
    if (pair.get('status')!='COMPLETE' or pair.get('commit')!=payload['commit']
        or pair.get('engine')!=ENGINE or payload.get('previous_report_sha256')!=sha(path)):
        raise ValueError('closed complete reviewed pair required before virtue')
    if ledger is not None and ledger.get('pair/closed')!=dict(status='COMPLETE',report_sha256=sha(path)):
        raise ValueError('durable pair closure absent')
    # Published A10080 GPU-only rate; do not treat estimated CPU/RAM charges as a billing minimum.
    floor=sum(w.get('software_wall_seconds',0) for w in pair['arms'].values())*2.4984/3600
    if payload['actual_total_usd']+.01<pair['budget']['actual_prior_usd']+floor:
        raise ValueError('actual spend cannot decrease or omit measured pair use')


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
    if sha(Path(assets)/'integrity.json')!=payload['asset_sha256']:raise ValueError('asset receipt differs')
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
