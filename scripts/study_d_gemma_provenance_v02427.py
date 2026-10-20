"""CPU-only additive provenance repair. Original v02426 evidence is never written."""
import copy
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_union(provenance):
    if len(provenance)!=132 or len({(u['case_id'],u['repeat']) for u in provenance})!=132:
        raise ValueError('union roster differs')
    missing=[u for u in provenance if u.get('missing')]
    if len(missing)!=2 or any(not u.get('no_resend') for u in missing):
        raise ValueError('two no-resend missing units required')
    for u in provenance:
        if u.get('missing'):continue
        if (u.get('status')!='completed' or not u.get('path')
            or len(u.get('output_sha256',''))!=64 or not u.get('issued_request_ids')
            or len(set(u['issued_request_ids']))!=len(u['issued_request_ids'])):
            raise ValueError('non-missing unit lacks complete provenance')
    return dict(status='PASS',completed=130,missing=2)


def repair_composite(root,original,binding):
    """Rebuild ALL completed paths/IDs from native starts/returns and output bytes."""
    root=Path(root);result=copy.deepcopy(original)
    if original['status']!='COMPLETE' or original['arms']['neutral']['transfer_episodes']!=130:
        raise ValueError('source composite not closed')
    events={}
    for producer,folder in [('v02425',root/'prior-pair/pair/neutral'),
                            ('v02426',root/'neutral-completion/neutral')]:
        starts={};returns={}
        for line in (folder/'events.jsonl').read_text().splitlines():
            e=json.loads(line);key=e.get('request_id')
            if e['event']=='generation_start':
                if key in starts:raise ValueError('duplicate generation start')
                starts[key]=e
            elif e['event']=='generation_return':
                if key not in starts or key in returns:raise ValueError('unissued or duplicate return')
                returns[key]=e
        events[producer]=(starts,returns)
    provenance=[]
    for unit in binding['units']:
        u=copy.deepcopy(unit)
        if unit['status']=='interrupted_missing':
            u.update(producer='v02425',missing=True,no_resend=True);provenance.append(u);continue
        producer='v02425' if unit['status']=='completed' else 'v02426'
        rel=('prior-pair/'+unit['path'] if producer=='v02425' else
             'neutral-completion/neutral/transfer/'+unit['case_id']+'-r'+str(unit['repeat'])+'.json')
        path=root/rel;row=json.loads(path.read_text())
        if (row['case_id'],row['repeat'])!=(unit['case_id'],unit['repeat']):raise ValueError('episode identity differs')
        starts,returns=events[producer]
        prefix='neutral/'+unit['case_id']+'/r'+str(unit['repeat'])+'/t'
        ids=sorted((k for k in starts if k.startswith(prefix)),key=lambda k:int(k.rsplit('/t',1)[1]))
        expected=[prefix+str(t) for t in range(1,len(row['packets'])+1)]
        if ids!=expected or not ids:raise ValueError('episode request roster differs')
        for key,packet in zip(ids,row['packets']):
            if key not in returns or returns[key]['raw_text']!=packet['raw']:
                raise ValueError('first native text differs from episode')
        digest=sha(path)
        if producer=='v02425' and (digest!=unit['sha256'] or ids!=unit['issued_request_ids']):
            raise ValueError('old completed provenance changed')
        u.update(status='completed',producer=producer,path=rel,sha256=digest,
                 output_sha256=digest,issued_request_ids=ids,missing=False)
        provenance.append(u)
    validate_union(provenance)
    # No scoring, labels, bounds, seeds or outcomes change.
    result['arms']['neutral']['episode_provenance']=provenance
    result['provenance_repair']=dict(version='v02427',cpu_only=True,
        source_record='source-composite-v02426.json',source_sha256=sha(root/'source-composite-v02426.json'),
        original_evidence_modified=False,scoring_changed=False,
        disclosure='Rebuilt completed paths, output hashes and issued IDs from transfer files and native event journals; original v02426 record preserved.')
    return result
