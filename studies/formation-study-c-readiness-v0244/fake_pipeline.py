"""Free2160-native pipeline, stopped reply adoption and frozen final analysis."""
import importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('usage_fixture',ROOT/'tests/test_formation_study_c_execution_v0244.py');t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
f=t.UsageExecutionTests('test_adopts_once_full540_native_audit_report_and_Luna72');f.full_prior_pipeline=True;f.setUp();c=t.c;report=t.report
try:
    gemma=f.launch();assert gemma['primary_closed']==540
    with f.patched():report.model_report(f.root,'gemma-4-31b-it');c.snapshot_boundary(f.root,'gemma-4-31b-it',True)
    luna=f.launch('gpt-6-luna',after=False,adopt=False)
    with f.patched():report.model_report(f.root,'gpt-6-luna');c.snapshot_boundary(f.root,'gpt-6-luna',True)
    luna=f.launch('gpt-6-luna',after=True,adopt=False)
    with f.patched():report.model_report(f.root,'gpt-6-luna');c.snapshot_boundary(f.root,'gpt-6-luna',True)
    # Explicit scripted B placeholders; no model calls or inference.
    from formation.study_b_evaluation_v0235 import output_name
    b=c.read(ROOT/'studies/formation-study-b-freeze-v0235.json');c.atomic(f.root/'studies/formation-study-b-freeze-v0235.json',b);rows=[]
    for name in b['case_files']:
        p=f.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes());case=c.read(p)
        rows.extend(dict(case_id=case['id'],repeat=i,label='primary',score=dict(substance_outcome='correct',mechanical_outcome=None,executed_violations={'servile':0})) for i in range(1,11))
    out=f.root/output_name('gemini-3.1-flash-lite');out.mkdir(parents=True,exist_ok=True);c.atomic(out/'progress-summary.json',dict(records=rows))
    with f.patched():final=report.final_report(f.root)
    for path,digest in f.before350.items():assert c.sha(Path(path))==digest
    assert (f.out/(t.u.CELL+'-checkpoint.json')).read_bytes()==f.old351
    result=dict(fake_fixture_only=True,HTTP_calls=0,scheduled=2160,judgments=2160,models=dict(f.prior_totals,**{'gemma-4-31b-it':gemma['primary_closed'],'gpt-6-luna':luna['primary_closed']}),Gemma_usage_accounting=gemma['audit']['usage_accounting'],original350_and351_archive_unchanged=True,all_native_source_replay_identity_usage_reserve_ledger_quota_prefix_reports='passed',frozen_C1_C4_primary_and_Luna_sensitivity='produced',Gemini_B_comparison='produced',pilot_failed_test_unpooled=True)
    c.atomic(ROOT/'studies/formation-study-c-readiness-v0244/fake-pipeline-result.json',result);print(json.dumps(result),flush=True)
finally:f.doCleanups()
