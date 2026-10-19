"""Offline speed-smoke policy; no scientific arms can be launched by this revision."""
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

VERSION='v02421'
LEDGER='taa-study-d-gemma-v02421-speed-budget-once'
VOLUME='taa-study-d-gemma-v02421-speed-evidence'
PRIVATE='taa-study-d-gemma-v02421-speed-private'
CPU_COMMIT='90454d4a508d2b373625300834d719e8f1fb5cce'
CPU_RECEIPT='a42dfe109cd576ad04ef2d43729d4cdc7f837db232a465389648a1405bbb8f8b'
CPU_ASSETS='3cf5731fda0b24390fb5bf5d1431abbb5f4f87474d3483592b654a888e5e9f5a'
CAP=30.0
RATE=3.20
TARGET=2.50
TIMEOUT=2300
SOFTWARE=2100
RESERVE=(TIMEOUT+120+2)*RATE/3600+.30
MODES=('live','merged')
CACHE_MODES=('cold','retained')
MERGE_MAX_ABS=.5
MERGE_REL_L2=.01


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(p,now=None):
    now=now or datetime.now(timezone.utc)
    if not datetime(2026,10,19,1,tzinfo=timezone.utc)<=now<datetime(2026,10,26,1,tzinfo=timezone.utc):
        raise ValueError('fresh finite speed window closed; no ledger reset')
    c=p.get('commit','')
    if len(c)!=40 or any(x not in '0123456789abcdef' for x in c):raise ValueError('full reviewed commit required')
    if p.get('approved') is not True or p.get('approval_receipt')!=f'Owner approved Study D Gemma speed smoke v02421, commit {c}':
        raise ValueError('new exact-commit speed-smoke approval required')
    actual=p.get('actual_total_usd');credit=p.get('available_credit_usd')
    if any(type(x) not in (float,int) or not math.isfinite(x) for x in (actual,credit)):
        raise ValueError('fresh finite dashboard totals required')
    if not p.get('billing_attestation','').strip() or actual<5.41 or credit<RESERVE or actual+RESERVE>CAP or RESERVE>TARGET:
        raise ValueError('speed reservation exceeds cumulative cap/current free credit or billing missing')
    return dict(reservation_usd=RESERVE,target_usd=TARGET,actual_prior_usd=actual,
        current_credit_usd=credit,cumulative_cap_usd=CAP,actual_invoice_usd=None,
        future_arms_reserved=False,rate_ceiling_usd_per_hour=RATE)


def engine(original,mode,merged=None):
    if mode not in MODES:raise ValueError('unknown serving mode')
    cfg=dict(original,enforce_eager=False,enable_prefix_caching=True,
        compilation_config=dict(cudagraph_specialize_lora=True,cudagraph_capture_sizes=[1,2],max_cudagraph_capture_size=2))
    if mode=='merged':
        if not merged:raise ValueError('private merged checkpoint required')
        cfg.update(model=str(merged),revision=None,tokenizer=original['model'],enable_lora=False)
    return cfg


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
        free_after_capture_bytes=free_bytes,extra_margin_GiB=.25,max_model_len=16384,
        disclosure='graph memory conservatively subtracted even if already reserved by native profile')


def merge_pass(max_abs,relative_l2):
    return all(math.isfinite(x) and x>=0 for x in (max_abs,relative_l2)) and max_abs<=MERGE_MAX_ABS and relative_l2<=MERGE_REL_L2


def select(results):
    """Only elapsed times and token counts enter selection; never score or parse outcomes."""
    if len(results)!=4 or {(r['mode'],r['cache']) for r in results}!={(m,c) for m in MODES for c in CACHE_MODES}:
        raise ValueError('all four benchmark cells required; no partial winner')
    rows=[]
    for r in results:
        if (r['requests']!=8 or len(r['round_seconds'])!=2 or r['tokens']!=512
            or any(not math.isfinite(x) or x<=0 for x in r['round_seconds'])):
            raise ValueError('incomplete/nonpositive fixed-workload timing')
        rows.append(dict(mode=r['mode'],cache=r['cache'],requests=r['requests'],tokens=r['tokens'],
            round_seconds=r['round_seconds'],tokens_per_second=r['tokens']/sum(r['round_seconds'])))
    # Caching is chosen only for >=5% elapsed-time benefit within the serving mode.
    candidates=[]
    for mode in MODES:
        cold=next(r for r in rows if r['mode']==mode and r['cache']=='cold')
        retained=next(r for r in rows if r['mode']==mode and r['cache']=='retained')
        candidates.append(retained if sum(retained['round_seconds'])<=.95*sum(cold['round_seconds']) else cold)
    winner=min(candidates,key=lambda r:(sum(r['round_seconds']),r['mode']))
    return dict(mode=winner['mode'],prefix_policy=winner['cache'],measurement=winner,
        rule='lowest fixed-workload elapsed time; >=5% benefit to retain prefixes; no outcomes used',
        applies_identically_to_all_arms=True,further_execution_approved=False)


def project(selection,training,counts,overhead,oct_credit,speed_reservation=RESERVE,actual=5.41):
    train_tps=training['processed_tokens']/training['seconds'];tps=selection['measurement']['tokens_per_second']
    if min(train_tps,tps)<=0:raise ValueError('positive measured throughput required')
    arms={}
    for a in ('contrary','neutral','virtue'):
        checks=220 if a=='neutral' else 120
        seconds=counts[a]['tokens']/train_tps+(132*(9001/34)+checks*128)/tps+overhead+300
        stress=seconds*1.25
        arms[a]=dict(nominal_seconds=seconds,stress_seconds=stress,existing_guard_seconds=6000,
            fits_existing_guard=stress<=6000,nominal_worker_usd=seconds*RATE/3600,
            stress_worker_with_allowance_usd=stress*RATE/3600+.375,
            transfer_episodes=132,training_examples=2000,epochs=1,
            max_output_tail_seconds=(132*(139/34)*4096+checks*512)/tps)
    total=sum(r['stress_worker_with_allowance_usd'] for r in arms.values())
    return dict(arms=arms,three_arm_stress_usd=total,
        october_credit_owner_report=oct_credit,october_after_speed_reservation_usd=max(0,oct_credit-speed_reservation),
        october_all_fit=total<=oct_credit-speed_reservation,november_fresh_credit_usd=30.,
        november_all_fit_credit_only=total<=30.,
        current_cumulative_headroom_after_speed_usd=CAP-actual-speed_reservation,
        fits_current_cumulative_cap=total<=CAP-actual-speed_reservation,
        monthly_credit_does_not_reset_cumulative_spend=True,
        october_fit_subsets={name:sum(arms[a]['stress_worker_with_allowance_usd'] for a in subset)<=oct_credit-speed_reservation
            for name,subset in [('pair',('contrary','neutral')),('virtue',('virtue',))]},
        uncertainty='eight fixed benchmark requests per cell, capped64; workload extrapolation not a confidence bound; long tails may not fit',
        cap_increase_approved=False,further_execution_approved=False)


def verify_runtime(payload,controller=False):
    folder=Path('/opt/study-d/speed-assets')
    if sha(folder/'integrity.json')!=payload['asset_sha256']:raise ValueError('speed asset receipt differs')
    manifest=json.loads((folder/'integrity.json').read_text())
    for n,want in manifest['assets'].items():
        if sha(folder/n)!=want:raise ValueError('speed asset differs: '+n)
    names=('speed_policy.py','stages_policy.py','base_policy.py') if controller else manifest['remote']
    for n in names:
        if sha(Path('/opt/study-d')/n)!=manifest['remote'][n]:raise ValueError('remote source differs: '+n)
    if not controller:
        old=json.loads(Path('/opt/study-d/assets/integrity.json').read_text())
        if sha('/opt/study-d/assets/integrity.json')!=CPU_ASSETS:raise ValueError('legacy scientific asset index differs')
        for n,want in old['sha256'].items():
            if sha(Path('/opt/study-d/assets')/n)!=want:raise ValueError('legacy scientific asset differs: '+n)
