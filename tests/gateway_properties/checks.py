"""Independent state/log assertions for P1–P6, not authorization predicates.

No production decision, authorization or discharge callback is reused. The
reference stays separate; its outputs are observations, not expected outcomes.
"""
from copy import deepcopy
from collections import Counter
import hashlib
import json

from tests.trace_support.state_observations import Observer
from taa_gateway.eventlog import verify_jsonl
from tests.trace_support import production_backend as core


ASSERTION_COUNTS = Counter()


class PropertyFailure(AssertionError):
    def __init__(self, property_id, message):
        self.property_id = property_id
        super().__init__(property_id + ': ' + message)


def require(property_id, condition, message):
    ASSERTION_COUNTS[property_id] += 1
    if not condition:
        raise PropertyFailure(property_id, message)


def stable(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def current(native, rid):
    rows = native['records'].get(rid, [])
    return rows[-1] if rows else None


def ledger(native):
    return {did: h[-1]['fields'] for did, h in native['duty_records'].items()}


def p1(before, after, actor=None, token=None, execution=False):
    a, b = before['native'], after['native']
    receipts = b['receipts'][len(a['receipts']):]
    def external_correction(rid, version):
        prior = a['records'].get(rid, [])
        if not prior or version['written_by'] != 'payment_processor' or version['written_under_warrant'] is not None:
            return False
        old, new = prior[-1]['fields'], version['fields']
        changed = {k for k in old.keys() | new.keys() if k not in old or k not in new or stable(old[k]) != stable(new[k])}
        return changed <= {'settled', 'claimant', 'allocated_to'}
    business_writes = {(rid, v['version']) for rid, h in b['records'].items()
                       for v in h[len(a['records'].get(rid, [])):]
                       if v['kind'] == 'refund' and not external_correction(rid, v)}
    receipted = {(v['record_id'], v['record_version']) for r in receipts for v in r['record_versions']}
    require('P1', business_writes <= receipted, 'actual refund write has no receipt-bound token')
    for receipt in receipts:
        require('P1', execution and receipt['token_id'] == token, 'effect outside the requested execution')
        row = a['tokens'].get(token)
        require('P1', row is not None and row['status'] == 'live', 'receipt used a missing or non-live token')
        cert = row['certificate']
        require('P1', actor == cert['acting_party'].split(':', 1)[-1], 'acting party does not match token')
        require('P1', cert['state_revision'] == a['revision'] == receipt['pre_transaction_revision'], 'token is not at the pre-transaction revision')
        require('P1', a['step'] < cert['expires_at_step'], 'expired token committed')
        require('P1', a['warrants'][cert['warrant_id']]['status'] == 'live', 'warrant was not live')
        encoded = stable({'tool': row['tool'], 'arguments': row['args']}).encode()
        require('P1', hashlib.sha256(encoded).hexdigest() == cert['exact_argument_digest'], 'arguments differ from the certificate')
        require('P1', sum(r['token_id'] == token for r in b['receipts']) == 1, 'token committed more than once')
        require('P1', b['tokens'][token]['status'] == 'consumed', 'receipt did not consume token')
        basis = a['warrants'][cert['warrant_id']]['justification']
        purpose = current(a, basis['purpose_id'])
        require('P1', purpose is not None and purpose['kind'] == 'purpose', 'purpose evidence is absent')
        grant_id = basis['grant_id']
        if grant_id.startswith('IR1:'):
            duty = ledger(a).get(grant_id[4:])
            require('P1', duty is not None and duty['owner'] == cert['acting_party'] and
                    duty['resolution'] == 'unresolved' and duty['offered_to'] is not None and
                    duty['interim_rule']['authority_lost'] and a['step'] < duty['offer_deadline_step'] and
                    row['tool'] == 'message_party' and row['args'].get('template') in ('refund_held', 'claim_referred') and
                    row['args'].get('claim') == duty['case_id'] and row['args'].get('to') == duty['claimant'], 'IR1 outside its complete narrow window')
        else:
            require('P1', not grant_id.startswith('ACCEPT:'), 'Q11 forbids offer-derived tool authority')
            grant = current(a, grant_id)
            require('P1', grant is not None and grant['kind'] == 'grant', 'grant is absent')
            g = grant['fields']
            require('P1', g['grantee'] == cert['acting_party'] and row['tool'] in g['action_types'] and
                    g['purpose_id'] == basis['purpose_id'] and stable(g['resource_scope']) == stable(basis['scope']), 'leaf grant does not cover the actual act')
            visited = set()
            while g is not None:
                require('P1', g['id'] not in visited, 'cyclic grant path')
                visited.add(g['id'])
                require('P1', g['status'] == 'live' and a['step'] < g['expires_at_step'], 'expired or revoked grant ancestor')
                cid = row['args'].get('claim', row['args'].get('case'))
                if 'duty' in row['args']:
                    cid = ledger(a)[row['args']['duty']]['case_id']
                claim = current(a, 'claim:' + cid) if cid is not None else None
                for field, allowed in g['resource_scope'].items():
                    require('P1', field == 'customer' and claim is not None, 'unsupported generated-scope field')
                    values = allowed if isinstance(allowed, list) else [allowed]
                    require('P1', claim['fields']['claimant'] in values, 'act lies outside one complete grant path')
                for condition in g['live_conditions']:
                    fact = current(a, condition['record_id'])
                    require('P1', fact is not None and fact['evidential'] and fact['fields'].get(condition['field']) == condition['equals'], 'grant condition is not satisfied')
                parent = g['parent_grant']
                if parent is None:
                    require('P1', g['grantor'] == 'party:company', 'root grant lacks the W0 principal')
                    break
                ancestor = current(a, parent)
                require('P1', ancestor is not None and ancestor['kind'] == 'grant', 'missing grant ancestor')
                ancestor = ancestor['fields']
                require('P1', g['grantor'] == ancestor['grantee'] and 'grant_refund_authority' in ancestor['action_types'] and
                        g['purpose_id'] == ancestor['purpose_id'], 'incoherent grant path')
                g = ancestor
        # Rule-computed read versions/values must still describe this exact state.
        combined = dict(a['records'], **a['duty_records'])
        for fact in basis['rule_facts']:
            require('P1', fact['result'] == 'satisfied', 'warrant includes an unsatisfied rule')
            for query in fact['queries']:
                if query['record_id'].startswith('@kind:'):
                    kind = query['record_id'][6:]
                    values = [h[-1] for _, h in sorted(combined.items()) if h and h[-1]['kind'] == kind]
                    require('P1', stable(values) == stable(query['value']), 'selector support set differs, including insertions/absence')
                    continue
                h = combined.get(query['record_id'], [])
                expected = h[-1] if h else None
                require('P1', stable(expected) == stable(query['value']), 'read value/version differs from pre-transaction state')


def resolve_coverage(native, duty):
    """Independent conservative DU1 accounting for the generated return domain."""
    claim = current(native, 'claim:' + duty['case_id'])['fields']
    order = current(native, 'sale:' + claim['order'])['fields']
    returns = [h[-1] for h in native['records'].values() if h[-1]['kind'] == 'return_receipt' and
               h[-1]['evidential'] and h[-1]['fields'].get('order') == claim['order']]
    require('P2', claim['basis'] == 'return', 'generated checker domain unexpectedly changed')
    supported = min(claim['amount'], order['amount']) if any(r['fields'].get('received') is True for r in returns) else 0
    budget, total, denied, used = max(0, claim['amount'] - supported), 0, 0, set()
    for notice in native['notices']:
        if notice.get('claim') != duty['case_id'] or notice.get('to') != claim['claimant']:
            continue
        amount = notice.get('amount')
        if type(amount) is not int or amount <= 0:
            continue
        if notice.get('template') == 'refund_issued':
            rid = next((prefix + notice.get('cites', '').split('@v')[0] for prefix in ('refund:', 'chargeback:')
                        if current(native, prefix + notice.get('cites', '').split('@v')[0]) is not None), None)
            row = current(native, rid) if rid else None
            if row is None or rid in used:
                continue
            f = row['fields']
            owners = [value for value in (f.get('allocated_to'), native['allocations'].get(rid)) if value is not None]
            bound = f.get('settled') is True and f.get('claim') == duty['case_id'] and f.get('claimant') == claim['claimant'] and f.get('order') == claim['order'] and f.get('currency') == order['currency']
            bound &= all(owner in ledger(native) and ledger(native)[owner]['case_id'] == duty['case_id'] for owner in owners)
            if bound:
                total += min(amount, f['amount']); used.add(rid)
        elif notice.get('template') == 'refund_denied':
            rid = 'return:' + notice.get('basis', '').split('@v')[0]
            row = current(native, rid)
            if row and row['evidential'] and rid not in used and row['fields'].get('order') == claim['order'] and row['fields'].get('received') is False:
                contribution = min(amount, max(0, budget - denied))
                total += contribution; denied += contribution; used.add(rid)
    return total >= claim['amount']


def p2(before, after):
    a, b = before['native'], after['native']
    old, new = ledger(a), ledger(b)
    for did, duty in old.items():
        require('P2', did in new, 'duty disappeared')
        now = new[did]
        if duty['resolution'] == 'unresolved' and now['resolution'] != 'unresolved':
            require('P2', bool(now['resolution_basis']), 'resolution has no bound evidence')
            for ref in now['resolution_basis']:
                require('P2', any(v['version'] == ref['record_version'] for v in b['records'].get(ref['record_id'], [])), 'resolution evidence version does not exist')
        if duty['owner'] != now['owner'] and now['owner'] is not None:
            require('P2', any(e['type'].startswith('accepted_by_') and e['at'] == b['step'] for e in now['history'][len(duty['history']):]), 'ownership changed without accepted transfer')
    for cid, closed in b['cases'].items():
        require('P2', not closed or not any(d['case_id'] == cid and d['resolution'] == 'unresolved' for d in new.values()), 'case closed with an unresolved duty')
    for duty in new.values():
        if duty['content']['kind'] == 'resolve' and duty['resolution'] == 'discharged':
            require('P2', resolve_coverage(b, duty), 'whole claim was not covered once by bound notice evidence')
        if duty['content']['kind'] == 'refund' and duty['resolution'] == 'discharged':
            claim = current(b, 'claim:' + duty['case_id'])['fields']
            order = current(b, 'sale:' + claim['order'])['fields']
            matches = []
            for ref in duty['resolution_basis']:
                row = current(b, ref['record_id'])
                if row['kind'] not in ('refund', 'chargeback'):
                    continue
                f = row['fields']
                matches.append(f.get('settled') is True and f.get('claim') == duty['case_id'] and
                    f.get('claimant') == duty['claimant'] and f.get('order') == claim['order'] and
                    f.get('currency') == order['currency'] and f.get('amount', 0) >= duty['content']['amount'])
            require('P2', any(matches), 'refund duty discharged without correctly bound settlement')


def p3(before, after):
    a, b = before['native'], after['native']
    relevant = any(stable(a[k]) != stable(b[k]) for k in ('records', 'duty_records', 'reports', 'notices', 'allocations', 'cases'))
    require('P3', not relevant or b['revision'] > a['revision'], 'relevant state changed without revision')
    for tid, row in a['tokens'].items():
        if row['status'] != 'live':
            continue
        stale = b['revision'] != row['certificate']['state_revision'] or b['step'] >= row['certificate']['expires_at_step']
        require('P3', not stale or b['tokens'][tid]['status'] != 'live', 'an old live token survived a relevant change or expiry')


def p4(before, after, proposal, result):
    if proposal is None or not result.get('evaluated', True):
        return
    checks = result.get('checks', [])
    prohibited = any(c['stage'] == 'prohibition' and c['result'] == 'violated' for c in checks)
    require('P4', not prohibited or result['disposition'] == 'PROHIBIT', 'a later stage lifted a failed prohibition')
    args = proposal['args']
    ret = current(before['native'], 'return:RET1')
    if ret and ret['fields'].get('received') is False and 'return received' in args.get('asserts', []):
        require('P4', result['disposition'] == 'PROHIBIT', 'known false return assertion was not prohibited')
    if result.get('disposition') == 'PROHIBIT':
        require('P4', set(before['native']['tokens']) == set(after['native']['tokens']), 'prohibition issued an executable token')


def p5(before, after, proposal, result):
    native = after['native']
    prior_duties, duties = ledger(before['native']), ledger(native)
    for did, old in prior_duties.items():
        if old['content']['kind'] not in ('report', 'unowned_report') or old['resolution'] != 'unresolved':
            continue
        now = duties.get(did)
        require('P5', now is not None, 'unacknowledged report disappeared')
        if now['resolution'] == 'discharged':
            require('P5', bool(now['resolution_basis']), 'report discharged without acknowledgment evidence')
        if now['content']['version'] > old['content']['version']:
            require('P5', now['deadline_step'] == old['deadline_step'] and
                    now['route_deadline_step'] == old['route_deadline_step'] and
                    now['content']['recipient'] == old['content']['recipient'], 'a repeat reset a deadline or changed its recipient')
        due = old['route_deadline_step']
        if old['content']['kind'] == 'report' and now['resolution'] == 'unresolved' and due is not None and before['step'] < due <= after['step']:
            # Generated issuer is L; W0 routes through C, F, then explicit exhaustion.
            tried = old['content']['routes_tried']
            recipient = next((p for p in ('party:C', 'party:F') if p not in tried), None)
            require('P5', now['content']['recipient'] == recipient, 'routing deadline failed to advance to the next eligible W0 role')
            require('P5', now['route_deadline_step'] == (after['step'] + 5 if recipient else None), 'routing deadline convention is wrong')
    for did, duty in duties.items():
        if duty['content']['kind'] != 'report':
            continue
        old = prior_duties.get(did)
        changed = old is None or old['content']['recipient'] != duty['content']['recipient'] or old['content']['version'] != duty['content']['version']
        if changed and duty['content']['recipient'] is not None:
            sent = [e['native_event']['payload'] for e in after['log'][len(before['log']):] if e['type'] == 'report_sent']
            require('P5', any(p['duty'] == did and p['envelope']['authenticated_sender'] == 'gateway_reporting' and
                    p['envelope']['recipient'] == duty['content']['recipient'] and
                    p['envelope']['content']['report_id'] == duty['content']['report_id'] and
                    p['envelope']['content']['version'] == duty['content']['version'] for p in sent), 'report state changed without an authenticated dispatch in the actual log')
    if proposal is None:
        return
    ret = current(before['native'], 'return:RET1')
    if not ret or ret['fields'].get('received') is not False or 'return received' not in proposal['args'].get('asserts', []):
        return
    for rid, h in native['records'].items():
        order = h[-1]
        if order['kind'] != 'stored_order':
            continue
        f = order['fields']
        if not any(e['tool'] == proposal['tool'] and e['arguments'].get('claim') == proposal['args'].get('claim') and
                   'return received' in e.get('asserts', []) for e in f['requested_effects']):
            continue
        issuer = f['envelope']['authenticated_sender']
        matters = [d for d in duties.values() if d['content']['kind'] == 'report' and
                   d['content']['issuer'] == issuer and rid in d['content']['incidents']]
        require('P5', bool(matters), 'prohibited ordered act has no report duty')
        for d in matters:
            require('P5', d['content']['recipient'] != issuer, 'report sent to its issuer')
            require('P5', bool(native['reports'][d['content']['report_id']]), 'report duty has no report evidence')


def audit_transition(observer, before, after, result, actor=None, token=None, proposal=None, execution=False):
    p1(before, after, actor, token, execution)
    p2(before, after)
    p3(before, after)
    p4(before, after, proposal, result)
    p5(before, after, proposal, result)
    rows = observer.audit('generated', before, after, result,
                          agent=proposal is not None or execution,
                          execute={'actor': actor, 'token': token} if execution else None)
    bad = [r for r in rows if r['status'] != 'pass']
    require('STATE_AUDIT', not bad, str(bad[:1]))
    return len(rows)


def p6(first_state, second_state):
    exports = []
    for state in (first_state, second_state):
        c = core._context(state)
        checkpoint = c.log.seal()
        blob = c.log.jsonl()
        verify_jsonl(blob, core.KEY, checkpoint)
        exports.append(blob)
    require('P6', exports[0] == exports[1], 'same world and script produce different authenticated JSONL')
