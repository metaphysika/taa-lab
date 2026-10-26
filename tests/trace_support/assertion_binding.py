"""Inputs/observations only; expected literals are authored from owner rules."""
from copy import deepcopy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT/'tests/regression_scenarios/assertion_binding_v02.json'
IMPLEMENTATIONS = ('reference', 'core', 'mcp', 'conventional', 'oracle')


def cases():
    return json.loads(FIXTURE.read_bytes())['cases']


def observe(case, implementation):
    from tests.trace_support import production_backend, mcp_backend
    from taa_gateway_reference import refunds
    from conventional_gateway import backend
    modules = dict(reference=refunds, core=production_backend, mcp=mcp_backend,
                   conventional=backend, oracle=refunds)
    engine = modules[implementation]
    world = json.loads((ROOT/'live_demo/frozen/world.json').read_bytes())
    state = engine.start(world, deepcopy(case['setup']), defer_first_step=True)
    state, _ = engine.enter_step(state, 1, [])
    if implementation == 'oracle':
        from comparators.duty_oracle import Oracle
        from comparators import commit_oracle
        result = commit_oracle.evaluate(commit_oracle.snapshot(Oracle(state), state), 'A', case['tool'], deepcopy(case['args']))['evaluation']
    elif implementation == 'reference':
        result = refunds.constraints(state, 'A', case['tool'], deepcopy(case['args']))
    else:
        _, result = engine.propose(state, 'A', case['tool'], deepcopy(case['args']))
    checks = result.get('checks', result.get('constraints', []))
    statuses = [r['result'] for r in checks if r.get('id', r.get('rule')) == 'PR1']
    pr1 = 'violated' if 'violated' in statuses else 'unknown' if 'unknown' in statuses else 'satisfied'
    return dict(disposition=result.get('disposition'), pr1=pr1,
                findings=[r for r in checks if r.get('id', r.get('rule')) == 'PR1'])
