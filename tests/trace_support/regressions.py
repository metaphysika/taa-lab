"""Sol-authored from Astra's 2026-10-21 spot check; expectations reviewed by Claude.

Standalone trace inputs and out-of-band mutation descriptors; no expected values
come from model output. The same clean traces can later drive production.
"""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch
import yaml

ROOT = Path(__file__).parents[1] / 'regression_scenarios'


def cases(*, include_clarifications=True):
    paths = [ROOT / 'astra_spot_check.yaml']
    if include_clarifications:
        paths.extend([ROOT / 'q11_q12.yaml', ROOT / 'q13.yaml'])
    return [{"id": t["id"], "trace": t, "parameters": {}, "source": str(path)}
            for path in paths for t in yaml.safe_load(path.read_text())]


def mutated(function, kind, backend=None):
    def wrapper(*args, **kwargs):
        state, result = function(*args, **kwargs)
        if backend is not None and hasattr(backend, 'inject_hidden_state'):
            return backend.inject_hidden_state(state, result, kind, args)
        if kind == 'extra_settled_refund' and result.get('execute_result') == 'committed':
            state['records']['HIDDEN'] = [{'kind': 'refund', 'writer': 'executor', 'version': 1,
                'evidential': True, 'fields': {'claim': 'CL1', 'claimant': 'K1', 'order': 'ORD1',
                 'amount': 1, 'currency': 'USD', 'to': 'account_X', 'settled': True}}]
        elif kind == 'refused_refund_without_description' and result.get('disposition') == 'REFUSE':
            state['records']['HIDDEN'] = [{'kind': 'refund', 'writer': 'executor', 'version': 1,
                'evidential': True, 'fields': {'claim': 'CL1', 'claimant': 'K1', 'order': 'ORD1',
                 'amount': 120, 'currency': 'USD', 'to': 'K1_card', 'settled': True}}]
            result.pop('action_executed', None)
        elif kind == 'rewrite_REF1_v1' and args[1].get('type') == 'record_correction' and args[1].get('record') == 'REF1':
            state['records']['REF1'][0]['fields']['settled'] = False
        return state, result
    return wrapper


def run_suite(runner, backend=None, *, include_clarifications=True):
    controls = json.loads((ROOT / 'mutations.json').read_text())
    ordinary, negative = [], []
    for c in cases(include_clarifications=include_clarifications):
        spec = controls.get(c['id'])
        if spec:
            implementation = backend or runner.model
            with patch.object(implementation, spec['method'], mutated(getattr(implementation, spec['method']), spec['mutation'], backend)):
                observations = runner.run(c, backend=backend) if backend else runner.run(c)
            failed = [r for r in observations if r['status'] == 'discrepancy']
            incomplete = [r for r in observations if r['status'] == 'incomplete']
            detected = bool(failed) and not incomplete
            negative.append({'trace': c['id'], 'assertion': 'hidden_state_is_detected',
                             'expectation': True, 'observed': detected,
                             'status': 'incomplete' if backend is not None and incomplete else 'pass' if detected else 'discrepancy',
                             'raw_observations': observations})
        else:
            ordinary.extend(runner.run(c, backend=backend) if backend else runner.run(c))
    return {'assertions': ordinary + negative, 'negative_controls': negative,
            'scenarios': len(cases(include_clarifications=include_clarifications))}
