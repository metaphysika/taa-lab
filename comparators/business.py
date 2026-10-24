"""Ledger-free business arms and a common-runner host for frozen TraceGrant.

Only simulator inputs can write evidence. Proposal handles route intentions;
floor/static handles confer no authority and are neither expiring nor single use.
No core, conventional, or reference decision/transaction code is imported.
"""
from contextlib import contextmanager
from copy import deepcopy

from comparators.tracegrant import TraceGrant, contract, digest, canonical
from comparators.business_faults import FaultAdapter, InjectedBusinessFault

KEY = b'POEC-offline-simulator-certificate-key'
TG_FIELDS = ('states', 'evidence', 'certificates', 'receipts', 'history', 'budget')


def put(s, rid, fields, writer):
    f = deepcopy(fields)
    kind = f.pop('kind')
    rows = s['records'].setdefault(rid, [])
    if rows and rows[-1]['kind'] != kind:
        raise ValueError('record kind change')
    written = dict(id=rid, version=len(rows) + 1, kind=kind, fields=f,
                   writer=writer, evidential=kind != 'agent_note')
    if kind in ('refund','chargeback'):
        # Ordinary version-log metadata: sequence and fact commit in the same
        # append. No extra receipt/log write, authorization or duty machinery.
        written['commit_sequence'] = 1 + max((r['commit_sequence'] for history in s['records'].values()
            for r in history if r['kind'] in ('refund','chargeback')),default=0)
    rows.append(written)
    s['revision'] += 1


def describe(before, after, answer):
    result = deepcopy(answer)
    result['state_delta'] = {k: dict(before_present=k in before, after_present=k in after,
                                    before=deepcopy(before.get(k)), after=deepcopy(after.get(k)))
                             for k in sorted(before.keys() | after.keys())
                             if (k in before) != (k in after) or canonical(before.get(k)) != canonical(after.get(k))}
    return after, result


def schema(tool, args):
    strings = {'claim', 'to', 'basis', 'record', 'case', 'duty', 'template',
               'missing', 'referred_to', 'prose', 'customer', 'cites'}
    required = {'issue_refund': {'claim', 'amount', 'to', 'basis'}, 'message_party': {'to'},
                'close_case': {'case'}, 'read_record': {'record'}, 'offer_duty': {'duty', 'to'},
                'accept_duty': {'duty'}, 'report': {'to'}, 'hold_refund': {'claim', 'missing'},
                'deny_refund': {'claim', 'amount', 'basis'}}
    if not isinstance(args, dict) or not required.get(tool, set()) <= args.keys():
        return False
    allowed = strings | {'amount', 'asserts'} | ({'portion'} if tool=='message_party' else set())
    if tool in ('hold_refund', 'deny_refund'):
        allowed -= {'to'}
    if not args.keys() <= allowed or any(type(v) is not str for k, v in args.items() if k in strings):
        return False
    if 'amount' in args and (type(args['amount']) not in (int, float) or
                            args['amount'] < 1 or type(args['amount']) is float and not args['amount'].is_integer()):
        return False
    if 'asserts' in args and (type(args['asserts']) is not list or any(type(x) is not str for x in args['asserts'])):
        return False
    if 'template' in args and args['template'] not in ('refund_issued', 'refund_denied', 'refund_held', 'claim_referred'):
        return False
    return tool != 'issue_refund' or args['basis'] in ('return', 'nondelivery', 'goodwill')


class Service:
    def __init__(self, state):
        self.s = state

    def current(self, rid):
        history = self.s['records'].get(rid, [])
        return {k: deepcopy(history[-1][k]) for k in ('id', 'version', 'kind', 'fields')} if history else None

    def snapshot(self):
        return dict(deepcopy({k: self.s[k] for k in ('records', 'notices', 'cases')}), operations=deepcopy(self.s['business_operations']))

    @contextmanager
    def transaction(self):
        before = deepcopy(self.s)
        try:
            yield
        except BaseException:
            self.s.clear()
            self.s.update(before)
            raise

    def apply(self, tool, args, actor, fault=None):
        s = self.s
        if tool == 'issue_refund':
            claim = self.current(args['claim'])['fields']
            order = self.current(claim['order'])['fields']
            n = 1
            while 'REF' + str(n) in s['records']:
                n += 1
            put(s, 'REF' + str(n), dict(kind='refund', claim=args['claim'], claimant=claim['claimant'],
                order=claim['order'], amount=args['amount'], currency=order['currency'],
                to=args['to'], settled=True), 'executor')
        elif tool == 'message_party':
            s['notices'].append(dict(actor=actor, args=deepcopy(args), step=s['step']))
        elif tool == 'close_case':
            s['cases'][args['case']] = True
        if fault is not None and tool in ('issue_refund','message_party','close_case'):
            fault.hit('during_effect_commit')
        # Other registered calls are ordinary recorded business operations.
        # In particular, offers/acceptance do not create or consult a ledger.
        s['business_operations'].append(dict(actor=actor, tool=tool, args=deepcopy(args), step=s['step']))
        if fault is not None and tool not in ('issue_refund','message_party','close_case'):
            fault.hit('during_effect_commit')
        s['revision'] += 1

    def observed_execution(self, before):
        from comparators.execution_observation import invocation, check_notice
        actual = invocation(before['operations'], self.s['business_operations'])
        effect = self.observed_effect(before, actual['tool'])
        check_notice(actual, effect)
        return dict(actual, effect=effect)

    def observed_effect(self, before, tool):
        s = self.s
        if tool == 'issue_refund':
            rows = [(rid, row) for rid, h in s['records'].items()
                    for row in h[len(before['records'].get(rid, [])):]]
            if len(rows) != 1:
                raise ValueError('not one observed refund')
            rid, row = rows[0]
            return dict(row['fields'], record=rid, kind=row['kind'])
        if tool == 'message_party':
            delta = s['notices'][len(before['notices']):]
            if len(delta) != 1:
                raise ValueError('not one observed notice')
            return dict(delta[0]['args'], actor=delta[0]['actor'], kind='notice')
        changes = [cid for cid, closed in s['cases'].items() if closed and not before['cases'].get(cid)]
        if len(changes) != 1:
            raise ValueError('not one observed closure')
        return dict(kind='case_closed', claim=changes[0])


class Backend:
    def __init__(self, arm, task=None):
        if arm not in ('floor', 'static', 'tracegrant'):
            raise ValueError('unknown business arm')
        self.arm, self.task = arm, task

    def start(self, world, setup=None, *, defer_first_step=False):
        setup = deepcopy(setup or {})
        s = dict(world=deepcopy(world), setup=setup, revision=0, step=0, records={}, orders={},
                 grants=deepcopy(world['grants']), duties={}, cases={}, tokens={}, decisions=[],
                 receipts=[], log=[], reports={}, allocations={}, notices=[], phase_order=[],
                 intents={}, business_operations=[], messages=[], arm=self.arm,
                 execution_protocol='poec' if self.arm == 'tracegrant' else 'business_operations')
        if 'roster_change' in setup.get('host_events', []):
            for party in list(world['parties']) + ['company']:
                put(s, party, dict(kind='party', name=party, role=world['parties'].get(party, {}).get('role', 'root'),
                    jurisdictions=[j for j, members in world['jurisdictions'].items() if party in members]
                        if party != 'company' else ['root', 'interim'],
                    conflicts=[], may_receive=[j for j in ('misconduct_reports', 'unowned_duties')
                        if party in world['jurisdictions'][j]]), 'company')
        seed = deepcopy(world['records'])
        for rid in setup.get('remove_records', []):
            seed.pop(rid, None)
        for rid, change in setup.get('records', {}).items():
            seed.setdefault(rid, {}).update(change)
        for rid, fields in seed.items():
            writer = world['trust_boundary'].get(fields['kind'], {}).get('create', ['setup'])[0]
            put(s, rid, fields, writer)
            if fields['kind'] == 'claim':
                s['cases'][rid] = False
        for gid, change in setup.get('grants', {}).items():
            s['grants'].setdefault(gid, {}).update(change)
        s['static_grants'] = deepcopy(s['grants'])
        if self.arm == 'tracegrant':
            self._save(s, TraceGrant(contract(self.task), certificate_key=KEY))
        return s if defer_first_step else self.enter_step(s, 1)[0]

    def _load(self, s):
        g = TraceGrant(contract(self.task), certificate_key=KEY)
        for name in TG_FIELDS:
            setattr(g, name, deepcopy(s['poec'][name]))
        return g

    def _save(self, s, g):
        s['poec'] = {k: deepcopy(getattr(g, k)) for k in TG_FIELDS}
        old = s['tokens']
        s['tokens'] = {tid: dict(actor=row['certificate']['actor'], tool=row['certificate']['tool'],
            args=deepcopy(row['certificate']['arguments']), status=row['status'], expires=None,
            revision=old.get(tid, {}).get('revision', s['revision'])) for tid, row in g.certificates.items()}

    def _admit(self, s, g):
        service = Service(s)
        for key, node in g.c['MUST'].items():
            if node['kind'] == 'evidence' and g.states[key] == 'ACTIVE':
                record = service.current(node['record'])
                if record:
                    writer = s['records'][record['id']][-1]['writer']
                    g.admit(key, [dict(record, integrity=digest(record))], authenticated_source=writer, query=node['query'])

    def enter_step(self, before, step, events=(), *, event_observer=None):
        s = deepcopy(before)
        if step < s['step']:
            raise ValueError('clock reversal')
        s['step'], s['phase_order'] = step, []
        for index, event in enumerate(events):
            prior = deepcopy(s)
            self.event(s, event)
            if event_observer:
                event_observer(index, prior, deepcopy(s), describe(prior, s, {})[1])
        if self.arm == 'tracegrant':
            g = self._load(s)
            self._admit(s, g)
            self._save(s, g)
        s['phase_order'].append('duty_engine')  # common phase slot; no internal duty computation
        return describe(before, s, {})

    def advance(self, before, step):
        return self.enter_step(before, step)[0]

    @staticmethod
    def reconcile(s):
        return None

    @staticmethod
    def event(s, event):
        e = deepcopy(event)
        typ = e['type']
        if typ == 'roster_change':
            if typ not in s['setup'].get('host_events', []):
                raise ValueError('roster event requires regression overlay')
            row = Service(s).current(e.get('party')) if type(e.get('party')) is str else None
            keys = ('add_jurisdictions', 'remove_jurisdictions', 'add_may_receive', 'remove_may_receive')
            valid = (not set(e) - {'type', 'by', 'party', *keys} and
                all(type(e.get(k, [])) is list and all(type(x) is str and x for x in e.get(k, [])) for k in keys))
            if e.get('by') != 'company' or not row or row['kind'] != 'party' or not valid:
                s['log'].append(dict(type='rejected_roster_change', event=e))
                return
            fields = deepcopy(row['fields'])
            for field in ('jurisdictions', 'may_receive'):
                members = (set(fields[field]) - set(e.get('remove_' + field, []))) | set(e.get('add_' + field, []))
                fields[field] = [v for v in fields[field] if v in members]
                for v in e.get('add_' + field, []):
                    if v not in fields[field]:
                        fields[field].append(v)
            if fields != row['fields']:
                put(s, e['party'], dict(fields, kind='party'), 'company')
            else:
                s['log'].append(dict(type='roster_change_noop', event=e))
        elif typ in ('record_insert', 'record_correction'):
            rid = e['record']
            current = Service(s).current(rid)
            if typ == 'record_insert':
                fields = e['fields']
                if current or e['by'] not in s['world']['trust_boundary'][fields['kind']].get('create', []):
                    raise ValueError('untrusted creation')
            else:
                if current is None:
                    raise ValueError('correction lacks record')
                rights = s['world']['trust_boundary'][current['kind']].get('correct', {}).get(e['by'], [])
                if not set(e['new']) <= set(rights):
                    raise ValueError('untrusted correction')
                fields = dict(current['fields'], kind=current['kind'], **e['new'])
            put(s, rid, fields, e['by'])
        elif typ == 'order':
            if e['from'] not in s['world']['parties'] or e['id'] in s['orders']:
                raise ValueError('untrusted/duplicate order')
            s['orders'][e['id']] = e
            s['revision'] += 1
        elif typ.startswith('grant_'):
            if e['by'] not in s['world']['jurisdictions']['refund_authority']:
                raise ValueError('untrusted grant change')
            if typ == 'grant_issue':
                s['grants'][e['grant']] = dict(deepcopy(s['grants'][e['same_terms_as']]), grantee=e['to'], grantor=e['by'], status='live')
            elif typ == 'grant_revocation':
                s['grants'][e['grant']]['status'] = 'revoked'
            elif typ == 'grant_amendment':
                for key, value in e['change'].items():
                    if key == 'per_refund_max':
                        s['grants'][e['grant']]['limits'][key] = value
                    else:
                        s['grants'][e['grant']][key] = value
            s['revision'] += 1
        elif typ == 'resolution':
            spec = s['world']['reserved_questions'].get(e['question'])
            if isinstance(spec, dict) and e.get('via') == 'reviewer_interface' and e['by'] in s['world']['jurisdictions'][spec['resolver']]:
                rid = 'RES' + str(1 + sum(h[-1]['kind'] == 'resolution' for h in s['records'].values()))
                fields = {k: v for k, v in e.items() if k not in ('type', 'via', 'reviewer_says')}
                put(s, rid, dict(kind='resolution', **fields), 'reviewer_interface')
        elif typ not in ('message', 'acknowledgment', 'duty_acceptance'):
            raise ValueError('unregistered external event: ' + typ)
        s['messages'].append(dict(step=s['step'], event=e))
        s['log'].append(dict(type='host_event', step=s['step'], event=e))

    def allowed(self, s, actor, tool, args):
        if self.arm != 'static':
            return True
        resource = args.get('claim', args.get('case'))
        if resource is None and '(' in args.get('duty', ''):
            resource = args['duty'].split('(', 1)[1].split(',', 1)[0].split(')', 1)[0]
        claim = Service(s).current(resource)
        customer = (claim or {}).get('fields', {}).get('claimant', args.get('customer'))
        if customer is None and s['world']['parties'].get(args.get('to'), {}).get('role') == 'customer':
            customer = args['to']
        for gid, grant in s['static_grants'].items():
            if grant['grantee'] != actor or tool not in grant['actions']:
                continue
            path, seen = [], set()
            while gid and gid not in seen:
                seen.add(gid)
                node = s['static_grants'].get(gid)
                if not node or node['status'] != 'live' or node.get('expires_at', 10**12) <= 0:
                    break
                parent = s['static_grants'].get(node.get('parent'))
                if node.get('parent') and (not parent or parent['grantee'] != node['grantor'] or
                                           'grant_refund_authority' not in parent['actions']):
                    break
                path.append(node)
                gid = node.get('parent')
            else:
                if gid:  # cyclic ancestry
                    continue
                if any(customer and customer not in g.get('scope', {}).get('customers', [customer]) for g in path):
                    continue
                if args.get('amount', 0) > min(g.get('limits', {}).get('per_refund_max', 10**12) for g in path):
                    continue
                return True
        return False

    def propose(self, before, actor, tool, args, order_reference=None):
        s = deepcopy(before)
        answer = dict(disposition='REFUSE')
        if tool not in s['world']['tool_registry']['registered'] or not schema(tool, args):
            answer['call_result'] = 'rejected_unregistered_tool' if tool not in s['world']['tool_registry']['registered'] else 'rejected_arguments'
        elif self.arm == 'tracegrant':
            g = self._load(s)
            decision = g.decide(actor, tool, args)
            self._save(s, g)
            answer.update(poec_decision=decision, disposition='PERMIT' if decision['decision'] == 'ALLOW' else 'REFUSE',
                          token=decision.get('certificate', {}).get('id'))
        elif self.allowed(s, actor, tool, args):
            intent = 'I' + str(len(s['intents']) + 1)
            s['intents'][intent] = dict(actor=actor, tool=tool, args=deepcopy(args))
            answer.update(disposition='PERMIT', execution_intent=intent)
        s['log'].append(dict(type='proposal', actor=actor, tool=tool, args=deepcopy(args), answer=deepcopy(answer)))
        return describe(before, s, answer)

    def execute(self, before, actor, token=None, fault=None):
        adapter = FaultAdapter(fault) if fault is not None and self.arm != 'tracegrant' else None
        s = deepcopy(before)
        interrupted = False
        answer = dict(execute_result='refused_no_token')
        if self.arm == 'tracegrant':
            g = self._load(s)
            cert = g.certificates.get(token, {}).get('certificate')
            if cert:
                if fault is not None:
                    raise ValueError('cross-arm development programs contain no POEC fault injection')
                result = g.dispatch(cert, actor, cert['tool'], cert['arguments'], Service(s))
                answer.update(poec_dispatch=result, execute_result='committed' if result['dispatch'] == 'committed' else result['dispatch'])
            self._save(s, g)
        elif token in s['intents']:
            act = s['intents'][token]
            if self.allowed(s, actor, act['tool'], act['args']):
                try:
                    if adapter is not None:
                        adapter.hit('after_validate')
                    # Floor/static have no rollback. A failure preserves writes.
                    Service(s).apply(act['tool'], act['args'], actor, adapter)
                    answer['execute_result'] = 'committed'
                except InjectedBusinessFault as error:
                    interrupted = True
                    answer.update(execute_result='failed', reason=str(error), fault_at=fault)
                except (KeyError, ValueError) as error:
                    answer.update(execute_result='failed', reason=str(error))
            else:
                answer['execute_result'] = 'refused_static_permissions'
        if answer['execute_result'] == 'committed':
            written = [dict(row['fields'], record=rid, kind=row['kind']) for rid, h in s['records'].items()
                       for row in h[len(before['records'].get(rid, [])):]]
            receipt = dict(actor=actor, pre_transaction_revision=before['revision'], committed=written,
                           step=s['step'], tool=s['business_operations'][-1]['tool'], args=deepcopy(s['business_operations'][-1]['args']))
            receipt['token' if self.arm == 'tracegrant' else 'intent'] = token
            try:
                if adapter is not None:
                    adapter.hit('during_receipt_write')
                s['receipts'].append(receipt)
                if adapter is not None:
                    adapter.hit('before_log_write')
            except InjectedBusinessFault as error:
                interrupted = True
                answer.update(execute_result='failed', reason=str(error), fault_at=fault)
        if not interrupted:
            s['log'].append(dict(type='execute', actor=actor, reference=token, result=answer['execute_result']))
        return describe(before, s, answer)
