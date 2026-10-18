"""Offline-only policy/projection helpers; no model or Modal imports."""
import hashlib
import json
import math
import os
import re
import traceback
from datetime import datetime, timezone
from pathlib import Path

MODEL = 'google/gemma-4-31B-it'
REVISION = '842da3794eaa0b77d5f08bae87a17459d91ff475'
VLLM = '0.31.0'
APP = 'taa-study-d-gemma-base-v02414'
VOLUME = 'taa-study-d-gemma-base-v02414-evidence'
LEDGER = 'taa-study-d-gemma-base-v02414-budget-once'
STAGE_KEY = 'gemma-base-v02414/stage-once'
WORKER_KEY = 'gemma-base-v02414/worker-once'
CAP = 25.0
PRIOR_FLOOR = 2.17  # Owner-reported rounded dashboard total after v02413.
V02413_RESERVED_CUMULATIVE = 5.501777777777778
GPU_MEMORY_UTILIZATION = .95
MAX_MODEL_LEN = 16384
RATE = 3.20
PUBLIC_WORKER_RATE = (.000694 + 2*.0000131 + 64*.00000222)*3600
TIMEOUT = 3300
STARTUP = 300
IDLE = 2
SOFTWARE_LIMIT = 3000
REPLY_LIMIT = 600
OVERHEAD = .60
RESERVATION = (TIMEOUT+STARTUP+IDLE)/3600*RATE+OVERHEAD
ARMS = ('contrary', 'virtue', 'neutral')


def check_window(now=None):
    now = now or datetime.now(timezone.utc)
    if not datetime(2026,10,18,4,tzinfo=timezone.utc) <= now < datetime(2026,10,24,4,tzinfo=timezone.utc):
        raise ValueError('launch window closed; review, never reset once-only claims')


def budget(prior_usd, approved=False):
    if not approved or isinstance(prior_usd,bool) or not math.isfinite(prior_usd) or prior_usd < PRIOR_FLOOR:
        raise ValueError('explicit approval and reconciled cumulative actual total >= $2.17 required')
    accounting_prior=max(prior_usd,V02413_RESERVED_CUMULATIVE)
    if RESERVATION >= 4 or accounting_prior+RESERVATION > CAP:
        raise ValueError('gate/cumulative reservation exceeds cap')
    return dict(actual_prior_dashboard_usd=prior_usd, prior_usd=accounting_prior,
                old_v02413_reservation_retained=True, gate_reservation_usd=RESERVATION,
                actual_prior_plus_new_reservation_usd=prior_usd+RESERVATION,
                cumulative_reserved_usd=accounting_prior+RESERVATION, cap_usd=CAP,
                whole_worker_ceiling_usd_per_hour=RATE, overhead_allowance_usd=OVERHEAD,
                gpu_timeout_seconds=TIMEOUT, startup_seconds=STARTUP, idle_seconds=IDLE,
                actual_invoice_usd=None, refunds=False, training_authorized=False)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_assets(folder):
    folder = Path(folder)
    manifest = json.loads((folder/'integrity.json').read_text())
    for name, expected in manifest['sha256'].items():
        if sha(folder/name) != expected:
            raise ValueError('asset hash mismatch: '+name)
    return manifest


def validate_receipt(receipt, commit, now=None):
    check_window(now)
    if len(commit)!=40 or any(c not in '0123456789abcdef' for c in commit):
        raise ValueError('full reviewed commit required')
    expected = 'Owner approved Gemma base-format gate v02414, commit '+commit
    if receipt.get('commit')!=commit or receipt.get('approval_receipt')!=expected:
        raise ValueError('separate exact-commit approval receipt required')
    if not receipt.get('billing_attestation','').strip():
        raise ValueError('current billing/no-card/no-other-workloads attestation required')
    return budget(receipt['prior_usd'], receipt.get('approved') is True)


def project(measurements, training_tokens, load_seconds, gate_reserved_cumulative):
    """Decode measurements are NOT backward-pass benchmarks or training admission."""
    if (not measurements or load_seconds < 0 or any(
            not math.isfinite(x[k]) or x[k] <= 0 for x in measurements
            for k in ('output_tokens','wall_seconds'))):
        return dict(status='UNAVAILABLE', training_authorized=False)
    tokens = sum(x['output_tokens'] for x in measurements)
    seconds = sum(x['wall_seconds'] for x in measurements)
    tps = tokens/seconds
    avg = tokens/len(measurements)
    requests_per_episode = len(measurements)/34
    arms = {}
    for arm in ARMS:
        count = training_tokens[arm]['tokens']
        checks = 220 if arm=='neutral' else 120
        generation = (checks*min(avg,512)+132*requests_per_episode*avg)/tps
        full_ceiling = (checks*512+132*requests_per_episode*4096)/tps
        overhead = load_seconds+540  # future load + acquisition barrier/storage
        arms[arm] = dict(examples=2000, epochs=1, training_tokens=count,
            measured_generation_based_probe_seconds=generation,
            maximum_output_probe_seconds_at_measured_tps=full_ceiling,
            training_seconds_optimistic_UNMEASURED=count/(4*tps),
            training_seconds_slow_UNMEASURED=count/tps,
            total_seconds_optimistic=overhead+generation+count/(4*tps),
            total_seconds_slow=overhead+generation+count/tps,
            future_candidate_operation_guard_seconds=5700,
            optimistic_fits_5700=(overhead+generation+count/(4*tps)<=5700),
            slow_fits_5700=(overhead+generation+count/tps<=5700))
    totals = {}
    for scenario in ('optimistic','slow'):
        hours=sum(a['total_seconds_'+scenario] for a in arms.values())/3600
        cost=hours*RATE+.75  # provisional future CPU/storage/build allowance
        totals[scenario]=dict(gpu_worker_hours=hours, incremental_usd=cost,
            cumulative_usd=gate_reserved_cumulative+cost,
            additional_cap_needed_usd=max(0,gate_reserved_cumulative+cost-CAP))
    return dict(status='PROVISIONAL OWNER REVIEW; TRAINING SPEED/MEMORY UNMEASURED',
        measured_output_tokens=tokens, measured_generation_wall_seconds=seconds,
        measured_tokens_per_second=tps, requests=len(measurements), arms=arms, totals=totals,
        training_proxy='1x and 4x measured decode TPS are sensitivity assumptions, not training measurements',
        parallel_arms_reduce_elapsed_time_not_aggregate_GPU_hours=True,
        training_authorized=False, cap_usd=CAP,
        monthly_credit_note='October plus November credit may support a separately approved cap increase; no cumulative reset or assumed rollover')


def kv_prediction(total_gpu_bytes, baseline_bytes):
    """Conservative prediction from the same pinned v02413 stack's rounded logs.

    Not a replacement for vLLM's exact current profiling/check inside constructor.
    Increasing utilization is the ONLY serving-parameter change.
    """
    gib=2**30
    old_total=85118156800
    old_baseline=784596992
    required=math.ceil(13.765*gib)  # Upper edge of 13.76 rounded to 2 decimals.
    available=math.floor(11.875*gib + GPU_MEMORY_UTILIZATION*total_gpu_bytes-.90*old_total
                         -max(0,baseline_bytes-old_baseline)-.25*gib)
    if total_gpu_bytes<=0 or baseline_bytes<0:
        raise ValueError('invalid GPU memory observation')
    return dict(status='PASS' if available>=required else 'STOP_FOR_REVIEW',
        required_bytes_upper_estimate=required, available_bytes_lower_estimate=available,
        safety_margin_bytes=int(.25*gib), max_model_len=MAX_MODEL_LEN,
        gpu_memory_utilization=GPU_MEMORY_UTILIZATION,
        basis='v02413 rounded native profile; current GPU size/baseline adjusted; .25 GiB margin',
        exact_current_vllm_profile_still_required=True)


def current_kv_preflight(log_text):
    """Read current native profiler evidence after vLLM's exact admission check."""
    matches=re.findall(r'Available KV cache memory:\s*([-+]?\d+(?:\.\d+)?) GiB',log_text)
    if not matches:
        raise RuntimeError('current native KV profile missing; no generation')
    available_lower=(float(matches[-1])-.005)*2**30
    required_upper=13.765*2**30
    if available_lower<required_upper:
        raise RuntimeError('current KV memory below conservative 16384-token requirement; no generation')
    return dict(status='PASS',native_engine_initialization_passed=True,
        current_available_GiB_rounded=float(matches[-1]),required_GiB_upper_estimate=13.765,
        exact_native_check='unmodified vLLM0.31.0 _check_enough_kv_cache_memory during constructor',
        max_model_len=MAX_MODEL_LEN,automatic_context_reduction=False)


def redact(text):
    for name in ('HF_TOKEN','MODAL_TOKEN_ID','MODAL_TOKEN_SECRET'):
        value=os.environ.get(name)
        if value:
            text=text.replace(value,'[REDACTED '+name+']')
    return text


def failure_record(exc, phase):
    return dict(status='STOP_FOR_REVIEW',phase=phase,error_type=type(exc).__name__,
        error_message=redact(str(exc)),
        traceback=redact(''.join(traceback.format_exception(type(exc),exc,exc.__traceback__))),
        no_restart=True,training_authorized=False)


def save_failure(path, exc, phase):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    value=failure_record(exc,phase)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n')
    temporary.replace(path)
    return value
