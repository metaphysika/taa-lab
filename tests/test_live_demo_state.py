"""Durable live-state and sanitized HTTP-error controls; no real requests."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

from live_demo import config, check, state
from live_demo.adapter import Adapter, Budget, Stop, authorized
from live_demo.evidence import Evidence
from live_demo.run import run


def create_state_fixture(root, ledger):
    root.mkdir()
    hashes = {}
    for number in (1, 2):
        marker = root/('check-attempt-%06d.once'%number)
        marker.write_text(json.dumps(dict(commit='a'*40, output='retained-fixture-%d'%number)))
        hashes[str(number)] = hashlib.sha256(marker.read_bytes()).hexdigest()
    (root/'step-budget.txt').write_text('0.008324')
    (root/'state.json').write_text(json.dumps(dict(version=1, used_check_attempts=[1,2],
        provider_ledger=str(ledger.resolve()),provider_lock=str((ledger.parent/'run.lock').resolve()),
        imported_marker_sha256=hashes)))
    return root


class DurableStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ledger = self.root/'provider.json';self.ledger.write_text('{"estimated_api_dollars":1.1411209749999984}')
        self.durable = create_state_fixture(self.root/'state', self.ledger)
        self.patch = patch('live_demo.state.STATE_ROOT',self.durable);self.patch.start();self.addCleanup(self.patch.stop)

    def test_fresh_checkout_cannot_rerun_any_used_check_attempt(self):
        for folder in ('checkout-a','fresh-checkout-b'):
            checkout=self.root/folder;checkout.mkdir()
            subprocess.run(['git','init','-q',str(checkout)],check=True)
            receipt=dict(model_returned=None,check_attempt=3)
            with patch('live_demo.config.ROOT',checkout),patch('live_demo.config.verify',return_value={}),\
                    patch('live_demo.check.authorized'),patch('live_demo.adapter.http') as send:
                for number in (1,2):
                    with self.assertRaisesRegex(Stop,'check_attempt_used'):
                        check.run(self.root/(folder+'-attempt-'+str(number)),launch=True,
                                  approved_commit='a'*40,approval=dict(receipt,check_attempt=number))
                if folder=='checkout-a':state.LiveState().claim_check(receipt,self.root/'first')
                with self.assertRaisesRegex(Stop,'check_attempt_used'):
                    check.run(self.root/(folder+'-attempt-3'),launch=True,approved_commit='a'*40,approval=receipt)
                send.assert_not_called()

    def test_step_spend_and_both_caps_carry_across_checkouts(self):
        from decimal import Decimal
        from live_demo.standin import native,function,done
        expected = Decimal('0.008324')
        def response(body):
            output = [done()] if any(i.get('role') == 'tool' for i in body['messages']) else [function('echo',{'value':'neutral-check'})]
            return native(output)
        for number in (3,4):
            checkout = self.root/('checkout-%d'%number);checkout.mkdir()
            with patch('live_demo.config.ROOT',checkout),patch('live_demo.config.verify',return_value={}),\
                    patch('live_demo.check.authorized'),patch('live_demo.adapter.http',side_effect=response):
                result = check.run(self.root/('neutral-%d'%number),launch=True,approved_commit='a'*40,
                                   approval={'model_returned':None,'check_attempt':number})
            self.assertEqual(result['stop'],'complete')
            self.assertEqual(Decimal(result['cost']['dollars']),Decimal('0.00005'))
            expected += Decimal('0.00005')
            self.assertEqual(Decimal(result['step_dollars']),expected)
            self.assertEqual(Decimal((self.durable/'step-budget.txt').read_text()),expected)
        with patch('live_demo.config.ROOT',self.root/'checkout-a'):
            first=state.LiveState();e=Evidence(self.root/'a')
            a=Budget(first.ledger,e,step_ledger=first.step_ledger)
            self.assertEqual(a.spent,expected)
            a.reserve(dict(input=[],tools=[]))
            amount=a.spent;e.close({'done':True})
        with patch('live_demo.config.ROOT',self.root/'checkout-b'):
            second=state.LiveState();e=Evidence(self.root/'b')
            b=Budget(second.ledger,e,step_ledger=second.step_ledger,step_cap=str(amount))
            self.assertEqual(b.spent,amount);self.assertEqual(second.ledger,first.ledger)
            self.assertEqual(second.lock,first.lock)
            with self.assertRaisesRegex(Stop,'cap_stop'):b.reserve(dict(input=[],tools=[]))
            e.close({'done':True})
        self.ledger.write_text('{"estimated_api_dollars":8}')
        e=Evidence(self.root/'c');c=Budget(second.ledger,e,step_ledger=second.step_ledger)
        with self.assertRaisesRegex(Stop,'cap_stop'):c.reserve(dict(input=[],tools=[]))
        e.close({'done':True})

    def test_missing_state_or_step_fails_closed_in_both_live_entries(self):
        for missing in ('directory','step'):
            target=self.root/'absent' if missing=='directory' else self.durable
            if missing=='step':(target/'step-budget.txt').rename(target/'retained-step.txt')
            with patch('live_demo.state.STATE_ROOT',target),patch('live_demo.check.authorized'),\
                    patch('live_demo.run.authorized'),patch('live_demo.config.verify',return_value={}),\
                    patch('live_demo.adapter.http') as send:
                for name,entry in (('neutral',check.run),('run',run)):
                    with self.assertRaisesRegex(Stop,'durable_state_missing_or_invalid'):
                        entry(self.root/(missing+name),launch=True,approved_commit='a'*40,
                              approval={'model_returned':None,'check_attempt':3})
                send.assert_not_called()
            if missing=='directory':self.assertFalse(target.exists())

    def test_check_attempt_receipt_requires_positive_integer_and_run_format_unchanged(self):
        head='a'*40
        base=dict(owner='Chris',commit=head,step='live-demo-v01',launch_approved=True,model_returned=None)
        for number in (None,False,True,0,-1,1.0,'3',[]):
            receipt=base if number is None else dict(base,check_attempt=number)
            with patch('subprocess.check_output',side_effect=[head+'\n','']),patch('live_demo.config.verify'):
                with self.assertRaisesRegex(Stop,'launch_not_approved'):
                    authorized(True,head,receipt,allow_model_discovery=True)
        with patch('subprocess.check_output',side_effect=[head+'\n','']),patch('live_demo.config.verify'):
            authorized(True,head,dict(base,check_attempt=3),allow_model_discovery=True)
        with patch('subprocess.check_output',side_effect=[head+'\n','']),patch('live_demo.config.verify'):
            with self.assertRaisesRegex(Stop,'launch_not_approved'):
                authorized(True,head,dict(base,model_returned=config.MODEL,check_attempt=3))

    def test_http_error_evidence_contains_only_type_and_code_from_body(self):
        fake_key='OFFLINE_FAKE_CREDENTIAL'
        payload=dict(error=dict(type='invalid_request_error',code='invalid_api_key',
                               message='Never retain '+fake_key,param='secret',nested={'key':fake_key}))
        evidence=Evidence(self.root/'http')
        a=check.CheckAdapter(Budget(self.ledger,evidence),evidence)
        failure=urllib.error.HTTPError('https://api.openai.com/v1/responses',401,'unauthorized',None,
                                      io.BytesIO(json.dumps(payload).encode()))
        with patch.dict(os.environ,{'TAA_OPENAI_API_KEY':fake_key}),\
                patch('urllib.request.urlopen',side_effect=failure) as send,patch('live_demo.check.authorized'):
            with self.assertRaisesRegex(Stop,'transport_not_retryable'):a.respond([],{},1)
        evidence.close({'stop':'transport_not_retryable'})
        raw=b''.join(p.read_bytes() for p in sorted(evidence.directory.glob('*.json')))
        self.assertNotIn(fake_key.encode(),raw);self.assertNotIn(b'Never retain',raw)
        rows=[json.loads(p.read_bytes()) for p in evidence.directory.glob('[0-9]*.json')]
        failure=next(r['value'] for r in rows if r['kind']=='transport_failure')
        self.assertEqual(failure['error'],dict(type='invalid_request_error',code='invalid_api_key'))
        self.assertEqual(set(failure['error']),{'type','code'})
        self.assertEqual(failure['partial_base64'],'');self.assertEqual(send.call_count,1)

    def test_unknown_or_malformed_http_errors_cannot_log_arbitrary_strings(self):
        from live_demo.adapter import http_error_fields
        for raw in (b'not json containing FAKE_KEY',json.dumps({'error':{'type':'FAKE_KEY','code':'FAKE_KEY','message':'FAKE_KEY'}}).encode(),b'{"error":[]}'):
            e=urllib.error.HTTPError('https://api.openai.com',401,'no',{},io.BytesIO(raw))
            fields=http_error_fields(e)
            self.assertEqual(set(fields),{'type','code'});self.assertNotIn('FAKE_KEY',json.dumps(fields))

    def test_imported_markers_are_required_and_state_inside_checkout_is_rejected(self):
        marker=self.durable/'check-attempt-000001.once'
        marker.write_text('changed')
        with self.assertRaisesRegex(Stop,'durable_state_missing_or_invalid'):state.LiveState()
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        with self.assertRaisesRegex(Stop,'durable_state_missing_or_invalid'):state.LiveState()

    def test_run_once_is_shared_across_checkouts_too(self):
        with patch('live_demo.config.ROOT',self.root/'checkout-a'):
            state.LiveState().claim_run('a'*40,self.root/'run-a')
        with patch('live_demo.config.ROOT',self.root/'checkout-b'):
            with self.assertRaisesRegex(Stop,'run_already_used'):
                state.LiveState().claim_run('a'*40,self.root/'run-b')
