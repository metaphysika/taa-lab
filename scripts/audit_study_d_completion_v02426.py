"""Read-only frozen replay audit, applied after the v02426 completion return."""
import json
import random
import re
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def audit(source,assets):
    from formation.study_d_base_gate_v0248 import evaluate_episode
    from formation import study_d_gemma_stages_v02427 as policy
    from scripts.study_d_gemma_provenance_v02427 import repair_composite,validate_union
    probes=json.loads((assets/'transfer-cases.json').read_text());cases={q['case']['id']:q['case'] for q in probes}
    schedule=[(q['case']['id'],r) for q in probes for r in range(1,5)];random.Random(247053).shuffle(schedule)
    index={k:i for i,k in enumerate(schedule)};rows=[];unfinished={k:0 for k in ('W','U','other')};completed={k:0 for k in ('W','U','other')}
    for folder in (source/'prior-pair/pair/neutral',source/'neutral-completion/neutral'):
        events=[json.loads(x) for x in (folder/'events.jsonl').read_text().splitlines()]
        starts={e['request_id']:e for e in events if e['event']=='generation_start'}
        returns={e['request_id']:e for e in events if e['event']=='generation_return'}
        for path in sorted((folder/'transfer').glob('*.json')):
            row=json.loads(path.read_text());cid=row['case_id'];rep=row['repeat']
            def generate(system,history,turn):
                key=f'neutral/{cid}/r{rep}/t{turn}';e=starts[key]
                if e['messages']!=[dict(role='system',content=system)]+history:raise ValueError('seeded full wire differs')
                if not re.search(r'\bseed='+str(247053+index[cid,rep]+turn-1)+r'[,)]',e['sampling_params']):raise ValueError('seed differs')
                raw=returns[key]['raw_text']
                if row['packets'][turn-1]['raw']!=raw:raise ValueError('first native output differs')
                return raw
            replay=evaluate_episode(cases[cid],generate)
            for k,v in replay.items():
                if row[k]!=v:raise ValueError('frozen replay differs: '+str(path)+' '+k)
            rows.append(row);kind=cases[cid]['kind'];kind=kind if kind in unfinished else 'other';completed[kind]+=1
            unfinished[kind]+=int(row['score']['substance_outcome']=='unfinished_work')
    if len(rows)!=130:raise ValueError('completed roster differs')
    return dict(status='PASS',completed=130,missing=2,planned=132,first_native_seeded_wire_frozen_replay='PASS',
        bounds=policy.planned_bounds(rows,list(cases.values())),unfinished_work=unfinished,completed_denominators=completed,
        contrasts_computed=False,scoring_unchanged=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--assets',type=Path,required=True)
    a=p.parse_args();print(json.dumps(audit(a.source,a.assets),indent=2))
