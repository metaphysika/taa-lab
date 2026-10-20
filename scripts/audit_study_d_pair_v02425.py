"""Read-only, free first-reply and frozen replay audit of a returned pair folder."""
import argparse
import importlib.util
import json
import random
import re
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def audit(source,assets):
    from formation.study_d_base_gate_v0248 import evaluate_episode
    from formation import study_d_gemma_stages_v02425 as policy
    cases={q['case']['id']:q['case'] for q in json.loads((assets/'transfer-cases.json').read_text())}
    schedule=[(q['case']['id'],rep) for q in json.loads((assets/'transfer-cases.json').read_text()) for rep in range(1,5)]
    random.Random(247053).shuffle(schedule);indices={key:i for i,key in enumerate(schedule)}
    summary={}
    for arm in ('contrary','neutral'):
        ev=[json.loads(x) for x in (source/f'pair/{arm}/events.jsonl').read_text().splitlines()]
        starts={};returns={};interruptions={}
        for e in ev:
            key=e.get('request_id');kind=e['event']
            if kind=='generation_start':
                if key in starts:raise ValueError('duplicate request start')
                starts[key]=e
            if kind=='generation_return':
                if key not in starts or key in returns:raise ValueError('duplicate/unissued reply')
                returns[key]=e
            if kind=='generation_interrupted':interruptions[key]=e
        if set(starts)!=set(returns)|set(interruptions):raise ValueError('unclosed request evidence')
        rows=[]
        for path in sorted((source/f'pair/{arm}/transfer').glob('*.json')):
            row=json.loads(path.read_text());cid=row['case_id'];rep=row['repeat']
            def generate(system,history,turn):
                key=f'{arm}/{cid}/r{rep}/t{turn}';start=starts[key]
                if start['messages']!=[dict(role='system',content=system)]+history:
                    raise ValueError('native full-history/replay differs: '+key)
                seed=247053+indices[cid,rep]+turn-1
                if not re.search(r'\bseed='+str(seed)+r'[,)]',start['sampling_params']):raise ValueError('frozen request seed differs: '+key)
                raw=returns[key]['raw_text']
                if row['packets'][turn-1]['raw']!=raw:raise ValueError('not first native text')
                return raw
            replay=evaluate_episode(cases[cid],generate)
            for key,value in replay.items():
                if row[key]!=value:raise ValueError('frozen replay differs: '+str(path)+' '+key)
            rows.append(row)
        summary[arm]=dict(completed=len(rows),requests=len(starts),replies=len(returns),interrupted=len(interruptions),
                          bounds=policy.planned_bounds(rows,list(cases.values())))
    return dict(status='PASS',pair_closed=False,final_contrasts=False,arms=summary)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--assets',type=Path,required=True)
    a=p.parse_args();print(json.dumps(audit(a.source,a.assets),indent=2))
