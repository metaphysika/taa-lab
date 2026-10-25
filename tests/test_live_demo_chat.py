"""Chat Completions fallback: native wire and guard equivalence, canned only."""
from copy import deepcopy
from decimal import Decimal
import json,os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from live_demo import chat,config
from live_demo.adapter import Adapter,Budget,Stop,http
from live_demo.evidence import Evidence,encoded
from live_demo.standin import native,function,done
from live_demo.surface import manifest

class ChatWireTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.ledger=self.root/'ledger.json'
        self.ledger.write_text('{"estimated_api_dollars":1.1411209749999984}')

    def test_frozen_system_and_function_schemas_have_only_required_chat_wrapping(self):
        a=Adapter(Budget(self.ledger,Evidence(self.root/'body')),Evidence(self.root/'unused'))
        body=a.body([dict(role='user',content='neutral fixture')])
        self.assertEqual(set(body),{'model','messages','tools','max_completion_tokens','store'})
        self.assertEqual(body['max_completion_tokens'],4096);self.assertIs(body['store'],False)
        self.assertEqual(body['messages'][0],dict(role='system',content=(config.FROZEN/'system.txt').read_text()))
        self.assertEqual([{'type':'function',**t['function']} for t in body['tools']],manifest())
        measures=config.load('measures.json')['reasoning_carry_over']
        self.assertIs(measures['enabled'],False);self.assertIs(measures['identical_across_arms'],True)

    def test_assistant_multi_calls_and_tool_messages_preserve_ids_arguments_and_order(self):
        first=function('read_record',{'record':'CL1'},1);second=function('read_record',{'record':'ORD1'},2)
        history=[dict(role='user',content='task'),dict(type='reasoning',encrypted_content='DO_NOT_SEND',summary=[]),
                 first,second,dict(type='function_call_output',call_id=first['call_id'],output='one'),
                 dict(type='function_call_output',call_id=second['call_id'],output='two'),dict(role='user',content='next step')]
        original=deepcopy(history);messages=chat.messages('system',history)
        self.assertEqual([m['role'] for m in messages],['system','user','assistant','tool','tool','user'])
        self.assertEqual([c['id'] for c in messages[2]['tool_calls']],['call_1','call_2'])
        self.assertEqual([c['function']['arguments'] for c in messages[2]['tool_calls']],[first['arguments'],second['arguments']])
        self.assertEqual([m['tool_call_id'] for m in messages[3:5]],['call_1','call_2'])
        self.assertNotIn('DO_NOT_SEND',encoded(messages).decode());self.assertEqual(history,original)

    def test_cached_chat_usage_is_charged_and_native_usage_retained(self):
        reply=json.loads(native([done()]));reply['usage']['prompt_tokens_details']['cached_tokens']=40
        evidence=Evidence(self.root/'cached');budget=Budget(self.ledger,evidence)
        a=Adapter(budget,evidence,transport=lambda _:encoded(reply))
        with patch('live_demo.adapter.authorized'):a.respond([],{},1)
        self.assertEqual(budget.spent,Decimal('0.0000214'))
        self.assertEqual((budget.input_tokens,budget.output_tokens),(100,30))
        rows=[json.loads(p.read_bytes()) for p in evidence.directory.glob('[0-9]*.json')]
        self.assertEqual(next(r['value']['native'] for r in rows if r['kind']=='usage'),reply['usage'])

    def test_malformed_chat_output_stops_after_charging_usage_without_retry(self):
        good=json.loads(native([function('read_record',{'record':'CL1'})]));fixtures=[]
        for choices in ([],[good['choices'][0]]*2,[dict(finish_reason='stop',message={'role':'tool','content':'x'})]):
            r=deepcopy(good);r['choices']=choices;fixtures.append(r)
        for calls in ({},'',0,[{'id':'x','type':'computer_call'}],good['choices'][0]['message']['tool_calls']*2):
            r=deepcopy(good);r['choices'][0]['message']['tool_calls']=calls;fixtures.append(r)
        for index,r in enumerate(fixtures):
            evidence=Evidence(self.root/('malformed-%d'%index));budget=Budget(self.ledger,evidence);sent=[]
            a=Adapter(budget,evidence,transport=lambda body:(sent.append(body) or encoded(r)))
            with patch('live_demo.adapter.authorized'),self.assertRaisesRegex(Stop,'unknown_output'):
                a.respond([],{},1)
            self.assertEqual(len(sent),1);self.assertEqual(budget.spent,Decimal('0.000025'))

    def test_completion_usage_guards_retain_reservation_for_invalid_native_counts(self):
        good=json.loads(native([done()]));fixtures=[]
        for field,value in [('prompt_tokens',True),('completion_tokens',4097),('total_tokens',129),('prompt_tokens',-1)]:
            r=deepcopy(good);r['usage'][field]=value;fixtures.append(r)
        r=deepcopy(good);r['usage']['prompt_tokens_details']['cached_tokens']=101;fixtures.append(r)
        for index,r in enumerate(fixtures):
            evidence=Evidence(self.root/('usage-%d'%index));budget=Budget(self.ledger,evidence)
            a=Adapter(budget,evidence,transport=lambda _:encoded(r))
            with patch('live_demo.adapter.authorized'),self.assertRaises(Stop):a.respond([],{},1)
            self.assertEqual(budget.attempts,1);self.assertGreater(budget.spent,Decimal('0.000025'))

    def test_harness_http_transport_uses_chat_endpoint_and_environment_binding(self):
        raw=native([done()])
        class Reply:
            def __enter__(self):self.pending=raw;return self
            def __exit__(self,*args):pass
            def read1(self,*args):value=self.pending;self.pending=b'';return value
        captured=[]
        def opener(request,timeout):
            captured.append(request)
            self.assertEqual(request.full_url,'https://api.openai.com/v1/chat/completions')
            self.assertEqual(request.get_header('Authorization'),'Bearer OFFLINE_FAKE_KEY')
            self.assertEqual(json.loads(request.data),{'messages':[]})
            return Reply()
        with patch.dict(os.environ,{'TAA_OPENAI_API_KEY':'OFFLINE_FAKE_KEY'}),patch('urllib.request.urlopen',side_effect=opener):
            self.assertEqual(http({'messages':[]}),raw)
        self.assertEqual(len(captured),1)

    def test_tool_calls_finish_without_calls_stops_whole_run(self):
        from live_demo.run import run
        reply = json.loads(native([done()]))
        reply['choices'][0]['finish_reason'] = 'tool_calls'
        requests = []
        def adapter(budget, evidence, **kwargs):
            return Adapter(budget, evidence,
                           transport=lambda body: (requests.append(body) or encoded(reply)))
        schedule = [dict(program='T02', arm='floor', repeat=1),
                    dict(program='T02', arm='taa', repeat=1)]
        with patch('live_demo.config.verify', return_value={}), \
                patch('live_demo.run.StandIn', side_effect=adapter), \
                patch('live_demo.config.schedule', return_value=schedule), \
                patch('live_demo.adapter.authorized'):
            result = run(self.root/'empty-tool-calls')
        self.assertEqual(result['stop'], 'unknown_output')
        self.assertEqual(len(result['episodes']), 1)
        self.assertEqual(result['episodes'][0]['stop'], 'unknown_output')
        self.assertNotEqual(result['episodes'][0]['stop'], 'model_done')
        self.assertEqual(len(requests), 1)
        self.assertEqual(result['totals']['attempts'], 1)
        self.assertEqual(Decimal(result['totals']['dollars']), Decimal('0.000025'))
