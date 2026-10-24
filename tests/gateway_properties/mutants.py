"""Six deliberate broken builds/state faults, isolated to test processes.

State faults alter the authoritative native checkpoint, never returned effect
lists. The baseline core and independent fixtures remain untouched on disk.
"""
from contextlib import ExitStack
from copy import deepcopy
from itertools import count
from unittest.mock import patch

from tests.trace_support import production_backend as core
from taa_gateway import refunds, pipeline
from taa_gateway.duties import DutyEngine
from taa_gateway.executor import Runtime
from taa_gateway.rules import Outcome

PROBES = {
    'P1': [('refund', 1), ('execute', 1)],
    'P2': [('close', 1)],
    'P3': [('refund', 1), ('return_false', 1)],
    'P4': [('order', 1), ('asserted', 1)],
    'P5': [('order', 1), ('asserted', 1)],
    'P6': [('refund', 1)],
}
FIXTURES = {'P1': 'T02', 'P2': 'T09', 'P3': 'T03', 'P4': 'T01', 'P5': 'T01'}


class StateFault:
    def __init__(self, property_id):
        self.property_id = property_id

    def __getattr__(self, key):
        return getattr(core, key)

    def execute(self, before, actor, token=None, fault=None):
        after, result = core.execute(before, actor, token, fault)
        if self.property_id == 'P1':
            after, result = core.inject_hidden_state(after, result, 'extra_settled_refund', (before, actor, token))
        return after, result

    def enter_step(self, before, step, events=(), *, event_observer=None):
        after, result = core.enter_step(before, step, events, event_observer=event_observer)
        if self.property_id == 'P3':
            native = deepcopy(after['native'])
            changed = False
            for tid, old in before['native']['tokens'].items():
                row = native['tokens'][tid]
                if old['status'] == 'live' and row['status'] == 'void':
                    row['status'] = 'live'
                    native['warrants'][row['certificate']['warrant_id']]['status'] = 'live'
                    changed = True
            if changed:
                altered = dict(after, native=native)
                after = core._project(core._context(altered), altered)
        return after, result


class Installed:
    def __init__(self, name):
        self.name = name
        self.stack = ExitStack()

    def __enter__(self):
        if self.name in ('P1', 'P3'):
            return StateFault(self.name)
        if self.name == 'P2':
            original = refunds.ledger_condition
            def waive(ctx, view, capacity):
                return Outcome('satisfied') if ctx['tool'] == 'close_case' else original(ctx, view, capacity)
            self.stack.enter_context(patch.object(refunds, 'ledger_condition', waive))
        elif self.name == 'P4':
            original = pipeline.strictest
            def weaken(*values):
                rest = [v for v in values if v != 'PROHIBIT']
                return original(*rest) if rest else 'PERMIT'
            self.stack.enter_context(patch.object(pipeline, 'strictest', weaken))
        elif self.name == 'P5':
            self.stack.enter_context(patch.object(DutyEngine, 'report_from_log', lambda *args: False))
        elif self.name == 'P6':
            original, counter = Runtime.propose, count(1)
            def nondeterministic(runtime, *args, **kwargs):
                result = original(runtime, *args, **kwargs)
                runtime.store.audit('unreset_hidden_counter', {'counter': next(counter)})
                return result
            self.stack.enter_context(patch.object(Runtime, 'propose', nondeterministic))
        else:
            raise ValueError('unknown property mutant')
        return core

    def __exit__(self, *args):
        self.stack.close()
