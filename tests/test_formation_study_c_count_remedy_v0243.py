"""Offline count recovery and metadata-only exemption; never study inference."""
import copy
import hashlib
import json
import tempfile
import unittest
import io
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from agents.call_telemetry import BudgetStopped
from formation.evaluation_gemma_continuation_v0223 import RetryQuota
from formation.transport_retry_v0223 import RetryTransport
from formation import study_c_count_remedy_v0243 as remedy


class CountRemedyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.body={'contents':[{'role':'user','parts':[{'text':'arbitrary neutral fixture'}]}]}
        self.digest=remedy.body_hash(self.body);self.job='countTokens:'+self.digest
        self.old=dict(body_sha256=self.digest,attempts=1,received=True,phase='complete',ready_at=0,counted_retry=False)
        self.state={'jobs':{self.job:copy.deepcopy(self.old)},'requests_needing_retry':5,'stop':None}
        self.receipts=self.root/'old-counts.jsonl';self.statepath=self.root/'old-state.json'
        self.receipts.write_text(json.dumps(dict(event='count_complete',body_sha256=self.digest,totalTokens=1028))+'\n')
        self.statepath.write_text(json.dumps(self.state))
        self.clock=[0.]

    def source(self):
        return [(self.receipts,self.statepath,hashlib.sha256(self.receipts.read_bytes()).hexdigest(),hashlib.sha256(self.statepath.read_bytes()).hexdigest())]

    def client(self,state=None):
        p=self.root/'retry.json';p.write_text(json.dumps(state or self.state))
        retry=RetryTransport(p,self.root/'retry-journal.jsonl',now=lambda:self.clock[0],sleep=lambda t:self.clock.__setitem__(0,self.clock[0]+t))
        quota=RetryQuota(self.root/'quota.json',self.root/'counts.jsonl',now=lambda:self.clock[0])
        sent=[]
        def send(endpoint,body,received):
            sent.append((endpoint,body));received();return {'totalTokens':1030}
        client=SimpleNamespace(model=remedy.MODEL,quota=quota,retry=retry,
                               reserve=Mock(return_value=6788),native_send=send,send=Mock(side_effect=AssertionError('generation must not run')))
        return client,sent

    def test_exact_prior_count_recovered_without_HTTP_or_mutating_original(self):
        before=(self.receipts.read_bytes(),self.statepath.read_bytes())
        index=remedy.verified_counts(self.source());client,sent=self.client()
        self.assertEqual(remedy.count_body(client,self.body,index),1028)
        self.assertEqual(remedy.count_body(client,self.body,index),1028)
        self.assertEqual(sent,[]);client.reserve.assert_not_called();client.send.assert_not_called()
        self.assertEqual(client.retry.state,self.state)
        self.assertEqual(before,(self.receipts.read_bytes(),self.statepath.read_bytes()))
        records=remedy.events(client.quota.receipts)
        self.assertEqual(len(records),1);self.assertTrue(records[0]['no_HTTP_request'])
        self.assertEqual(records[0]['body_sha256'],self.digest)

    def test_source_tamper_fails_closed(self):
        source=self.source();self.receipts.write_text(self.receipts.read_text()+' ')
        with self.assertRaisesRegex(BudgetStopped,'binding'):remedy.verified_counts(source)

    def test_unclosed_or_unreceived_job_never_certifies_count(self):
        for change in [{'phase':'inflight'},{'received':False},{'body_sha256':'0'*64}]:
            with self.subTest(change=change):
                state=copy.deepcopy(self.state);state['jobs'][self.job].update(change);self.statepath.write_text(json.dumps(state))
                with self.assertRaises(BudgetStopped):remedy.verified_counts(self.source())

    def test_conflicting_or_invalid_counts_fail_closed(self):
        for count in [True,0,-1,'1028',1029]:
            with self.subTest(count=count):
                first=dict(event='count_complete',body_sha256=self.digest,totalTokens=1028)
                other=dict(first,totalTokens=count)
                self.receipts.write_text(json.dumps(first)+'\n'+json.dumps(other)+'\n')
                with self.assertRaises(BudgetStopped):remedy.verified_counts(self.source())

    def test_metadata_fallback_new_job_preserves_original_and_counters(self):
        client,sent=self.client();before=copy.deepcopy(client.retry.state['jobs'][self.job])
        self.assertEqual(remedy.count_body(client,self.body,{}),1030)
        self.assertEqual(len(sent),1);self.assertEqual(sent[0][0],remedy.ENDPOINT)
        self.assertEqual(client.retry.state['jobs'][self.job],before)
        self.assertEqual(client.retry.state['requests_needing_retry'],5)
        new='countTokens:v0243:'+self.digest+':metadata-only-1'
        self.assertEqual(client.retry.state['jobs'][new]['phase'],'complete')
        self.assertEqual(remedy.count_body(client,self.body,{}),1030);self.assertEqual(len(sent),1)
        client.send.assert_not_called()

    def test_no_second_metadata_job_after_receipt_loss(self):
        client,sent=self.client();remedy.count_body(client,self.body,{})
        client.quota.counts.clear()
        with self.assertRaisesRegex(BudgetStopped,'no second'):remedy.count_body(client,self.body,{})
        self.assertEqual(len(sent),1)

    def test_generation_received_barrier_is_unchanged(self):
        client,sent=self.client();generation='C:first:turn1'
        client.retry.state['jobs'][generation]=copy.deepcopy(self.old)
        before=copy.deepcopy(client.retry.state['jobs'][generation])
        with self.assertRaisesRegex(BudgetStopped,'cannot be resent'):
            client.retry.execute(generation,self.body,Mock(),Mock(),Mock())
        self.assertEqual(before,client.retry.state['jobs'][generation]);self.assertEqual(sent,[])

    def test_exemption_rejects_generation_endpoint_and_other_models(self):
        client,sent=self.client()
        for endpoint,model in [(remedy.ENDPOINT.replace(':countTokens',':generateContent'),remedy.MODEL),
                               (remedy.ENDPOINT,'gemini-3.1-flash-lite')]:
            with self.assertRaises(BudgetStopped):remedy.metadata_job(client.retry,self.body,endpoint,model)
        client.model='gemini-3.1-flash-lite'
        with self.assertRaises(BudgetStopped):remedy.count_body(client,self.body,{})
        self.assertEqual(sent,[])

    def test_unclosed_metadata_or_run_stop_gets_no_new_job(self):
        for phase,received in [('inflight',True),('ready',False),('failed',False)]:
            client,sent=self.client();client.retry.state['jobs'][self.job].update(phase=phase,received=received)
            with self.assertRaises(BudgetStopped):remedy.count_body(client,self.body,{})
            self.assertEqual(sent,[])
        client,sent=self.client();client.retry.state['stop']='exhausted'
        with self.assertRaises(BudgetStopped):remedy.count_body(client,self.body,{})
        self.assertEqual(sent,[])

    def test_unknown_later_body_gets_regular_metadata_job(self):
        client,sent=self.client();body=copy.deepcopy(self.body)
        body['contents'].append({'role':'model','parts':[{'text':'future reply not known at freeze'}]})
        self.assertEqual(remedy.count_body(client,body,{}),1030)
        self.assertIn('countTokens:'+remedy.body_hash(body),client.retry.state['jobs'])
        self.assertEqual(client.retry.state['jobs'][self.job],self.old)

    def test_secondary_byte_guard_remains(self):
        client,sent=self.client()
        with self.assertRaisesRegex(BudgetStopped,'byte guard'):remedy.count_body(client,{'text':'x'*64000},{})
        self.assertEqual(sent,[])

    def test_invalid_received_metadata_is_not_automatically_reissued(self):
        client,sent=self.client()
        def invalid(endpoint,body,received):received();return {'totalTokens':True}
        client.native_send=invalid
        with self.assertRaisesRegex(BudgetStopped,'valid token count'):remedy.count_body(client,self.body,{})
        with self.assertRaisesRegex(BudgetStopped,'review'):remedy.count_body(client,self.body,{})

    def test_normal_quota_pause_reuses_same_unsent_metadata_job(self):
        client,sent=self.client();new='countTokens:v0243:'+self.digest+':metadata-only-1'
        client.retry.state['jobs'][new]=dict(body_sha256=self.digest,attempts=0,received=False,phase='ready',ready_at=0,counted_retry=False)
        self.assertEqual(remedy.metadata_job(client.retry,self.body),new)
        self.assertEqual(len(client.retry.state['jobs']),2)

    def test_metadata_transport_retry_inherits_counters_and_honors_reset(self):
        client,sent=self.client();attempts=[]
        def send(endpoint,body,received):
            attempts.append(endpoint)
            if len(attempts)==1:
                raise urllib.error.HTTPError('https://offline.invalid',429,'fixture',{'Retry-After':'30'},io.BytesIO(b'{}'))
            received();return {'totalTokens':1030}
        client.native_send=send
        self.assertEqual(remedy.count_body(client,self.body,{}),1030)
        self.assertEqual(client.retry.state['requests_needing_retry'],6)
        self.assertEqual(client.retry.state['jobs'][self.job],self.old)
        self.assertEqual(len(attempts),2);self.assertGreaterEqual(self.clock[0],30)

    def test_original_zero_request_stop_admission_without_resume_labels(self):
        p=self.root/'stop';p.mkdir()
        (p/'controller-status.json').write_text(json.dumps(dict(state='stopped_for_review',completed=0)))
        cell=dict(sequence=1,cell_id='C-first')
        cp=p/'C-first-checkpoint.json';cp.write_text(json.dumps(dict(phase='guard',packets=[],cell=cell)))
        index={'files_sha256':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in p.iterdir()}}
        before={x.name:x.read_bytes() for x in p.iterdir()}
        self.assertEqual(remedy.verify_unstarted_boundary(p,index),cell)
        self.assertEqual(before,{x.name:x.read_bytes() for x in p.iterdir()})
        (p/'calls.jsonl').write_text('')
        with self.assertRaises(BudgetStopped):remedy.verify_unstarted_boundary(p,index)

    def test_live_preserved_receipt_for_original_blocked_body(self):
        from formation.study_a import ROOT
        from formation.study_b_evaluation_v0235 import output_name
        p=ROOT/output_name('gemma-4-31b-it')
        rp,sp=p/'token-count-receipts.jsonl',p/'transport-retry-state.json'
        index=remedy.verified_counts([(rp,sp,hashlib.sha256(rp.read_bytes()).hexdigest(),hashlib.sha256(sp.read_bytes()).hexdigest())])
        self.assertEqual(index['e507615e6e93056a75ffbde22704a26fd0541fc7f9bb54024af1a14456090b12']['totalTokens'],1028)

    def test_all540_fixed_histories_and_every_frozen_fixture_prefix(self):
        from scripts.formation_study_c_count_preflight_v0243 import scan
        result=scan()
        self.assertEqual(result['scheduled_cells'],540)
        self.assertEqual(len({x['cell']['cell_id'] for x in result['items']}),540)
        self.assertEqual(result['HTTP_calls'],0)
        self.assertEqual(result['fixture_prefixes'],6480)
        self.assertEqual(result['unique_bodies'],756)
        self.assertNotIn('metadata_only_new_job_required',result['routes'])
        self.assertEqual(result['routes']['recover_prior_exact_count'],405)
        self.assertEqual(result['recovered_blocked_body']['totalTokens'],1028)
        self.assertEqual(sum(result['routes'].values()),6480)


if __name__=='__main__':unittest.main()
