"""Input-only Q18 fixtures and representation conversion; no expected generation."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'tests/regression_scenarios/q18.json'
LIVE = ROOT / 'studies/live-demo-03131469-review/internal-adjudication'


def cases():
    return json.loads(FIXTURES.read_bytes())['cases'] + json.loads(FIXTURES.with_name('q18_additional.json').read_bytes())['cases']


def live_source(case):
    source = json.loads((LIVE / (case['source_case'] + '.json')).read_bytes())
    native = source['replay']['native_pre_state']
    from taa_gateway.serialization import canonical
    # Source used the live evidence canonical encoder (ensure_ascii=False).
    raw = json.dumps(native, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
    if hashlib.sha256(raw).hexdigest() != source['replay']['native_pre_state_sha256']:
        raise ValueError('archived live pre-state hash changed')
    if case['tool'] != source['call']['tool'] or case['args'] != source['call']['args']:
        raise ValueError('exact live call changed')
    return source


def conventional_host(reference_state):
    """Hydrate the same logical state, not an invented conventional trajectory."""
    from conventional_gateway.world import World
    from conventional_gateway.policy import Policy
    from conventional_gateway.ledger import Ledger
    s = deepcopy(reference_state)
    definition = deepcopy(s['world'])
    definition['records'], definition['grants'] = {}, {}
    host = World(definition)
    host.definition = deepcopy(s['world'])
    host.policy = Policy(host.definition)
    host.ledger = Ledger(host.policy)
    with host.store.transaction():
        host.store.append('configuration', 'world', host.definition, relevant=False)
        for relation in ('records', 'grants', 'duties', 'allocations', 'orders', 'reports'):
            for identity, values in s[relation].items():
                for value in values if relation == 'records' else [values]:
                    host.store.append(relation, identity, value, relevant=False)
        for index, notice in enumerate(s['notices']):
            host.store.append('notices', str(index), notice['args'], relevant=False)
        for identity, value in s['cases'].items():
            host.store.append('cases', identity, {'closed': value}, relevant=False)
    host.store.clock(s['step'])
    return host


def observe(case, implementation):
    from tests.trace_support import production_backend as core, mcp_backend as mcp
    from taa_gateway_reference import refunds as reference
    from conventional_gateway import backend as conventional
    modules = dict(core=core, mcp=mcp, reference=reference, conventional=conventional)
    backend = modules[implementation]
    actor = case.get('actor', 'A')
    if 'source_case' in case:
        source = live_source(case)
        if implementation == 'reference':
            return reference.constraints(deepcopy(source['stored_assessment']['pre_commit_state']), actor, case['tool'], deepcopy(case['args']))
        if implementation == 'conventional':
            host = conventional_host(source['stored_assessment']['pre_commit_state'])
            try:
                return host.propose(actor, case['tool'], deepcopy(case['args']))
            finally:
                host.store._db.close()
        state = deepcopy(source['replay']['native_pre_state'])
    else:
        world = json.loads((ROOT/'live_demo/frozen/world.json').read_bytes())
        state = backend.start(world, deepcopy(case['setup']), defer_first_step=True)
        state, _ = backend.enter_step(state, 1, case.get('events', []))
        for act in case.get('prelude', []):
            state, proposal = backend.propose(state, act['actor'], act['tool'], deepcopy(act['args']))
            if proposal.get('disposition') != 'PERMIT':
                raise AssertionError('rule-authored fixture prelude was not permitted')
            state, result = backend.execute(state, act['actor'], proposal['token'])
            if result.get('execute_result') != 'committed':
                raise AssertionError('rule-authored fixture prelude did not commit')
    _, result = backend.propose(state, actor, case['tool'], deepcopy(case['args']))
    return {key: value for key, value in result.items() if key != 'state_delta'}
