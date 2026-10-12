"""Dedicated B native fixtures: no credential file or real provider transport."""
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
from formation import study_b_pilot_v0231 as b
from scripts.formation_study_b_review_v0230 import build_cases
from scripts.formation_study_b_gate5a_v0228 import correct_packets

class Response:
    def __init__(self,data,partial=False):self.data=json.dumps(data).encode();self.done=False;self.partial=partial
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def read1(self,n):
        if self.done:
            if self.partial:raise TimeoutError()
            return b''
        self.done=True
        return self.data[:10] if self.partial else self.data

def err(code):return urllib.error.HTTPError('https://fixture.invalid',code,'offline',{'retry-after':'13'},io.BytesIO(b'{"error":{}}'))

@unittest.skipUnless(sys.version_info[:2]==(3,11),'Study B pilot executes only in the original Python 3.11 runtime')
class PilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'root';self.root.mkdir();self.cases={c['id']:c for c in build_cases()}
        plan=copy.deepcopy(b.read(b.ROOT/b.PLAN));plan['root']=str(self.root)
        for path in [*plan['case_sha256'],plan['plan'],plan['transport_policy'],'studies/formation-study-a-prices-v0217.json']:
            target=self.root/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(b.ROOT/path,target)
        (self.root/b.PLAN).write_text(json.dumps(plan))
        self.approval={'approval':b.APPROVAL_TEXT,'plan_sha256':b.sha(self.root/b.PLAN),'bound_sha256':{},'protected_sha256':{}}
        self.save_approval()
        led=self.root/'results/formation-spending-v021';led.mkdir(parents=True)
        (led/'openai.json').write_text(json.dumps({'estimated_api_dollars':plan['OpenAI_cumulative_start_dollars']}))
        self.output=self.root/plan['output'];self.calls=[];self.clock=[1000.];self.waits=[];self.seen={};self.mode=None

    def save_approval(self):(self.root/b.APPROVAL).write_text(json.dumps(self.approval))
    def sleep(self,x):self.clock[0]+=x;self.waits.append(x)
    def send(self,request,timeout):
        body=json.loads(request.data);self.calls.append(body)
        # Fixture target from the exact native full-history view, not passed gold.
        context=json.loads(body['messages'][1]['content'])['task_context']
        cid=next(c['id'] for c in self.cases.values() if b.visible(c)==context or self.initial(c)==context)
        turn=(len(body['messages'])-1)//2+1
        raw=correct_packets(self.cases[cid])[turn-1]['raw']
        key=(cid,turn);n=self.seen.get(key,0);self.seen[key]=n+1
        if self.mode=='retry' and len(self.seen)<=2 and n==0:raise err(503 if len(self.seen)==1 else 429)
        if self.mode=='exhaust':raise err(503)
        if self.mode=='malformed':raw='_tool_call_placeholder'
        data={'id':'fixture','model':b.MODEL,'choices':[{'message':{'content':raw},'finish_reason':'stop'}],'usage':{'prompt_tokens':100,'completion_tokens':20}}
        if self.mode=='identity':data['model']='wrong-model'
        if self.mode=='usage':del data['usage']
        return Response(data,partial=self.mode=='partial')

    def initial(self,c):
        view=b.visible(c);view['world']['step']=1;return view
    def run_fixture(self):
        with patch.object(b.PilotChat,'_key',return_value='offline-fixture'),patch('urllib.request.urlopen',side_effect=self.send):
            return b.run(True,self.root,now=lambda:self.clock[0],sleep=self.sleep)

    def test_full72_native_histories_503_429_and_complete_resume_no_calls(self):
        self.mode='retry';result=self.run_fixture()
        self.assertEqual(result['status'],'complete');self.assertEqual(result['primary_completed'],72)
        self.assertTrue(all(x['score']['substantive_correct'] for x in result['records']))
        self.assertEqual(len(self.calls),242)
        self.assertEqual(self.calls[0],self.calls[1]);self.assertEqual(self.calls[2],self.calls[3])
        self.assertEqual(b.read(self.output/'transport-retry-state.json')['requests_needing_retry'],2)
        self.assertGreaterEqual(sum(self.waits),26)
        self.assertLessEqual(result['pilot_dollars'],.25)
        self.assertFalse((self.root/'results/formation-spending-v021/run.lock').exists())
        prior=len(self.calls);self.assertEqual(self.run_fixture()['status'],'complete');self.assertEqual(len(self.calls),prior)
        for body in self.calls:self.assertEqual(set(body),{'model','messages','max_completion_tokens'})

    def test_missing_approval_no_key_transport_or_output(self):
        with patch.object(b.PilotChat,'_key') as key,patch('urllib.request.urlopen') as transport:
            with self.assertRaises(ValueError):b.run(False,self.root)
            self.assertFalse(self.output.exists());key.assert_not_called();transport.assert_not_called()
        self.approval['plan_sha256']='wrong';self.save_approval()
        with self.assertRaises(ValueError):self.run_fixture()
        self.assertEqual(self.calls,[])

    def test_exhaustion_preserves_failure_reserves_and_stops_no_restart(self):
        self.mode='exhaust';result=self.run_fixture()
        self.assertEqual(result['status'],'stopped_for_review');self.assertEqual(len(self.calls),5)
        self.assertTrue(result['records'][0]['transport_lost'])
        self.assertEqual(result['records'][0]['score']['substance_outcome'],'error')
        self.assertEqual(len(result['pending_transport_replacements']),1)
        self.assertEqual(result['replacement_records'],[])
        with self.assertRaises(BudgetStopped):self.run_fixture()
        self.assertEqual(len(self.calls),5)
        ends=[x for x in b.journal(self.output/'calls.jsonl') if x['event']=='attempt_end']
        self.assertTrue(all(x['reserve_retained'] for x in ends))

    def test_malformed_first_received_reply_scored_once_each_no_replacement(self):
        self.mode='malformed';result=self.run_fixture()
        self.assertEqual(len(self.calls),72)
        self.assertTrue(all(x['score']['substance_outcome']=='malformed_reply' for x in result['records']))
        self.assertEqual(result['pending_transport_replacements'],[])

    def test_partial_bytes_block_resend_and_stop_review(self):
        self.mode='partial';result=self.run_fixture()
        self.assertEqual(result['status'],'stopped_for_review');self.assertEqual(len(self.calls),1)
        self.assertTrue(any(x['event']=='partial_native_response' for x in b.journal(self.output/'calls.jsonl')))
        self.assertEqual(result['pending_transport_replacements'],[])

    def test_identity_and_usage_guards_stop_after_one_native(self):
        for mode in ('identity','usage'):
            with self.subTest(mode=mode):
                if self.output.exists():shutil.rmtree(self.output) # isolated mock fixtures only
                (self.root/'results/formation-spending-v021/openai.json').write_text(json.dumps({'estimated_api_dollars':.256613715}))
                self.mode=mode;self.calls=[]
                if mode=='identity':
                    with self.assertRaises(BudgetStopped):self.run_fixture()
                    result=b.read(self.output/'progress-summary.json')
                else:result=self.run_fixture()
                self.assertEqual(result['status'],'stopped_for_review');self.assertEqual(len(self.calls),1)
                self.assertEqual(result['records'][0]['score']['substance_outcome'],'error')

    def test_corrected_case_and_protected_old_evidence_tamper_stop_before_send(self):
        path=self.root/next(iter(b.read(self.root/b.PLAN)['case_sha256']))
        original=path.read_bytes();path.write_bytes(original+b' ')
        with self.assertRaises(ValueError):self.run_fixture()
        self.assertEqual(self.calls,[]);path.write_bytes(original)
        preserved=self.root/'old-pilot-evidence.json';preserved.write_text('immutable')
        self.approval['protected_sha256']={'old-pilot-evidence.json':b.sha(preserved)};self.save_approval()
        preserved.write_text('changed')
        with self.assertRaises(ValueError):self.run_fixture()
        self.assertEqual(self.calls,[]);self.assertFalse(self.output.exists())

    def test_cap_guard_blocks_before_send_and_foreign_lock_preserved(self):
        lock=self.root/'results/formation-spending-v021/run.lock';lock.write_text('foreign')
        with self.assertRaises(FileExistsError):self.run_fixture()
        self.assertEqual(lock.read_text(),'foreign');self.assertEqual(self.calls,[]);lock.unlink()
        with patch.object(b.PilotRecorder,'before_attempt',side_effect=BudgetStopped('fixture budget guard')):
            with self.assertRaises(BudgetStopped):self.run_fixture()
        self.assertEqual(self.calls,[])
        self.assertEqual(b.read(self.output/'controller-status.json')['state'],'stopped_for_review')

if __name__=='__main__':unittest.main()
