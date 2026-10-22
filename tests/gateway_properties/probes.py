"""Checks whose expected values come from Claude's Q11/Q12, not a backend."""
from tests.trace_support.bundle import world
from tests.trace_support import production_backend as core
from taa_gateway_reference import refunds as reference


def acceptance_authority():
    rows = {}
    for name, backend in (('production', core), ('reference', reference)):
        s = backend.start(world())
        s, _ = backend.enter_step(s, 2)
        s, offered = backend.propose(s, 'A', 'offer_duty', {'duty': 'D_resolve(CL1)', 'to': 'F'})
        s, _ = backend.execute(s, 'A', offered['token'])
        s, _ = backend.enter_step(s, 3)
        s, result = backend.propose(s, 'F', 'accept_duty', {'duty': 'D_resolve(CL1)'})
        rows[name] = {'disposition': result.get('disposition'), 'rule': result.get('rule')}
    expected = {'disposition': 'REFUSE', 'rule': 'AU1'}
    return {'id': 'PROP-Q1', 'status': 'pass' if all(r == expected for r in rows.values()) else 'discrepancy',
            'source': 'Claude Q11 verbatim in TAA_GATEWAY_ALIGNMENT_v031.md',
            'expected_outcome': expected, 'observations': rows}


def offer_window():
    rows = {}
    for name, backend in (('production', core), ('reference', reference)):
        s = backend.start(world())
        s, _ = backend.enter_step(s, 2)
        s, offered = backend.propose(s, 'A', 'offer_duty', {'duty': 'D_resolve(CL1)', 'to': 'F'})
        s, _ = backend.execute(s, 'A', offered['token'])
        s, _ = backend.enter_step(s, 3, [{'type': 'grant_revocation', 'grant': 'G1', 'by': 'F'}])
        d = s['duties']['D_resolve(CL1)']
        expiry = d.get('offer_due', d.get('offer_deadline_step'))
        s, _ = backend.enter_step(s, 7)
        rows[name] = {'expiry': expiry, 'owner_at_expiry': s['duties']['D_resolve(CL1)']['owner'],
                      'unowned_report': 'D_unowned_report(CL1)' in s['duties']}
    expected = {'expiry': 7, 'owner_at_expiry': None, 'unowned_report': True}
    return {'id': 'PROP-Q2', 'status': 'pass' if all(r == expected for r in rows.values()) else 'discrepancy',
            'source': 'Claude Q12 verbatim in TAA_GATEWAY_ALIGNMENT_v031.md',
            'expected_outcome': expected, 'observations': rows}
