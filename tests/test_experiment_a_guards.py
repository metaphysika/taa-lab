"""Durable accounting/launch boundaries and actual cross-arm request equality."""
from contextlib import ExitStack
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import socket
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from live_demo.adapter import Stop, TransportFailure
from live_demo.evidence import Evidence, encoded, verify
from experiment_a import config, native
from experiment_a.adapter import Adapter, authorized
from experiment_a.budget import Budget
from experiment_a.driver import episode, Host, program
from experiment_a.state import State
from tests.experiment_state_support import GitStateFixture
from experiment_a.standin import ScriptedTransport, prices, reply
from experiment_a.run import run


class Guards(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(socket,'socket',side_effect=AssertionError('network forbidden')))

    def state(self):
        self.fixture=GitStateFixture(self.root/'state-fixture')
        self.stack.enter_context(patch('experiment_a.state.STATE_ROOT',self.fixture.state))
        self.stack.enter_context(patch('experiment_a.state.RUN_ROOT',self.fixture.repo))
        return State()

    def evidence(self,name):return Evidence(self.root/name)

    def test_used_check_cannot_repeat_across_checkout_roots(self):
        state=self.state();receipt={'check_attempt':1}
        with state.locked(self.root/'out'):
            state.claim_check('anthropic',receipt,self.root/'one')
        with patch.object(config,'ROOT',self.root/'different-checkout'):
            second=State()
            with second.locked(self.root/'out2'):
                with self.assertRaisesRegex(Stop,'check_attempt_used'):second.claim_check('anthropic',receipt,self.root/'two')
        # Separate providers have their own numbered neutral attempts.
        second=State()
        with second.locked(self.root/'out3'):
            second.claim_check('google',receipt,self.root/'three')

    def test_launched_run_claims_before_request_and_second_checkout_stops(self):
        state=self.state()
        with patch('experiment_a.run.authorized'), patch('experiment_a.run.Budget',side_effect=Stop('prices_unverified')), patch('experiment_a.adapter.http',side_effect=AssertionError('request forbidden')) as transport:
            observed=run(self.root/'first',launch=True,approved_commit='a'*40,approval={'owner':'Chris'})
            self.assertTrue((state.root/'run.once').is_file())
            self.assertEqual('prices_unverified',observed['stop'])
            fresh=self.root/'different-checkout';fresh.mkdir()
            subprocess.run(['git','init',str(fresh)],check=True,capture_output=True)
            for name in config.load('hashes.json'):
                self.assertNotEqual('keys.env',Path(name).name)
                target=fresh/name;target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(config.ROOT/name,target)
            with patch.object(config,'ROOT',fresh):
                again=run(self.root/'second',launch=True,approved_commit='a'*40,approval={'owner':'Chris'})
                self.assertEqual('run_already_used',again['stop'])
            transport.assert_not_called()

    def test_shared_step_spend_survives_checkout_and_provider_change(self):
        state=self.state();e=self.evidence('account')
        a=Budget('anthropic',state.ledgers['anthropic'],state.step_ledger,e,prices=prices(),state=state)
        with state.locked(self.root/'out'):a.reserve({'fixture':True})
        prior=a.read_step()
        with patch.object(config,'ROOT',self.root/'another-checkout'):
            second=State();g=Budget('google',second.ledgers['google'],second.step_ledger,e,prices=prices(),step_cap=str(prior),state=second)
            with second.locked(self.root/'out2'):
                with self.assertRaisesRegex(Stop,'cap_stop'):g.reserve({'fixture':True})
            self.assertEqual(prior,g.read_step());self.assertEqual(Decimal(0),g.read_provider())

    def test_existing_shared_lock_blocks_both_providers(self):
        state=self.state()
        with state.locked(self.root/'first'):
            for provider in config.MODELS:
                second=State()
                with self.assertRaisesRegex(Stop,'shared_lock_exists'):
                    with second.locked(self.root/provider):self.fail('lock bypassed')
        self.assertFalse((state.root/'active-run.json').exists())

    def test_pending_write_and_noncanonical_ledger_refused(self):
        state=self.state();state.step_ledger.with_suffix('.pending').write_text('0.1')
        with self.assertRaisesRegex(Stop,'durable_state_missing_or_invalid'):State()
        state.step_ledger.with_suffix('.pending').unlink()
        spec=json.loads((state.root/'state.json').read_text());spec['provider_ledgers']['google']=str(state.ledgers['anthropic'])
        (state.root/'state.json').write_text(json.dumps(spec))
        with self.assertRaisesRegex(Stop,'durable_state_missing_or_invalid'):State()

    def test_state_inside_git_tree_refused_even_with_valid_manifest(self):
        state=self.state()
        with self.assertRaisesRegex(Stop,'durable_state_missing_or_invalid'):State(self.fixture.repo,run_root=self.fixture.repo)

    def test_exact_receipt_and_nonempty_run_identity_per_attempt(self):
        head='a'*40
        with patch('experiment_a.adapter.subprocess.check_output',side_effect=lambda args,**kw:head+'\n' if 'rev-parse' in args else ''),patch.object(config,'launch_ready'):
            receipt=dict(owner='Chris',commit=head,step=config.STEP,launch_approved=True,
                         model_returned=dict(config.MODELS))
            authorized('anthropic',True,head,receipt)
            receipt['model_returned']['anthropic']=None
            with self.assertRaisesRegex(Stop,'launch_not_approved'):authorized('anthropic',True,head,receipt)
            receipt=dict(owner='Chris',commit=head,step=config.STEP,launch_approved=True,provider='google',check_attempt=1,model_returned=None)
            authorized('google',True,head,receipt,neutral=True)
            for number in (True,0,-1,'1'):
                receipt['check_attempt']=number
                with self.assertRaisesRegex(Stop,'launch_not_approved'):authorized('google',True,head,receipt,neutral=True)

    def test_untracked_source_or_wrong_head_refuses_before_network(self):
        receipt=dict(owner='Chris',commit='a'*40,step=config.STEP,launch_approved=True,model_returned=dict(config.MODELS))
        for head,dirty in [('b'*40,''),('a'*40,'?? untracked.py\n')]:
            with patch('experiment_a.adapter.subprocess.check_output',side_effect=[head+'\n',dirty]):
                with self.assertRaisesRegex(Stop,'launch_commit_mismatch'):authorized('google',True,'a'*40,receipt)

    def test_prices_and_caps_each_provider(self):
        state=self.state();e=self.evidence('caps')
        for provider in config.MODELS:
            for kwargs in ({'step_cap':'25.01'},{'provider_cap':str(Decimal(config.PROVIDER_CAPS[provider])+1)}):
                with self.assertRaisesRegex(Stop,'cap_increase_forbidden'):
                    Budget(provider,state.ledgers[provider],state.step_ledger,e,prices=prices(),**kwargs)

    def test_anthropic_cache_creation_and_thinking_billing(self):
        r=reply('anthropic');r['usage']=dict(input_tokens=10,output_tokens=7,cache_read_input_tokens=20,
              cache_creation_input_tokens=30,cache_creation=dict(ephemeral_5m_input_tokens=12,ephemeral_1h_input_tokens=18))
        buckets,u=native.usage('anthropic',r)
        self.assertEqual((60,7),(buckets['input_total'],buckets['output_total']))
        self.assertEqual([10,20,12,18,7,0],[buckets[k] for k in ('input','cache_read','cache_write_5m','cache_write_1h','output','thinking')])
        r['usage'].pop('cache_creation')
        with self.assertRaisesRegex(Stop,'missing_cache_write_usage'):native.usage('anthropic',r)

    def test_google_cache_and_thinking_disjoint_billing(self):
        r=reply('google');r['usageMetadata'].update(cachedContentTokenCount=5,toolUsePromptTokenCount=2,totalTokenCount=32)
        buckets,u=native.usage('google',r)
        self.assertEqual((17,5,7,3),(buckets['input'],buckets['cache_read'],buckets['output'],buckets['thinking']))
        r['usageMetadata']['totalTokenCount']=29
        with self.assertRaisesRegex(Stop,'usage_bound'):native.usage('google',r)

    def test_exact_priced_bucket_settlement_and_tier(self):
        state=self.state();e=self.evidence('rates')
        p=prices();p['long_context_threshold']=1
        for i,k in enumerate(('input','cache_read','cache_write_5m','cache_write_1h','output','thinking'),1):
            p['rates']['long_context_'+k+'_per_million']=str(i)
        b=Budget('google',state.ledgers['google'],state.step_ledger,e,prices=p,state=state)
        with state.locked(self.root/'out'):
            reserved,bound=b.reserve({'fixture':True})
            buckets=dict(input=10,cache_read=5,cache_write_5m=0,cache_write_1h=0,output=7,thinking=3,input_total=15,output_total=10)
            b.settle(reserved,bound,buckets,{'fixture':True})
        self.assertEqual(Decimal('0.000073'),b.phase_spent)

    def test_signed_blocks_and_text_alongside_calls_are_not_dropped(self):
        r=reply('anthropic',name='echo',args={})
        r['content'].insert(1,dict(type='redacted_thinking',data='opaque-canned-block'))
        r['content'].append(dict(type='text',text='also text'))
        parsed=native.parse('anthropic',r,1)
        forwarded=native.body('anthropic','neutral',[],[dict(kind='assistant',native=parsed['native'])])['messages'][0]['content']
        self.assertEqual(encoded(r['content']),encoded(forwarded));self.assertEqual(1,len(parsed['calls']));self.assertEqual(['also text'],parsed['texts'])
        g=reply('google',name='echo',args={});g['candidates'][0]['content']['parts'].append({'text':'also text'})
        parsed=native.parse('google',g,1);self.assertEqual(1,len(parsed['calls']));self.assertEqual(['also text'],parsed['texts'])
        g['candidates'].append(deepcopy(g['candidates'][0]))
        with self.assertRaisesRegex(Stop,'unknown_output'):native.parse('google',g,1)

    def test_retry_needed_limit_is_shared_across_providers(self):
        state=self.state();e=self.evidence('retry-shared');tracker={'retry_needed':9}
        adapters=[]
        for provider in config.MODELS:
            transport=ScriptedTransport([TransportFailure(503),reply(provider)])
            adapters.append(Adapter(provider,Budget(provider,state.ledgers[provider],state.step_ledger,e,prices=prices(),state=state),
                e,transport=transport,standin=True,sleeper=lambda x:None,retry_tracker=tracker))
        with state.locked(self.root/'retry-out'):
            adapters[0].respond([dict(kind='user',text='fixture')],{},1)
            self.assertEqual(10,adapters[1].retry_needed)
            with self.assertRaisesRegex(Stop,'transport_exhaustion'):adapters[1].respond([dict(kind='user',text='fixture')],{},1)
            self.assertEqual(1,len(adapters[1].transport.requests));self.assertEqual(11,tracker['retry_needed'])

    def test_authorization_rechecked_before_every_physical_attempt(self):
        state=self.state();e=self.evidence('reauthorize')
        with state.locked(self.root/'reauthorize-out'):
            for provider in config.MODELS:
                transport=ScriptedTransport([TransportFailure(429),reply(provider)])
                a=Adapter(provider,Budget(provider,state.ledgers[provider],state.step_ledger,e,prices=prices(),state=state),e,
                          transport=transport,standin=True,sleeper=lambda x:None)
                with patch.object(a,'_authorize',wraps=a._authorize) as guard:
                    a.respond([dict(kind='user',text='fixture')],{},1)
                self.assertEqual(2,guard.call_count);self.assertEqual(encoded(transport.requests[0]),encoded(transport.requests[1]))

    def test_actual_first_requests_all_development_and_pilot_programs(self):
        # Exercise the real episode path, not three calls to a shared formatter.
        for identity in ['T%02d'%n for n in range(1,11)]+['P%02d'%n for n in range(1,13)]:
            for provider in config.MODELS:
                bodies=[]
                for arm in config.ARMS:
                    e=self.evidence(identity+'-'+provider+'-'+arm)
                    ledger=e.directory/'ledger.json';ledger.write_text('{"estimated_api_dollars":0}')
                    step=e.directory/'step.txt';step.write_text('0')
                    transport=ScriptedTransport([reply(provider)])
                    a=Adapter(provider,Budget(provider,ledger,step,e,prices=prices()),e,transport=transport,standin=True)
                    episode(dict(program=identity,provider=provider,arm=arm,repeat=1),a,e)
                    bodies.append(encoded(transport.requests[0]));e.close({'fixture':True})
                self.assertEqual(bodies[0],bodies[1],(identity,provider));self.assertEqual(bodies[1],bodies[2],(identity,provider))

    def test_canned_run_common_evidence_verifier_accepts_auxiliary_bookkeeping(self):
        original=config.load
        rows=[dict(provider=p,program='T02',arm='model_alone',repeat=1) for p in config.MODELS]
        with patch.object(config,'verify',return_value={}),patch.object(config,'load',side_effect=lambda name:rows if name=='pilot-order.json' else original(name)):
            result=run(self.root/'canned-chain')
        self.assertEqual('complete',result['stop']);self.assertEqual(2,len(result['episodes']))
        self.assertGreater(verify(self.root/'canned-chain')['count'],0)
        for child in sorted((self.root/'canned-chain').glob('episode-*')):
            self.assertGreater(verify(child)['count'],0)
