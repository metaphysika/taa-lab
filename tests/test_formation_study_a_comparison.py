"""The comparison safeguards use declared fixture responses, never paid models."""
import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from agents.call_telemetry import BudgetStopped
from formation.clients import OpenAIChat
from formation.study_a import ROOT, load_cases
from formation.study_a_comparison import (ComparisonRecorder, PLAN_PATH, SOURCES,
    run_comparison, run_episode, validate_plan)
from tests.test_formation_study_a_pilot import Response

PRICES={'gpt-6-luna':{'input_per_million':.10,'cached_input_per_million':.01,
                     'cache_write_per_million':.125,'output_per_million':.50}}

class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name)
        self.plan=json.loads(PLAN_PATH.read_text())
        self.cases=validate_plan(self.plan)
        self.fixtures=[]
        for path in ('studies/formation-study-a-fixtures-v0213.json',
                     'studies/formation-study-a-pressure-fixtures-v0215.json'):
            self.fixtures+=json.loads((ROOT/path).read_text())['fixtures']

    def good(self,cid):
        return next(f['packets'] for f in self.fixtures if f['case_id']==cid and f['name']=='required_conduct')

    def recorder(self, **limits):
        values=dict(max_logical=288,max_attempts=288,max_dollars=1.50);values.update(limits)
        return ComparisonRecorder(self.directory/'calls.jsonl',PRICES,'gpt-6-luna',**values)

    def test_exact_approved_plan_and_case_hashes(self):
        self.assertEqual(len(validate_plan(self.plan)),24)
        for field,value in [('max_request_attempts',289),('model','other'),('automatic_retries',1),
                            ('proposed_stage_application_stop_dollars',1.51)]:
            modified=copy.deepcopy(self.plan);modified[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):validate_plan(modified)
        changed=copy.deepcopy(self.plan);changed['episode_order'].reverse()
        with self.assertRaises(ValueError):validate_plan(changed)

    def test_cache_write_reserve_then_actual_category_settlement(self):
        recorder=self.recorder()
        body={'model':'gpt-6-luna','messages':[{'role':'user','content':'small'}],'max_completion_tokens':2048}
        aid=recorder.before_attempt(body)
        event=next(json.loads(line) for line in recorder.path.read_text().splitlines() if json.loads(line)['event']=='attempt_start')
        self.assertAlmostEqual(event['reserved_dollars'],(event['input_token_upper_estimate']*.125+2048*.5)/1e6)
        recorder.finish_native(aid,{'model':'gpt-6-luna','usage':{'prompt_tokens':100,'completion_tokens':50,
            'prompt_tokens_details':{'cached_tokens':20,'cache_write_tokens':40}}},'openai')
        self.assertAlmostEqual(recorder.spent,(40*.10+20*.01+40*.125+50*.50)/1e6)
        self.assertEqual(recorder.prices,PRICES)

    def test_pressure_followup_once_in_actual_wire_history(self):
        packets=self.good('P_W01');raws=iter(p['raw'] for p in packets);bodies=[]
        def send(request,**kwargs):
            body=json.loads(request.data);bodies.append(body)
            self.assertLessEqual(len(request.data),32000)
            self.assertEqual(set(body),{'model','messages','max_completion_tokens'})
            return Response(next(raws))
        recorder=self.recorder()
        with patch.dict('os.environ',{'OPENAI_API_KEY':'scripted-test-key'}),patch('urllib.request.urlopen',side_effect=send):
            result,stopped=run_episode(self.cases['P_W01'],'pressure',OpenAIChat('gpt-6-luna',recorder,max_output_tokens=2048),recorder)
        self.assertFalse(stopped);self.assertEqual(result['score']['outcome'],'correct')
        self.assertEqual(len(result['issuer_message_deliveries']),1)
        delivery=result['issuer_message_deliveries'][0]
        self.assertGreater(delivery['before_reply_turn'],delivery['after_step'])
        inserted=[json.loads(m['content']) for m in result['conversation'] if m['role']=='user' and 'issuer_followup' in json.loads(m['content'])]
        self.assertEqual(len(inserted),1)
        self.assertEqual(inserted[0]['issuer_followup'],self.cases['P_W01']['issuer_followup']['text'])
        self.assertFalse('issuer_followup' in json.loads(bodies[0]['messages'][-1]['content']))

    def test_stop_does_not_trigger_extra_call(self):
        recorder=self.recorder()
        with patch.dict('os.environ',{'OPENAI_API_KEY':'scripted-test-key'}),patch('urllib.request.urlopen',return_value=Response('{"tool":null,"args":{}}')) as send:
            result,stopped=run_episode(self.cases['P_R01'],'pressure',OpenAIChat('gpt-6-luna',recorder,max_output_tokens=2048),recorder)
        self.assertEqual(send.call_count,1);self.assertFalse(stopped)
        self.assertEqual(result['score']['outcome'],'unfinished_work')
        self.assertEqual(result['issuer_message_deliveries'],[])

    def test_transport_stop_no_retry_and_retained_premium_reserve(self):
        recorder=self.recorder()
        with patch.dict('os.environ',{'OPENAI_API_KEY':'scripted-test-key'}),patch('urllib.request.urlopen',side_effect=TimeoutError) as send:
            result,stopped=run_episode(self.cases['A_R01'],'baseline',OpenAIChat('gpt-6-luna',recorder,max_output_tokens=2048),recorder)
        self.assertTrue(stopped);self.assertEqual(send.call_count,1)
        self.assertEqual(result['score']['outcome'],'error');self.assertGreater(recorder.spent,0)

    def test_caps_prevent_network(self):
        recorder=self.recorder(max_dollars=.000001)
        client=OpenAIChat('gpt-6-luna',recorder,max_output_tokens=2048)
        with patch.dict('os.environ',{'OPENAI_API_KEY':'scripted-test-key'}),patch('urllib.request.urlopen') as send:
            for message in ['small','x'*32000]:
                with self.assertRaises(BudgetStopped):client.chat('',[{'role':'user','content':message}])
            recorder.max_dollars=1.50;recorder.max_attempts=0
            with self.assertRaises(BudgetStopped):client.chat('',[{'role':'user','content':'small'}])
            send.assert_not_called()

    def test_complete_24_case_batch_fresh_histories_and_no_rerun(self):
        root=self.directory/'root'
        for relative in list(SOURCES)+[e['path'] for e in self.plan['episode_order']]:
            target=root/relative;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes((ROOT/relative).read_bytes())
        packets=[]
        for entry in self.plan['episode_order']:packets+=self.good(entry['case_id'])
        raws=iter(p['raw'] for p in packets);starts=[]
        def send(request,**kwargs):
            body=json.loads(request.data)
            if len(body['messages'])==2:starts.append(body['messages'][1]['content'])
            return Response(next(raws))
        output=self.directory/'output'
        with patch('formation.study_a_comparison.load_keys') as keys,patch.dict('os.environ',{'OPENAI_API_KEY':'scripted-test-key'}),patch('urllib.request.urlopen',side_effect=send) as transport,redirect_stdout(io.StringIO()):
            with self.assertRaises(ValueError):run_comparison(PLAN_PATH,output,root=root)
            keys.assert_not_called();transport.assert_not_called()
            summary=run_comparison(PLAN_PATH,output,approved=True,root=root)
            self.assertEqual(summary['outcomes_by_arm'],{'baseline':{'correct':12},'pressure':{'correct':12}})
            self.assertEqual(len(starts),24)
            self.assertEqual([r['case_id'] for r in summary['cases']],[e['case_id'] for e in self.plan['episode_order']])
            self.assertTrue(all(r['issuer_followups']==(1 if r['arm']=='pressure' else 0) for r in summary['cases']))
            self.assertEqual(transport.call_count,len(packets))
            with self.assertRaises(ValueError):run_comparison(PLAN_PATH,output,approved=True,root=root)
            self.assertEqual(transport.call_count,len(packets))
        self.assertFalse((root/'results/formation-spending-v021/run.lock').exists())

if __name__=='__main__':unittest.main()
