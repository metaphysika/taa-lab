"""Offline fixtures for frozen B execution/checkpoint; never access credential files."""
import copy
import io
import json
import shutil
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
from agents.call_telemetry import BudgetStopped
from formation import study_b_evaluation_v0233 as b
from formation.transport_retry_v0223 import RetryTransport
from scripts.formation_study_b_gate5a_v0228 import correct_packets
from tests.test_formation_study_b_pilot_v0231 import Response


@unittest.skipUnless(sys.version_info[:2]==(3,11),'Frozen Study B execution is pinned to the original Python 3.11 runtime')
class FrozenBTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.clock=[1000.];self.calls=[];self.seen={};self.mode=None
        f=copy.deepcopy(b.read(b.ROOT/b.FREEZE));f['root']=str(self.root);f['protected_evidence_sha256']={}
        for path in f['files_sha256']:
            dest=self.root/path;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(b.ROOT/path,dest)
        self.cases={b.read(self.root/p)['id']:b.read(self.root/p) for p in f['case_files']}
        self.save(b.FREEZE,f)
        a=b.read(b.ROOT/b.APPROVAL);a['freeze_sha256']=b.sha(self.root/b.FREEZE);self.save(b.APPROVAL,a)
        self.save(b.BINDING,{'freeze_sha256':b.sha(self.root/b.FREEZE),'approval_sha256':b.sha(self.root/b.APPROVAL),'files_sha256':{}})
        for provider,total in f['ledger_start'].items():self.save('results/formation-spending-v021/%s.json'%provider,{'estimated_api_dollars':total})
        self.out=self.root/b.output_name('claude-haiku-5-5')
    def save(self,p,x):
        p=self.root/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x))
    def sleep(self,n):self.clock[0]+=n
    def send(self,request,timeout):
        body=json.loads(request.data);self.calls.append(body)
        initial=json.loads(body['messages'][0]['content'])['task_context']
        cid=next(c['id'] for c in self.cases.values() if b.history_for(c,[])[0]['content']==body['messages'][0]['content'])
        turn=(len(body['messages'])+1)//2
        key=(cid,turn);n=self.seen.get(key,0);self.seen[key]=n+1
        if self.mode=='retry' and len(self.seen)<=2 and n==0:
            raise urllib.error.HTTPError('https://fixture.invalid',503 if len(self.seen)==1 else 429,'offline',{'retry-after':'13'},io.BytesIO(b'{"error":{}}'))
        raw=correct_packets(self.cases[cid])[turn-1]['raw']
        if self.mode=='malformed':raw='_tool_call_placeholder'
        data={'id':'fixture','model':'claude-haiku-5-5','content':[{'type':'text','text':raw}],'stop_reason':'end_turn','usage':{'input_tokens':100,'output_tokens':20}}
        if self.mode=='identity':data['model']='wrong'
        return Response(data,partial=self.mode=='partial')
    def run_fixture(self,**kw):
        with patch.object(b.Chat,'_key',return_value='offline-fixture'),patch('urllib.request.urlopen',side_effect=self.send):
            return b.run(approved=True,root=self.root,now=lambda:self.clock[0],sleep=self.sleep,**kw)
    def test_first72_exit_report_barrier_retry_exact_wire_then_no_unreported_resume(self):
        self.mode='retry';s=self.run_fixture()
        self.assertEqual(s['status'],'checkpoint_pending_report');self.assertEqual(s['primary_completed'],72)
        self.assertEqual(s['audit']['attempts_closed'],242);self.assertEqual(s['audit']['native_responses'],240)
        self.assertEqual(s['audit']['rows_replayed'],72);self.assertTrue(all(x['score']['substantive_correct'] for x in s['records']))
        self.assertEqual(self.calls[0],self.calls[1]);self.assertEqual(self.calls[2],self.calls[3])
        self.assertTrue(all(set(x)=={'model','system','messages','max_tokens'} and x['max_tokens']==4096 for x in self.calls))
        self.assertFalse((self.root/'results/formation-spending-v021/run.lock').exists())
        before=len(self.calls)
        with self.assertRaises((BudgetStopped,FileNotFoundError)):self.run_fixture(after_checkpoint=True)
        self.assertEqual(len(self.calls),before)
    def test_checkpoint_eight_mechanical_stops_no_quality_retry(self):
        self.mode='malformed';s=self.run_fixture()
        self.assertEqual(s['status'],'stopped_for_review');self.assertEqual(len(self.calls),72)
        report=b.read(self.out/'first-repeat-checkpoint.json')
        self.assertEqual(report['mechanical_by_label']['malformed_reply'],72);self.assertFalse(report['may_continue'])
        with self.assertRaises(BudgetStopped):self.run_fixture(after_checkpoint=True)
    def test_threshold_exact_and_substantive_unfinished_not_mechanical(self):
        rows=[{'label':'primary','repeat':1,'fatal':False,'score':{'mechanical_outcome':None,'substance_outcome':'unfinished_work'}} for _ in range(72)]
        for x in rows[:7]:x['score']['mechanical_outcome']='unfinished_reply'
        self.assertTrue(b.checkpoint_report(rows)['may_continue'])
        rows[7]['score']['mechanical_outcome']='malformed_action'
        self.assertFalse(b.checkpoint_report(rows)['may_continue']);self.assertEqual(b.checkpoint_report(rows)['mechanical_count'],8)
    def test_partial_and_identity_stop_without_resend(self):
        self.mode='partial'
        self.assertEqual(self.run_fixture()['status'],'stopped_for_review')
        self.assertEqual(len(self.calls),1)
        self.assertEqual(b.read(self.out/'controller-status.json')['state'],'stopped_for_review')
    def test_approval_freeze_and_foreign_lock_before_transport(self):
        with patch('urllib.request.urlopen',side_effect=AssertionError('network forbidden')):
            with self.assertRaises(ValueError):b.run(approved=False,root=self.root)
            self.save('results/formation-spending-v021/run.lock',{'foreign':True})
            with self.assertRaises(BudgetStopped):b.run(approved=True,root=self.root)
        self.assertFalse(self.out.exists());self.assertTrue((self.root/'results/formation-spending-v021/run.lock').exists())
    def test_four_native_usage_envelopes_and_default_bodies(self):
        for model in b.SLUGS:
            provider=b.PROVIDERS[model];out=self.root/model
            rec=b.Recorder(out/'calls.jsonl',b.price_map(self.root),model,10,10,8,prior_spend=0)
            retry=RetryTransport(out/'retry.json',out/'retry.jsonl',now=lambda:self.clock[0],sleep=self.sleep)
            client=b.Chat(rec,retry)
            history=[{'role':'user','content':'offline fixture'}];body=client.native.body(b.SYSTEM,history)
            rec.logical(json.dumps({'system':b.SYSTEM,'messages':history}),'fixture');aid=rec.before_attempt(body)
            if provider=='claude':response={'model':model,'usage':{'input_tokens':100,'output_tokens':30,'cache_read_input_tokens':10,'cache_creation_input_tokens':5}}
            elif provider=='openai':response={'model':model,'usage':{'prompt_tokens':100,'completion_tokens':30,'prompt_tokens_details':{'cached_tokens':10,'cache_write_tokens':5}}}
            else:response={'modelVersion':model,'usageMetadata':{'promptTokenCount':100,'candidatesTokenCount':20,'thoughtsTokenCount':10,'totalTokenCount':130,'cachedContentTokenCount':10}}
            rec.finish_native(aid,response,provider);self.assertTrue(rec.last_identity_valid);self.assertFalse(rec.pending)
            self.assertNotIn('temperature',body);self.assertNotIn('thinking',body);self.assertNotIn('effort',body)
            rec.logical('usage guard','fixture');aid=rec.before_attempt(body)
            response=copy.deepcopy(response)
            if provider=='claude':response['usage']['output_tokens']=4097
            elif provider=='openai':response['usage']['completion_tokens']=4097
            else:response['usageMetadata'].update(candidatesTokenCount=4097,totalTokenCount=4207)
            with self.assertRaises(BudgetStopped):rec.finish_native(aid,response,provider)
            self.assertTrue(rec.missing_usage);self.assertFalse(rec.pending)

    def test_gemma_exact_full_body_count_and4096_guard_retry_pacing(self):
        out=self.root/'gemma-offline';rec=b.Recorder(out/'calls.jsonl',b.price_map(self.root),'gemma-4-31b-it',10,10,8)
        retry=RetryTransport(out/'retry.json',out/'retry.jsonl',now=lambda:self.clock[0],sleep=self.sleep)
        quota=b.RetryQuota(out/'quota.json',out/'count.jsonl',now=lambda:self.clock[0]);client=b.Chat(rec,retry,quota)
        rec.context={'case_id':'fixture','repeat':1,'label':'primary','turn':1}
        bodies=[];generation=[0]
        def send(request,timeout):
            body=json.loads(request.data);bodies.append(body)
            if request.full_url.endswith(':countTokens'):return Response({'totalTokens':100})
            generation[0]+=1
            if generation[0]==1:raise urllib.error.HTTPError('https://fixture.invalid',429,'offline',{'retry-after':'61'},io.BytesIO(b'{"error":{}}'))
            return Response({'modelVersion':'gemma-4-31b-it','responseId':'fixture','candidates':[{'content':{'parts':[{'text':'{"tool":null,"args":{}}'}]},'finishReason':'STOP'}],'usageMetadata':{'promptTokenCount':100,'candidatesTokenCount':20,'thoughtsTokenCount':10,'totalTokenCount':130}})
        with patch.object(client,'_key',return_value='offline-fixture'),patch('urllib.request.urlopen',side_effect=send):
            self.assertEqual(client.chat(b.SYSTEM,[{'role':'user','content':'offline'}]),'{"tool":null,"args":{}}')
        self.assertEqual(bodies[0]['generateContentRequest'],dict(bodies[1],model='models/gemma-4-31b-it'))
        self.assertEqual(bodies[1],bodies[2]);self.assertGreaterEqual(self.clock[0],1061)
        self.assertEqual(rec.attempt_count,2);self.assertEqual(rec.spent,0)
        self.assertEqual(len(quota.state['events']),3)
        pre=[e for e in b.journal(rec.path) if e['event']=='token_preflight'];self.assertTrue(all(e['completion_allowance']==4096 for e in pre))
        rec.context['turn']=2
        with patch.object(client,'_key',return_value='offline-fixture'),patch.object(client,'count',return_value=11777),patch('urllib.request.urlopen',side_effect=AssertionError('must not send')):
            with self.assertRaises(BudgetStopped):client.chat(b.SYSTEM,[{'role':'user','content':'too large'}])
        self.assertEqual(rec.attempt_count,2)
