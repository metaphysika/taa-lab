"""Open spec/model questions: report both observations, supply no expected winner."""
from tests.trace_support.bundle import world
from tests.trace_support import production_backend as core
from taa_gateway_reference import refunds as reference


def acceptance_authority():
    rows = {}
    for name, backend in (('production', core), ('reference', reference)):
        s = backend.start(world(), {'records': {'RET1': {'received': True}}})
        s, _ = backend.enter_step(s, 2)
        s, offered = backend.propose(s, 'A', 'offer_duty', {'duty': 'D_resolve(CL1)', 'to': 'F'})
        s, _ = backend.execute(s, 'A', offered.get('token'))
        s, _ = backend.enter_step(s, 3)
        s, result = backend.propose(s, 'F', 'accept_duty', {'duty': 'D_resolve(CL1)'})
        rows[name] = {'disposition': result.get('disposition'), 'result': result, 'state': s}
    return {'id': 'PROP-Q1', 'status': 'incomplete', 'question': 'Does an offer itself authorize F to use accept_duty, or does AU1 require a covering grant?',
            'observations': rows, 'expected_outcome': None,
            'label': 'OPEN QUESTION; observations are not expected outcomes; Claude clarification pending'}
