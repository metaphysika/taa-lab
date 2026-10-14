"""End-to-end native/resume/audit/report fixtures. Every HTTP callback is mocked."""
import copy
import importlib.util
import io
import json
import sys
import unittest
from contextlib import ExitStack,redirect_stdout
from pathlib import Path
from unittest.mock import patch

from agents.call_telemetry import BudgetStopped
from formation import study_c_evaluation_v0244 as c
from formation import study_c_report_v0244 as report
from formation import study_c_usage_runtime_v0244 as u

spec=importlib.util.spec_from_file_location('usage_counted_helpers',Path(__file__).with_name('test_formation_study_c_execution_v0243.py'))
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)

@unittest.skipUnless(sys.version_info[:2]==(3,11),'Original Python3.11 execution')
class UsageExecutionTests(unittest.TestCase):
    def setUp(self):
        self.fixture=t.CountedExecutionTests('test_pending_CI_no_archive_key_or_request');self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.case=self.fixture.fixture;self.root=self.case.root;self.out=self.fixture.out
        if getattr(self,'full_prior_pipeline',False):
            # Temporary scripted fixtures ONLY; original evidence is never touched.
            import shutil
            effective=c.runtime_freeze(self.root,self.case.f,self.case.am)
            for model in c.MODELS[:2]:shutil.rmtree(self.root/effective['outputs'][model])
            self.prior_totals={}
            for model in c.MODELS[:2]:
                if model=='gemini-3.1-flash-lite':self.case.compatibility();self.case.seal_compatibility()
                self.case.launch(model)
                with self.case.patched():t.helpers.report.model_report(self.root,model);t.helpers.c.snapshot_boundary(self.root,model,True)
                last=self.case.launch(model,after=True)
                with self.case.patched():t.helpers.report.model_report(self.root,model);t.helpers.c.snapshot_boundary(self.root,model,True)
                self.prior_totals[model]=last['primary_closed']
            shutil.rmtree(self.out)
            self.fixture.make_zero_request_stop();self.fixture.bind_count_remedy()
        self.original_send=self.case.send
        def stop(client,body,received):
            response=self.original_send(client,body,received)
            ctx=client.recorder.context
            if not client.url.endswith(':countTokens') and ctx.get('cell_id')==u.CELL and ctx.get('turn')==3:
                response['candidates'][0]['content']['parts']=[{'text':'{"tool":"decline_order","args":{"order_id":"ORDER-PRIMARY"},"reason":"fixture: missing independent signature"}'}]
                response['usageMetadata'].pop('candidatesTokenCount');response['usageMetadata']['totalTokenCount']=100
            return response
        self.case.send=stop
        first=self.fixture.launch()
        with self.fixture.patched():t.report.model_report(self.root,'gemma-4-31b-it');t.c.snapshot_boundary(self.root,'gemma-4-31b-it',True)
        with self.assertRaises(BudgetStopped):self.fixture.launch(after=True)
        self.assertEqual(c.read(self.out/'controller-status.json')['completed'],351)
        events=c.journal(self.out/'calls.jsonl');self.aid=next(e['id'] for e in reversed(events) if e['event']=='native_response')
        start=next(e for e in events if e['event']=='attempt_start' and e['id']==self.aid)
        wire=next(e for e in events if e['event']=='native_request' and e['id']==self.aid)
        native=next(e for e in events if e['event']=='native_response' and e['id']==self.aid)
        raw,_=c.CLASSES['google'].extract(None,native['response']);c.parse_action(raw)
        c.atomic(self.out/'native-usage-stop-integrity-v0243.json',dict(files_sha256={str(p.relative_to(self.out)):c.sha(p) for p in self.out.rglob('*') if p.is_file()}))
        am=dict(execution_authorized=True,root=str(self.root),output=str(self.out.relative_to(self.root)),reserve=4096,review_after=5,paid_models_exempt=False,Study_D_authorized=False,science_sha256=c.sha(self.root/c.FREEZE),count_binding_sha256=c.sha(self.root/c.COUNT_BINDING),stop_index_sha256=c.sha(self.out/'native-usage-stop-integrity-v0243.json'),completed_checkpoint_sha256={str(c.checkpoint_path(self.out,cell).relative_to(self.root)):c.sha(c.checkpoint_path(self.out,cell)) for cell in self.case.cells[:351]},journal_prefixes={n:dict(bytes=(self.out/n).stat().st_size,sha256=c.sha(self.out/n)) for n in ['calls.jsonl','transport-retry-journal.jsonl','token-count-receipts.jsonl','metadata-native-journal.jsonl']},logical_id=start['logical_id'],received_body_sha256=c.body_hash(wire['body']),received_text_sha256=c.hashlib.sha256(raw.encode()).hexdigest(),historical_combined_peak=19004)
        c.atomic(self.root/u.APPROVAL,am);c.atomic(self.root/u.BINDING,dict(approval_sha256=c.sha(self.root/u.APPROVAL),files_sha256={}))
        c.atomic(self.root/u.CI,dict(binding_sha256=c.sha(self.root/u.BINDING),checks=[dict(name=n,conclusion='success') for n in ['Harness checks','Formation Python 3.9 checks']]))
        self.before350={str(c.checkpoint_path(self.out,cell)):c.sha(c.checkpoint_path(self.out,cell)) for cell in self.case.cells[:350]}
        self.old351=(self.out/(u.CELL+'-checkpoint.json')).read_bytes();self.prefix=(self.out/'calls.jsonl').read_bytes();self.sent=[];self.missing_remaining=0

    def send(self,client,body,received):
        ctx=copy.deepcopy(client.recorder.context);self.sent.append((client.model,client.url,ctx))
        if client.model=='gemma-4-31b-it' and not client.url.endswith(':countTokens') and ctx.get('cell_id')==u.CELL and ctx.get('turn')==4:
            received()
            response={'responseId':'fixture','modelVersion':client.model,'candidates':[{'content':{'parts':[{'text':'{"tool":null,"args":{}}'}]},'finishReason':'STOP'}],'usageMetadata':{'promptTokenCount':100,'candidatesTokenCount':20,'totalTokenCount':120}}
        else:response=self.original_send(client,body,received)
        if client.model=='gemma-4-31b-it' and not client.url.endswith(':countTokens') and self.missing_remaining:
            if self.missing_remaining==1 and getattr(self,'malformed_sixth',False):
                response['candidates'][0]['content']['parts']=[{'text':'_unusable_reply'}]
            self.missing_remaining-=1;response['usageMetadata'].pop('candidatesTokenCount');response['usageMetadata']['totalTokenCount']=100
        return response

    def patched(self):
        stack=ExitStack();stack.enter_context(patch.object(u,'ATTEMPT',self.aid))
        stack.enter_context(patch.object(c.CChat,'_key',return_value='offline-placeholder'))
        stack.enter_context(patch.object(c.CChat,'send',lambda client,body,received:self.send(client,body,received)))
        stack.enter_context(patch.object(c,'provider_processes',return_value=[]));stack.enter_context(redirect_stdout(io.StringIO()));return stack

    def launch(self,model='gemma-4-31b-it',after=True,adopt=True):
        with self.patched():return c.run(model,approved=True,after_checkpoint=after,adopt_received=adopt,root=self.root,now=lambda:self.case.clock[0],sleep=self.case.sleep)

    def test_adopts_once_full540_native_audit_report_and_Luna72(self):
        result=self.launch();self.assertEqual(result['primary_closed'],540)
        self.assertEqual(result['audit']['usage_accounting']['missing_output_usage_count'],1)
        first_generation=next(ctx for model,url,ctx in self.sent if not url.endswith(':countTokens'))
        self.assertEqual((first_generation['cell_id'],first_generation['turn']),(u.CELL,4))
        self.assertEqual((self.out/(u.CELL+'-checkpoint.json')).read_bytes(),self.old351)
        self.assertTrue((self.out/'calls.jsonl').read_bytes().startswith(self.prefix))
        for path,digest in self.before350.items():self.assertEqual(c.sha(Path(path)),digest)
        with self.patched():
            s=report.model_report(self.root,'gemma-4-31b-it');c.snapshot_boundary(self.root,'gemma-4-31b-it',True)
        self.assertEqual(s['completed'],540);c.verify_completed(self.out)
        before=len(self.sent)
        with self.assertRaises(BudgetStopped):self.launch()
        self.assertEqual(len(self.sent),before)
        luna=self.launch('gpt-6-luna',after=False,adopt=False);self.assertEqual(luna['primary_closed'],72)
        with self.patched():report.model_report(self.root,'gpt-6-luna');c.snapshot_boundary(self.root,'gpt-6-luna',True)
        self.assertEqual(luna['audit']['rows_replayed'],72)

    def test_sixth_reply_is_scored_and_no_later_metadata_or_generation(self):
        self.missing_remaining=5
        self.malformed_sixth=True
        with self.assertRaises(BudgetStopped):self.launch()
        state=c.read(self.out/u.BOOKINGS);self.assertEqual(state['missing_usage_count'],6);self.assertTrue(state['review_required'])
        with self.patched():
            f,a,cases,cells,seeds=c.check(self.root,True)
            audit=c.audit(self.root,self.out,c.read(self.out/'execution-manifest.json'),cases,cells,seeds)
        self.assertTrue(audit['usage_accounting']['review_required'])
        rows=c.read(self.out/'progress-summary.json')['records'];self.assertTrue(rows[-1]['fatal'])
        self.assertEqual(rows[-1]['score']['mechanical_outcome'],'malformed_reply')
        self.assertNotEqual(rows[-1]['stop_reason'],None)
        before=len(self.sent)
        with self.assertRaises(BudgetStopped):self.launch()
        self.assertEqual(len(self.sent),before)

    def test_CI_gate_before_adoption_preserves_originals(self):
        ci=c.read(self.root/u.CI);ci['checks'][0]['conclusion']=None;c.atomic(self.root/u.CI,ci)
        with self.assertRaises(BudgetStopped):self.launch()
        self.assertFalse((self.out/u.MARKER).exists());self.assertFalse((self.out/u.ARCHIVE).exists());self.assertEqual(self.sent,[])

if __name__=='__main__':unittest.main()

class PaidAndCounterGuards(unittest.TestCase):
    def test_paid_native_missing_usage_still_stops(self):
        import tempfile
        for model in c.MODELS[:2]+c.MODELS[3:]:
            with self.subTest(model=model),tempfile.TemporaryDirectory() as folder:
                rec=c.CRecorder(Path(folder)/'calls.jsonl',c.price_map(c.ROOT),model,max_logical=2,max_attempts=2,max_dollars=1,prior_spend=0)
                native=c.CLASSES[c.PROVIDERS[model]](model,rec,max_output_tokens=4096)
                body=native.body(c.SYSTEM,[dict(role='user',content='neutral fixture '*100)])
                rec.logical('offline fixture','fixture');aid=rec.before_attempt(body)
                if model=='claude-haiku-5-5':response=dict(model=model,id='fixture',content=[dict(type='text',text='{}')],usage=dict(input_tokens=100))
                elif model.startswith('gpt'):response=dict(model=model,id='fixture',choices=[dict(message=dict(content='{}'))],usage=dict(prompt_tokens=100))
                else:response=dict(modelVersion=model,responseId='fixture',candidates=[dict(content=dict(parts=[dict(text='{}')]))],usageMetadata=dict(promptTokenCount=100,totalTokenCount=100))
                with self.assertRaises(BudgetStopped):rec.finish_native(aid,response,c.PROVIDERS[model])
                self.assertFalse(rec.pending)
                self.assertFalse((Path(folder)/u.BOOKINGS).exists())

    def test_counter_tamper_blocks_before_key_or_metadata(self):
        import tempfile
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);c.atomic(folder/u.BOOKINGS,dict(bookings={},missing_usage_count=0,review_required=False));c.atomic(folder/u.PACING,dict(events=[],first_new_event=0))
            rec=c.CRecorder(folder/'calls.jsonl',c.price_map(c.ROOT),'gemma-4-31b-it',max_logical=2,max_attempts=2,max_dollars=0,prior_spend=0)
            quota=c.CQuota(folder/'quota.json',folder/'counts.jsonl')
            retry=c.CTransport(folder/'retry.json',folder/'retry-journal.jsonl')
            client=c.CChat(rec,retry,quota)
            client._key=Mock();client.count=Mock()
            c.atomic(folder/u.BOOKINGS,dict(bookings={},missing_usage_count=0,review_required=False,unexpected=True))
            with self.assertRaisesRegex(BudgetStopped,'counter changed'):client.chat(c.SYSTEM,[dict(role='user',content='neutral')])
            client._key.assert_not_called();client.count.assert_not_called()
