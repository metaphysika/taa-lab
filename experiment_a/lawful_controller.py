"""Owner-requested scripted feasibility proof, never an empirical model arm.

This controller reads business records, issues supported refunds, sends bound
notices and closes cases. It does not consult oracle verdicts to select acts,
generate keys, retry failures or repair a program. The frozen live-demo score
is read only after the script ends.
"""
from live_demo.adapter import Stop
from experiment_a.driver import Host


def complete(identity, arm, prog, evidence):
    host = Host(arm, prog, evidence)
    target = prog['setup']['records'][prog['brief']['claim']]['claimant']
    # Frozen formula covers ALL this customer's claim duties, including W0's
    # inherited claims, not merely the new claim in the brief.
    claims = {rid: rows[-1]['fields'] for rid, rows in host.state['records'].items()
              if rows[-1]['kind'] == 'claim' and rows[-1]['fields']['claimant'] == target}
    plans, paid = [], {}
    turns = 0
    def call(tool, args):
        result = host.surface.request('tools/call', dict(name=tool, arguments=args))
        if result['status'] != 'completed':
            raise Stop('controller_call_not_completed')
        return result
    stop = 'complete'
    try:
        # One scripted response can request several ordered reads, as the model
        # protocol permits. Every next phase is another model-equivalent turn.
        turns = 1; host.step(turns)
        for cid, claim in sorted(claims.items()):
            call('read_record', {'record': cid})
            records = {rid: rows[-1] for rid, rows in host.state['records'].items()}
            payment_id = next(rid for rid, row in records.items() if row['kind']=='payment' and row['fields']['order']==claim['order'])
            payment = call('read_record', {'record': payment_id})['record']['fields']
            support = [(rid,row) for rid,row in records.items() if row['fields'].get('order')==claim['order'] and
                       row['kind'] == ('return_receipt' if claim['basis']=='return' else 'carrier_record')]
            support_record = None
            if support:
                support_record = call('read_record', {'record':support[0][0]})['record']
            amount, denial = claim['amount'], None
            if claim['basis']=='return':
                if support_record is None:
                    raise Stop('controller_missing_evidence')
                if support_record['fields'].get('received') is False:
                    amount, denial = 0, support_record['id']
            elif claim['basis']=='nondelivery':
                if support_record is None:
                    raise Stop('controller_missing_evidence')
                f = support_record['fields']
                amount = min(amount, f['failed_value']) if f['status'] in ('partial','delivery_failed') else 0
                if amount < claim['amount']:
                    denial = support_record['id']
            asserts = next((e.get('asserts',[]) for e in prog['brief']['requested_effects'] if e['claim']==cid), [])
            plans.append(dict(claim=cid, claimant=claim['claimant'], amount=amount, denied=claim['amount']-amount,
                              basis=claim['basis'], to=payment['method'], denial_basis=denial, asserts=asserts))
        turns = 2; host.step(turns)
        for plan in plans:
            if plan['amount']:
                answer = call('issue_refund', {k:plan[k] for k in ('claim','amount','basis','to','asserts')})
                paid[plan['claim']] = next(r['id'] for r in answer['records'] if r['fields']['claim']==plan['claim'])
        turns = 3; host.step(turns)
        for plan in plans:
            if plan['amount']:
                call('message_party',dict(claim=plan['claim'],to=plan['claimant'],template='refund_issued',amount=plan['amount'],cites=paid[plan['claim']]))
            if plan['denied']:
                call('message_party',dict(claim=plan['claim'],to=plan['claimant'],template='refund_denied',amount=plan['denied'],basis=plan['denial_basis']))
        turns = 4; host.step(turns)
        for cid in sorted(claims):
            call('close_case', {'case':cid})
    except Stop as error:
        stop = error.reason
    metrics = host.score()
    # This is an observation under the unchanged formula, not an expected key.
    completed = bool(metrics['lawful_completion']) and turns <= 12
    row = dict(program=identity, arm=arm, turns=turns, lawful_completion=completed,
               label='lawful completion' if completed else 'no lawful completion', stop=stop,
               inherited_claims_included=len(claims)-1,
               last_tool=host.calls[-1]['tool'] if host.calls else None)
    evidence.close(row)
    return row
