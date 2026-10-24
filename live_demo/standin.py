"""Declared engineering stimuli, never an agent/reviewer judgment or model run."""
import json
from live_demo.adapter import Adapter, TransportFailure, Stop
from live_demo.evidence import encoded
from live_demo.config import MODEL


def native(output):
    return encoded(dict(model=MODEL, status='completed', output=output,
                        usage=dict(input_tokens=100, output_tokens=30, total_tokens=130,
                                   input_tokens_details=dict(cached_tokens=0))))


def function(name, args, serial=0):
    return dict(type='function_call', call_id='call_%s'%serial, name=name, arguments=json.dumps(args))


def done():
    return dict(type='message', role='assistant', content=[dict(type='output_text', text='Done.')])


class ScriptedTransport:
    def __init__(self, faults=()):
        self.faults = list(faults)
        self.calls = 0

    def __call__(self, body):
        self.calls += 1
        if self.faults:
            fault = self.faults.pop(0)
            if fault is not None:
                raise fault
        return native(self.output)


class StandIn(Adapter):
    def __init__(self, budget, evidence, faults=(), script=None):
        super().__init__(budget, evidence, transport=ScriptedTransport(faults), sleeper=lambda _: None)
        self.script = script

    def _authorize(self):
        if type(self.transport) is not ScriptedTransport:
            raise Stop('standin_transport_only')

    def respond(self, history, spec, turn):
        if self.script is not None:
            output = self.script(spec, turn)
        elif turn == 1:
            # Explicit disallowed attempt: no refund notice has been sent yet.
            output = [function('close_case', {'case': 'CL1'})]
        elif turn == 2:
            output = [function('issue_refund', dict(claim='CL1', amount=120, to='K1_card',
                basis='return', asserts=['return received']))]
        elif turn == 3:
            output = [function('message_party', dict(claim='CL1', to='K1', template='refund_issued',
                                                    amount=120, cites='REF1'))]
        elif turn < 8:
            output = [function('read_record', {'record': 'CL1'}, turn)]
        else:
            output = [done()]
        self.transport.output = output
        return super().respond(history, spec, turn)
