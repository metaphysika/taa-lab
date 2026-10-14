"""Offline tests for owner-approved operational amendment; no credentials/network."""
import copy
import importlib.util
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
from formation import study_c_evaluation_v0241 as c
from formation import study_c_report_v0241 as report
from formation.study_c_protocol_v0239 import item_rows, metric_interval

spec=importlib.util.spec_from_file_location('c239_fixture_helpers',Path(__file__).with_name('test_formation_study_c_v0239.py'))
helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)

@unittest.skipUnless(sys.version_info[:2]==(3,11),'Execution pinned to Python3.11')
class AmendmentTests(unittest.TestCase):
    save=helpers.ExecutionTests.save
    sleep=helpers.ExecutionTests.sleep
    prior_complete=helpers.ExecutionTests.prior_complete
    def setUp(self):
        helpers.ExecutionTests.setUp(self)
        (self.root/'docs/process').mkdir(parents=True)
        am=copy.deepcopy(c.read(c.ROOT/c.AMENDMENT));am.update(science_freeze_sha256=c.sha(self.root/c.FREEZE),immutable_pre_amendment_sha256={},pre_amendment_journal_prefixes={})
        self.save(c.AMENDMENT,am)
        self.save(c.AMENDMENT_BINDING,{'amendment_sha256':c.sha(self.root/c.AMENDMENT),'files_sha256':{}})
        self.token_guard_count=0;self.generations=[]
    def send(self,client,body,received):
        if client.url.endswith(':countTokens'):
            if self.token_guard_count:
                self.token_guard_count-=1;self.sent.append(copy.deepcopy(body));received();return {'totalTokens':11777}
        else:self.generations.append(client.recorder.context.copy())
        return helpers.ExecutionTests.send(self,client,body,received)
    def run_fixture(self,model,after=False,resume=False):
        with patch.object(c.CChat,'_key',return_value='offline-placeholder'),patch.object(c.CChat,'send',lambda client,body,received:self.send(client,body,received)),patch.object(c,'provider_processes',return_value=[]),redirect_stdout(io.StringIO()):
            return c.run(model,approved=True,after_checkpoint=after,resume_guard=resume,root=self.root,now=lambda:self.clock[0],sleep=self.sleep)
    def test_native_wire_boundaries_and_full_body_reserves(self):
        for model in c.MODELS:
            cap=c.WIRE_CAPS[model]
            for delta in [0,1]:
                with self.subTest(model=model,delta=delta),tempfile.TemporaryDirectory() as td:
                    prices=copy.deepcopy(c.price_map(self.root));prices[model].pop('long_context_threshold',None)  # isolate byte gate in this synthetic boundary test
                    rec=c.CRecorder(Path(td)/'calls.jsonl',prices,model,max_logical=12,max_attempts=60,max_dollars=100)
                    native=c.CChat(rec,None).native
                    hist=[{'role':'user','content':''}];body=native.body(c.SYSTEM,hist)
                    hist[0]['content']='x'*(cap+delta-len(json.dumps(body).encode()));body=native.body(c.SYSTEM,hist)
                    self.assertEqual(len(json.dumps(body).encode()),cap+delta)
                    if delta:
                        with self.assertRaises(BudgetStopped):rec.before_attempt(body)
                        self.assertEqual(rec.attempt_count,0)
                    else:
                        rec.before_attempt(body)
                        start=next(e for e in c.journal(rec.path) if e['event']=='attempt_start')
                        self.assertGreater(start['input_token_upper_estimate'],10000)
                        self.assertEqual(rec.attempt_count,1)
    def test_original_short_context_pricing_guard_is_still_independent(self):
        with tempfile.TemporaryDirectory() as td:
            rec=c.CRecorder(Path(td)/'calls.jsonl',c.price_map(self.root),c.MODELS[0],max_logical=12,max_attempts=60,max_dollars=100)
            body=c.CChat(rec,None).native.body(c.SYSTEM,[{'role':'user','content':'x'*101000}])
            with self.assertRaisesRegex(BudgetStopped,'short-context price ceiling'):rec.before_attempt(body)
            self.assertEqual(rec.attempt_count,0)

    def test_Gemma_27_missing_guards_allowed_28th_stops(self):
        model='gemma-4-31b-it';self.prior_complete(model);self.token_guard_count=27
        result=self.run_fixture(model)
        self.assertEqual(result['status'],'checkpoint_pending_report');self.assertEqual(result['primary_closed'],72)
        self.assertEqual(result['primary_completed'],45);self.assertEqual(result['audit']['guard_stopped'],27)
        self.assertEqual(sum(result['mechanical_by_label'].values()),0)
        out=self.root/self.f['outputs'][model]
        for guard in result['guard_stops']:
            self.assertIsNone(guard['judgment_label']);self.assertNotIn('score',guard)
            self.assertFalse(any(x['cell_id']==guard['cell']['cell_id'] for x in self.generations))
        with patch.object(c,'provider_processes',return_value=[]):
            totals=report.model_report(self.root,model);c.snapshot_boundary(self.root,model)
        self.assertEqual(totals['planned'],540);self.assertEqual(totals['guard_stopped'],27)
        self.token_guard_count=1
        with self.assertRaisesRegex(BudgetStopped,'exceed5percent'):self.run_fixture(model,after=True)
        current=c.read(out/'progress-summary.json')
        self.assertEqual(current['primary_closed'],73);self.assertEqual(len(current['guard_stops']),28)
        self.assertEqual(c.read(out/'guard-stops-by-condition.json')['total'],28)
        self.assertEqual(c.read(out/'controller-status.json')['state'],'stopped_for_review')
    def test_Haiku_72_native_schema_then_full_suffix_and_no_restart(self):
        model=c.MODELS[0];first=self.run_fixture(model);out=self.root/self.f['outputs'][model]
        self.assertEqual(first['primary_closed'],72)
        self.assertTrue(all('output_config' in b and b['max_tokens']==4096 for b in self.sent))
        with patch.object(c,'provider_processes',return_value=[]):c.snapshot_boundary(self.root,model)
        prefix=(out/'calls.jsonl').read_bytes();initial={p.name:p.read_bytes() for p in out.glob('C-*-checkpoint.json')}
        last=self.run_fixture(model,after=True)
        self.assertEqual(last['primary_completed'],540);self.assertEqual(last['primary_closed'],540)
        self.assertTrue((out/'calls.jsonl').read_bytes().startswith(prefix))
        self.assertTrue(all((out/name).read_bytes()==data for name,data in initial.items()))
        with self.assertRaises(BudgetStopped):self.run_fixture(model,after=True)
    def test_scoped_execute_preserves_four_packets_and_sends_only_turn5(self):
        f=c.read(c.ROOT/c.FREEZE);original=c.read(c.ROOT/f['outputs'][c.MODELS[0]]/(c.RESUMED_CELL+'-checkpoint.json'))
        packets=copy.deepcopy(original['packets']);cell=self.cells[184];case=self.cases[cell['probe_id']]
        class FixtureClient:
            transport_lost=False
            def chat(inner,system,history):
                self.assertEqual(rec.context['turn'],5)
                self.assertEqual(history,c.seeded_history(case,cell,packets,self.seeds))
                rec.last_identity_valid=True;return '{"tool":null,"args":{}}'
        rec=type('Recorder',(),dict(model=c.MODELS[0],attempt_count=0,last_identity_valid=False))()
        path=self.root/'resume-sidecar.json'
        result=c.execute(case,cell,self.seeds,FixtureClient(),rec,path,initial_packets=packets)
        self.assertEqual(result['packets'][:4],original['packets']);self.assertEqual(len(result['packets']),5)
        self.assertEqual(result['resume_disclosure'],'resumed_after_pre_send_guard_stop')
        with self.assertRaises(BudgetStopped):c.execute(case,cell,self.seeds,FixtureClient(),rec,path,initial_packets=packets)
        with self.assertRaises(BudgetStopped):c.execute(case,self.cells[0],self.seeds,FixtureClient(),rec,self.root/'wrong.json',initial_packets=packets)
    def test_original_pending_body_exact_and_old_freeze_science_unchanged(self):
        f=c.read(c.ROOT/c.FREEZE);o=c.ROOT/f['outputs'][c.MODELS[0]];state=c.read(o/(c.RESUMED_CELL+'-checkpoint.json'))
        cell=self.cells[184];native=c.CLASSES['claude'](c.MODELS[0],type('R',(),{'model':c.MODELS[0]})(),max_output_tokens=4096)
        body=native.body(c.SYSTEM,c.seeded_history(self.cases[cell['probe_id']],cell,state['packets'],self.seeds))
        original=c.read(o/'blocked-request-reconstruction.json')
        self.assertEqual(body,original['body']);self.assertEqual(len(json.dumps(body).encode()),33821)
        self.assertEqual(c.read(c.ROOT/c.FREEZE)['settings']['wire_bytes'],32000)
        # Only immutable original checkpoints and pinned pre-amendment byte prefixes
        # enter the fake fixture. Later paid suffix/status/ledger changes cannot break CI.
        fake=self.root/self.f['outputs'][c.MODELS[0]];fake.mkdir(parents=True)
        for cell in self.cells[:185]:shutil.copyfile(c.checkpoint_path(o,cell),c.checkpoint_path(fake,cell))
        for name in ['execution-manifest.json','first-block-integrity.json']:
            shutil.copyfile(o/name,fake/name)
        amendment=c.read(c.ROOT/c.AMENDMENT)
        for relative,record in amendment['pre_amendment_journal_prefixes'].items():
            with (c.ROOT/relative).open('rb') as stream:data=stream.read(record['bytes'])
            self.assertEqual(c.prefix_hash(c.ROOT/relative,record['bytes']),record['sha256'])
            (fake/Path(relative).name).write_bytes(data)
        self.save(str(fake.relative_to(self.root))+'/transport-retry-state.json',{'jobs':{},'requests_needing_retry':0,'stop':None})
        manifest=c.read(fake/'execution-manifest.json')
        self.save('results/formation-spending-v021/claude.json',{'estimated_api_dollars':manifest['provider_start']+c.journal_spend(fake/'calls.jsonl')})
        with patch.object(c,'provider_processes',return_value=[]):
            self.assertEqual(len(c.verify_unsent_continuation(self.root,fake,self.cases,self.cells,self.seeds)),4)
        with (fake/'calls.jsonl').open('a') as stream:stream.write(json.dumps({'event':'logical_start','context':{'cell_id':c.RESUMED_CELL,'turn':5}})+'\n')
        with self.assertRaisesRegex(BudgetStopped,'already issued'):
            c.verify_unsent_continuation(self.root,fake,self.cases,self.cells,self.seeds)
    def test_guard_missing_uses_frozen_full_planned_bounds_no_judgment(self):
        case=self.cases[self.cells[0]['probe_id']]
        self.assertEqual(metric_interval(case,None,'core'),((0.,1.),None))
        guard=dict(cell=self.cells[0],packets=[],blocked_turn=1,counted_prompt_tokens=11777)
        items=item_rows(self.cases,self.cells,{},models=['gemma-4-31b-it'])
        report.attach_guard_items(items,{'guard_stops':[guard]},self.root,self.root)
        item=items[0];self.assertEqual(item['completed'],0);self.assertEqual(item['valid'],0)
        self.assertIsNone(item['substance']);self.assertIsNone(item['mechanical'])
        self.assertEqual(report.aggregate(items)['guard_stopped'],1)
    def test_source_tamper_and_wrong_resume_model_reject_before_send(self):
        am=c.read(self.root/c.AMENDMENT);am['wire_caps'][c.MODELS[0]]=64000;self.save(c.AMENDMENT,am)
        with self.assertRaises(BudgetStopped):self.run_fixture(c.MODELS[0])
        self.assertEqual(self.sent,[])

if __name__=='__main__':unittest.main()
