"""Offline native-schema, single-call and unpooled rerun protections; no network."""
import copy
import importlib.util
import io
import json
import sys
import unittest
import urllib.error
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from agents.call_telemetry import BudgetStopped
from formation import study_c_evaluation_v0242 as c
from formation import study_c_report_v0242 as report

spec=importlib.util.spec_from_file_location('native_c_fixture_helpers',Path(__file__).with_name('test_formation_study_c_v0239.py'))
helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)


@unittest.skipUnless(sys.version_info[:2]==(3,11),'Execution pinned to original Python3.11')
class NativeRerunTests(unittest.TestCase):
    save=helpers.ExecutionTests.save
    sleep=helpers.ExecutionTests.sleep
    prior_complete=helpers.ExecutionTests.prior_complete

    def setUp(self):
        helpers.ExecutionTests.setUp(self)
        (self.root/'docs/process').mkdir(parents=True)
        amendment=copy.deepcopy(c.read(c.ROOT/c.AMENDMENT))
        amendment.update(science_freeze_sha256=c.sha(self.root/c.FREEZE),immutable_pre_amendment_sha256={},pre_amendment_journal_prefixes={})
        self.save(c.AMENDMENT,amendment)
        self.save(c.AMENDMENT_BINDING,{'amendment_sha256':c.sha(self.root/c.AMENDMENT),'files_sha256':{}})
        self.am=copy.deepcopy(c.read(c.ROOT/c.NATIVE_AMENDMENT))
        self.am.update(root=str(self.root),science_freeze_sha256=c.sha(self.root/c.FREEZE),v0241_amendment_sha256=c.sha(self.root/c.AMENDMENT),v0241_binding_sha256=c.sha(self.root/c.AMENDMENT_BINDING))
        self.failed=self.root/self.am['failed_output'];self.failed.mkdir(parents=True)
        self.save(self.am['failed_output']+'/first-repeat-checkpoint.json',{'episodes':72,'mechanical_count':9,'may_continue':False})
        self.save(self.am['failed_output']+'/controller-status.json',{'state':'stopped_for_review'})
        self.save(self.am['failed_output']+'/transport-retry-state.json',{'jobs':{},'requests_needing_retry':3,'stop':None})
        (self.failed/'transport-retry-journal.jsonl').write_text('')
        (self.failed/'calls.jsonl').write_text(json.dumps({'event':'attempt_start','id':'failed-fixture','reserved_dollars':self.am['failed_cost']})+'\n'+json.dumps({'event':'attempt_end','id':'failed-fixture','estimated_charge_dollars':self.am['failed_cost']})+'\n')
        self.am['failed_files_sha256']={str(p.relative_to(self.root)):c.sha(p) for p in self.failed.iterdir()}
        self.save(c.NATIVE_AMENDMENT,self.am)
        schema=self.root/c.NATIVE_SCHEMA;schema.parent.mkdir(parents=True,exist_ok=True);schema.write_bytes((c.ROOT/c.NATIVE_SCHEMA).read_bytes())
        self.save(c.NATIVE_BINDING,{'approval_sha256':c.sha(self.root/c.NATIVE_AMENDMENT),'files_sha256':{}})
        self.save(c.READY_CI,{'binding_sha256':c.sha(self.root/c.NATIVE_BINDING),'checks':[{'name':n,'conclusion':'success'} for n in ['Harness checks','Formation Python 3.9 checks']]})
        self.save('results/formation-spending-v021/google.json',{'estimated_api_dollars':self.f['ledger_start']['google']+self.am['failed_cost']})
        self.compat_mode=None;self.compat_sends=0

    def send(self,client,body,received):
        if client.recorder.context.get('stage')=='neutral native-schema compatibility; not study data':
            self.compat_sends+=1
            if self.compat_mode=='rejected':raise urllib.error.HTTPError('https://offline.invalid',400,'fixture',{},io.BytesIO(b'{}'))
            if self.compat_mode=='timeout':raise TimeoutError()
            received();raw='[{"tool":null,"args":{}}]' if self.compat_mode=='array' else '{"tool":null,"args":{}}'
            return {'responseId':'offline','modelVersion':'wrong-model' if self.compat_mode=='identity' else client.model,'candidates':[{'content':{'parts':[{'text':raw}]},'finishReason':'STOP'}],'usageMetadata':{'promptTokenCount':100,'candidatesTokenCount':20,'totalTokenCount':120}}
        return helpers.ExecutionTests.send(self,client,body,received)

    def patched(self):
        from contextlib import ExitStack
        stack=ExitStack();stack.enter_context(patch.object(c.CChat,'_key',return_value='offline-placeholder'))
        stack.enter_context(patch.object(c.CChat,'send',lambda client,body,received:self.send(client,body,received)))
        stack.enter_context(patch.object(c,'provider_processes',return_value=[]))
        stack.enter_context(redirect_stdout(io.StringIO()));return stack

    def compatibility(self):
        with self.patched():return c.compatibility_call(approved=True,root=self.root,now=lambda:self.clock[0])

    def seal_compatibility(self):
        out=self.root/self.am['compatibility_output']
        self.save(str((out/'compatibility-integrity.json').relative_to(self.root)),{'files_sha256':{p.name:c.sha(p) for p in out.iterdir() if p.name!='compatibility-integrity.json'}})

    def launch(self,model='gemini-3.1-flash-lite',after=False):
        with self.patched():return c.run(model,approved=True,after_checkpoint=after,root=self.root,now=lambda:self.clock[0],sleep=self.sleep)

    def test_only_Gemini_schema_changes_all_other_bodies_identical(self):
        from formation.study_b_evaluation_v0235 import CLASSES
        schema=c.read(c.ROOT/c.NATIVE_SCHEMA)
        for model in c.MODELS:
            rec=type('R',(),{'model':model})();opts={'max_output_tokens':4096}
            if model=='gpt-6-luna':opts['key_name']='TAA_OPENAI_API_KEY'
            history=[{'role':'user','content':'arbitrary neutral text'}]
            original=CLASSES[c.PROVIDERS[model]](model,rec,**opts).body(c.SYSTEM,history)
            current=c.CLASSES[c.PROVIDERS[model]](model,rec,**opts).body(c.SYSTEM,history)
            if model=='gemini-3.1-flash-lite':self.assertEqual(current['generationConfig'].pop('responseJsonSchema'),schema)
            self.assertEqual(current,original)
        self.assertEqual(len(schema['anyOf']),8)
        self.assertEqual({b['properties']['tool'].get('enum',[None])[0] for b in schema['anyOf']},{'set_record_status','dispatch_shipment','decline_order','decline_work','report_issue','refer_question','decide_question',None})
        for b in schema['anyOf']:
            self.assertEqual(b['required'],['tool','args']);self.assertEqual(b['properties']['reason'],{'type':'string'})
            self.assertTrue(all(v=={'type':'string'} for v in b['properties']['args']['properties'].values()))

    def test_compatibility_one_call_exact_body_full_accounting_not_study_data(self):
        self.prior_complete('gemini-3.1-flash-lite');terminal=self.compatibility();self.seal_compatibility()
        self.assertEqual(self.compat_sends,1);self.assertLess(terminal['cost'],.01)
        self.assertTrue(terminal['not_study_data']);self.assertEqual(terminal['attempts'],1)
        out=self.root/self.am['compatibility_output'];self.assertFalse(list(out.glob('C-*-checkpoint.json')))
        with self.patched():self.assertEqual(c.verify_compatibility(self.root),terminal)
        f,*_=c.check(self.root,True)
        self.assertAlmostEqual(f['Google_retained_failed_and_compatibility'],self.am['failed_cost']+terminal['cost'])
        self.assertAlmostEqual(f['first_block_subcaps']['gemini-3.1-flash-lite'],.60-self.am['failed_cost']-terminal['cost'])
        self.assertAlmostEqual(c.model_cap(f,'gemini-3.1-flash-lite'),3.25-self.am['failed_cost']-terminal['cost'])
        with self.assertRaises(BudgetStopped):self.compatibility()
        self.assertEqual(self.compat_sends,1)

    def test_rejection_stops_no_second_call(self):
        self.prior_complete('gemini-3.1-flash-lite');self.compat_mode='rejected'
        with self.assertRaises(BudgetStopped):self.compatibility()
        self.assertEqual(self.compat_sends,1)
        with self.assertRaises(BudgetStopped):self.compatibility()
        with self.assertRaises((BudgetStopped,FileNotFoundError)):self.launch()
        self.assertEqual(self.compat_sends,1)
        out=self.root/self.am['compatibility_output']
        self.assertEqual(c.read(out/'controller-status.json')['state'],'stopped_for_review')
        self.assertEqual(c.read(out/'transport-retry-state.json')['jobs']['neutral-compatibility:v0242']['attempts'],1)
        self.assertFalse((self.root/self.am['fresh_output']).exists())

    def test_timeout_count_persists_without_a_retry_or_reset(self):
        self.prior_complete('gemini-3.1-flash-lite');self.compat_mode='timeout'
        with self.assertRaises(BudgetStopped):self.compatibility()
        state=c.read(self.root/self.am['compatibility_output']/'transport-retry-state.json')
        self.assertEqual(state['requests_needing_retry'],4);self.assertEqual(self.compat_sends,1)
        self.assertEqual(state['stop'],'single_compatibility_attempt_failed')

    def test_received_wrong_identity_stops_no_study_call(self):
        self.prior_complete('gemini-3.1-flash-lite');self.compat_mode='identity'
        with self.assertRaises(BudgetStopped):self.compatibility()
        self.assertEqual(self.compat_sends,1)
        with self.assertRaises((BudgetStopped,FileNotFoundError)):self.launch()
        self.assertEqual(self.compat_sends,1)

    def test_received_array_is_not_retried_or_study_data(self):
        self.prior_complete('gemini-3.1-flash-lite');self.compat_mode='array'
        with self.assertRaises(ValueError):self.compatibility()
        self.assertEqual(self.compat_sends,1)
        self.assertEqual(c.read(self.root/self.am['compatibility_output']/'transport-retry-state.json')['jobs']['neutral-compatibility:v0242']['phase'],'complete')
        with self.assertRaises((BudgetStopped,FileNotFoundError)):self.launch()

    def test_pending_CI_and_failed_evidence_tamper_stop_before_key_or_call(self):
        self.prior_complete('gemini-3.1-flash-lite');p=self.root/c.READY_CI;value=c.read(p);value['checks'][0]['conclusion']=None;self.save(c.READY_CI,value)
        with self.assertRaises(BudgetStopped):self.compatibility()
        self.assertEqual(self.compat_sends,0)
        value['checks'][0]['conclusion']='success';self.save(c.READY_CI,value)
        with (self.failed/'calls.jsonl').open('a') as out:out.write(' ')
        with self.assertRaises(BudgetStopped):self.compatibility()
        self.assertEqual(self.compat_sends,0)

    def test_fresh72_suffix_full_audit_and_unpooled_first_prefix(self):
        self.prior_complete('gemini-3.1-flash-lite');self.compatibility();self.seal_compatibility()
        failed_bytes={p.name:p.read_bytes() for p in self.failed.iterdir()}
        first=self.launch();self.assertEqual(first['primary_closed'],72);self.assertEqual(first['status'],'checkpoint_pending_report')
        out=self.root/self.am['fresh_output'];self.assertEqual(c.read(out/'native-format-manifest-v0242.json')['study_block'],'native_format_rerun')
        self.assertEqual(first['audit']['inherited_requests_needing_retry'],3)
        self.assertTrue(all(b['generationConfig']['responseJsonSchema']==c.read(c.ROOT/c.NATIVE_SCHEMA) for b in self.sent))
        with self.patched():report.model_report(self.root,'gemini-3.1-flash-lite');c.snapshot_boundary(self.root,'gemini-3.1-flash-lite',reported=True)
        prefix=(out/'calls.jsonl').read_bytes();cp={p.name:p.read_bytes() for p in out.glob('C-*-checkpoint.json')}
        last=self.launch(after=True);self.assertEqual(last['primary_closed'],540)
        self.assertTrue((out/'calls.jsonl').read_bytes().startswith(prefix));self.assertTrue(all((out/n).read_bytes()==v for n,v in cp.items()))
        self.assertTrue(all((self.failed/n).read_bytes()==v for n,v in failed_bytes.items()))
        with self.assertRaises(BudgetStopped):self.launch(after=True)

    def test_failed_fresh_block_never_allows_second_rerun_or_suffix(self):
        self.prior_complete('gemini-3.1-flash-lite');self.compatibility();self.seal_compatibility();self.mode='malformed'
        first=self.launch();self.assertEqual(first['status'],'stopped_for_review');self.assertEqual(len(self.sent),72)
        with self.assertRaises(BudgetStopped):self.launch()
        with self.assertRaises(BudgetStopped):self.launch(after=True)
        self.assertEqual(len(self.sent),72)


if __name__=='__main__':unittest.main()
