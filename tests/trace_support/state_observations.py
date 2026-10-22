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
    return bool(business or consumed(before, after) or not equal(before['receipts'], after['receipts']))


def dispatches(before, after):
    found = []
    for did, d in after['duties'].items():
        if d.get('kind') not in ('report', 'unowned_report') or not d.get('recipient'):
            continue
        old = before['duties'].get(did)
        if old is None or old.get('version') != d['version'] or old.get('recipient') != d['recipient']:
            found.append({'type': 'report_dispatched', 'report_id': d['report_id'],
                          'version': d['version'], 'to': d['recipient']})
    return found


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
                check('consumption_matches_receipts', took, [r['token'] for r in new_receipts])
                check('record_effects_match_receipts', actual_effects, [e for r in new_receipts for e in r['committed']])
                if new_receipts:
                    check('exactly_one_requested_consumption', [execute.get('token')], took)
                    check('receipt_actor', [execute['actor']], [r['actor'] for r in new_receipts])
                    check('pre_transaction_revision', [before['revision']], [r['pre_transaction_revision'] for r in new_receipts])
        return checks
