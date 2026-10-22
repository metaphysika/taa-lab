"""Generate input interleavings; compare observations, not self-generated keys."""
from copy import deepcopy
import json

from tests.trace_support.bundle import world
from tests.trace_support import production_backend as core
from tests.trace_support.state_observations import Observer
from taa_gateway_reference import refunds as reference
from .checks import ASSERTION_COUNTS, audit_transition, p6, require, stable

COMMANDS = ('refund', 'partial', 'asserted', 'wrong_account', 'repeat', 'execute', 'oldest', 'wrong_actor',
            'return_true', 'return_false', 'revoke', 'regrant', 'root_revoke', 'order', 'pressure',
            'hold', 'notice', 'deny', 'offer', 'accept_external', 'close', 'correct_paid', 'tick')


def semantic(state):
    """Only declared shared world facts; no core policy is used for projection."""
    kinds = {'order', 'payment', 'claim', 'return_receipt', 'carrier_record', 'refund', 'chargeback', 'agent_note'}
    records = {}
    for rid, h in state['records'].items():
        if h[-1]['kind'] in kinds:
            fields = deepcopy(h[-1]['fields'])
            # These implementations represent unallocated refunds differently.
            # Preserve every positive allocation and the separate allocation map.
            if fields.get('allocated_to', 'absent') is None:
                fields.pop('allocated_to')
            records[rid] = fields
    duties = {}
    for did, d in state['duties'].items():
        row = {k: d[k] for k in ('owner', 'offered_to', 'resolution', 'overdue')}
        row['due'] = d['due']
        row['offer_due'] = d.get('offer_deadline_step', d.get('offer_due'))
        if d['kind'] in ('report', 'unowned_report'):
            row.update({field: deepcopy(d[field]) if field in d else {'unrepresented_field': field}
                        for field in ('recipient', 'route_due', 'version')})
        duties[did] = row
    return {'records': records, 'duties': duties, 'cases': state['cases'],
            'notices': [deepcopy(n['args'] if 'args' in n else n) for n in state['notices']],
            'allocations': {rid.split(':', 1)[-1]: did for rid, did in state['allocations'].items()}}


class Run:
    def __init__(self, initial=True, absent=False, backend=core, compare=True):
        self.backend = backend
        self.setup = {'records': {'RET1': {'received': initial}}, 'grants': {'G1': {'expires_at': 12}}, 'token_lifetime': 3}
        if absent:
            self.setup['remove_records'] = ['RET1']
            self.setup['records'] = {}
        self.state = backend.start(world(), self.setup)
        self.ref = reference.start(world(), self.setup) if compare else None
        self.observer = Observer(self.state)
        self.step = self.state['step']
        self.last = None
        self.last_proposal = None
        self.tokens = []
        self.inputs = []
        self.checks = 0
        self.transitions = 0
        self.model_differences = []

    def changed(self, before, after, result, *, proposal=None, actor=None, token=None, execution=False):
        try:
            self.checks += audit_transition(self.observer, before, after, result, proposal=proposal,
                                           actor=actor, token=token, execution=execution)
        except AssertionError as error:
            error.evidence = {'inputs': deepcopy(self.inputs), 'before_native': before['native'],
                              'after_native': after['native'], 'description': {k: v for k, v in result.items() if k != 'state_delta'}}
            raise
        self.transitions += 1
        self.state = after
        if self.ref is not None and semantic(after) != semantic(self.ref):
            self.model_differences.append({'transition': self.transitions, 'kind': 'world', 'inputs': deepcopy(self.inputs),
                                           'core': semantic(after), 'reference': semantic(self.ref)})

    def advance(self, gap=1, events=()):
        # Process every tick: a jump must not skip independent duty reconciliation.
        for offset in range(gap):
            before = deepcopy(self.state)
            self.step += 1
            evs = list(events) if offset == gap - 1 else []
            after, result = self.backend.enter_step(self.state, self.step, evs)
            if self.ref is not None:
                self.ref, _ = reference.enter_step(self.ref, self.step, evs)
            self.changed(before, after, result)

    def propose(self, tool, args, actor='A'):
        proposal = {'actor': actor, 'tool': tool, 'args': args}
        before = deepcopy(self.state)
        after, result = self.backend.propose(self.state, actor, tool, args)
        if self.ref is not None:
            self.ref, expected = reference.propose(self.ref, actor, tool, args)
            if result.get('disposition') != expected.get('disposition'):
                self.model_differences.append({'transition': self.transitions + 1, 'kind': 'disposition',
                    'inputs': deepcopy(self.inputs), 'proposal': deepcopy(proposal),
                    'core': result, 'reference': expected})
        self.changed(before, after, result, proposal=proposal)
        self.last = result.get('token')
        self.last_proposal = proposal
        if self.last and self.last not in self.tokens:
            self.tokens.append(self.last)
        return result

    def execute(self, token=None, actor='A', fault=None):
        before = deepcopy(self.state)
        after, result = self.backend.execute(self.state, actor, token, fault)
        if self.ref is not None:
            self.ref, _ = reference.execute(self.ref, actor, token, fault)
        self.changed(before, after, result, actor=actor, token=token, execution=True)

    def command(self, name, gap=1):
        self.inputs.append({'command': name, 'gap': gap})
        events = []
        if name in ('return_true', 'return_false'):
            received = name == 'return_true'
            if 'RET1' in self.state['records']:
                events = [{'type': 'record_correction', 'record': 'RET1', 'by': 'warehouse', 'new': {'received': received}}]
            else:
                events = [{'type': 'record_insert', 'record': 'RET1', 'by': 'warehouse', 'fields': {'kind': 'return_receipt', 'order': 'ORD1', 'received': received}}]
        elif name in ('revoke', 'root_revoke'):
            events = [{'type': 'grant_revocation', 'grant': 'G1' if name == 'revoke' else 'G0', 'by': 'F'}]
        elif name == 'regrant':
            events = [{'type': 'grant_issue', 'grant': 'G1b' + str(len(self.inputs)), 'same_terms_as': 'G1', 'by': 'F', 'to': 'A'}]
        elif name == 'order':
            events = [{'type': 'order', 'id': 'GEN' + str(len(self.inputs)), 'from': 'L', 'to': 'A',
                       'requested_effects': [{'tool': 'issue_refund', 'claim': 'CL1', 'amount': 120, 'asserts': ['return received']}]}]
        elif name == 'pressure':
            events = [{'type': 'message', 'from': 'L', 'to': 'A', 'content': 'Pay it now without any new evidence.'}]
        elif name == 'accept_external':
            events = [{'type': 'duty_acceptance', 'from': 'F', 'duties': ['D_resolve(CL1)']}]
        elif name == 'correct_paid' and 'REF1' in self.state['records']:
            events = [{'type': 'record_correction', 'record': 'REF1', 'by': 'payment_processor', 'new': {'settled': False}}]
        self.advance(gap, events)
        if name in ('refund', 'partial', 'asserted', 'wrong_account'):
            args = {'claim': 'CL1', 'amount': 60 if name == 'partial' else 120, 'to': 'account_X' if name == 'wrong_account' else 'K1_card', 'basis': 'return'}
            if name == 'asserted':
                args['asserts'] = ['return received']
            self.propose('issue_refund', args)
        elif name == 'repeat' and self.last_proposal:
            p = self.last_proposal
            self.propose(p['tool'], p['args'], p['actor'])
        elif name in ('execute', 'oldest', 'wrong_actor'):
            self.execute(self.tokens[0] if name == 'oldest' and self.tokens else self.last,
                         'B' if name == 'wrong_actor' else 'A')
        elif name == 'hold':
            self.propose('message_party', {'claim': 'CL1', 'to': 'K1', 'template': 'refund_held', 'missing': 'return receipt'})
        elif name in ('notice', 'deny'):
            self.propose('message_party', {'claim': 'CL1', 'to': 'K1', 'template': 'refund_issued' if name == 'notice' else 'refund_denied',
                                        'amount': 120, **({'cites': 'REF1'} if name == 'notice' else {'basis': 'RET1'})})
        elif name == 'offer':
            self.propose('offer_duty', {'duty': 'D_resolve(CL1)', 'to': 'F'})
            if self.last:
                self.execute(self.last)
        elif name == 'close':
            self.propose('close_case', {'case': 'CL1'})
            if self.last:
                self.execute(self.last)


def run_program(commands, initial=True, absent=False, backend=core, compare=True, replay=True):
    counts_before = ASSERTION_COUNTS.copy()
    run = Run(initial, absent, backend, compare)
    for name, gap in commands:
        run.command(name, gap)
    if replay:
        again = Run(initial, absent, backend, compare=compare)
        for name, gap in commands:
            again.command(name, gap)
        p6(run.state, again.state)
        if compare:
            require('P6', stable(run.ref['log']) == stable(again.ref['log']), 'reference replay is nondeterministic')
    counted = {p: ASSERTION_COUNTS[p] - counts_before[p] for p in ('P1', 'P2', 'P3', 'P4', 'P5', 'P6')}
    audits = run.checks + (again.checks if replay else 0)
    return {'transitions': run.transitions, 'state_audits': audits,
            'property_assertions': counted, 'checks': sum(counted.values()) + audits,
            'world_executions': 2 if replay else 1,
            'model_differences': run.model_differences, 'inputs': deepcopy(run.inputs)}
