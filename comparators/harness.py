"""Execute the same controller inputs and source events in a frozen POEC arm.

These are descriptive arm observations. TAA disposition keys are never fed into
POEC policy or treated as POEC success keys. No scientific comparison is made.
"""
from collections import Counter
from copy import deepcopy
from itertools import groupby

from agents.refunds import CONTROLLERS
from tests.trace_support.bundle import world
from worlds.refunds.catalog import catalog, inputs_only, provenance
from comparators.tracegrant import TraceGrant, contract, digest
from comparators.world import World

# Artificial simulator key, not a credential or claim about external custody.
SIMULATOR_KEY = b'POEC-offline-simulator-certificate-key'


def admit_active(gateway, service):
    for key, node in gateway.c['MUST'].items():
        if node['kind'] != 'evidence' or gateway.states[key] != 'ACTIVE':
            continue
        row = service.current(node['record'])
        if row is not None:
            authenticated = service.sources[(row['id'], row['version'])]
            gateway.admit(key, [dict(row, integrity=digest(row))], authenticated_source=authenticated, query=node['query'])


def episode(case, controller_name):
    controller = CONTROLLERS[controller_name]()
    program = controller.program(case if controller_name == 'correct' else inputs_only(case))
    definition = world()
    service = World(definition, program['trace'].get('setup'))
    gateway = TraceGrant(contract(case['id']), certificate_key=SIMULATOR_KEY)
    observations, certificates, last = [], {}, None
    # Match the common runner: all same-step events, then proposals, executions.
    # No POEC duty reconciliation phase exists; there is no TAA ledger here.
    for step, group in groupby(program['trace']['steps'], key=lambda e: e['step']):
        entries = list(group)
        service.step = step
        for entry in entries:
            for event in entry.get('events', []):
                service.event(event)
        admit_active(gateway, service)
        for entry in entries:
            if 'propose' not in entry:
                continue
            p = entry['propose']
            if controller.withhold:
                result = {'decision': 'WITHHELD'}
            else:
                result = gateway.decide(p['actor'], p['tool'], p['args'])
            last = result.get('certificate')
            if last:
                certificates['T' + last['id'][2:]] = last
            observations.append({'step': step, 'kind': 'proposal', 'input': deepcopy(p), 'result': deepcopy(result)})
        for entry in entries:
            if 'execute' not in entry:
                continue
            e = entry['execute']
            cert = last if e.get('token_from') == 'last_proposal' else certificates.get(e.get('token'))
            before = service.snapshot()
            result = gateway.dispatch(cert, e['actor'], cert['tool'], cert['arguments'], service) if cert else {'dispatch': 'refused', 'reason': 'no observed certificate'}
            # The token_from input never falls back to an earlier certificate.
            observations.append({'step': step, 'kind': 'execution', 'input': deepcopy(e), 'result': deepcopy(result),
                                 'before': before, 'after': service.snapshot()})
    decision_counts = Counter(row['result']['decision'] for row in observations if row['kind'] == 'proposal')
    return {'case': case['id'], 'controller': controller_name, 'arm': 'TraceGrant-faithful-local-reconstruction',
            'contract': gateway.c['id'], 'contract_hash': digest(gateway.c), 'split': 'development',
            'observations': observations, 'obligations': deepcopy(gateway.states), 'receipts': deepcopy(gateway.receipts),
            'history': deepcopy(gateway.history), 'world': service.snapshot(),
            'decision_counts': dict(decision_counts), 'success_claim_gate': gateway.final_answer(claims_success=True),
            'interpretation': 'POEC gate is not W0 lawful completion; diagnostic prefixes may leave hard tasks undone.'}


def run_suite():
    results = [episode(case, controller) for case in catalog() for controller in CONTROLLERS]
    return {'provenance': provenance(), 'scope': 'Descriptive offline harness check, not H3 evidence',
            'episodes': results, 'counts': {'episodes': len(results), 'development_cases': len(catalog()),
            'controllers': len(CONTROLLERS), 'receipts': sum(len(r['receipts']) for r in results),
            'step_up': sum(r['decision_counts'].get('STEP_UP_AUTH', 0) for r in results)}}
