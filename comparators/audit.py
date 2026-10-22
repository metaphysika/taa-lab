"""Independent observations of the POEC run, not its policy callbacks."""
from copy import deepcopy
import hashlib
import json


def audit(episode, contract):
    rows = []
    def check(name, condition):
        rows.append({'assertion': name, 'status': 'pass' if condition else 'discrepancy'})
    receipts = []
    for index, call in enumerate(episode['observations']):
        if call['kind'] != 'execution':
            continue
        before, after, result = call['before'], call['after'], call['result']
        if result['dispatch'] != 'committed':
            check(f'{index}.refused_or_rolled_back_world_unchanged', before == after)
            continue
        receipt = result['receipt'];receipts.append(receipt)
        cert, effect = receipt['certificate'], receipt['effect']
        check(f'{index}.acting_party', cert['actor'] == call['input']['actor'])
        check(f'{index}.contract', cert['contract'] == contract['id'])
        for rid, history in before['records'].items():
            check(f'{index}.{rid}.history_retained', rid in after['records'] and after['records'][rid][:len(history)] == history)
        writes = [(rid, v) for rid, history in after['records'].items() for v in history[len(before['records'].get(rid, [])):]]
        if cert['tool'] == 'issue_refund':
            check(f'{index}.one_actual_refund_write', len(writes) == 1 and writes[0][1]['kind'] == 'refund')
            if len(writes) == 1:
                rid, record = writes[0]
                check(f'{index}.receipt_matches_actual_refund', dict(record['fields'], record=rid, kind=record['kind']) == effect)
                check(f'{index}.benefit_route_and_amount', all(record['fields'][k] == cert['arguments'][k] for k in ('claim','amount','to')))
            check(f'{index}.other_channels_unchanged', before['notices'] == after['notices'] and before['cases'] == after['cases'])
        elif cert['tool'] == 'message_party':
            delta = after['notices'][len(before['notices']):]
            check(f'{index}.one_actual_notice', len(delta) == 1 and dict(delta[0], kind='notice') == effect)
            check(f'{index}.other_channels_unchanged', before['records'] == after['records'] and before['cases'] == after['cases'])
        elif cert['tool'] == 'close_case':
            check(f'{index}.actual_case_closed', after['cases'].get(cert['arguments']['case']) is True)
            check(f'{index}.other_channels_unchanged', before['records'] == after['records'] and before['notices'] == after['notices'])
        else:
            check(f'{index}.known_effect_profile', False)
        check(f'{index}.postconditions', all(k in effect and effect[k] == value for k,value in contract['VERIFY'][cert['obligation']].items()))
        slots = {p['slot'] for p in cert['proofs']}
        check(f'{index}.all_present_authority_slots_bound', set(cert['arguments']) & set(contract['BIND'][cert['tool']]) <= slots)
        check(f'{index}.proof_values_match_arguments', all(p['value'] == cert['arguments'][p['slot']] for p in cert['proofs']))
    check('all_successes_have_retained_receipts', receipts == episode['receipts'])
    ids = [r['certificate']['id'] for r in receipts]
    check('single_use', len(ids) == len(set(ids)))
    check('no_waivers', all(s in ('PENDING','ACTIVE','VERIFIED') for s in episode['obligations'].values()))
    missing = [k for k,n in contract['MUST'].items() if n['hard'] and episode['obligations'][k] != 'VERIFIED']
    check('final_answer_gate', episode['success_claim_gate']['accepted'] == (not missing) and
          episode['success_claim_gate']['unverified_hard'] == missing)
    for node, status in episode['obligations'].items():
        if status == 'VERIFIED' and contract['MUST'][node]['kind'] == 'effect':
            matches = [r for r in receipts if r['obligation'] == node]
            check(node + '.verified_effect_has_exactly_one_receipt', len(matches) == 1)
        if status == 'VERIFIED' and contract['MUST'][node]['kind'] == 'evidence':
            matches = [h for h in episode['history'] if h['type'] == 'evidence_admitted' and h['obligation'] == node]
            spec = contract['MUST'][node]
            check(node + '.verified_evidence_has_admission', len(matches) == 1 and matches[0]['authenticated_source'] == spec['source'] and
                  matches[0]['query'] == spec['query'] and matches[0]['record']['id'] == spec['record'])
    remaining = {t:v['budget'] for t,v in contract['MAY'].items()}
    issued = {}
    for index, event in enumerate(episode['history']):
        if event['type'] == 'certificate_issued':
            cert = event['certificate'];issued[cert['id']] = cert
            remaining[cert['tool']] -= 1
            check(f'history.{index}.budget_reserved', min(remaining.values()) >= 0 and remaining == cert['budget_state'])
        elif event['type'] == 'dispatch_rolled_back':
            remaining[issued[event['certificate']]['tool']] += 1
    return rows
