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


def cases():
    return [{"id": t["id"], "trace": t, "parameters": {}, "source": str(ROOT / 'astra_spot_check.yaml')}
            for t in yaml.safe_load((ROOT / 'astra_spot_check.yaml').read_text())]


def mutated(function, kind):
    def wrapper(*args, **kwargs):
        state, result = function(*args, **kwargs)
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


def run_suite(runner):
    controls = json.loads((ROOT / 'mutations.json').read_text())
    ordinary, negative = [], []
    for c in cases():
        spec = controls.get(c['id'])
        if spec:
            with patch.object(runner.model, spec['method'], mutated(getattr(runner.model, spec['method']), spec['mutation'])):
                observations = runner.run(c)
            failed = [r for r in observations if r['status'] == 'discrepancy']
            incomplete = [r for r in observations if r['status'] == 'incomplete']
            detected = bool(failed) and not incomplete
            negative.append({'trace': c['id'], 'assertion': 'hidden_state_is_detected',
                             'expectation': True, 'observed': detected,
                             'status': 'pass' if detected else 'discrepancy', 'raw_observations': observations})
        else:
            ordinary.extend(runner.run(c))
    return {'assertions': ordinary + negative, 'negative_controls': negative,
            'scenarios': len(cases())}
