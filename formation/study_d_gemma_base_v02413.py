"""Offline-only policy/projection helpers; no model or Modal imports."""
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

MODEL = 'google/gemma-4-31B-it'
REVISION = '842da3794eaa0b77d5f08bae87a17459d91ff475'
VLLM = '0.31.0'
APP = 'taa-study-d-gemma-base-v02413'
VOLUME = 'taa-study-d-gemma-base-v02413-evidence'
LEDGER = 'taa-study-d-gemma-base-v02413-budget-once'
STAGE_KEY = 'gemma-base-v02413/stage-once'
WORKER_KEY = 'gemma-base-v02413/worker-once'
CAP = 25.0
PRIOR_FLOOR = 1.70
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
    if not datetime(2026,10,18,tzinfo=timezone.utc) <= now < datetime(2026,10,24,tzinfo=timezone.utc):
        raise ValueError('launch window closed; review, never reset once-only claims')


def budget(prior_usd, approved=False):
    if not approved or isinstance(prior_usd,bool) or not math.isfinite(prior_usd) or prior_usd < PRIOR_FLOOR:
        raise ValueError('explicit approval and reconciled cumulative prior spend >= $1.70 required')
    if RESERVATION >= 4 or prior_usd+RESERVATION > CAP:
        raise ValueError('gate/cumulative reservation exceeds cap')
    return dict(prior_usd=prior_usd, gate_reservation_usd=RESERVATION,
                cumulative_reserved_usd=prior_usd+RESERVATION, cap_usd=CAP,
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
    expected = 'Owner approved Gemma base-format gate v02413, commit '+commit
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
