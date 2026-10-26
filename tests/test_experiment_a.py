"""Offline fixtures; no blind expected-outcome key or P/H dispositions."""
from copy import deepcopy
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

from live_demo.adapter import Stop, OutputCeiling, TransportFailure
from live_demo.evidence import Evidence, encoded, verify
from live_demo.surface import manifest, refusal
from experiment_a import config, native
from experiment_a.adapter import Adapter, error_fields, authorized, RETRYABLE
from experiment_a.budget import Budget
from experiment_a.cases import pair_check
from experiment_a.check import run as neutral, INSTRUCTION, TOOLS
from experiment_a.driver import Host, brief, episode, program
from experiment_a.standin import ScriptedTransport, reply, prices
from experiment_a.state import State


class Offline(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.network=patch.object(socket,'socket',side_effect=AssertionError('network forbidden'))
        self.network.start();self.addCleanup(self.network.stop)

    def adapter(self,provider,replies,**kwargs):
        directory=self.root/str(len(list(self.root.iterdir())))
        evidence=Evidence(directory)
        ledger=directory/'provider.json';ledger.write_text('{"estimated_api_dollars":0}')
        step=directory/'step.txt';step.write_text('0')
        budget=Budget(provider,ledger,step,evidence,prices=prices(),**kwargs)
        transport=ScriptedTransport(replies)
        return Adapter(provider,budget,evidence,transport=transport,standin=True),transport,evidence

    def test_approved_guide_bytes(self):
        guide=(config.INPUTS/'policy-guide.txt').read_bytes()
        self.assertEqual('8e47b55a72ab329500d2ccc76939328e026a6a4440033c832c42cff5ff51afd0',hashlib.sha256(guide).hexdigest())
        self.assertEqual(config.load('approval.json')['guide_sha256'],hashlib.sha256(guide).hexdigest())

    def test_p_twins_only_deciding_record_and_recognized_assertions(self):
        rows=pair_check(config.INPUTS/'P',config.load('P-pairs.json'))
        self.assertEqual(6,len(rows))

    def test_pilot_schedule_and_frozen_inputs(self):
        config.verify()
        rows=config.load('pilot-order.json')
        self.assertEqual(396,len(rows));self.assertEqual(396,len({tuple(sorted(r.items())) for r in rows}))
        self.assertEqual(('model_alone','conventional','taa'),config.ARMS)
        self.assertFalse(any(r['program'].startswith('H') for r in rows))
        self.assertTrue(all(rows[i]['provider']!=rows[i+1]['provider'] for i in range(len(rows)-1)))
        with self.assertRaisesRegex(Stop,'held_out_sealed'):program('H02')

    def test_unverified_prices_and_pending_reviews_block_launch(self):
        e=Evidence(self.root/'blocked');p=e.directory/'p.json';p.write_text('{"estimated_api_dollars":0}')
        s=e.directory/'s.txt';s.write_text('0')
        for provider in config.MODELS:
            unverified=deepcopy(config.load('prices.json')[provider]);unverified['status']='verify before launch'
            with self.assertRaisesRegex(Stop,'prices_unverified'):Budget(provider,p,s,e,prices=unverified)
        with self.assertRaisesRegex(Stop,'experiment_review_pending'):config.launch_ready()

    def test_exact_allowlists(self):
        self.assertEqual(frozenset(('text','thinking','redacted_thinking','tool_use')),native.OUTPUT_TYPES)
        self.assertEqual(frozenset((429,500,502,503,504)),RETRYABLE)

    def test_error_privacy(self):
        for parameter,expected in [('messages[0].content','messages[0].content'),('key SECRET','withheld'),('x'*129,'withheld')]:
            data=encoded(dict(error=dict(type='invalid_request_error',code='invalid_api_key',param=parameter,message='NEVER KEEP THIS MESSAGE')))
            error=urllib.error.HTTPError('https://example.invalid',400,'withheld',{},io.BytesIO(data))
            observed=error_fields(error)
            self.assertEqual(dict(type='invalid_request_error',code='invalid_api_key',param=expected),observed)
            self.assertNotIn('NEVER',json.dumps(observed))
        error=urllib.error.HTTPError('https://example.invalid',400,'withheld',{},io.BytesIO(encoded(dict(error=dict(status='INVALID_ARGUMENT',code=400,message='private')))))
        self.assertEqual(dict(type='INVALID_ARGUMENT',code=400,param='withheld'),error_fields(error))

    def test_state_missing_or_inside_any_git_tree_refused(self):
        with patch('experiment_a.state.STATE_ROOT',self.root/'absent'):
            with self.assertRaisesRegex(Stop,'durable_state_missing_or_invalid'):State()
        with patch('experiment_a.state.STATE_ROOT',config.ROOT):
            with self.assertRaisesRegex(Stop,'durable_state_missing_or_invalid'):State()


def add_provider_tests(provider):
    def carry(self):
        first=reply(provider,name='echo',args={'value':'neutral-check'})
        a,t,e=self.adapter(provider,[first,reply(provider)])
        a.neutral=True;a.system=INSTRUCTION;a.tools=TOOLS
        history=[dict(kind='user',text='neutral')]
        r=a.respond(history,{},1)
        history += [dict(kind='assistant',native=r['native']),dict(kind='tool_results',results=[dict(id=r['calls'][0]['id'],native_id=r['calls'][0].get('native_id'),name='echo',result={'value':'neutral-check'})])]
        a.respond(history,{},2)
        forwarded=t.requests[1]['messages'][1] if provider=='anthropic' else t.requests[1]['contents'][1]
        original=dict(role='assistant',content=first['content']) if provider=='anthropic' else first['candidates'][0]['content']
        self.assertEqual(encoded(original),encoded(forwarded))
        result=t.requests[1]['messages'][2]['content'][0] if provider=='anthropic' else t.requests[1]['contents'][2]['parts'][0]['functionResponse']
        self.assertIn('neutral-check',json.dumps(result));self.assertEqual(2,len(t.requests))
    def defaults(self):
        bodies=[native.body(provider,config.system(),manifest(),[dict(kind='user',text=encoded(brief(program('P02'))).decode())]) for arm in config.ARMS]
        self.assertEqual(encoded(bodies[0]),encoded(bodies[1]));self.assertEqual(encoded(bodies[1]),encoded(bodies[2]))
        body=bodies[0]
        if provider=='anthropic':
            self.assertEqual({'model','system','messages','tools','max_tokens'},set(body))
            self.assertEqual(32768,body['max_tokens'])
        else:
            self.assertEqual({'systemInstruction','contents','tools','generationConfig'},set(body))
            self.assertEqual({'maxOutputTokens':65536},body['generationConfig'])
        self.assertNotIn('temperature',json.dumps(body));self.assertNotIn('thinkingConfig',json.dumps(body))
    def ceiling(self):
        a,t,e=self.adapter(provider,[reply(provider,name='issue_refund',args={'claim':'CL1','amount':120,'basis':'return','to':'K1_card'},ceiling=True)])
        r=episode(dict(provider=provider,program='T02',arm='taa',repeat=1),a,e)
        self.assertEqual('output_ceiling',r['stop']);self.assertEqual(0,r['metrics']['reference_policy']['actual_committed_acts'])
        self.assertEqual(1,len(t.requests));self.assertGreater(a.budget.phase_spent,0)
    def refusal_test(self):
        value=reply(provider,text='I cannot do that.')
        if provider=='anthropic':value['stop_reason']='refusal'
        a,t,e=self.adapter(provider,[value])
        r=a.respond([dict(kind='user',text='fixture')],{},1)
        self.assertEqual([],r['calls']);self.assertEqual(['I cannot do that.'],r['texts']);self.assertEqual(1,len(t.requests))
    def gateway_refusal_roundtrip(self):
        for arm in ('conventional','taa'):
            a,t,e=self.adapter(provider,[reply(provider,name='issue_refund',args=dict(claim='CL1',amount=120,basis='return',to='account_X')),reply(provider)])
            row=episode(dict(provider=provider,program='T02',arm=arm,repeat=1),a,e)
            self.assertEqual('model_done',row['stop']);self.assertEqual(2,len(t.requests))
            messages=t.requests[1]['messages'] if provider=='anthropic' else t.requests[1]['contents']
            result=[r for r in messages if r.get('role')=='user'][1]
            self.assertIn('This request cannot be completed.',json.dumps(result))
            self.assertNotIn('failed_stage',json.dumps(result))
    def cap_step(self):
        a,t,e=self.adapter(provider,[reply(provider)],step_cap='0')
        with self.assertRaisesRegex(Stop,'cap_stop'):a.respond([dict(kind='user',text='fixture')],{},1)
        self.assertEqual([],t.requests);self.assertEqual(Decimal(0),a.budget.read_step())
    def cap_provider(self):
        a,t,e=self.adapter(provider,[reply(provider)],provider_cap='0')
        with self.assertRaisesRegex(Stop,'cap_stop'):a.respond([dict(kind='user',text='fixture')],{},1)
        self.assertEqual([],t.requests);self.assertEqual(Decimal(0),a.budget.read_provider())
    def retry(self):
        a,t,e=self.adapter(provider,[TransportFailure(503)]*5)
        waits=[];a.sleeper=waits.append
        with self.assertRaisesRegex(Stop,'transport_exhaustion'):a.respond([dict(kind='user',text='fixture')],{},1)
        self.assertEqual(5,len(t.requests));self.assertEqual(220,sum(waits));self.assertGreater(a.budget.phase_spent,0)
    def partial(self):
        a,t,e=self.adapter(provider,[TransportFailure(partial=b'{')]);a.sleeper=lambda x:self.fail('partial reply retried')
        with self.assertRaisesRegex(Stop,'partial_reply'):a.respond([dict(kind='user',text='fixture')],{},1)
        self.assertEqual(1,len(t.requests))
    def no_501_retry(self):
        a,t,e=self.adapter(provider,[TransportFailure(501)])
        with self.assertRaisesRegex(Stop,'transport_not_retryable'):a.respond([dict(kind='user',text='fixture')],{},1)
        self.assertEqual(1,len(t.requests))
    def malformed_usage(self):
        value=reply(provider)
        value['usage' if provider=='anthropic' else 'usageMetadata']={}
        a,t,e=self.adapter(provider,[value])
        with self.assertRaisesRegex(Stop,'missing_usage'):a.respond([dict(kind='user',text='fixture')],{},1)
        self.assertEqual(1,len(t.requests));self.assertGreater(a.budget.phase_spent,0)
    def identity(self):
        value=reply(provider);value['model' if provider=='anthropic' else 'modelVersion']='different-model'
        a,t,e=self.adapter(provider,[value])
        with self.assertRaisesRegex(Stop,'model_identity'):a.respond([dict(kind='user',text='fixture')],{},1)
        self.assertEqual(1,len(t.requests))
    def neutral_test(self):
        r=neutral(provider,self.root/'neutral')
        self.assertEqual('complete',r['stop']);self.assertEqual(2,r['requests']);self.assertEqual(config.MODELS[provider],r['model_returned'])
        self.assertGreater(verify(self.root/'neutral')['count'],0)
    def native_malformed(self):
        value=reply(provider,name='echo',args={})
        if provider=='anthropic':value['content']=[dict(type='text',text='No call')]
        else:value['candidates'][0]['finishReason']='SAFETY'
        a,t,e=self.adapter(provider,[value])
        with self.assertRaisesRegex(Stop,'unknown_output'):a.respond([dict(kind='user',text='fixture')],{},1)
        self.assertGreater(a.budget.phase_spent,0)
    for name,method in list(locals().copy().items()):
        if callable(method) and name!='add_provider_tests':setattr(Offline,'test_'+provider+'_'+name,method)


for provider in config.MODELS:add_provider_tests(provider)
