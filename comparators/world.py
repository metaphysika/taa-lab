"""Small trusted W0 service for the POEC arm; no gateway policy predicates.

Source authentication belongs to the scripted host, not tool arguments. This
module models business effects only; it creates no duties or automated reports.
"""
from contextlib import contextmanager
from copy import deepcopy
from threading import RLock


class World:
    def __init__(self, definition, setup=None):
        setup = setup or {}
        self.definition = deepcopy(definition)
        self.records, self.sources, self.notices, self.cases, self.external = {}, {}, [], {}, []
        self.operations = []
        self._lock, self.step = RLock(), 1
        seed = deepcopy(definition['records'])
        for rid in setup.get('remove_records', []):
            seed.pop(rid, None)
        for rid, changes in setup.get('records', {}).items():
            seed.setdefault(rid, {}).update(deepcopy(changes))
        for rid, fields in seed.items():
            source = definition['trust_boundary'].get(fields['kind'], {}).get('create', ['setup'])[0]
            self.put(rid, fields, source)

    def put(self, rid, fields, source):
        data = deepcopy(fields)
        kind = data.pop('kind')
        rows = self.records.setdefault(rid, [])
        if rows and rows[-1]['kind'] != kind:
            raise ValueError('kind change')
        row = {'id': rid, 'version': len(rows) + 1, 'kind': kind, 'fields': data}
        rows.append(row)
        self.sources[(rid, row['version'])] = source
        return deepcopy(row)

    def current(self, rid):
        rows = self.records.get(rid, [])
        return deepcopy(rows[-1]) if rows else None

    def snapshot(self):
        return deepcopy({'records': self.records, 'notices': self.notices, 'cases': self.cases, 'operations': self.operations})

    @contextmanager
    def transaction(self):
        with self._lock:
            before, sources = self.snapshot(), deepcopy(self.sources)
            try:
                yield
            except BaseException:
                self.records, self.notices, self.cases = before['records'], before['notices'], before['cases']
                self.operations = before['operations']
                self.sources = sources
                raise

    def event(self, event):
        # This entrypoint is simulator-only. No controller receives a source
        # handle or calls it; the shared harness supplies the original events.
        e = deepcopy(event)
        with self._lock:
            typ = e['type']
            if typ in ('record_insert', 'record_correction'):
                old = self.current(e['record'])
                if typ == 'record_insert':
                    if old is not None:
                        raise ValueError('create requires fresh record')
                    fields = e['fields']
                    policy = self.definition['trust_boundary'][fields['kind']]
                    if e['by'] not in policy.get('create', []):
                        raise ValueError('source cannot create kind')
                else:
                    if old is None:
                        raise ValueError('correction requires existing record')
                    policy = self.definition['trust_boundary'][old['kind']]
                    if not set(e['new']) <= set(policy.get('correct', {}).get(e['by'], [])):
                        raise ValueError('source cannot correct these fields')
                    fields = dict(old['fields'], kind=old['kind'], **e['new'])
                self.put(e['record'], fields, e['by'])
            # Grant/roster/order/reviewer events remain visible host inputs.
            # They do not mutate this arm's already-frozen POEC contract.
            self.external.append(e)

    def apply(self, tool, args, actor):
        if tool == 'issue_refund':
            claim = self.current(args['claim'])['fields']
            order = self.current(claim['order'])['fields']
            number = 1
            while 'REF' + str(number) in self.records:
                number += 1
            self.put('REF' + str(number), dict(kind='refund', claim=args['claim'], claimant=claim['claimant'],
                     order=claim['order'], amount=args['amount'], currency=order['currency'],
                     to=args['to'], settled=True), 'executor')
        elif tool == 'message_party':
            self.notices.append(dict(actor=actor, **deepcopy(args)))
        elif tool == 'close_case':
            self.cases[args['case']] = True
        else:
            raise ValueError('outside the frozen task contract effect profile')
        self.operations.append({'actor': actor, 'tool': tool, 'args': deepcopy(args)})

    def observed_execution(self, before):
        from comparators.execution_observation import invocation
        actual = invocation(before['operations'], self.operations)
        effect = self.observed_effect(before, actual['tool'])
        from comparators.execution_observation import check_notice
        check_notice(actual, effect)
        return dict(actual, effect=effect)

    def observed_effect(self, before, tool):
        # Never accept an effect list returned by apply(). Observe actual state.
        for rid, history in before['records'].items():
            if self.records.get(rid, [])[:len(history)] != history:
                raise ValueError('historical record changed')
        if tool != 'issue_refund' and self.records != before['records']:
            raise ValueError('unexpected record mutation')
        if tool != 'message_party' and self.notices != before['notices']:
            raise ValueError('unexpected notice mutation')
        if tool != 'close_case' and self.cases != before['cases']:
            raise ValueError('unexpected closure mutation')
        if tool == 'issue_refund':
            rows = [versions[-1] for rid, versions in self.records.items()
                    if len(versions) > len(before['records'].get(rid, []))]
            if len(rows) != 1:
                raise ValueError('effect must be one actual refund record')
            return dict(rows[0]['fields'], record=rows[0]['id'], kind=rows[0]['kind'])
        if tool == 'message_party':
            notices = self.notices[len(before['notices']):]
            if len(notices) != 1:
                raise ValueError('effect must be one actual notice')
            return dict(notices[0], kind='notice')
        changed = [claim for claim, closed in self.cases.items() if closed and before['cases'].get(claim) is not True]
        if len(changed) != 1:
            raise ValueError('effect must be one case closure')
        return {'kind': 'case_closed', 'claim': changed[0]}
