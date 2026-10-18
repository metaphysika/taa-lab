"""Reviewed three-stage policy. Pure offline helpers; imports allocate no resources."""
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

VERSION='v02418'
MODEL='google/gemma-4-31B-it'
REVISION='842da3794eaa0b77d5f08bae87a17459d91ff475'
LEDGER='taa-study-d-gemma-v02418-budget-once'
VOLUME='taa-study-d-gemma-v02418-evidence'
PRIVATE='taa-study-d-gemma-v02418-private-adapters'
CAP=25.0
PRIOR=4.31
CREDIT=25.69
RATE=3.20
STARTUP=120
IDLE=2
SMOKE_STEPS=8  # 64 microbatches/examples; never a scientific checkpoint.
CPU_RATE=.20
CPU_SOFTWARE=510
PACKAGES={'vllm':'0.31.0','transformers':'5.10.4','torch':'2.13.0','huggingface-hub':'1.31.0',
          'nvidia-ml-py':'13.580.82','peft':'0.21.2','accelerate':'1.15.0'}
STAGES={'cpu':dict(arms=['tokenizer'],target=.15,timeout=600,software=510,overhead=.10),
        'smoke':dict(arms=['smoke'],target=2.,timeout=1700,software=1500,overhead=.35),
        'pair':dict(arms=['contrary','neutral'],target=12.,timeout=6200,software=6000,overhead=.75),
        'virtue':dict(arms=['virtue'],target=6.,timeout=6200,software=6000,overhead=.375)}
ENGINE=dict(model=MODEL,revision=REVISION,tokenizer_revision=REVISION,dtype='bfloat16',
    quantization=None,tensor_parallel_size=1,max_model_len=16384,max_num_seqs=2,
    gpu_memory_utilization=.95,enable_lora=True,max_lora_rank=8,max_loras=1,
    language_model_only=True,enforce_eager=True,trust_remote_code=False,
    generation_config='auto',seed=248017,enable_prefix_caching=False,disable_log_stats=True)
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
    end=datetime(2026,11,7,22,tzinfo=timezone.utc) if stage=='virtue' else datetime(2026,10,24,22,tzinfo=timezone.utc)
    if not datetime(2026,10,18,22,tzinfo=timezone.utc)<=now<end:
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
    remaining_names={'cpu':('cpu','smoke','pair','virtue'),'smoke':('smoke','pair','virtue'),'pair':('pair','virtue'),'virtue':('virtue',)}[stage]
    full_remaining=sum(reservation(x) for x in remaining_names)
    if actual+full_remaining>CAP:raise ValueError('unchanged remaining study cannot fit cumulative cap')
    if actual<PRIOR or credit<reserve or actual+reserve>CAP:
        raise ValueError('stage would exceed current credit or original cumulative $25 cap')
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
    if payload.get('approval_receipt')!=f'Owner approved Study D Gemma {s} v02418, commit {c}':
        raise ValueError('new exact-commit separate stage approval required')
    return budget(s,payload['actual_total_usd'],payload['available_credit_usd'],
                  payload.get('approved'),payload.get('billing_attestation',''))


def measurable_projection(smoke,token_counts):
    """Use measured backward-pass TPS; never label inference TPS training speed."""
    if smoke.get('status')!='COMPLETE' or smoke.get('episodes')!=2 or not smoke.get('adapter_handoff_verified'):
        raise ValueError('complete excluded smoke/handoff evidence required')
    train_tps=smoke['training']['processed_tokens']/smoke['training']['seconds']
    decode_tps=smoke['generation']['tokens']/smoke['generation']['seconds']
    if min(train_tps,decode_tps)<=0:raise ValueError('positive training/generation measurements required')
    arms={}
    for arm in ('contrary','neutral','virtue'):
        checks=220 if arm=='neutral' else 120
        # Keep all 132 episodes, not just the two engineering smoke cases.
        # Historical 9001/34 mean output and 139/34 requests/episode; two-case smoke
        # is a provisional speed observation, not a validated workload forecast.
        probe_tokens=132*max(9001/34,smoke['generation']['tokens']/2)+checks*128
        nominal=token_counts[arm]['tokens']/train_tps+probe_tokens/decode_tps+smoke['load_and_handoff_seconds']+300
        stress=nominal*1.25
        arms[arm]=dict(training_tokens=token_counts[arm]['tokens'],transfer_episodes=132,
            acquisition_plus_secondary=checks,nominal_seconds=nominal,stress_seconds=stress,
            software_guard_seconds=6000,stress_fits_guard=stress<=6000,
            max_output_sensitivity_seconds=(132*(139/34)*4096+checks*512)/decode_tps,
            estimated_worker_usd=nominal*RATE/3600,training_speed_measured=True)
    return dict(arms=arms,measured_training_tokens_per_second=train_tps,
        measured_generation_tokens_per_second=decode_tps,
        pair_projection_fits=all(arms[a]['stress_fits_guard'] for a in ('contrary','neutral')),
        virtue_projection_fits=arms['virtue']['stress_fits_guard'],
        uncertainty='short smoke excludes science; 25% stress buffer is not a confidence bound; max-output tail may not fit',
        further_execution_approved=False)


def require_previous(root,payload):
    root=Path(root);stage=payload['stage']
    if stage in ('cpu','smoke'):return
    smoke_path=root/'smoke/report.json'
    proof=json.loads(smoke_path.read_text())
    if proof.get('commit')!=payload['commit'] or proof.get('engine')!=ENGINE:
        raise ValueError('smoke source/serving configuration differs')
    if payload.get('previous_report_sha256')!=sha(root/('smoke/report.json' if stage=='pair' else 'pair/report.json')):
        raise ValueError('owner-reviewed preceding stage report hash required')
    key='pair_projection_fits' if stage=='pair' else 'virtue_projection_fits'
    if proof.get('status')!='COMPLETE' or not proof.get('projection',{}).get(key):
        raise ValueError('measured projection does not fit unchanged stage guards; review, no case/dose cuts')
    previous=json.loads((root/('smoke/report.json' if stage=='pair' else 'pair/report.json')).read_text())
    workers=[previous] if stage=='pair' else list(previous['arms'].values())
    floor=sum(w.get('software_wall_seconds',0) for w in workers)*3.104208/3600
    if payload['actual_total_usd']+.01<previous['budget']['actual_prior_usd']+floor:
        raise ValueError('cumulative actual spend cannot decrease or omit measured worker use, including November')
    if stage=='virtue':
        pair=json.loads((root/'pair/report.json').read_text())
        if pair.get('status')!='COMPLETE' or pair.get('commit')!=payload['commit'] or pair.get('engine')!=ENGINE:
            raise ValueError('closed complete pair and new owner approval required')


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
    """Validate immutable PASS files and (controller/worker) durable Dict closure."""
    root=Path(root)/'cpu';receipt=json.loads((root/'receipt.json').read_text())
    expected=dict(status='PASS',commit=payload['commit'],asset_sha256=payload['asset_sha256'],
        model=MODEL,revision=REVISION,packages=PACKAGES,end_of_turn_id=106,gpu_allocated=False,
        weights_downloaded=False,training_steps=0,model_generation=False)
    for key,value in expected.items():
        if receipt.get(key)!=value:raise ValueError('CPU data PASS receipt differs: '+key)
    names={'report.json','tokenizer.json'}|{a+'-first3-supervision.json' for a in ('contrary','virtue','neutral')}
    if set(receipt.get('evidence_sha256',{}))!=names:raise ValueError('CPU evidence set differs')
    for name,digest in receipt['evidence_sha256'].items():
        if sha(root/name)!=digest:raise ValueError('CPU evidence changed: '+name)
    report=json.loads((root/'report.json').read_text())
    if report.get('status')!='PASS' or report.get('summaries')!=receipt.get('summaries'):
        raise ValueError('CPU report/receipt summaries differ')
    for arm in ('contrary','virtue','neutral'):
        summary=receipt['summaries'][arm]
        if (summary['examples']!=2000 or not 0<summary['max_sequence_tokens']<=1024
                or not 0<summary['supervised_tokens']<summary['tokens']
                or len(summary['dataset_sha256'])!=64):raise ValueError('CPU training counts/context invalid')
    if ledger is not None and ledger.get('cpu/pass')!=dict(status='PASS',commit=payload['commit'],receipt_sha256=sha(root/'receipt.json')):
        raise ValueError('durable CPU PASS closure absent or mismatched')
    return receipt
