"""Local checkpoint verification and fail-closed launch contract; no remote imports."""
from copy import deepcopy
import json
import math
from pathlib import Path
from exploratory.audit_tool.modal_adapter import PLAN, verify_checkpoint
from exploratory.audit_tool.step4 import MODEL, REVISION, verify_weights
from .analysis import PREDICTIONS, predictions
from .runner import ROOT, plan, sha
import hashlib
import subprocess


def verify_execution_commit(expected):
    repo = ROOT.parents[1]
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=repo, text=True).strip()
    if actual != expected or dirty:
        raise ValueError('exact clean approved execution commit required')


def inventory_hash(checkpoints):
    return hashlib.sha256(json.dumps(checkpoints, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def weight_verification(cache):
    """Full check result, scoped to one launch and its read-only mounted cache."""
    try:
        verify_weights(cache)
        return None
    except (ValueError, OSError, KeyError) as exc:
        return str(exc)


_UNCHECKED = object()


def inventory(cache, adapters, *, weights_result=_UNCHECKED):
    pinned = json.loads(PLAN.read_bytes())
    result = {}
    if weights_result is _UNCHECKED:
        weights_result = weight_verification(cache)
    for arm in ('base', 'neutral', 'contrary', 'virtue'):
        entry = dict(model=MODEL, revision=REVISION, available=False)
        if arm != 'base':
            entry['adapter'] = next(deepcopy(c) for c in pinned['checkpoints'] if c['arm'] == arm)
        try:
            if weights_result is not None:
                raise ValueError(weights_result)
            if arm != 'base':
                verify_checkpoint(adapters, arm)
            entry['available'] = True
        except (ValueError, OSError, KeyError) as exc:
            entry['blocked_reason'] = str(exc)
        result[arm] = entry
    return result


def binding(commit, block, checkpoints=None, *, crossing_repeats=1, k1_repeats=1, l1_repeats=1, l2_repeats=1):
    predictions()
    if block != 'l1': plan(block)
    if len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
        raise ValueError('exact full commit required')
    result = dict(commit=commit, block=block, cases_sha256=sha(ROOT/'cases.json'),
                roster_sha256=sha(ROOT/'held_out_roster.json'), prediction_sha256=sha(PREDICTIONS),
                labels_sha256=sha(ROOT/'independent_labels/astra_labels.json'))
    if block == 'l2':
        from .l2 import binding as l2_binding
        result.update(l2_binding(l2_repeats))
    if block == 'l1':
        from .l1 import binding as l1_binding
        result.update(l1_binding(l1_repeats))
    if block == 'k1':
        from .k1 import binding as k1_binding
        result.update(k1_binding(k1_repeats))
    if block == 'crossing':
        from .crossing import binding as crossing_binding
        result.update(crossing_binding(crossing_repeats))
    if block == 'development_remainder':
        from .remainder import remainder_binding
        result.update(remainder_binding())
    if checkpoints is not None:
        result['inventory_sha256'] = inventory_hash(checkpoints)
    return result


class LaunchGuard:
    """Retain session or per-call reserves; never release uncertain amounts.

    persist must durably write before generation. A fresh run id/output is required;
    there is deliberately no resume API. Approval receipt is owner-supplied, and
    must also be explicitly trusted by the operator, not inferred from JSON fields.
    """
    def __init__(self, receipt, expected, checkpoints, persist, *, owner_approved=False, existing=False):
        if not owner_approved or existing or receipt.get('approved_by') != 'Chris Lahn':
            raise ValueError('fresh owner-approved receipt required; no resume')
        if any(receipt.get(k) != v for k, v in expected.items()):
            raise ValueError('receipt binding mismatch')
        if expected.get('inventory_sha256') != inventory_hash(checkpoints):
            raise ValueError('checkpoint inventory binding required')
        cap = receipt.get('dollar_cap')
        if isinstance(cap, bool) or not isinstance(cap, (int, float)) or not math.isfinite(cap) or cap <= 0:
            raise ValueError('finite positive dollar cap required')
        config = expected.get('backend_settings')
        if config is not None:
            from .modal_backend import settings
            if config != settings(cap, expected['block']):
                raise ValueError('cap/time settings mismatch')
        self.cap, self.reserved, self.persist, self.attempts = cap, cap if config else 0, persist, []
        self.checkpoints = checkpoints
        self.block = expected['block']
        self.commit = expected['commit']
        self.started = False

    def call(self, checkpoint, maximum_cost, generate):
        if hasattr(self, 'before_cell') and not self.before_cell():
            raise ValueError('session time limit; no new request')
        if not self.checkpoints.get(checkpoint, {}).get('available'):
            raise ValueError('checkpoint blocked; no substitution')
        if not math.isfinite(maximum_cost) or maximum_cost < 0 or self.reserved+maximum_cost > self.cap:
            raise ValueError('dollar cap stop')
        self.reserved += maximum_cost
        attempt = dict(checkpoint=checkpoint, reserved=maximum_cost, status='reserved')
        self.attempts.append(attempt)
        self.persist(deepcopy(self.attempts))
        try:
            result = generate()
        except Exception as exc:
            from .runner import CallTimeout
            attempt['status'] = 'call_timeout' if isinstance(exc, CallTimeout) else 'failed_unknown_cost'
            self.persist(deepcopy(self.attempts))
            raise
        attempt['status'] = 'returned'
        self.persist(deepcopy(self.attempts))
        return result
