"""Free full2160 pipeline: old sealed-model fixtures, new Gemma/Luna adapter.
No HTTP/credential files; B comparison rows are explicitly scripted placeholders.
"""
import copy,importlib.util,json,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('counted_pipeline_helpers',ROOT/'tests/test_formation_study_c_execution_v0243.py');t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
c=t.c;report=t.report;fixture=t.CountedExecutionTests('test_pending_CI_no_archive_key_or_request');fixture.setUp();case=fixture.fixture
try:
    # Replace only synthetic dummy prior completions with native fixture batches.
    import shutil
    effective=c.runtime_freeze(case.root,case.f,case.am)
    for model in c.MODELS[:2]:shutil.rmtree(case.root/effective['outputs'][model])
    totals={}
    for model in c.MODELS[:2]:
        if model=='gemini-3.1-flash-lite':case.compatibility();case.seal_compatibility()
        case.launch(model)
        with case.patched():t.helpers.report.model_report(case.root,model);t.helpers.c.snapshot_boundary(case.root,model,reported=True)
        last=case.launch(model,after=True)
        with case.patched():t.helpers.report.model_report(case.root,model);t.helpers.c.snapshot_boundary(case.root,model,reported=True)
        totals[model]=dict(planned=540,closed=last['primary_closed'],judgments=last['primary_completed'],missing=0)
        print('closed scripted fixture',model,totals[model],flush=True)
    # Rebuild ONLY the temporary zero-request stop after the preceding synthetic
    # Gemini ledger has settled, matching the real launch order/provider baseline.
    shutil.rmtree(fixture.out)
    fixture.make_zero_request_stop();fixture.bind_count_remedy()
    send=case.send;guards=[2]
    def with_guards(client,body,received):
        if client.model=='gemma-4-31b-it' and client.url.endswith(':countTokens') and guards[0]:
            guards[0]-=1;received();return {'totalTokens':11777}
        return send(client,body,received)
    case.send=with_guards
    for model in c.MODELS[2:]:
        first=fixture.launch(model=model)
        with fixture.patched():report.model_report(case.root,model);c.snapshot_boundary(case.root,model,reported=True)
        last=fixture.launch(after=True,model=model)
        with fixture.patched():report.model_report(case.root,model);c.snapshot_boundary(case.root,model,reported=True)
        totals[model]=dict(planned=540,closed=last['primary_closed'],judgments=last['primary_completed'],missing=len(last['guard_stops']))
        print('closed scripted fixture',model,totals[model],flush=True)
    # B descriptions need no new inference. Explicitly scripted rows only.
    from formation.study_b_evaluation_v0235 import output_name
    b=c.read(ROOT/'studies/formation-study-b-freeze-v0235.json');c.atomic(case.root/'studies/formation-study-b-freeze-v0235.json',b);rows=[]
    for name in b['case_files']:
        p=case.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes());data=c.read(p)
        rows.extend(dict(case_id=data['id'],repeat=i,label='primary',score=dict(substance_outcome='correct',mechanical_outcome=None,executed_violations={'servile':0})) for i in range(1,11))
    bo=case.root/output_name('gemini-3.1-flash-lite');bo.mkdir(parents=True,exist_ok=True);c.atomic(bo/'progress-summary.json',dict(records=rows))
    with fixture.patched():final=report.final_report(case.root)
    assert sum(x['closed'] for x in totals.values())==2160
    assert sum(x['missing'] for x in totals.values())==10
    assert sum(x['judgments'] for x in totals.values())==2150
    out=case.root/effective['outputs']['gemma-4-31b-it'];c.verify_completed(out)
    extra=c.read(case.root/report.FINAL_OUTPUT/'Gemini-servility-B-C-descriptive.json');assert len(extra['by_history_length_theme_rung'])==54
    result=dict(fake_fixture_only=True,HTTP_calls=0,model_calls=0,planned=2160,judgments=2150,missing=10,models=totals,source_native_replay_first_reply_identity_usage_reserve_ledger_quota_metadata_prefix_reports='passed',first_unsent_Gemma_archive_and_original_job_counter_protection='passed',Gemini_postresults_descriptive_comparison='passed',frozen_primary_and_Luna_verdicts='produced separately',pilot_failed_test_unpooled=True)
    c.atomic(ROOT/'studies/formation-study-c-readiness-v0243/fake-pipeline-result.json',result);print(json.dumps(result))
finally:fixture.doCleanups()
