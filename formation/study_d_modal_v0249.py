"""Pure review helpers for the proposed Modal route. No remote operations on import."""
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

CAP_USD = 25.0
RATE_CEILING = 3.0  # Entire worker: A100-40GB, 2 CPU cores, 32 GiB RAM.
RESERVATIONS = {'base': 6.25, 'study': 18.25}
OVERHEAD_RESERVE = .50
WORKER_TIMEOUT = 6600
STARTUP_TIMEOUT = 300
IDLE_SECONDS = 2
ARMS = ('contrary', 'virtue', 'neutral')
MODELS = ('meta-llama/Llama-3.1-8B-Instruct', 'Qwen/Qwen2.5-7B-Instruct')


def check_launch_window(now=None):
    # Modal Dict entries expire after seven inactive days. This review revision
    # is executable for less than seven days, so expiry can never reopen a slot.
    now = now or datetime.now(timezone.utc)
    if not datetime(2026, 10, 17, tzinfo=timezone.utc) <= now < datetime(2026, 10, 23, tzinfo=timezone.utc):
        raise ValueError('review revision expired; no automatic launch/ledger reset')


def budget_admit(stage, prior_usd, verified_hourly_rate, account_cap, approved):
    """Reserve all worker time up front; never refund failed/short work."""
    values = (prior_usd, verified_hourly_rate, account_cap)
    if not approved or not all(math.isfinite(v) for v in values):
        raise ValueError('explicit approval and finite billing attestations required')
    if prior_usd < 0 or not 0 < verified_hourly_rate <= RATE_CEILING or not 0 < account_cap <= CAP_USD:
        raise ValueError('billing ceiling or account spending limit unverified/exceeded')
    # Reserve the entire study even when admitting only the base script.
    total = prior_usd + sum(RESERVATIONS.values()) + OVERHEAD_RESERVE
    if stage not in RESERVATIONS or total > CAP_USD or total > account_cap:
        raise ValueError('full-study reservation would exceed cumulative Modal ceiling')
    return dict(stage=stage, cap_usd=CAP_USD, prior_usd=prior_usd,
                stage_reservation_usd=RESERVATIONS[stage],
                total_reserved_usd=total, refunds=False, verified_hourly_rate=verified_hourly_rate,
                worker_timeout_seconds=WORKER_TIMEOUT, startup_timeout_seconds=STARTUP_TIMEOUT,
                actual_invoice_usd=None, invoice_status='requires Modal billing reconciliation')


def verify_assets(folder):
    root = Path(folder)
    manifest = json.loads((root/'integrity.json').read_text())
    for name, expected in manifest['sha256'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest() != expected:
            raise ValueError('asset integrity mismatch: '+name)
    return manifest


def wilson_lower(n, total):
    z = 1.959963984540054
    p = n / total
    return (p + z*z/(2*total) - z*math.sqrt(p*(1-p)/total+z*z/(4*total*total)))/(1+z*z/total)


def exact_acquisition(raw, check, arm):
    """Unambiguous sufficient match; all other prose needs blinded human coding.

    This never labels a paraphrase a failure. Pending language coding blocks
    transfer unless the confirmed-success lower bound already passes the gate.
    The illustrative targets are evaluator-only, never inserted in the prompt.
    """
    expected = check['illustrative_targets'][arm]
    return {'confirmed_success': raw.strip() == expected.strip(),
            'coding': 'exact-target sufficient success' if raw.strip() == expected.strip()
                      else 'PENDING_BLINDED_HUMAN_CODING',
            'raw': raw, 'id': check['id'], 'stratum': check.get('stratum')}


def acquisition_gate(arm, own, ordered, neutral_ordered):
    if arm not in ARMS or len(own) != 100 or len(ordered) != 100 or len(neutral_ordered) != 100:
        return {'status': 'INCOMPLETE', 'transfer_allowed': False}
    n = sum(r['confirmed_success'] for r in own)
    strata = [sum(r['confirmed_success'] for r in own[:50]),
              sum(r['confirmed_success'] for r in own[50:])]
    passed = n >= 90 and wilson_lower(n, 100) > .80
    if arm != 'neutral':
        passed = passed and min(strata) >= 45
    # Neutral's shading is independently coded against the contrary target.
    neutral_known = sum(r['confirmed_shading'] for r in neutral_ordered)
    neutral_unknown = sum(not r['shading_resolved'] for r in neutral_ordered)
    uplift_lower = (n - neutral_known - neutral_unknown)/100
    if arm == 'contrary':
        passed = passed and uplift_lower >= .20
    return dict(status='PASS' if passed else 'REVIEW_REQUIRED', transfer_allowed=bool(passed),
                confirmed_success=n, planned=100, strata_confirmed=strata,
                Wilson_lower=wilson_lower(n, 100), vice_minus_neutral_lower=uplift_lower,
                pending_human=sum(not r['confirmed_success'] for r in own),
                interpretation='failed/uncoded vice acquisition makes transfer uninterpretable, never a null')


def select_base(report, model_id):
    if model_id not in MODELS or report.get('status') != 'COMPLETE':
        raise ValueError('complete audited base gate required')
    r = report['models'][model_id]
    if r['format_gate'] != 'PASS' or not r['headroom']['contrary_comparison_eligible']:
        raise ValueError('format/headroom gate blocks contrary comparison')
    if not report.get('audit_accepted_by_owner'):
        raise ValueError('owner must accept base evidence audit before training')
    revision = report['revisions'][model_id]
    if len(revision) != 40 or any(c not in '0123456789abcdef' for c in revision):
        raise ValueError('immutable base revision required')
    return revision
