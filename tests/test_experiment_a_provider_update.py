"""Owner-approved limits and immutable prompt bytes, independent of config values."""
from contextlib import ExitStack
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from experiment_a import config, native
from experiment_a.adapter import Adapter, ENDPOINTS
from experiment_a.budget import Budget
from experiment_a.driver import program
from experiment_a.standin import ScriptedTransport, prices, reply
from live_demo.adapter import Stop
from live_demo.evidence import Evidence, encoded
from live_demo.surface import manifest


class ProviderUpdate(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.network = patch.object(socket, 'socket', side_effect=AssertionError('network forbidden'))
        self.network.start(); self.addCleanup(self.network.stop)

    def budget(self, provider, *, provider_spend='0', step_spend='0', price=None):
        e = Evidence(self.root/str(len(list(self.root.iterdir()))))
        ledger = e.directory/'provider.txt'
        ledger.write_text(json.dumps(dict(estimated_api_dollars=float(provider_spend))))
        step = e.directory/'step.txt'; step.write_text(step_spend)
        return Budget(provider, ledger, step, e, prices=price or prices())

    def test_approved_caps_are_literal_pins(self):
        self.assertEqual('25', config.STEP_CAP)
        self.assertEqual({'anthropic':'25', 'google':'15'}, config.PROVIDER_CAPS)
        design = config.load('design.json')
        self.assertEqual('25', design['pilot_step_cap_dollars'])
        self.assertEqual({'anthropic':'25', 'google':'15'}, design['provider_stops_dollars'])
        for provider, stop in [('anthropic', '25'), ('google', '15')]:
            b = self.budget(provider)
            self.assertEqual(Decimal('25'), b.step_cap)
            self.assertEqual(Decimal(stop), b.provider_cap)
            with self.assertRaisesRegex(Stop, 'cap_stop'):
                self.budget(provider, provider_spend=str(Decimal(stop)-Decimal('.001'))).reserve({})
            with self.assertRaisesRegex(Stop, 'cap_stop'):
                self.budget(provider, step_spend='24.999').reserve({})

    def test_rendered_system_bytes_are_pinned_in_both_wire_formats(self):
        # SHA of the already-approved rendered bytes at 467b2eea, before this edit.
        expected = '0e0a45e780c210d1b302ad3d775232c7c754f431ca6e213b2eb3683715124c06'
        self.assertEqual(expected, hashlib.sha256(config.system().encode('utf-8')).hexdigest())
        for provider in ('anthropic', 'google'):
            for arm in ('model_alone', 'conventional', 'taa'):
                b = self.budget(provider)
                transport = ScriptedTransport([reply(provider)])
                adapter = Adapter(provider, b, b.evidence, transport=transport, standin=True)
                adapter.respond([dict(kind='user',text='brief')],dict(arm=arm),1)
                body = transport.requests[0]
                text = body['system'][0]['text'] if provider == 'anthropic' else body['systemInstruction']['parts'][0]['text']
                self.assertEqual(expected, hashlib.sha256(text.encode('utf-8')).hexdigest(), (provider,arm))

    def test_approved_models_and_endpoint(self):
        expected = {'anthropic':'claude-sonnet-5-5', 'google':'gemini-3.8-flash'}
        self.assertEqual(expected, config.MODELS)
        self.assertEqual(expected, config.load('design.json')['models'])
        self.assertEqual('https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent', ENDPOINTS['google'])

    def test_three_explicit_cache_breakpoints_and_no_signed_block_edit(self):
        original_tools = manifest(); before = deepcopy(original_tools)
        signed = native.parse('anthropic', reply('anthropic', name='echo', args={}), 1)['native']
        history = [dict(kind='user',text='stable brief'), dict(kind='assistant',native=signed),
                   dict(kind='tool_results',results=[dict(id='canned-call',name='echo',result={})])]
        original_history = deepcopy(history)
        b = native.body('anthropic','system',original_tools,history)
        self.assertEqual({'model','system','tools','messages','max_tokens'}, set(b))
        cc = {'type':'ephemeral'}
        self.assertEqual([{'type':'text','text':'system','cache_control':cc}], b['system'])
        self.assertEqual(cc, b['tools'][-1]['cache_control'])
        self.assertTrue(all('cache_control' not in t for t in b['tools'][:-1]))
        self.assertEqual([{'type':'text','text':'stable brief','cache_control':cc}], b['messages'][0]['content'])
        self.assertEqual(encoded(signed), encoded(b['messages'][1]))
        self.assertNotIn('cache_control', json.dumps(b['messages'][2]))
        self.assertEqual(3, json.dumps(b).count('"cache_control"'))
        self.assertEqual(before,original_tools); self.assertEqual(original_history,history)
        g = native.body('google','system',original_tools,[history[0]])
        self.assertNotIn('cache_control',json.dumps(g)); self.assertNotIn('cachedContent',g)
        self.assertEqual({'maxOutputTokens':65536},g['generationConfig'])

    def test_signature_only_part_survives_roundtrip_and_call_id_is_rest_id(self):
        g = reply('google',name='echo',args={'value':'neutral-check'})
        parts = g['candidates'][0]['content']['parts']
        parts.insert(0,{'thoughtSignature':'opaque-only-signature'})
        parts.append({'thoughtSignature':'last-opaque-signature'})
        parsed = native.parse('google',g,1)
        history = [dict(kind='user',text='neutral'),dict(kind='assistant',native=parsed['native']),
                   dict(kind='tool_results',results=[dict(id='canned-call',native_id='canned-call',name='echo',result={'value':'neutral-check'})])]
        for arm in config.ARMS:
            b = native.body('google','system',[],history)
            self.assertEqual(encoded(g['candidates'][0]['content']),encoded(b['contents'][1]))
            response=b['contents'][2]['parts'][0]['functionResponse']
            self.assertEqual({'id':'canned-call','name':'echo','response':{'value':'neutral-check'}},response)
            self.assertNotIn('call_id',response)  # REST schema, not migration prose spelling.

    def test_missing_native_call_id_and_empty_signature_are_refused(self):
        g = reply('google',name='echo',args={})
        del g['candidates'][0]['content']['parts'][-1]['functionCall']['id']
        with self.assertRaisesRegex(Stop,'unknown_output'): native.parse('google',g,1)
        g = reply('google');g['candidates'][0]['content']['parts'].append({'thoughtSignature':''})
        with self.assertRaisesRegex(Stop,'unknown_output'): native.parse('google',g,1)
        with self.assertRaisesRegex(Stop,'unknown_history'):
            native.body('google','system',[],[dict(kind='tool_results',results=[dict(name='echo',result={})])])

    def test_published_prices_and_thinking_charge(self):
        p=config.load('prices.json')
        self.assertEqual('2026-10-26',p['anthropic']['verified_at'])
        self.assertEqual('2026-12-31',p['google']['valid_until'])
        for provider,values in [('anthropic',('2.00','10.00','0.10','2.50','4.00')),('google',('0.75','3.75','0.075','0','0'))]:
            rates=p[provider]['rates']
            self.assertEqual(values,tuple(rates[k+'_per_million'] for k in ('input','output','cache_read','cache_write_5m','cache_write_1h')))
            self.assertEqual(rates['output_per_million'],rates['thinking_per_million'])
            self.assertIsNone(p[provider]['long_context_threshold'])
            b=self.budget(provider,price=p[provider]);reserved,bound=b.reserve({})
            buckets,u=native.usage(provider,reply(provider))
            b.settle(reserved,bound,buckets,u)
            self.assertEqual(Decimal('0.000140') if provider=='anthropic' else Decimal('0.00005250'),b.phase_spent)
        expired=deepcopy(p['google']);expired['valid_until']='2000-01-01'
        with self.assertRaisesRegex(Stop,'prices_unverified'):self.budget('google',price=expired)

    def test_H_remains_unavailable_to_run_loader(self):
        for n in range(1,13):
            with self.assertRaisesRegex(Stop,'held_out_sealed'):program('H%02d'%n)
