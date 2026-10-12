"""Offline parser equivalence and descriptive review; never rescore H55 history."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from formation.study_b_v0227 import replay as original_replay
from formation.study_b_replay_v0234 import replay
from formation.study_b_parser_v0234 import parse_action
from formation.study_b_pilot_v0231 import read,sha


def verify():
    pilots=[('results/2026-10-12 v0.22.8 luna-none r1 study-b pilot','scenarios/formation/study-b-draft-v0228'),('results/2026-10-12 v0.23.0 luna-none r1 study-b corrected pilot','scenarios/formation/study-b-draft-v0230')]
    matches={};protected={}
    for output,case_dir in pilots:
        paths=list((ROOT/output).rglob('*'));protected.update({str(p.relative_to(ROOT)):sha(p) for p in paths if p.is_file()})
        rows=read(ROOT/output/'progress-summary.json')['records']
        for row in rows:
            case=read(ROOT/case_dir/(row['case_id']+'.json'))
            old=original_replay(case,row['packets']);new=replay(case,row['packets'])
            if old!=new or old['score']!=row['score']:raise ValueError('Luna pilot replay differs: '+row['case_id'])
        matches[output]=len(rows)
    fixtures={}
    for v in ('0227','0228','0230'):
        dotted={'0227':'0.22.7','0228':'0.22.8','0230':'0.23.0'}[v]
        choices=[x for x in (ROOT/'results').glob('*study-b*') if dotted in x.name and (x/'dry-run.json').exists()]
        if len(choices)!=1:raise ValueError('fixture source missing/ambiguous for '+v)
        data=read(choices[0]/'dry-run.json');rows=data['results'];cases={read(p)['id']:read(p) for p in (ROOT/('scenarios/formation/study-b-draft-v'+v)).glob('*.json')}
        import importlib
        module=importlib.import_module('scripts.formation_study_b_gate5a_v'+('0227' if v=='0227' else '0228'))
        ordered=[cases[c['id']] for c in module.build_cases()]
        old=module.dry_run(ordered)
        original=module.replay
        try:
            module.replay=replay
            new=module.dry_run(ordered)
        finally:module.replay=original
        if old!=new:raise ValueError('scripted fixture replay differs for '+v)
        keyed=lambda rs:{(x['case_id'],x['fixture']):x['result'] for x in rs}
        if keyed(old)!=keyed(rows):raise ValueError('scripted results differ from saved evidence for '+v)
        fixtures[dotted]=len(old)
    output=ROOT/'results/2026-10-12 v0.23.3 haiku55-none r10 study-b evaluation'
    hashes={str(p.relative_to(ROOT)):sha(p) for p in output.rglob('*') if p.is_file()};protected.update(hashes)
    malformed=[row for row in read(output/'progress-summary.json')['records'] if row['score']['mechanical_outcome']=='malformed_reply']
    accepted=[];rejected=[]
    # Parse the terminal raw string only. Do not replay, execute or rescore the
    # original H55 episode; an accepted action's later episode outcome is unknown.
    for row in malformed:
        raw=row['packets'][-1]['raw']
        try:parse_action(raw);accepted.append(row['case_id'])
        except ValueError:rejected.append(row['case_id'])
    if len(malformed)!=42 or len(accepted)!=28 or len(rejected)!=14:raise ValueError('owner descriptive counts differ; review before calls')
    for name,digest in protected.items():
        if sha(ROOT/name)!=digest:raise ValueError('historical source changed: '+name)
    return {'model_calls':0,'Luna_pilot_full_replay_identical':matches,'scripted_fixture_full_replay_identical':fixtures,'original_H55_labels_rescored':False,'H55_malformed_episodes':42,'H55_terminal_raw_valid_action_with_surrounding_text':28,'H55_no_accepted_terminal_action':14,'excluded_breakdown':{'placeholder_only':11,'XML_style_parameters':2,'multiple_actions':1},'accepted_case_ids_descriptive_only':accepted,'rejected_case_ids_descriptive_only':rejected,'historical_files_unchanged':len(protected),'historical_sha256':protected}
if __name__=='__main__':
    r=verify();print(json.dumps({k:v for k,v in r.items() if k!='historical_sha256'},indent=2))
