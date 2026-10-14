"""Offline 2160 planned C reporting fixture, including missing guards and rerun.

Only synthetic temporary outputs and mocked native calls; never paid model data.
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('native_readiness_helpers',ROOT/'tests/test_formation_study_c_v0242.py')
tests=importlib.util.module_from_spec(spec);spec.loader.exec_module(tests)
case=tests.NativeRerunTests('test_only_Gemini_schema_changes_all_other_bodies_identical')
case.setUp()
try:
    # Two canonical blocked bodies recur over five repeats: ten missing cells.
    counts={};guard_budget=[2];send=case.send
    def with_guards(client,body,received):
        if client.model=='gemma-4-31b-it' and client.url.endswith(':countTokens') and guard_budget[0]:
            guard_budget[0]-=1;received();return {'totalTokens':11777}
        return send(client,body,received)
    case.send=with_guards
    for model in tests.c.MODELS:
        if model=='gemini-3.1-flash-lite':case.compatibility();case.seal_compatibility()
        first=case.launch(model)
        with case.patched():tests.report.model_report(case.root,model);tests.c.snapshot_boundary(case.root,model,reported=True)
        last=case.launch(model,after=True)
        with case.patched():tests.report.model_report(case.root,model);tests.c.snapshot_boundary(case.root,model,reported=True)
        counts[model]={'planned':540,'closed':last['primary_closed'],'judgments':last['primary_completed'],'missing':len(last['guard_stops'])}
    with case.patched():final=tests.report.final_report(case.root)
    assert sum(v['closed'] for v in counts.values())==2160
    assert sum(v['judgments'] for v in counts.values())==2150
    assert sum(v['missing'] for v in counts.values())==10
    assert case.compat_sends==1
    assert final['costs']['retained_failed_Gemini_and_compatibility_dollars']>.1971865
    assert final['costs']['native_format_disclosure']['failed_original_unpooled']
    result={'fake_fixture_only':True,'model_calls':0,'compatibility_HTTP_calls':0,'planned':2160,'judgments':2150,'missing':10,'models':counts,'primary_verdicts':{k:v.get('verdict') if k!='C3' else {s:x['verdict'] for s,x in v.items()} for k,v in final['primary_verdicts'].items() if k in ['C1','C2','C3','C4']},'all_native_source_ledger_prefix_replay_report_boundaries':'passed','failed_original_and_compatibility_unpooled':True}
    (ROOT/'studies/formation-study-c-readiness-v0242/fake-pipeline-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
finally:case.doCleanups()
