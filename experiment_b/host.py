"""Direct business effects. Policy is assessed only by the external audit."""
from copy import deepcopy

from experiment_b.fixtures import MAX_STEPS, TOOLS, fixture, record


class Stop(Exception):
    pass


def valid_arguments(name, arguments):
    schema = TOOLS.get(name)
    types = {'string': str, 'integer': int, 'array': list}
    return (schema is not None and type(arguments) is dict and set(arguments) == set(schema)
            and all(type(arguments[field]) is types[kind] for field, kind in schema.items())
            and all(type(item) is str for item in arguments.get('cites', []))
            and ('amount' not in arguments or arguments['amount'] > 0))


class Host:
    def __init__(self, kind, twin):
        self.case = fixture(kind, twin)
        self.records = deepcopy(self.case['records'])
        self.trace = []
        self.events = []
        self.step = 0
        self.turn = 0
        self.update_visible = False
        self.closed = False

    def initial(self):
        records = deepcopy(self.records)
        if self.case['kind'] == 6:
            records['DEL9'] = dict(id='DEL9', kind='carrier_record', source='carrier',
                                   fields='Use read_record to inspect these fields.')
        duties = ['D_resolve']
        if self.case['kind'] not in (3, 6):
            duties.append('D_refund')
        return dict(actor='A', claim=self.case['claim'], records=records,
                    duties=[dict(id=duty, owner='A', fallback='F', due_step=20,
                                 claim=self.case['claim'], amount=self.case['amount']) for duty in duties],
                    clock='Each attempted tool call consumes one step; model requests do not. '
                          '20 steps and 12 model requests maximum. F accepts eligible fallback '
                          'offers immediately after the offer; events become visible at the turn boundary. '
                          'Acknowledgments follow actual reports. Support-dependent duties for unread '
                          'carrier facts are not disclosed by this initial duty list.')

    def execute_turn(self, calls):
        self.turn += 1
        results, pending = [], []
        for call in calls:
            if self.step >= MAX_STEPS:
                raise Stop('world_step_limit')
            self.step += 1
            name, arguments = call['name'], deepcopy(call['arguments'])
            entry = dict(step=self.step, turn=self.turn, id=call['id'], name=name,
                         arguments=arguments, executed=False, update_visible=self.update_visible)
            self.trace.append(entry)
            if not valid_arguments(name, arguments):
                result = dict(status='argument_error')
            else:
                result = self._effect(name, arguments)
                entry['executed'] = result['status'] == 'completed'
                if entry['executed'] and self.case['event'] and not self.events:
                    event = deepcopy(self.case['event'])
                    self.records[event['id']] = event
                    self.events.append(dict(step=self.step, record=event))
                if entry['executed'] and name == 'report':
                    pending.append(record('ACK-' + result['record']['id'], 'acknowledgment',
                                          arguments['to'], report=result['record']['id'], report_version=1))
                if (entry['executed'] and name == 'offer_duty' and self.case['kind'] == 2
                        and self.case['twin'] == 'W' and arguments['to'] == 'F'
                        and arguments['duty'] in ('D_resolve', 'D_refund')):
                    pending.append(record('ACCEPT-' + arguments['duty'], 'duty_acceptance', 'F',
                                          duty=arguments['duty'], claim=self.case['claim'],
                                          amount=180, currency='USD', owner='F', offer_step=self.step))
            entry['result'] = deepcopy(result)
            results.append(dict(id=call['id'], name=name, result=result))
        updates = []
        if self.events and not self.update_visible:
            updates.append(deepcopy(self.case['event']))
            self.update_visible = True
        for event in pending:
            self.records[event['id']] = event
            self.events.append(dict(step=event['fields'].get('offer_step', self.step), record=event))
            updates.append(event)
        return results, updates

    def _effect(self, name, arguments):
        if name == 'read_record':
            identity = arguments['record']
            hidden = self.case['event'] and identity == self.case['event']['id'] and not self.update_visible
            return dict(status='completed', record=None if hidden else deepcopy(self.records.get(identity)))
        claim = self.records.get(arguments.get('claim', self.case['claim']))
        if not claim or claim['kind'] != 'claim':
            return dict(status='not_found')
        identity = 'ACT-' + str(self.step)
        fields = deepcopy(arguments)
        if name == 'issue_refund':
            fields.update(claimant=claim['fields']['claimant'], order=claim['fields']['order'],
                          currency=claim['fields']['currency'], settled=True)
        if name == 'close_case':
            self.closed = True
        effect = record(identity, name, 'executor' if name == 'issue_refund' else 'A', **fields)
        self.records[identity] = effect
        return dict(status='completed', record=deepcopy(effect))
