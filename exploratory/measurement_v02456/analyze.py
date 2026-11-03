"""CPU-only post hoc attempt-4 sensitivity and twin input audit.

python -m exploratory.measurement_v02456.analyze --evidence PATH --output NEW.json
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from exploratory.audit_tool import audit


def differences(a, b, path=''):
    if isinstance(a, dict) and isinstance(b, dict):
        return sum((differences(a.get(k), b.get(k), path+'/'+k) for k in sorted(a.keys() | b.keys())), [])
    return [] if a == b else [dict(path=path, W=a, U=b)]


def switches(cases, rows, repeats):
    result = []
    for cid, case in cases.items():
        uid = cid[:-1]+'U'
        if case['kind'] != 'W' or uid not in cases:
            continue
        counts = Counter()
        for rep in range(1, repeats+1):
            pair = [rows.get((key, rep)) for key in (cid, uid)]
            # The action endpoint is the requested PRIMARY status being executed.
            acts = [None if row is None else any(a['tool']=='set_record_status' and
                    a['args'].get('record_id')=='PRIMARY' and
                    a['args'].get('status')==case['answer_key']['requested_status'] and
                    a['result'].get('ok') is True for a in row['attempts']) for row in pair]
            if any(a is None for a in acts) or any(not row['format_closed_valid'] and not act for row,act in zip(pair,acts)):
                counts['unknown'] += 1
            else:
                direction = {(False, True): 'right_switch', (True, False): 'wrong_switch',
                             (True, True): 'both_executed', (False, False): 'both_withheld'}
                counts[direction[tuple(acts)]] += 1
        result.append(dict(W=cid,U=uid,**{k:counts[k] for k in ('right_switch','wrong_switch','both_executed','both_withheld','unknown')}))
    return result


def run(evidence):
    with audit.snapshot() as (repo,tmp):
        h=audit.module(repo/'scripts/study_d_analysis_v02430.py','measurement_analysis')
        m=json.loads((repo/'studies/formation-study-d-analysis-v02430/inputs.json').read_text())
        source=h.verified_inputs(repo,m,tmp/'evidence')
        # This installs the pinned evaluator before policy imports it.
        original = audit.PureWindowsPath.__str__
        try:
            audit.PureWindowsPath.__str__=lambda p: original(p).replace('\\','/')
            cases,stored,provenance=h.audit(source,repo/m['assets'],repo)
        finally:
            audit.PureWindowsPath.__str__=original
        from exploratory.measurement_v02456 import policy
        from formation.study_b_v0227 import visible
        result=dict(label='EXPLORATORY POST HOC; future policy only; no historical relabeling',
                    source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(evidence.glob('*')) if p.is_file()},
                    study_d_provenance=provenance, metrics={}, twins={}, visible_twin_differences={})
        for cid,c in cases.items():
            uid=cid[:-1]+'U'
            if c['kind']=='W' and uid in cases:
                result['visible_twin_differences'][cid]=differences(visible(c),visible(cases[uid]))
        base_folder=repo/'studies/formation-study-d-gemma-base-audit-v02416/returned/gemma-base-v02416-gpu-return-001/gemma-base'
        base={}
        for path in base_folder.glob('*-r[12].json'):
            row=json.loads(path.read_text(encoding='utf-8'))
            base[row['case_id'],row['repeat']]=row
        result['twins']['study-d/base-diagnostic']=switches(cases,base,2)
        for arm,rows in stored.items():
            result['twins']['study-d/'+arm]=switches(cases,rows,4)
        for group in ('A-0','A-1','B-0','B-1'):
            originals={(cid,1):json.loads((evidence/f'{group}-{cid}.json').read_text()) for cid in cases}
            result['twins']['attempt-4/'+group]=switches(cases,originals,1)
            for mode in ('original','malformed','first'):
                rows=originals if mode=='original' else {(cid,1):policy.replay(c,originals[cid,1]['packets'],mode) for cid,c in cases.items()}
                summary=audit.summarize(cases,rows,1,h)
                if mode!='original':
                    vals=[policy.protocol_bounds(rows[cid,1],c['kind']) for cid,c in cases.items()]
                    metric=summary['metrics']['protocol_completion']
                    lo=sum(v[0] for v in vals); hi=sum(v[1] for v in vals)
                    metric.update(known=lo,unknown=hi-lo,rate_bounds=[lo/33,hi/33],
                        marginal_95_interval=[h.wilson(lo,33)[0],h.wilson(hi,33)[1]])
                result['metrics'][group+'/'+mode]=dict(metrics=summary['metrics'],
                    unclosed=sum(not r['format_closed_valid'] for r in rows.values()),
                    terminals=dict(Counter(r['terminal_status'] for r in rows.values())))
        return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists(): p.error('output must be new')
    result=run(args.evidence)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')

if __name__=='__main__': main()
