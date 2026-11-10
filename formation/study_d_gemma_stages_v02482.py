"""Seed 2 stage policy. Pure offline helpers; imports allocate no resources."""
import hashlib
import json
import math
import importlib.util
import re
from datetime import datetime, timezone
from pathlib import Path

TRAIN_SEED=347056
SHUFFLE_SEED=347052

VERSION='v02482'
MODEL='google/gemma-4-31B-it'
REVISION='842da3794eaa0b77d5f08bae87a17459d91ff475'
LEDGER='taa-study-d-gemma-v02482-budget-once'
VOLUME='taa-study-d-gemma-v02482-evidence'
PRIVATE='taa-study-d-gemma-v02482-private-adapters'
CAP=10.0
EVALUATION_CAP=7.0
PRIOR=0.0
CREDIT=0.0
RATE=3.20
STARTUP=120
IDLE=2
SMOKE_STEPS=8  # 64 microbatches/examples; never a scientific checkpoint.
CPU_RATE=.35
CPU_SOFTWARE=1100
PACKAGES={'vllm':'0.31.0','transformers':'5.10.4','torch':'2.13.0','huggingface-hub':'1.31.0',
          'nvidia-ml-py':'13.580.82','peft':'0.21.2','accelerate':'1.15.0'}
STAGES={'cpu':dict(arms=['tokenizer'],target=.25,timeout=1200,software=1100,overhead=.10),
        'pair':dict(arms=['contrary','neutral'],target=CAP-.25,timeout=4900,software=4800,overhead=.75)}
# Reserve CPU first; round the cap-derived worker timeout down to 100 seconds.
_cpu_reserve=(1200+STARTUP+IDLE)*CPU_RATE/3600+.10
_pair_timeout=100*math.floor(((CAP-_cpu_reserve-.75)*3600/(2*RATE)-STARTUP-IDLE)/100)
STAGES['pair'].update(timeout=_pair_timeout,software=_pair_timeout-100)
ENGINE=dict(model=MODEL,revision=REVISION,tokenizer_revision=REVISION,dtype='bfloat16',
    quantization=None,tensor_parallel_size=1,max_model_len=16384,max_num_seqs=2,
    gpu_memory_utilization=.95,enable_lora=True,max_lora_rank=8,max_loras=1,
    language_model_only=True,enforce_eager=False,trust_remote_code=False,
    generation_config='auto',seed=248017,enable_prefix_caching=True,disable_log_stats=True,
    compilation_config=dict(cudagraph_specialize_lora=True,cudagraph_capture_sizes=[1,2],max_cudagraph_capture_size=2))
LORA=dict(r=8,lora_alpha=16,lora_dropout=0,bias='none',task_type='CAUSAL_LM',
    target_modules=r'.*language_model.*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)')
TRAIN=dict(examples=2000,epochs=1,learning_rate=.0002,batch=1,accumulate=8,
    context=1024,seed=TRAIN_SEED,bf16=True,optimizer='adamw_torch',scheduler='constant',
    weight_decay=0,warmup_steps=0,gradient_checkpointing=True,assistant_only=True)
SMOKE_CASES=('C-brake-r1-W','C-brake-r1-U')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify_assets(folder):
    folder=Path(folder); m=json.loads((folder/'integrity.json').read_text())
    for name,want in m['sha256'].items():
        if sha(folder/name)!=want:raise ValueError('asset differs: '+name)
    return m


def window(now=None,stage='pair'):
    now=now or datetime.now(timezone.utc)
    if not datetime(2026,11,9,tzinfo=timezone.utc)<=now<datetime(2027,1,1,tzinfo=timezone.utc):
        raise ValueError('finite seed 2 launch window closed; review required')


def reservation(stage):
    s=STAGES[stage]
    rate=CPU_RATE if stage=='cpu' else RATE
    value=len(s['arms'])*(s['timeout']+STARTUP+IDLE)*rate/3600+s['overhead']
    if value>s['target']:raise ValueError('stage reservation exceeds target')
    return value


def budget(stage,actual,credit,approved,billing):
    if stage not in STAGES or approved is not True or not isinstance(billing,str) or not billing.strip():
        raise ValueError('separate stage approval and owner billing attestation required')
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in (actual,credit)):
        raise ValueError('finite nonnegative spend and headroom required')
    reserve=reservation(stage)
    if actual+reserve>CAP or credit<reserve:
        raise ValueError('training/acquisition cap or current headroom insufficient')
    return dict(stage=stage,actual_prior_usd=actual,current_available_credit_usd=credit,
        stage_reservation_usd=reserve,training_cap_usd=CAP,evaluation_cap_usd=EVALUATION_CAP,
        invoice_actual_usd=None,accounting='conservative time reservation; dashboard authoritative')


def validate(payload,now=None):
    window(now,payload.get('stage'))
    c=payload.get('commit','');s=payload.get('stage')
    if len(c)!=40 or any(x not in '0123456789abcdef' for x in c) or s not in STAGES:
        raise ValueError('reviewed full commit and named stage required')
    if payload.get('approval_receipt')!=f'Owner approved Study D Gemma {s} v02482, commit {c}':
        raise ValueError('new exact-commit separate stage approval required')
    return budget(s,payload['actual_total_usd'],payload['available_credit_usd'],
                  payload.get('approved'),payload.get('billing_attestation',''))


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


def require_cpu(root,payload,ledger=None):
    """Validate immutable PASS files and (controller/worker) durable Dict closure."""
    root=Path(root)/'cpu';receipt=json.loads((root/'receipt.json').read_text())
    expected=dict(status='PASS',commit=payload['commit'],asset_sha256=payload['asset_sha256'],
        model=MODEL,revision=REVISION,packages=PACKAGES,end_of_turn_id=106,gpu_allocated=False,
        weights_downloaded=False,training_steps=2,model_generation=False,rehearsal_pass=True,vllm_adapter_load_tested=False)
    for key,value in expected.items():
        if receipt.get(key)!=value:raise ValueError('CPU data PASS receipt differs: '+key)
    names={'report.json','tokenizer.json','rehearsal-integrity.json','architecture-expected-real-model.json'}|{a+'-first3-supervision.json' for a in ('contrary','virtue','neutral')}
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
    rehearsal=json.loads((root/'rehearsal-integrity.json').read_text())
    if rehearsal.get('status')!='PASS' or rehearsal.get('optimizer_steps')!=2:
        raise ValueError('actual CPU rehearsal PASS missing')
    for name,digest in rehearsal['sha256'].items():
        path=Path(name)
        if path.is_absolute() or '..' in path.parts or sha(root/path)!=digest:
            raise ValueError('rehearsal file changed')
    if ledger is not None and ledger.get('cpu/pass')!=dict(status='PASS',commit=payload['commit'],receipt_sha256=sha(root/'receipt.json')):
        raise ValueError('durable CPU PASS closure absent or mismatched')
    return receipt


def verify_remote(assets,payload):
    manifest=verify_assets(assets)
    if sha(Path(assets)/'integrity.json')!=payload['asset_sha256']:
        raise ValueError('asset receipt differs')
    for name,digest in manifest['remote_code_sha256'].items():
        if sha(Path('/opt/study-d')/name)!=digest:
            raise ValueError('remote code differs: '+name)
    return manifest


def require_previous(root,payload,ledger=None):
    if payload['stage']=='cpu':return
    require_cpu(root,payload,ledger)
    if payload.get('previous_report_sha256')!=sha(Path(root)/'cpu/report.json'):
        raise ValueError('reviewed seed 2 CPU report required')
