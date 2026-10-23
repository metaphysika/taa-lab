"""Independent, non-normative observations of full before/after state.

No model policy/helper imports. Returned descriptions are checked, never used as
world evidence. Historical versions are pinned on first observation.
"""
from copy import deepcopy
import json


def equal(a, b):
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def latest_records(state, kind):
    return [(rid, versions[-1]['fields']) for rid, versions in sorted(state['records'].items())
            if versions and versions[-1]['kind'] == kind]


def state_delta(before, after):
    return {key: {"before_present": key in before, "after_present": key in after,
                  "before": deepcopy(before.get(key)), "after": deepcopy(after.get(key))}
            for key in sorted(before.keys() | after.keys())
            if (key in before) != (key in after) or not equal(before.get(key), after.get(key))}


def record_writes(before, after):
    writes = []
    for rid, versions in after['records'].items():
        old = before['records'].get(rid, [])
        for index, version in enumerate(versions):
            if index >= len(old) or not equal(old[index], version):
                writes.append({'record': rid, 'index': index, 'version': deepcopy(version)})
    return writes


def effects(before, after):
    # In the frozen trace vocabulary committed is the list of record effects.
    # Other committed changes (duties, notices, allocations, etc.) are separately
    # visible in full state_delta and lifecycle assertions, never discarded.
    return [{'record': w['record'], 'kind': w['version']['kind'], **deepcopy(w['version']['fields'])}
            for w in record_writes(before, after)]


def consumed(before, after):
    return [tid for tid, t in after['tokens'].items() if t['status'] == 'consumed' and
            (tid not in before['tokens'] or before['tokens'][tid]['status'] != 'consumed')]


def issued(before, after):
    return [tid for tid, t in after['tokens'].items() if tid not in before['tokens'] or
            (t['status'] == 'live' and before['tokens'][tid]['status'] != 'live')]


def executed(before, after):
    # Legitimate gateway reporting is not execution of the proposed agent act.
    business = any(w['version']['kind'] != 'report' for w in record_writes(before, after))
    business |= not equal(before['notices'], after['notices']) or not equal(before['allocations'], after['allocations'])
    business |= any(closed and not before['cases'].get(cid) for cid, closed in after['cases'].items())
    for did in before['duties'].keys() | after['duties'].keys():
        old, new = before['duties'].get(did), after['duties'].get(did)
        if (new or old).get('kind') not in ('report', 'unowned_report') and not equal(old, new):
            business = True
    business |= any(not equal(before[k], after[k]) for k in ('orders', 'grants', 'world'))
    if 'business_operations' in before or 'business_operations' in after:
        business |= (('business_operations' in before) != ('business_operations' in after) or
                     not equal(before['business_operations'], after['business_operations']))
    return bool(business or consumed(before, after) or not equal(before['receipts'], after['receipts']))


def report_sends(state):
    """Actual dispatch artifacts in commit order, including same-role re-dispatch."""
    found = []
    if 'native' in state:
        for row in state['log']:
            event = row['native_event']
            if event['type'] == 'report_sent':
                envelope = event['payload']['envelope']; content = envelope['content']
                found.append(dict(type='report_dispatched', report_id=content['report_id'],
                                  version=content['version'], to=envelope['recipient'].split(':', 1)[-1]))
    elif 'relational_checkpoint' in state:
        prior = {}
        for event in (entry['sql_event'] for entry in state['log'] if 'sql_event' in entry):
            if event['kind'] != 'version_written' or event['payload']['relation'] != 'reports':
                continue
            rid, payload = event['payload']['id'], event['payload']['payload']
            old = prior.get(rid)
            if payload['recipient'] and (old is None or any(payload.get(k) != old.get(k)
                    for k in ('recipient', 'version', 'dispatch_step'))):
                found.append(dict(type='report_dispatched', report_id=rid,
                                  version=payload['version'], to=payload['recipient']))
            prior[rid] = payload
    else:
        found = [{k: e[k] for k in ('type', 'report_id', 'version', 'to')}
                 for e in state['log'] if e['type'] == 'report_dispatched']
    return found


def dispatches(before, after):
    old, new = report_sends(before), report_sends(after)
    if old != new[:len(old)]:
        raise ValueError('retained report dispatch history changed')
    return new[len(old):]


def sql_relations(state):
    """Non-normative decoding of actual relational checkpoint rows."""
    relations = {}
    for name, rows in state['relational_checkpoint']['relations'].items():
        histories = {}
        for rid, version, serialized in rows:
            history = histories.setdefault(rid, [])
            if type(version) is not int or version != len(history) + 1:
                raise ValueError('non-contiguous SQL version sequence')
            history.append(json.loads(serialized))
        relations[name] = histories
    return relations


def sql_projection(state):
    """Independently check observations against SQL rows, not adapter outputs.

    Only published serialization mappings live here; no policy, authorization,
    discharge or transaction predicates. This supplements the same state audits.
    """
    history = sql_relations(state)
    current = {name: {rid: rows[-1] for rid, rows in histories.items()} for name, histories in history.items()}
    expected = {name: current[name] for name in ('duties', 'reports', 'grants', 'orders', 'allocations')}
    expected['records'] = {rid: [dict(row, version=index + 1) for index, row in enumerate(rows)] for rid, rows in history['records'].items()}
    expected['cases'] = {rid: row['closed'] for rid, row in current['cases'].items()}
    expected['notices'] = [row for rid, row in sorted(current['notices'].items(), key=lambda x: (len(x[0]), x[0]))]
    expected['tokens'] = {'T' + rid[1:]: {'actor': row['actor'], 'tool': row['tool'], 'args': row['args'],
                          'revision': row['epoch'], 'expires': row['expires'], 'status': row['status']}
                          for rid, row in current['handles'].items()}
    expected['receipts'] = [{'token': 'T' + rid[1:], 'actor': row['actor'], 'pre_transaction_revision': row['pre_transaction_epoch'],
        'committed': [{'record': effect['id'], 'kind': effect['payload']['kind'], **effect['payload']['fields']}
                      for effect in row['effects'] if effect['relation'] == 'records']}
        for rid, row in sorted(current['receipts'].items(), key=lambda x: int(x[0][1:]))]
    expected['decisions'] = [row for rid, row in sorted(current['decisions'].items(), key=lambda x: int(x[0][1:]))]
    expected['world'] = current['configuration']['world']
    expected['setup'] = current['configuration']['setup']
    expected['revision'] = state['relational_checkpoint']['epoch']
    expected['step'] = state['relational_checkpoint']['step']
    return expected


class Observer:
    def __init__(self, initial):
        self.versions = {}
        self.committed = []
        self.audit_count = 0
        self.capture(initial)

    def capture(self, state):
        collections = {"": state['records']}
        if 'native' in state:
            collections['native.records:'] = state['native']['records']
            collections['native.duties:'] = state['native']['duty_records']
        if 'relational_checkpoint' in state:
            for name, rows in sql_relations(state).items():
                collections['sql.' + name + ':'] = rows
        all_records = {prefix + rid: versions for prefix, records in collections.items() for rid, versions in records.items()}
        changed = []
        for ref, original in self.versions.items():
            rid, index = ref
            versions = all_records.get(rid, [])
            if index >= len(versions) or not equal(versions[index], original):
                changed.append(f'{rid}@v{index + 1}')
        for rid, versions in all_records.items():
            for index, version in enumerate(versions):
                self.versions.setdefault((rid, index), deepcopy(version))
        return changed

    def audit(self, label, before, after, result, *, agent=False, execute=None):
        self.audit_count += 1
        checks = []
        def check(name, actual, reported):
            matches = equal(actual, reported)
            checks.append({'assertion': label + '.' + name,
                           'expectation': 'matches actual state' if matches else actual,
                           'observed': 'verified' if matches else reported,
                           'status': 'pass' if matches else 'discrepancy', 'origin': 'state-audit'})
        check('immutable_record_versions', [], self.capture(after))
        if 'relational_checkpoint' in after:
            for key, actual_rows in sql_projection(after).items():
                check('sql_projection.' + key, actual_rows, after[key])
        if 'business_operations' in before:
            for channel in ('business_operations', 'messages'):
                check(channel + '_history_retained', before[channel], after[channel][:len(before[channel])])
        if after.get('execution_protocol') == 'poec':
            actual = {tid: dict(actor=row['certificate']['actor'], tool=row['certificate']['tool'],
                               args=row['certificate']['arguments'], status=row['status'])
                      for tid, row in after['poec']['certificates'].items()}
            projected = {tid: {k: row[k] for k in ('actor', 'tool', 'args', 'status')}
                         for tid, row in after['tokens'].items()}
            check('poec_certificate_projection', actual, projected)
        # Every state collection, including all record versions, is included.
        # Absence of this adapter contract is incomplete, not a fabricated zero.
        if 'state_delta' not in result:
            checks.append({'assertion': label + '.state_delta', 'expectation': 'full before/after description',
                           'observed': 'missing', 'status': 'incomplete', 'origin': 'state-audit'})
        else:
            check('state_delta', state_delta(before, after), result['state_delta'])
        actual_effects = effects(before, after) if agent else []
        if agent:
            self.committed.extend(deepcopy(actual_effects))
        if 'committed' in result:
            check('committed', actual_effects, result['committed'])
        if 'action_executed' in result:
            check('action_executed', executed(before, after) if agent else False, result['action_executed'])
        if 'records_written' in result:
            actual = [{'kind': w['version']['kind'], 'evidential': w['version']['evidential']}
                      for w in record_writes(before, after)]
            check('records_written', actual, result['records_written'])
        if 'tokens_issued_by_reviewer' in result:
            check('tokens_issued_by_reviewer', len(issued(before, after)), result['tokens_issued_by_reviewer'])
        if 'gateway_transitions' in result:
            check('gateway_transitions', [dict(d, step=after["step"]) for d in dispatches(before, after)], result['gateway_transitions'])
        if agent and execute is None:
            old, new = before['decisions'], after['decisions']
            fresh = len(new) > len(old)
            repeat = len(new) == len(old) and any(n['repeats'] > o['repeats'] for o, n in zip(old, new))
            for field, actual in (('fresh_evaluation', fresh), ('recorded_decision_returned', repeat)):
                if field in result:
                    check(field, actual, result[field])
        if agent:
            new_receipts = after['receipts'][len(before['receipts']):]
            check('receipt_history_retained', before['receipts'], after['receipts'][:len(before['receipts'])])
            if execute is None:
                check('proposal_does_not_execute', False, executed(before, after))
            else:
                took = consumed(before, after)
                no_tokens = before.get('execution_protocol') == 'business_operations'
                if no_tokens:
                    check('business_arms_have_no_tokens', {}, after['tokens'])
                    check('business_receipts_have_no_security_token', [], [r['token'] for r in new_receipts if 'token' in r])
                    check('no_security_consumption', [], took)
                elif before.get('execution_protocol') == 'poec':
                    # Published POEC certificates are one-shot on dispatch,
                    # including an aborted dispatch. Verify aborts from the
                    # actual retained policy history, never returned reasons.
                    aborted = [e['certificate'] for e in after['poec']['history'][len(before['poec']['history']):]
                               if e['type'] == 'dispatch_rolled_back']
                    check('consumption_matches_receipts_or_retained_poec_abort', took,
                          [r['token'] for r in new_receipts] + aborted)
                else:
                    check('consumption_matches_receipts', took, [r['token'] for r in new_receipts])
                check('record_effects_match_receipts', actual_effects, [e for r in new_receipts for e in r['committed']])
                if new_receipts:
                    if no_tokens:
                        check('exactly_one_requested_business_operation', [execute.get('token')], [r['intent'] for r in new_receipts])
                        operations = after['business_operations'][len(before['business_operations']):]
                        check('one_actual_business_operation', 1, len(operations))
                        intent = before['intents'][execute['token']]
                        expected_operation = dict(actor=execute['actor'], tool=intent['tool'],
                                                  args=intent['args'], step=after['step'])
                        check('business_operation_matches_bound_intent', [expected_operation], operations)
                    else:
                        check('exactly_one_requested_consumption', [execute.get('token')], took)
                    check('receipt_actor', [execute['actor']], [r['actor'] for r in new_receipts])
                    check('pre_transaction_revision', [before['revision']], [r['pre_transaction_revision'] for r in new_receipts])
        return checks
