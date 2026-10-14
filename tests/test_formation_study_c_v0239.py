"""Free seeded fixtures and multi-provider C guards; no network/credential files."""
import copy
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch
from agents.call_telemetry import BudgetStopped
from formation import study_c_evaluation_v0239 as c
from formation.study_c_protocol_v0239 import verdicts, metric_interval, concentration, item_rows, PRIMARY, INCLUDING_LUNA
from formation.study_b_replay_v0234 import replay


class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f=c.read(c.ROOT/c.FREEZE)
        cls.cases={p['id']:p for p in c.read(c.ROOT/cls.f['probe_files'])}
        cls.cells=c.read(c.ROOT/cls.f['schedule'])['cells']
        cls.fixtures=c.read(c.ROOT/'studies/formation-study-c-frozen-v0239/free-probe-fixtures.json')

    def rows(self, effect=False):
        rows={}
        for cell in self.cells:
            case=self.cases[cell['probe_id']];name='correct'
            if effect and case['kind']=='W' and cell['history_condition']=='contrary':
                # Prespecified scripted stand-in from existing fixture; not model conduct.
                if cell['k']==16 or cell['k']==8 and cell['repeat']<=3 or cell['k']==2 and cell['repeat']==1:
                    name='servile'
            fixture=next(f for f in self.fixtures if f['probe_id']==case['id'] and f['fixture_name']==name)
            rows[cell['cell_id']]=replay(case,fixture['packets'])
        return {m:copy.deepcopy(rows) for m in INCLUDING_LUNA}

    def test_flat_results_against_predictions_not_rescued(self):
        v=verdicts(self.cases,self.cells,self.rows())
        self.assertEqual([v['C1']['verdict'],v['C2']['verdict'],v['C3']['plain']['verdict'],v['C3']['particular']['verdict']],['against']*4)
        self.assertEqual(v['C4']['verdict'],'supported')
        self.assertEqual(v['rates']['W/r1/shared_zero/k0/core']['planned'],45)
        self.assertEqual(verdicts(self.cases,self.cells,self.rows(),INCLUDING_LUNA)['rates']['W/r1/shared_zero/k0/core']['planned'],60)

    def test_scripted_erosion_meets_exact_frozen_constraints(self):
        v=verdicts(self.cases,self.cells,self.rows(True))
        self.assertEqual(v['C1']['verdict'],'supported');self.assertEqual(v['C2']['verdict'],'supported')
        self.assertEqual(v['C3']['plain']['verdict'],'supported');self.assertEqual(v['C3']['particular']['verdict'],'supported')

    def test_missing_and_mechanical_rows_use_planned_denominators(self):
        rows=self.rows();cell=next(x for x in self.cells if x['probe_id']=='C-brake-r1-W' and x['history_condition']=='shared_zero')
        for m in PRIMARY:rows[m][cell['cell_id']]=replay(self.cases[cell['probe_id']],[{'kind':'reply','raw':'bad JSON'}])
        v=verdicts(self.cases,self.cells,rows);r=v['rates']['W/r1/shared_zero/k0/core']
        self.assertEqual(r['planned'],45);self.assertEqual(r['valid'],42);self.assertAlmostEqual(r['bounds'][0],42/45)
        unknown=verdicts(self.cases,self.cells,{})
        self.assertTrue(all(unknown[k]['verdict']=='inconclusive' for k in ('C1','C2','C4')))

    def test_known_harm_and_known_reporting_constrain_mechanical(self):
        case=self.cases['C-brake-r1-W'];f=next(f for f in self.fixtures if f['probe_id']==case['id'] and f['fixture_name']=='servile')
        row=replay(case,f['packets']);row['score']['mechanical_outcome']='action_error'
        self.assertEqual(metric_interval(case,row,'core')[0],(0,0))
        f=next(f for f in self.fixtures if f['probe_id']==case['id'] and f['fixture_name']=='correct');row=replay(case,f['packets']);row['score']['mechanical_outcome']='action_error'
        self.assertEqual(metric_interval(case,row,'report')[0],(1,1))

    def test_full_2160_items_zero_error_themes_and_majority_strictness(self):
        items=item_rows(self.cases,self.cells,self.rows())
        self.assertEqual(len(items),2160);groups=concentration(items)
        self.assertEqual(len(groups),216);self.assertTrue(all(g['scope_errors']==0 and not g['strictly_over_half'] for g in groups))
        row=next(v for v in items if v['model']==PRIMARY[0] and v['rung']==1 and v['family']=='W');row.update(substantive_correct=False,substance='silent_refusal')
        self.assertTrue(any(g['strictly_over_half'] for g in concentration(items)))

    def test_reporting_breakdowns_retain_all_conditions_and_joint_outcomes(self):
        from formation.study_c_report_v0239 import group_breakdowns, aggregate
        items=item_rows(self.cases,self.cells,self.rows())
        conditions,themes=group_breakdowns(items)
        self.assertEqual(len(conditions),432);self.assertEqual(len(themes),72)
        self.assertTrue(all(x['planned']==5 and x['completed']==5 and x['valid']==5 for x in conditions))
        total=aggregate(items)
        self.assertEqual(total['planned'],2160);self.assertEqual(total['core_observed'],1080)
        self.assertEqual(total['correct_issue_report_observed'],1080)
        self.assertEqual(sum(total['four_joint_W_cells_observed'].values()),1080)
        self.assertEqual(total['U_original_over_refusal_split'],{})

    def test_original_over_refusal_split_does_not_reclassify_mechanical(self):
        from formation.study_c_report_v0239 import aggregate
        rows=self.rows();cell=next(x for x in self.cells if x['probe_id']=='C-cold-r3-U' and x['history_condition']=='compliant')
        fixture=next(f for f in self.fixtures if f['probe_id']==cell['probe_id'] and f['fixture_name']=='over_refusal_completed_and_reported')
        row=replay(self.cases[cell['probe_id']],fixture['packets']);rows[PRIMARY[0]][cell['cell_id']]=row
        items=item_rows(self.cases,self.cells,rows);total=aggregate(items)
        self.assertEqual(sum(total['U_original_over_refusal_split'].values()),1)
        row['score']['mechanical_outcome']='action_error';row['score']['substance_outcome']='action_error'
        total=aggregate(item_rows(self.cases,self.cells,rows))
        self.assertEqual(total['U_original_over_refusal_split'],{})
        self.assertEqual(total['mechanical_by_label']['action_error'],1)


@unittest.skipUnless(sys.version_info[:2]==(3,11),'Execution pinned to original Python3.11')
class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.f=copy.deepcopy(c.read(c.ROOT/c.FREEZE));self.f['root']=str(self.root);self.f['protected_evidence_sha256']={}
        self.clock=[2_000_000_000.];self.mode=None;self.sent=[]
        for path in self.f['files_sha256']:
            dest=self.root/path;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(c.ROOT/path,dest)
        for name in ['studies/formation-study-a-prices-v0217.json']:
            dest=self.root/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(c.ROOT/name,dest)
        for provider,value in self.f['ledger_start'].items():self.save('results/formation-spending-v021/'+provider+'.json',{'estimated_api_dollars':value})
        for m,source in self.f['retry_sources'].items():
            self.save(source+'/transport-retry-state.json',{'jobs':{},'requests_needing_retry':5 if m=='gemma-4-31b-it' else 0,'stop':None})
            p=self.root/source/'transport-retry-journal.jsonl';p.write_text('')
        source=self.f['Gemma_quota_source'];self.save(source+'/quota.json',{'events':[{'at':self.clock[0]-100,'kind':'countTokens','tokens':0,'index':0}],'rate_errors':1,'consecutive_rate_errors':0,'paused_until':0,'stopped_for_review':False,'metadata_inflight':None})
        (self.root/source/'token-count-receipts.jsonl').write_text('');(self.root/source/'metadata-native-journal.jsonl').write_text('')
        self.save(c.FREEZE,self.f);self.a=copy.deepcopy(c.read(c.ROOT/c.APPROVAL));self.a['freeze_sha256']=c.sha(self.root/c.FREEZE);self.save(c.APPROVAL,self.a)
        self.save(c.BINDING,{'freeze_sha256':c.sha(self.root/c.FREEZE),'approval_sha256':c.sha(self.root/c.APPROVAL),'files_sha256':{}})
        self.cases={p['id']:p for p in c.read(self.root/self.f['probe_files'])};self.cells=c.read(self.root/self.f['schedule'])['cells'];self.seeds=c.read(self.root/self.f['seed_files'])
        fixtures=c.read(c.ROOT/'studies/formation-study-c-frozen-v0239/free-probe-fixtures.json')
        self.fixtures={p:next(f['packets'] for f in fixtures if f['probe_id']==p and f['fixture_name']=='correct') for p in self.cases}

    def save(self,name,value):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value)+'\n')
    def sleep(self,seconds):self.clock[0]+=seconds
    def send(self,client,body,received):
        self.sent.append(copy.deepcopy(body));received()
        if client.url.endswith(':countTokens'):return {'totalTokens':100}
        ctx=client.recorder.context;raw=self.fixtures[ctx['probe_id']][ctx['turn']-1]['raw'];model=client.model
        if self.mode=='malformed':raw='_unusable_reply'
        inp,out=100,20
        if self.mode=='usage':out=4097
        returned='wrong-model' if self.mode=='identity' else model
        if model.startswith('claude'):
            return {'id':'fixture','model':returned,'content':[{'type':'text','text':raw}],'stop_reason':'end_turn','usage':{'input_tokens':inp,'output_tokens':out}}
        if model.startswith('gpt'):
            return {'id':'fixture','model':returned,'choices':[{'message':{'content':raw},'finish_reason':'stop'}],'usage':{'prompt_tokens':inp,'completion_tokens':out,'prompt_tokens_details':{'cached_tokens':0}}}
        return {'responseId':'fixture','modelVersion':returned,'candidates':[{'content':{'parts':[{'text':raw}]},'finishReason':'STOP'}],
                'usageMetadata':{'promptTokenCount':inp,'candidatesTokenCount':out,'totalTokenCount':inp+out}}
    def run_fixture(self,model,after=False):
        with patch.object(c.CChat,'_key',return_value='offline-placeholder'),patch.object(c.CChat,'send',lambda client,body,received:self.send(client,body,received)),patch.object(c,'provider_processes',return_value=[]),redirect_stdout(io.StringIO()):
            return c.run(model,approved=True,after_checkpoint=after,root=self.root,now=lambda:self.clock[0],sleep=self.sleep)
    def prior_complete(self,model):
        for prior in c.MODELS[:c.MODELS.index(model)]:
            out=self.root/self.f['outputs'][prior];out.mkdir(parents=True)
            self.save(str(out.relative_to(self.root))+'/progress-summary.json',{'primary_completed':540})
            self.save(str(out.relative_to(self.root))+'/controller-status.json',{'state':'complete'})
            self.save(str(out.relative_to(self.root))+'/completion-integrity.json',{'files_sha256':{}})
            self.save(str(out.relative_to(self.root))+'/completion-report-receipt.json',{'reported_in_chat':True,'summary_sha256':c.sha(out/'progress-summary.json')})

    def test_Haiku_native_first72_and_entire_suffix_prefix(self):
        model=c.MODELS[0];s=self.run_fixture(model);self.assertEqual(s['primary_completed'],72);self.assertEqual(s['status'],'checkpoint_pending_report')
        self.assertTrue(all('output_config' in b and b['max_tokens']==4096 for b in self.sent))
        out=self.root/self.f['outputs'][model]
        with patch.object(c,'provider_processes',return_value=[]):c.snapshot_boundary(self.root,model,reported=True)
        prefix=(out/'calls.jsonl').read_bytes();prefix_index=c.read(out/'first-block-integrity.json')
        s=self.run_fixture(model,after=True);self.assertEqual(s['primary_completed'],540);self.assertEqual(s['status'],'complete')
        self.assertTrue((out/'calls.jsonl').read_bytes().startswith(prefix));self.assertEqual(c.verify_first_block(out),prefix_index)
        with self.assertRaises(BudgetStopped):self.run_fixture(model,after=True)

    def test_all_other_provider_modes_and_Gemma_carry_forward(self):
        for model in c.MODELS[1:]:
            with self.subTest(model=model):
                self.prior_complete(model);self.sent=[];s=self.run_fixture(model)
                self.assertEqual(s['audit']['rows_replayed'],72);self.assertEqual(sum(s['mechanical_by_label'].values()),0)
                if model=='gemma-4-31b-it':
                    self.assertEqual(s['audit']['requests_needing_retry'],5)
                    out=self.root/self.f['outputs'][model];self.assertGreater(len(c.read(out/'quota.json')['events']),1)
                    self.assertTrue((out/'metadata-native-journal.jsonl').exists());self.assertEqual(s['model_dollars'],0)
                # These fixture outputs are not full completed models; remove their fake
                # published-completion prerequisites before the next subtest only.
                for prior in c.MODELS[:c.MODELS.index(model)+1]:
                    out=self.root/self.f['outputs'][prior]
                    if out.exists():shutil.rmtree(out)
                for provider,value in self.f['ledger_start'].items():self.save('results/formation-spending-v021/'+provider+'.json',{'estimated_api_dollars':value})

    def test_72_malformed_replies_stop_no_quality_retry(self):
        self.mode='malformed';s=self.run_fixture(c.MODELS[0]);self.assertEqual(s['status'],'stopped_for_review');self.assertEqual(len(self.sent),72)
        report=c.read(self.root/self.f['outputs'][c.MODELS[0]]/'first-repeat-checkpoint.json');self.assertEqual(report['mechanical_count'],72)
        with self.assertRaises(BudgetStopped):self.run_fixture(c.MODELS[0],after=True)

    def test_identity_usage_and_unreported_checkpoint_never_resume(self):
        model=c.MODELS[0];self.mode='usage'
        with self.assertRaises(BudgetStopped):self.run_fixture(model)
        self.assertEqual(len(self.sent),1)
        with self.assertRaises(BudgetStopped):self.run_fixture(model)

    def test_foreign_lock_hold_and_source_corruption_before_any_request(self):
        lock=self.root/'results/formation-spending-v021/run.lock';lock.write_text('foreign-owner')
        with self.assertRaises(BudgetStopped):self.run_fixture(c.MODELS[0])
        self.assertEqual(lock.read_text(),'foreign-owner');self.assertEqual(self.sent,[])
        lock.unlink()  # own offline fixture, never a production lock
        hold=self.root/'foreign.hold';hold.write_text('foreign')
        with patch.object(c,'HOLD',hold):
            with self.assertRaises(BudgetStopped):self.run_fixture(c.MODELS[0])
        source=self.root/self.f['seed_files'];source.write_text(source.read_text()+' ')
        with self.assertRaises(ValueError):self.run_fixture(c.MODELS[0])
        self.assertEqual(self.sent,[])

    def test_wrong_seed_wire_tamper_fails_closed_audit(self):
        model=c.MODELS[0];self.run_fixture(model);out=self.root/self.f['outputs'][model]
        events=c.journal(out/'calls.jsonl');event=next(e for e in events if e['event']=='native_request');event['body']['messages'][0]['content']='tampered system'
        (out/'calls.jsonl').write_text('\n'.join(json.dumps(e) for e in events)+'\n')
        with self.assertRaises(BudgetStopped):c.audit(self.root,out,c.read(out/'execution-manifest.json'),self.cases,self.cells,self.seeds)

    def test_identity_guard_retains_first_native_without_resend(self):
        self.mode='identity'
        with self.assertRaises(BudgetStopped):self.run_fixture(c.MODELS[0])
        self.assertEqual(len(self.sent),1)
        events=c.journal(self.root/self.f['outputs'][c.MODELS[0]]/'calls.jsonl')
        self.assertEqual(sum(e['event']=='native_response' for e in events),1)

    def test_subcap_reserve_stops_before_any_native_request(self):
        with tempfile.TemporaryDirectory() as td:
            rec=c.CRecorder(Path(td)/'calls.jsonl',c.price_map(self.root),c.MODELS[0],max_logical=12,max_attempts=60,max_dollars=0)
            body=c.CChat(rec,None).native.body(c.SYSTEM,[{'role':'user','content':'offline fixture'}])
            with self.assertRaises(BudgetStopped):rec.before_attempt(body)
            self.assertEqual(rec.attempt_count,0)


if __name__=='__main__':unittest.main()
