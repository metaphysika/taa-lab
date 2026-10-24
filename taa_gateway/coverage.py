"""Q14 receipt-bound claim-line coverage, native implementation only.

Original admissions and recomputed layout are separate. This module imports
neither the reference relation, comparator oracle, nor SQL implementation.
"""
from taa_gateway.serialization import canonical, copy_json


def portion(arguments, budget):
    amount = arguments.get('amount')
    if type(amount) is not int or amount <= 0 or type(budget) is not int:
        return None
    value = arguments.get('portion', {'from': 0, 'to': amount})
    if not isinstance(value, dict) or set(value) != {'from', 'to'}:
        return None
    left, right = value['from'], value['to']
    if type(left) is not int or type(right) is not int or not 0 <= left < right <= budget or right-left != amount:
        return None
    return copy_json(value)


def union(intervals, maximum):
    merged = []
    for left, right in sorted((max(0,a),min(maximum,b)) for a,b in intervals):
        if left >= right:
            continue
        if merged and left <= merged[-1]['to']:
            merged[-1]['to'] = max(merged[-1]['to'], right)
        else:
            merged.append({'from':left,'to':right})
    return merged


def receipt_notices(state, pending=None):
    """Bind each physical notice at most once to actual receipt effects.

    `pending` is private executor input inside the copy-on-write transaction;
    neither its admissions nor effects can escape without the actual receipt.
    """
    available = {}
    for index, notice in enumerate(state['notices']):
        available.setdefault(canonical(notice), []).append(index)
    receipts = list(state['receipts']) + ([pending] if pending is not None else [])
    for receipt in receipts:
        if not all(k in receipt for k in ('id','acting_party','effect')) or not isinstance(receipt['effect'],dict) or 'notices' not in receipt['effect']:
            continue
        for ordinal, notice in enumerate(receipt['effect']['notices']):
            matches = available.get(canonical(notice), [])
            if matches:
                yield dict(key=receipt['id']+':'+str(ordinal), receipt=receipt['id'],
                           actor=receipt['acting_party'], notice_index=matches.pop(0), notice=notice)


def financial_sequence(engine, events):
    ordered = []
    writes = [e['payload'] for e in engine.log.events() if e['type']=='record_version']
    writes += [payload for _,kind,payload in events if kind=='record_version']
    for item in writes:
        record = item['record']
        if record['kind'] in ('refund','chargeback') and record['id'] not in ordered:
            ordered.append(record['id'])
    return ordered


def calculate(engine, state, events, duty, claim, pending=None):
    content = duty['content']
    admissions = copy_json(content.get('notice_admissions', []))
    admitted = {a['key'] for a in admissions}
    supported = engine.supported(state, dict(claim,id=duty['case_id']))
    for candidate in receipt_notices(state, pending):
        notice = candidate['notice']
        if candidate['key'] in admitted or notice.get('claim')!=duty['case_id'] or notice.get('to')!=claim['claimant']:
            continue
        template = notice.get('template')
        kinds = ('refund','chargeback') if template=='refund_issued' else ('return_receipt','carrier_record') if template=='refund_denied' else ()
        cited = notice.get('cites' if template=='refund_issued' else 'basis','').split('@v')[0]
        row = next((r for kind in kinds if (r:=engine.row(state,kind,cited)) is not None),None)
        if row is None:
            continue
        budget = row['fields'].get('amount') if template=='refund_issued' else max(0,claim['amount']-supported)
        span = portion(notice,budget)
        if span is None:
            continue
        binding = (engine.settlement(state,row['id'],row,duty['case_id'],claim,span['to']) if template=='refund_issued' else
                   engine.denial_proof(state,row['id'],row,claim,span['to']))
        if not binding:
            continue
        admission = copy_json(candidate)
        admission.update(record=engine.ref(row['id'],row),original_record=copy_json(row),
                         portion=span,budget=budget,supported_at_admission=supported)
        admissions.append(admission);admitted.add(candidate['key'])
    # Actual first writes, including corrections' retained original positions.
    order = financial_sequence(engine,events)
    layout,offset,refs,proofs = [],0,[],[]
    for rid in order:
        history = state['records'].get(rid,[])
        row = history[-1] if history else None
        if row is None or not row['evidential'] or row['kind'] not in ('refund','chargeback'):
            continue
        if row['fields'].get('claim') == duty['case_id']:
            refs.append(engine.ref(rid,row))
        amount = row['fields'].get('amount')
        if type(amount) is not int or amount < 0:
            continue
        binding = engine.settlement(state,rid,row,duty['case_id'],claim,amount)
        if not binding:
            continue
        layout.append(dict(record=engine.ref(rid,row),offset=offset,amount=amount))
        offset += amount;refs.append(engine.ref(rid,row));proofs.append(binding)
    offsets = {x['record']['record_id']:x['offset'] for x in layout}
    intervals=[]
    # Re-map original admitted spans. Do not revalidate their old denial budget
    # against a changed S: Q14 explicitly requires the S-rise/S-fall results.
    for admission in admissions:
        rid=admission['record']['record_id'];h=state['records'].get(rid,[])
        row=h[-1] if h else None
        if row is None:
            continue
        refs.append(engine.ref(rid,row))
        if not row['evidential']:
            continue
        notice=admission['notice'];span=admission['portion']
        if notice['template']=='refund_issued':
            if rid not in offsets:
                continue
            origin=offsets[rid]
        else:
            if row['kind'] not in ('return_receipt','carrier_record') or row['fields'].get('order')!=claim['order']:
                continue
            origin=supported
        intervals.append((origin+span['from'],origin+span['to']))
        refs.append(engine.ref(rid,row))
    # Bind every fact that fixes layout/S, as well as original cited records.
    for kind in ('claim','order','return_receipt','carrier_record','resolution'):
        for rid,row in engine.rows(state,kind):
            fields=row['fields']
            about = fields.get('answer',{}).get('about') if kind=='resolution' else None
            relevant = (kind=='claim' and rid==engine.prefix['claim']+duty['case_id'] or
                        kind=='order' and rid==engine.prefix['order']+claim['order'] or
                        kind in ('return_receipt','carrier_record') and fields.get('order')==claim['order'] or
                        kind=='resolution' and about==duty['case_id'])
            if relevant:refs.append(engine.ref(rid,row))
    refs=list({(r['record_id'],r['record_version']):r for r in refs}.values())
    spans=union(intervals,claim['amount']);covered=sum(s['to']-s['from'] for s in spans)
    content.update(notice_admissions=admissions,coverage=covered,coverage_intervals=spans,
        coverage_proof=dict(supported=supported,claim_amount=claim['amount'],layout=layout,
                            financial_order=[rid for rid in order if state['records'][rid][-1]['fields'].get('claim')==duty['case_id']],
                            records=refs,receipt_bindings=[dict(key=a['key'],receipt=a['receipt'],notice_index=a['notice_index']) for a in admissions]))
    return (refs,proofs,{},None) if covered==claim['amount'] else None
