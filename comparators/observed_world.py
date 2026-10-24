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
    roster_enabled = 'roster_change' in state.get('setup', {}).get('host_events', state.get('host_events', []))
    for rid, rows in source.items():
        if rows[-1]['kind'] == 'party' and not roster_enabled:
            continue
        if rows[-1]['kind'] not in KINDS | {'party'}:
            if rows[-1]['kind'] not in {'grant', 'purpose', 'party', 'stored_order', 'report', 'acknowledgment', 'acceptance'}:
                raise ValueError('unmapped actual record kind: ' + rows[-1]['kind'])
            continue
        name = aliases.get(rid, short(rid))
        history = []
        for row in rows:
            kind, f = row['kind'], deepcopy(row['fields'])
            if kind == 'party':
                f = {k: sorted(f[k]) if k in ('jurisdictions', 'may_receive') else f[k]
                     for k in ('name', 'role', 'jurisdictions', 'conflicts', 'may_receive')}
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


def context_payload(state, oracle, *, normalize_neutral=True):
    v = view(state)
    # Explicit simulator defaults: omitted root expiry/purpose mean 100000/P1
    # in the reviewed native world. All development steps are strictly below it.
    v['duties'] = oracle.board()
    if normalize_neutral:
        # Narrow schema-specific equivalences only, not recursive null removal.
        # Never mutate actual records, normative facts or original proofs.
        def neutral_fields(kind, fields):
            key = 'allocated_to' if kind in ('refund', 'chargeback') else 'condition' if kind == 'return_receipt' else None
            if key is not None and key in fields and fields[key] is None:
                del fields[key]
        for history in v['records'].values():
            for record in history:
                neutral_fields(record['kind'], record['fields'])
        for record in v['world']['records'].values():
            neutral_fields(record['kind'], record)
        # The current-grant projector already maps absent parent to None.
        # Apply that same root/no-parent representation to seed configuration.
        for grant in v['world']['grants'].values():
            grant.setdefault('parent', None)
        for duty in v['duties'].values():
            for admission in duty.get('admissions', []):
                if admission['args']['template'] == 'refund_issued':
                    neutral_fields('refund', admission['original'])
                elif admission['args']['template'] == 'refund_denied':
                    kind = v['records'][admission['record']][-1]['kind']
                    neutral_fields(kind, admission['original'])
    return v


def context(state, oracle):
    v = context_payload(state, oracle)
    return hashlib.sha256(canonical(v).encode()).hexdigest()


def legacy_context(state, oracle):
    """v0 fingerprint retained for exact observation-level correction auditing."""
    return hashlib.sha256(canonical(context_payload(state, oracle, normalize_neutral=False)).encode()).hexdigest()


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
        previous = {}
        for event in (entry['sql_event'] for entry in state['log'] if 'sql_event' in entry):
            if event['kind'] != 'version_written' or event['payload']['relation'] != 'reports':
                continue
            rid, p = event['payload']['id'], event['payload']['payload']
            prior = previous.get(rid); previous[rid] = p
            if prior is not None and all(p.get(k) == prior.get(k) for k in ('recipient', 'version', 'dispatch_step')):
                continue
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
    for number, artifact in enumerate(found, 1):
        artifact['delivery'] = number
    return found


def payment_commit_order(state):
    """First actual financial writes, from persisted record/audit events only."""
    result=[]
    if 'intents' in state:
        # The business store's version rows are its ordinary write journal.
        financial=[(rid,r) for rid,history in state['records'].items() for r in history if r['kind'] in ('refund','chargeback')]
        if any('commit_sequence' not in r or type(r['commit_sequence']) is not int or r['commit_sequence']<1 for rid,r in financial):
            raise ValueError('business financial record lacks actual write provenance')
        writes=sorted((r['commit_sequence'],rid) for rid,r in financial)
        for sequence,rid in writes:
            if short(rid) not in result:result.append(short(rid))
        return result
    for item in state['log']:
        rid=None
        if 'native_event' in item:
            event=item['native_event']
            if event['type']=='record_version' and event['payload']['record']['kind'] in ('refund','chargeback'):
                rid=event['payload']['record']['id']
        elif 'sql_event' in item:
            event=item['sql_event']
            if event['kind']=='version_written' and event['payload']['relation']=='records' and event['payload']['payload']['kind'] in ('refund','chargeback'):
                rid=event['payload']['id']
        elif item['type']=='financial_write':
            rid=item['record']
        if rid is not None and short(rid) not in result:result.append(short(rid))
    return result


def committed_notice_bindings(state):
    """Pair actual notices with actual committed receipt effects, not decisions.

    Only representation code is used. No arm's duty/ownership/proof ledger is
    consulted. A receipt's argument body must match an actual physical notice.
    """
    physical=notices(state);unused=set(range(len(physical)));receipts=[]
    if 'native' in state:
        for receipt in state['native']['receipts']:
            receipts.append((short(receipt['acting_party']),deepcopy(receipt['effect']['notices'])))
    elif 'relational_checkpoint' in state:
        stored={rid:json.loads(payload) for rid,version,payload in state['relational_checkpoint']['relations']['receipts']}
        for item in state['log']:
            event=item.get('sql_event')
            if not event or event['kind']!='receipt':continue
            receipt=event['payload']
            if stored.get(receipt['handle'])!=receipt:continue
            receipts.append((receipt['actor'],[deepcopy(e['payload']) for e in receipt['effects'] if e['relation']=='notices']))
    else:
        for receipt in state['receipts']:
            candidates=[]
            if 'intents' in state:
                # Ordinary business receipts retain their executed operation.
                if receipt['tool']=='message_party':candidates=[deepcopy(receipt['args'])]
                actor=receipt['actor']
            else:
                token=state['tokens'].get(receipt.get('token'))
                actor=receipt.get('actor')
                if token and token['actor']==actor:
                    a=deepcopy(token['args'])
                    if token['tool']=='message_party':candidates=[a]
                    elif token['tool'] in ('deny_refund','hold_refund'):
                        claim=records(state)[a['claim']][-1]['fields']
                        candidates=[dict(a,to=claim['claimant'],template='refund_denied' if token['tool']=='deny_refund' else 'refund_held')]
            receipts.append((actor,candidates))
    found=[]
    for ordinal,(actor,candidates) in enumerate(receipts):
        if actor is None:continue
        for candidate in candidates:
            for key in ('claim','to','customer','claimant'):
                if key in candidate:candidate[key]=short(candidate[key])
            index=next((i for i in sorted(unused) if canonical(physical[i])==canonical(candidate)),None)
            if index is not None:
                unused.remove(index);found.append(dict(receipt=ordinal,notice_index=index,actor=short(actor),args=deepcopy(physical[index])))
    return found
