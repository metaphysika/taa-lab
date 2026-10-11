"""Native-response stand-ins validate adapters with no real provider requests."""
import io,json,tempfile,unittest,urllib.error
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from agents.call_telemetry import BudgetStopped
from formation.study_a import ROOT,load_cases
from formation.study_a_comparison import run_episode as frozen_episode
from formation.limits import RatePaused
from formation.evaluation_transport_v0218 import QuotaRecorder,GroqSlots,make_client
from formation.evaluation_runner_v0218 import execute_cell,run_batch,ADAPTERS,history_for_next,atomic
from scripts.formation_study_a_gate3 import verify_freeze

PRICES=json.loads((ROOT/'studies/formation-study-a-prices-v0217.json').read_text())['models']
PLAN=json.loads((ROOT/'studies/formation-study-a-evaluation-plan-v0217.json').read_text())

class Response:
    headers={}
    def __init__(self,model,provider,raw):self.model,self.provider,self.raw=model,provider,raw
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self):
        if self.provider=='google':data={'modelVersion':self.model,'responseId':'fixture',
            'usageMetadata':{'promptTokenCount':100,'candidatesTokenCount':50,'thoughtsTokenCount':10},
            'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':self.raw}]}}]}
        elif self.provider=='claude':data={'model':self.model,'id':'fixture','stop_reason':'end_turn',
            'usage':{'input_tokens':100,'output_tokens':50},'content':[{'type':'text','text':self.raw}]}
        else:data={'model':self.model,'id':'fixture','usage':{'prompt_tokens':100,'completion_tokens':50},
            'choices':[{'finish_reason':'stop','message':{'content':self.raw}}]}
        return json.dumps(data).encode()

class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.folder=Path(self.temp.name)
        self.cases={c['id']:c for c in load_cases([ROOT/p for p in {c['path'] for c in PLAN['cells']}])}
        self.fixtures=[]
        for path in ('studies/formation-study-a-fixtures-v0213.json','studies/formation-study-a-pressure-fixtures-v0215.json'):
            self.fixtures+=json.loads((ROOT/path).read_text())['fixtures']

    def good(self,cid):return next(f['packets'] for f in self.fixtures if f['case_id']==cid and f['name']=='required_conduct')
    def recorder(self,model,path=None,quota=None,**limits):
        args=dict(max_logical=2880,max_attempts=2880,max_dollars=8);args.update(limits)
        return QuotaRecorder(path or self.folder/(model.replace('/','_')+'.jsonl'),PRICES,model,quota=quota,**args)

    def test_all_five_native_envelopes_use_defaults_and_same_score(self):
        for item in PLAN['models']:
            model,provider=item['model'],item['provider'];rec=self.recorder(model)
            quota=type('Quota',(),{'before':lambda *a:None,'observe':lambda *a:None})() if provider=='groq' else None
            client=make_client(model,provider,rec,quota)
            for cid in ('A_W01','P_R01','P_U04'):
                cell=next(c for c in PLAN['cells'] if c['model']==model and c['case_id']==cid and c['repeat']==1)
                raws=iter(p['raw'] for p in self.good(cid));requests=[]
                def send(request,**kwargs):
                    b=json.loads(request.data);requests.append(b)
                    self.assertLessEqual(len(request.data),32000)
                    self.assertNotIn('temperature',b);self.assertNotIn('reasoning_effort',b);self.assertNotIn('thinking',b)
                    return Response(model,provider,next(raws))
                keys={name:'scripted-test-key' for name in ('OPENAI_API_KEY','ANTHROPIC_API_KEY','GEMINI_API_KEY','GROQ_API_KEY')}
                with self.subTest(model=model,cid=cid),patch.dict('os.environ',keys),patch('urllib.request.urlopen',side_effect=send):
                    result,status=execute_cell(cell,self.cases[cid],client,rec,self.folder/(model.replace('/','_')+cid+'.json'))
                    self.assertEqual(status,'complete');self.assertEqual(result['score']['outcome'],'correct')
                    self.assertEqual(result['agent'],model);self.assertTrue(result['identity_valid'])
                    self.assertEqual(len(result['issuer_message_deliveries']),1 if cell['arm']=='pressure' else 0)

    def test_wire_history_equals_frozen_episode(self):
        cid='P_W01';packets=self.good(cid);model='gpt-6-luna'
        def capture(executor,path):
            rec=self.recorder(model,path);client=make_client(model,'openai',rec);raws=iter(p['raw'] for p in packets);bodies=[]
            def send(request,**kwargs):bodies.append(json.loads(request.data));return Response(model,'openai',next(raws))
            with patch.dict('os.environ',{'OPENAI_API_KEY':'scripted-test-key'}),patch('urllib.request.urlopen',side_effect=send):executor(client,rec)
            return bodies
        expected=capture(lambda client,rec:frozen_episode(self.cases[cid],'pressure',client,rec),self.folder/'old.jsonl')
        cell=next(c for c in PLAN['cells'] if c['model']==model and c['case_id']==cid)
        actual=capture(lambda client,rec:execute_cell(cell,self.cases[cid],client,rec,self.folder/'checkpoint.json'),self.folder/'new.jsonl')
        self.assertEqual(actual,expected)

    def test_groq_pause_resume_keeps_one_delivery_and_no_repeat_request(self):
        model='qwen/qwen3.8-27b';cell=next(c for c in PLAN['cells'] if c['model']==model and c['case_id']=='P_R01')
        clock=[1000.0];quota=GroqSlots(self.folder/'quota.json',now=lambda:clock[0]);rec=self.recorder(model,quota=quota)
        client=make_client(model,'groq',rec,quota);raws=iter(p['raw'] for p in self.good('P_R01'));state=self.folder/'state.json'
        with patch.dict('os.environ',{'GROQ_API_KEY':'scripted-test-key'}),patch('urllib.request.urlopen',side_effect=lambda *a,**k:Response(model,'groq',next(raws))) as send:
            while True:
                result,status=execute_cell(cell,self.cases['P_R01'],client,rec,state)
                if status=='complete':break
                self.assertEqual(status,'paused');clock[0]+=61
            self.assertEqual(send.call_count,len(self.good('P_R01')))
            self.assertEqual(result['score']['outcome'],'correct');self.assertEqual(len(result['issuer_message_deliveries']),1)
            execute_cell(cell,self.cases['P_R01'],client,rec,state)
            self.assertEqual(send.call_count,len(self.good('P_R01')))

    def test_groq_full_slot_settlement_and_daily_guard(self):
        clock=[1000.0];q=GroqSlots(self.folder/'q.json',now=lambda:clock[0]);q.before(30000)
        self.assertEqual(json.loads(q.path.read_text())['events'][0][1],8000)
        q.settle({'usage':{'prompt_tokens':1000,'completion_tokens':100,'prompt_tokens_details':{'cached_tokens':800}}})
        self.assertEqual(json.loads(q.path.read_text())['events'][0][1],300)
        with self.assertRaises(RatePaused):q.before(1)
        clock[0]+=61;q.before(1)
        q.observe({'x-ratelimit-remaining-tokens':'0','x-ratelimit-reset-tokens':'2m'})
        clock[0]+=61
        with self.assertRaises(RatePaused):q.before(1)
        atomic(q.path,{'events':[[clock[0]-100,195000]]})
        with self.assertRaises(RatePaused):q.before(1)

    def test_known_terminal_response_recovered_without_generation(self):
        model='gpt-6-luna';cell=next(c for c in PLAN['cells'] if c['model']==model)
        rec=self.recorder(model);client=make_client(model,'openai',rec);state=self.folder/'recover.json'
        packets=self.good(cell['case_id']);raws=iter(p['raw'] for p in packets)
        with patch.dict('os.environ',{'OPENAI_API_KEY':'scripted-test-key'}),patch('urllib.request.urlopen',side_effect=lambda *a,**k:Response(model,'openai',next(raws))) as send:
            result,status=execute_cell(cell,self.cases[cell['case_id']],client,rec,state)
            atomic(state,{'phase':'ready','packets':packets})
            restored=self.recorder(model)
            recovered,status=execute_cell(cell,self.cases[cell['case_id']],make_client(model,'openai',restored),restored,state)
            self.assertEqual(send.call_count,len(packets))
            self.assertEqual(recovered['score'],result['score']);self.assertTrue(recovered['identity_valid'])

    def test_interrupted_checkpoint_and_pending_journal_never_repeat(self):
        model='gpt-6-luna';cell=next(c for c in PLAN['cells'] if c['model']==model)
        rec=self.recorder(model);state=self.folder/'state.json';atomic(state,{'phase':'inflight','packets':[]})
        with patch('urllib.request.urlopen') as send:
            with self.assertRaises(BudgetStopped):execute_cell(cell,self.cases[cell['case_id']],make_client(model,'openai',rec),rec,state)
            send.assert_not_called()
        rec.before_attempt({'model':model,'messages':[{'role':'user','content':'tiny'}],'max_completion_tokens':2048})
        restored=self.recorder(model)
        self.assertTrue(restored.pending)
        with self.assertRaises(BudgetStopped):restored.before_attempt({'model':model,'max_completion_tokens':2048})

    def test_issued_rejection_and_identity_failure_are_not_retried(self):
        for mismatch in (False,True):
            model='gpt-6-luna';cell=next(c for c in PLAN['cells'] if c['model']==model)
            rec=self.recorder(model,self.folder/('reject-%s.jsonl'%mismatch));client=make_client(model,'openai',rec)
            state=self.folder/('reject-%s.json'%mismatch)
            failure=Response('different-model','openai','{"tool":null,"args":{}}') if mismatch else urllib.error.HTTPError('https://example.invalid',429,'fixture',{'retry-after':'61'},None)
            with patch.dict('os.environ',{'OPENAI_API_KEY':'scripted-test-key'}),patch('urllib.request.urlopen',side_effect=None if mismatch else failure,return_value=failure) as send:
                result,status=execute_cell(cell,self.cases[cell['case_id']],client,rec,state)
                self.assertEqual(status,'stopped');self.assertEqual(result['score']['outcome'],'error')
                self.assertFalse(result['identity_valid']);self.assertEqual(send.call_count,1)
                execute_cell(cell,self.cases[cell['case_id']],client,rec,state)
                self.assertEqual(send.call_count,1)

    def test_full_luna_batch_checkpoint_skip_and_approval_barrier(self):
        root=self.folder/'root'
        for relative in list(ADAPTERS)+['studies/formation-study-a-evaluation-plan-v0217.json','studies/formation-study-a-freeze-v0217.json',PLAN['price_file']]+list({c['path'] for c in PLAN['cells']}):
            target=root/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/relative).read_bytes())
        packets=[]
        for c in PLAN['cells']:
            if c['model']=='gpt-6-luna':packets+=self.good(c['case_id'])
        raws=iter(p['raw'] for p in packets);output=self.folder/'output'
        with patch('formation.evaluation_runner_v0218.load_keys') as keys,patch.dict('os.environ',{'OPENAI_API_KEY':'scripted-test-key'}),patch('urllib.request.urlopen',side_effect=lambda *a,**k:Response('gpt-6-luna','openai',next(raws))) as send:
            with self.assertRaises(ValueError):run_batch('gpt-6-luna',1,output,root=root)
            keys.assert_not_called();send.assert_not_called()
            summary=run_batch('gpt-6-luna',1,output,approved=True,root=root)
            self.assertEqual(summary['completed_cells'],240)
            self.assertEqual(send.call_count,len(packets))
            self.assertEqual(len(summary['analysis_records']),240)
            summary=run_batch('gpt-6-luna',1,output,approved=True,root=root)
            self.assertEqual(send.call_count,len(packets));self.assertEqual(summary['completed_cells'],240)
            with self.assertRaises(ValueError):run_batch('gpt-6-luna',2,output,approved=True,root=root)
        self.assertEqual(verify_freeze(),59)

if __name__=='__main__':unittest.main()
