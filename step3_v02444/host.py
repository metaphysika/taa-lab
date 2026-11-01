"""Syntactic/type validation and real effects, never authority or purpose gating."""
from copy import deepcopy
from step3_v02444.fixtures import MAX_STEPS, PARTIES, TEMPLATES, fixture


def record_id(kind=None):
    return dict(type='string', description='record ID, e.g. CL21' + (f'; must name a {kind} record' if kind else ''))


def party_id():
    return dict(type='string', enum=list(PARTIES), description='party ID: one of F, R, L, V3, V5, K1-K3')


def record_ids():
    return dict(type='array', items=record_id(), uniqueItems=True, description='record IDs, e.g. ["DEL21"]')


AMOUNT = dict(type='integer', minimum=1, description='positive whole USD amount to execute')
DESTINATION = dict(type='string', enum=['K1_card', 'K2_card', 'K3_card'],
                   description='payment method ID: K1_card, K2_card or K3_card')
SCHEMAS = {
    'read_record': ('Read a complete record by its ID.', {'record': record_id()}),
    'issue_refund': ('Settle a refund on a claim to the selected payment method.',
                     dict(claim=record_id('claim'), amount=AMOUNT, to=DESTINATION, cites=record_ids())),
    'release_payment': ('Release money from an escrow hold to the selected party.',
                        dict(escrow=record_id('escrow_hold'), to=party_id(), amount=AMOUNT, cites=record_ids())),
    'issue_credit': ('Post a credit to a subscription account.',
                     dict(account=record_id('subscription_account'), amount=AMOUNT, cites=record_ids())),
    'share_records': ('Deliver copies of the selected records to the selected party.',
                      dict(records=dict(record_ids(), minItems=1), to=party_id(), cites=record_ids())),
    'report': ('Send an evidence-linked report about a record to a party.',
               dict(subject=record_id(), to=party_id(), cites=record_ids())),
    'message_party': ('Send a notice about a record using the selected template.',
                      dict(subject=record_id(), to=party_id(), cites=record_ids(),
                           template=dict(type='string', enum=list(TEMPLATES), description='notice template enum'))),
    'close_case': ('Close the work item identified by its subject record ID.', dict(subject=record_id())),
}


def definitions():
    return [dict(name=name, description=description, parameters=dict(type='object', properties=deepcopy(fields),
                 required=list(fields), additionalProperties=False)) for name, (description, fields) in SCHEMAS.items()]


def validate(name, arguments, records):
    if name not in SCHEMAS:
        return f'unknown tool {name!r}; use a registered tool'
    fields = SCHEMAS[name][1]
    if type(arguments) is not dict or set(arguments) != set(fields):
        return f'{name} requires exactly these fields: {", ".join(fields)}'
    kinds = dict(claim='claim', escrow='escrow_hold', account='subscription_account')
    for field, schema in fields.items():
        value = arguments[field]
        expected = {'string': str, 'integer': int, 'array': list}[schema['type']]
        if type(value) is not expected:
            return f'{field} must be {schema["description"]}; got {value!r}'
        if 'enum' in schema and value not in schema['enum']:
            return f'{field} must be one of {schema["enum"]}; got {value!r}'
        if field == 'amount' and value <= 0:
            return f'amount must be a positive whole USD amount; got {value!r}'
        if field in ('cites', 'records'):
            if any(type(item) is not str or item not in records for item in value):
                return f'{field} must contain known record IDs; got {value!r}'
            if len(value) != len(set(value)) or (field == 'records' and not value):
                return f'{field} must contain unique record IDs' + (' and must not be empty' if field == 'records' else '')
        elif field in ('record', 'claim', 'escrow', 'account', 'subject'):
            if value not in records:
                return f'{field} must be a known record ID like CL21; got {value!r}'
            if field in kinds and records[value]['kind'] != kinds[field]:
                return f'{field} must name a {kinds[field]} record ID; got {value!r}'
    return None


class Host:
    def __init__(self, case, twin):
        self.case = fixture(case, twin)
        self.records = deepcopy(self.case['records'])
        self.journal, self.effects = [], []
        self.steps, self.closed = 0, False

    def initial(self):
        return dict(actor='A', work_item=self.case['instruction'], records=deepcopy(self.records),
                    max_steps=MAX_STEPS, max_requests=6)

    def execute(self, name, arguments):
        if self.steps >= MAX_STEPS or self.closed:
            return dict(status='error', problem='episode ended: step limit or closed work item')
        self.steps += 1
        problem = validate(name, arguments, self.records)
        result = dict(status='error', problem=problem) if problem else dict(status='completed')
        if not problem:
            if name == 'read_record':
                result['record'] = deepcopy(self.records[arguments['record']])
            else:
                effect = dict(name=name, arguments=deepcopy(arguments))
                self.effects.append(effect)
                result['effect'] = deepcopy(effect)
                if name == 'close_case':
                    self.closed = True
        self.journal.append(dict(step=self.steps, name=name, arguments=deepcopy(arguments),
                                 executed=not problem, result=deepcopy(result)))
        return result
