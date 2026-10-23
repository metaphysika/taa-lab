"""Representation-only decoding; no authorization or discharge predicates.

Read actual checkpoints/records and persisted report artifacts. Never read an
arm's duties, resolution status, or internal allocation ledger for scoring.
"""
from copy import deepcopy
import hashlib
import json

KINDS = {'order', 'payment', 'claim', 'return_receipt', 'carrier_record', 'refund',
         'chargeback', 'withdrawal', 'resolution', 'agent_note'}
PREFIXES = ('sale:', 'payment:', 'claim:', 'return:', 'carrier:', 'refund:', 'chargeback:',
            'withdrawal:', 'resolution:', 'note:', 'grant:', 'purpose:', 'party:', 'order:', 'report:')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def short(value):
    if isinstance(value, str) and value.startswith(PREFIXES):
        return value.split(':', 1)[1]
    return value


def records(state):
    source = state['native']['records'] if 'native' in state else state['records']
    aliases = {rid: 'RES' + str(i + 1) for i, rid in enumerate(
        rid for rid, rows in source.items() if rows[-1]['kind'] == 'resolution')}
    found = {}
    for rid, rows in source.items():
        if rows[-1]['kind'] not in KINDS:
            if rows[-1]['kind'] not in {'grant', 'purpose', 'party', 'stored_order', 'report', 'acknowledgment', 'acceptance'}:
                raise ValueError('unmapped actual record kind: ' + rows[-1]['kind'])
            continue
        name = aliases.get(rid, short(rid))
        history = []
        for row in rows:
            kind, f = row['kind'], deepcopy(row['fields'])
            if kind == 'resolution' and 'question_id' in f:
                answer = f['answer']
                if set(answer) - {'about', 'decision', 'surviving', 'substantive_basis', 'correction_envelope'}:
                    raise ValueError('unmapped resolution answer fields')
                refs = f.get('basis', [])
                if len(refs) > 1:
                    raise ValueError('multiple resolution basis records are outside the finite W0 encoding')
                normalized = dict(question=f['question_id'], about=short(answer['about']),
                    answer=answer['decision'], by=short(f['envelope']['authenticated_sender']))
                if answer.get('surviving') is not None:
                    normalized['surviving'] = short(answer['surviving'])
                if answer.get('substantive_basis') is not None:
                    normalized['basis'] = answer['substantive_basis']
                if refs:
                    ref = refs[0]
                    normalized['evidence'] = short(ref['record_id']) + '@v' + str(ref['record_version'])
                f = normalized
            for key in ('claim', 'claimant', 'order', 'payer', 'customer', 'about', 'surviving'):
                if key in f:
                    f[key] = short(f[key])
            history.append(dict(kind=kind, fields=f, version=row['version'], evidential=row['evidential']))
        if name in found:
            raise ValueError('ambiguous record alias: ' + name)
        found[name] = history
    return found


def grants(state):
    result = {}
    for gid, original in state['grants'].items():
        g = deepcopy(original)
        scope = g.get('scope', {})
        if 'customer' in scope:
            scope['customers'] = scope.pop('customer')
        result[short(gid)] = dict(grantor=short(g['grantor']), grantee=short(g['grantee']),
            parent=short(g.get('parent')), actions=sorted(g['actions']), status=g['status'],
            scope=scope, limits=g.get('limits', {}), purpose=short(g.get('purpose', 'P1')),
            expires_at=g.get('expires_at', 100000))
    return result


def orders(state):
    found = {}
    for oid, order in state['orders'].items():
        effects = []
        for effect in order['requested_effects']:
            f = deepcopy(effect)
            if 'arguments' in f:
                f = dict(f.pop('arguments'), **f)
            effects.append(f)
        found[short(oid)] = dict(id=short(oid), **{'from': short(order['from']), 'to': short(order['to'])}, requested_effects=effects)
    return found


def notices(state):
    return [deepcopy(n['args'] if 'args' in n else n) for n in state['notices']]


def view(state):
    return dict(step=state['step'], world=deepcopy(state['world']), records=records(state),
                grants=grants(state), orders=orders(state), notices=notices(state), cases=deepcopy(state['cases']))


def context(state, oracle):
    v = view(state)
    # Explicit simulator defaults: omitted root expiry/purpose mean 100000/P1
    # in the reviewed native world. All development steps are strictly below it.
    v['duties'] = oracle.board()
    return hashlib.sha256(canonical(v).encode()).hexdigest()


def report_artifacts(state):
    """Actual report records/dispatches, never internal duty status assertions."""
    found = []
    if 'native' in state:
        for row in state['log']:
            event = row['native_event']
            if event['type'] != 'report_sent':
                continue
            env = event['payload']['envelope']
            p = env['content']
            if 'duty_id' in p:
                claim = p['duty_id'].split('(', 1)[1].split(',', 1)[0].split(')', 1)[0]
                key = ['unowned', claim]
            else:
                order = p['order']
                issuer = short(order['envelope']['authenticated_sender'])
                claim = next(e['arguments']['claim'] for e in order['requested_effects'] if 'claim' in e['arguments'])
                elements = [el for c in p['facts'] if c['id'] == p['rule'] for el in c.get('prohibited_elements', [])]
                if len(elements) != 1:
                    raise ValueError('ambiguous physical report element')
                el = elements[0]
                effect = el.get('assertion', 'to:' + str(el.get('arguments', {}).get('to')))
                key = [issuer, claim, effect]
            found.append(dict(id=p['report_id'], version=p['version'], to=short(env['recipient']),
                              key=key, incidents=[short(i) for i in p['incidents']]))
    elif 'relational_checkpoint' in state:
        # Versioned SQL report rows are the comparator's committed abstract
        # dispatch artifacts. Its duty and allocation relations are not read.
        for rid, version, payload in state['relational_checkpoint']['relations']['reports']:
            p = json.loads(payload)
            if not p['recipient']:
                continue
            if p['matter'] is None:
                key = ['unowned', p['duty'].split('(', 1)[1].split(')', 1)[0]]
            else:
                key = deepcopy(p['matter'])
                if key[2] == 'payment_route':
                    destinations = {e['to'] for oid in p['incidents']
                                    for e in state['orders'][oid]['requested_effects']
                                    if e['tool'] == 'issue_refund' and 'to' in e}
                    if len(destinations) != 1:
                        raise ValueError('ambiguous SQL payment-route report')
                    key[2] = 'to:' + destinations.pop()
            found.append(dict(id=rid, version=p['version'], to=p['recipient'], key=key, incidents=deepcopy(p['incidents'])))
    # Ledger-free arms actually have no report artifact collection or dispatch
    # log. Agent report calls are business operations, not fabricated gateways.
    return found
