"""SQL-native Q14 admissions and interval union; no other arm's code is used."""
from .kernel import copy, encode
from .policy import Facts, latest


def notice_span(args, limit):
    value=args.get('portion',{'from':0,'to':args.get('amount')})
    if type(args.get('amount')) is not int or args['amount']<=0 or type(limit) is not int or not isinstance(value,dict) or set(value)!={'from','to'}:
        return None
    lo,hi=value['from'],value['to']
    if type(lo) is int and type(hi) is int and 0<=lo<hi<=limit and hi-lo==args['amount']:
        return copy(value)
    return None


def compute(store,policy,duty):
    snapshot=store.snapshot();facts=Facts(snapshot);claim=facts.get(duty['claim'])
    if claim is None:return None
    support=policy.support(snapshot,duty['claim']);supported=support.get('amount',0)
    supported=0 if supported is None else supported
    notices=latest(snapshot,'notices');receipts=list(latest(snapshot,'receipts').items())
    if store._pending_receipt is not None:receipts.append(('@pending',store._pending_receipt))
    # Match actual notice rows to the exact written payload in a receipt plan.
    admissions=copy(duty.get('notice_admissions',[]));keys={a['notice'] for a in admissions}
    for receipt_id,receipt in receipts:
        for effect in receipt['effects']:
            nid=effect['id']
            if effect['relation']!='notices' or nid in keys or nid not in notices or encode(effect['payload'])!=encode(notices[nid]):continue
            n=notices[nid]
            if n.get('claim')!=duty['claim'] or n.get('to')!=duty['claimant']:continue
            issued=n.get('template')=='refund_issued'
            if not issued and n.get('template')!='refund_denied':continue
            rid=str(n.get('cites' if issued else 'basis','')).split('@v')[0];basis=facts.get(rid)
            if basis is None:continue
            limit=basis.get('amount') if issued else max(0,claim['amount']-supported)
            span=notice_span(n,limit)
            valid=(policy.settlement_valid(snapshot,rid,duty['claim'],span['to']) if issued and span else
                   policy.denial_valid(snapshot,n['basis'],duty['claim'],span['to']) if span else False)
            if valid:
                # Actual handle id is stable between the private projection and
                # the final SQL receipt row; no projected fact is published alone.
                admissions.append(dict(notice=nid,receipt=receipt['handle'],actor=receipt['actor'],args=copy(n),
                    record=rid,version=len(snapshot['records'][rid]),original=copy(basis),portion=span,budget=limit))
                keys.add(nid)
    sequence=[]
    for event in store.events():
        if event['kind']!='version_written':continue
        e=event['payload']
        if e['relation']=='records' and e['payload']['kind'] in ('refund','chargeback') and e['id'] not in sequence:sequence.append(e['id'])
    layout=[];at=0
    for rid in sequence:
        basis=facts.get(rid)
        if basis is None:continue
        value=basis.get('amount')
        if type(value) is int and value>=0 and policy.settlement_valid(snapshot,rid,duty['claim'],value):
            layout.append(dict(record=rid,version=len(snapshot['records'][rid]),offset=at,amount=value));at+=value
    ranges=[]
    for a in admissions:
        basis=facts.get(a['record'])
        if basis is None:continue
        if a['args']['template']=='refund_issued':
            payment=next((p for p in layout if p['record']==a['record']),None)
            if payment is None:continue
            base=payment['offset']
        else:
            if facts.records[a['record']]['kind'] not in ('carrier_record','return_receipt','resolution') or basis.get('order',claim['order'])!=claim['order']:continue
            base=supported
        ranges.append((max(0,base+a['portion']['from']),min(claim['amount'],base+a['portion']['to'])))
    combined=[]
    for lo,hi in sorted(ranges):
        if hi<=lo:continue
        if combined and lo<=combined[-1]['to']:combined[-1]['to']=max(hi,combined[-1]['to'])
        else:combined.append({'from':lo,'to':hi})
    refs={p['record'] for p in layout}|{a['record'] for a in admissions}|{duty['claim'],claim['order']}
    refs.update(rid for rid in sequence if (facts.get(rid) or {}).get('claim')==duty['claim'])
    for kind in ('carrier_record','return_receipt','resolution'):
        refs.update(rid for rid,f in facts.of(kind) if f.get('order')==claim['order'] or kind=='resolution' and f.get('about')==duty['claim'])
    refs={rid for rid in refs if rid in snapshot['records']}
    duty.update(notice_admissions=admissions,coverage_intervals=combined,
        coverage=sum(p['to']-p['from'] for p in combined),
        coverage_proof=dict(layout=layout,financial_order=[rid for rid in sequence if (facts.get(rid) or {}).get('claim')==duty['claim']],supported=supported,claim_amount=claim['amount'],versions={rid:len(snapshot['records'][rid]) for rid in sorted(refs)}))
    return [dict(record=rid,version=len(snapshot['records'][rid]),kind='coverage') for rid in sorted(refs)] if duty['coverage']==claim['amount'] else None
