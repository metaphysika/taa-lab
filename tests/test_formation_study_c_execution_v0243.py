"""Approved unsent Gemma startup and full native/report audit, all HTTP mocked."""
import copy
import importlib.util
import io
import ast
import inspect
import textwrap
import json
import sys
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from agents.call_telemetry import BudgetStopped
from formation import study_c_evaluation_v0243 as c
from formation import study_c_report_v0243 as report

spec=importlib.util.spec_from_file_location('counted_execution_helpers',Path(__file__).with_name('test_formation_study_c_v0242.py'))
helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)


@unittest.skipUnless(sys.version_info[:2]==(3,11),'Original execution Python3.11')
class CountedExecutionTests(unittest.TestCase):
    def setUp(self):
        self.fixture=helpers.NativeRerunTests('test_only_Gemini_schema_changes_all_other_bodies_identical')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root;self.f=self.fixture.f;self.model='gemma-4-31b-it'
        self.configure_priors()
        self.make_zero_request_stop()
        self.bind_count_remedy()

    def configure_priors(self):
        effective=c.runtime_freeze(self.root,self.f,self.fixture.am)
        for model in c.MODELS[:2]:
            out=self.root/effective['outputs'][model];out.mkdir(parents=True)
            c.atomic(out/'progress-summary.json',dict(primary_completed=540))
            c.atomic(out/'controller-status.json',dict(state='complete'))
            c.atomic(out/'completion-integrity.json',dict(files_sha256={}))
            c.atomic(out/'completion-report-receipt.json',dict(reported_in_chat=True,summary_sha256=c.sha(out/'progress-summary.json')))

    def make_zero_request_stop(self):
        source=self.root/self.f['Gemma_quota_source'];cell=self.fixture.cells[0]
        rec=type('R',(),{'model':self.model})();body=c.CLASSES['google'](self.model,rec,max_output_tokens=4096).body(c.SYSTEM,c.seeded_history(self.fixture.cases[cell['probe_id']],cell,[],self.fixture.seeds))
        self.digest=c.body_hash(body);self.job='countTokens:'+self.digest
        self.old=dict(body_sha256=self.digest,attempts=1,received=True,phase='complete',ready_at=0,counted_retry=False)
        state=c.read(source/'transport-retry-state.json');state['jobs'][self.job]=copy.deepcopy(self.old);c.atomic(source/'transport-retry-state.json',state)
        with self.assertRaisesRegex(BudgetStopped,'cannot be resent'):
            self.fixture.launch(self.model)
        self.out=self.root/self.f['outputs'][self.model]
        self.assertFalse((self.out/'calls.jsonl').exists())
        c.atomic(self.out/'stop-integrity-v0242.json',dict(files_sha256={p.name:c.sha(p) for p in self.out.iterdir()}))
        self.original={p.name:p.read_bytes() for p in self.out.iterdir()}

    def bind_count_remedy(self):
        source=self.root/self.f['Gemma_quota_source'];rp=source/'older-count-receipts.jsonl'
        rp.write_text(json.dumps(dict(event='count_complete',body_sha256=self.digest,totalTokens=1028))+'\n')
        cp=next(self.out.glob('C-*-checkpoint.json'))
        am=dict(execution_authorized=True,root=str(self.root),science_sha256=c.sha(self.root/c.FREEZE),native_binding_sha256=c.sha(self.root/c.NATIVE_BINDING),generation_no_resend_unchanged=True,maximum_metadata_only_new_jobs_per_body=1,Study_D_authorized=False,original_stop_index_sha256=c.sha(self.out/'stop-integrity-v0242.json'),original_guard_checkpoint=cp.name,original_guard_sha256=c.sha(cp),first_cell_id=self.fixture.cells[0]['cell_id'],count_sources=[dict(receipts=str(rp.relative_to(self.root)),state=str((source/'transport-retry-state.json').relative_to(self.root)),receipt_sha256=c.sha(rp),state_sha256=c.sha(source/'transport-retry-state.json'))])
        c.atomic(self.root/c.COUNT_APPROVAL,am);c.atomic(self.root/c.COUNT_BINDING,dict(approval_sha256=c.sha(self.root/c.COUNT_APPROVAL),files_sha256={}))
        self.ci=dict(binding_sha256=c.sha(self.root/c.COUNT_BINDING),checks=[dict(name=n,conclusion='success') for n in ['Harness checks','Formation Python 3.9 checks']])
        c.atomic(self.root/c.COUNT_CI,self.ci)

    def patched(self):
        stack=ExitStack();stack.enter_context(patch.object(c.CChat,'_key',return_value='offline-placeholder'))
        stack.enter_context(patch.object(c.CChat,'send',lambda client,body,received:self.fixture.send(client,body,received)))
        stack.enter_context(patch.object(c,'provider_processes',return_value=[]))
        stack.enter_context(redirect_stdout(io.StringIO()));return stack

    def launch(self,after=False,model=None):
        with self.patched():return c.run(model or self.model,approved=True,after_checkpoint=after,root=self.root,now=lambda:self.fixture.clock[0],sleep=self.fixture.sleep)

    def test_first_unsent_request_full540_archive_counts_and_reports(self):
        first=self.launch();self.assertEqual(first['primary_closed'],72);self.assertEqual(first['guard_stops'],[])
        self.assertEqual(c.read(self.out/'transport-retry-state.json')['jobs'][self.job],self.old)
        receipts=c.journal(self.out/'token-count-receipts.jsonl')
        self.assertTrue(any(e.get('receipt_kind')=='recovered_exact_body_v0243' and e['body_sha256']==self.digest and e['totalTokens']==1028 for e in receipts))
        native=c.journal(self.out/'metadata-native-journal.jsonl')
        self.assertFalse(any(e.get('event')=='C_count_native_start' and c.body_hash({k:v for k,v in e['body']['generateContentRequest'].items() if k!='model'})==self.digest for e in native))
        for name,content in self.original.items():
            if name=='stop-integrity-v0242.json':self.assertEqual((self.out/name).read_bytes(),content)
            else:self.assertEqual((self.out/c.ARCHIVE/name).read_bytes(),content)
        oldguard=c.read(self.root/c.COUNT_APPROVAL)['original_guard_checkpoint']
        self.assertEqual((self.out/oldguard).read_bytes(),self.original[oldguard])
        self.assertNotEqual(c.checkpoint_path(self.out,self.fixture.cells[0]).name,oldguard)
        self.assertNotIn('resume_disclosure',c.read(c.checkpoint_path(self.out,self.fixture.cells[0]))['result'])
        with self.patched():report.model_report(self.root,self.model);c.snapshot_boundary(self.root,self.model,reported=True)
        prefix=(self.out/'calls.jsonl').read_bytes();first_index=c.read(self.out/'first-block-integrity.json')
        last=self.launch(after=True);self.assertEqual(last['primary_closed'],540)
        self.assertEqual(last['audit']['requests_needing_retry'],5);self.assertEqual(last['model_dollars'],0)
        self.assertTrue((self.out/'calls.jsonl').read_bytes().startswith(prefix));self.assertEqual(c.verify_first_block(self.out),first_index)
        with self.patched():report.model_report(self.root,self.model);c.snapshot_boundary(self.root,self.model,reported=True)
        with self.assertRaises(BudgetStopped):self.launch(after=True)
        c.verify_completed(self.out)

    def test_pending_CI_no_archive_key_or_request(self):
        self.ci['checks'][0]['conclusion']=None;c.atomic(self.root/c.COUNT_CI,self.ci)
        with self.assertRaises(BudgetStopped):self.launch()
        self.assertFalse((self.out/c.START_MARKER).exists());self.assertFalse((self.out/c.ARCHIVE).exists())

    def test_source_receipt_change_no_request(self):
        spec=c.read(self.root/c.COUNT_APPROVAL)['count_sources'][0]
        with (self.root/spec['receipts']).open('a') as h:h.write(' ')
        with self.assertRaises(BudgetStopped):self.launch()
        self.assertFalse((self.out/c.START_MARKER).exists())

    def test_first_start_once_no_duplicate_or_generation_relabel(self):
        self.launch()
        with self.assertRaises(BudgetStopped):self.launch()
        for p in self.out.glob('*-first-request-v0243-checkpoint.json'):
            row=c.read(p)['result'];self.assertEqual(row['label'],'primary');self.assertNotIn('resume_disclosure',row)

    def test_generation_body_and_send_path_remain_identical(self):
        old=helpers.c
        self.assertEqual(ast.dump(ast.parse(textwrap.dedent(inspect.getsource(c.CChat.chat)))),
                         ast.dump(ast.parse(textwrap.dedent(inspect.getsource(old.CChat.chat)))))
        for model in c.MODELS[2:]:
            rec=type('R',(),{'model':model})();history=[{'role':'user','content':'neutral fixture'}]
            a=c.CChat(rec,None).native.body(c.SYSTEM,history)
            b=old.CChat(rec,None).native.body(c.SYSTEM,history)
            self.assertEqual(a,b)


if __name__=='__main__':unittest.main()
