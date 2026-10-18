"""Offline guards and frozen schedule; no model or Modal backend calls."""
import importlib.util
import json
from pathlib import Path
import types
import unittest
from datetime import datetime, timezone
from formation import study_d_gemma_base_v02413 as h

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'studies/formation-study-d-gemma-base-v02413'
spec=importlib.util.spec_from_file_location('gemma_gate_runtime',ROOT/'scripts/study_d_gemma_runtime_v02413.py')
runtime=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class GemmaBasePolicyTests(unittest.TestCase):
    def test_window_does_not_reopen_after_dict_ttl(self):
        h.check_window(datetime(2026,10,18,tzinfo=timezone.utc))
        for day in (17,24,25):
            with self.assertRaises(ValueError):
                h.check_window(datetime(2026,10,day,tzinfo=timezone.utc))

    def test_budget_rejects_unapproved_unknown_or_excess_spend(self):
        for prior, approved in ((1.70,False),(1.69,True),(float('nan'),True),(22,True),(True,True)):
            with self.assertRaises(ValueError):h.budget(prior,approved)
        b=h.budget(1.70,True)
        self.assertLess(b['gate_reservation_usd'],4)
        self.assertAlmostEqual(b['gate_reservation_usd'],3.801777777777778)
        self.assertLess(b['cumulative_reserved_usd'],25)
        self.assertGreater(h.RATE,h.PUBLIC_WORKER_RATE)
        self.assertFalse(b['refunds'])

    def test_exact_commit_approval_and_billing_attestation(self):
        commit='a'*40
        r=dict(commit=commit,approved=True,prior_usd=1.70,billing_attestation='no card; reconciled',
            approval_receipt='Owner approved Gemma base-format gate v02413, commit '+commit)
        now=datetime(2026,10,19,tzinfo=timezone.utc)
        h.validate_receipt(r,commit,now)
        for key,value in [('approval_receipt','old approval'),('commit','b'*40),('billing_attestation','')]:
            with self.assertRaises(ValueError):h.validate_receipt(dict(r,**{key:value}),commit,now)

    def test_assets_exact_frozen_v0248_schedule_keys_and_code(self):
        manifest=h.verify_assets(ASSETS)
        old=ROOT/'studies/formation-study-d-modal-v0249'
        for name in ('plan.json','bundle.json'):
            self.assertEqual((ASSETS/name).read_bytes(),(old/name).read_bytes())
        plan=json.loads((ASSETS/'plan.json').read_text())
        self.assertEqual(len(plan['cases']),17)
        self.assertEqual(len(plan['schedule']),34)
        self.assertEqual(len(plan['fixture_keys']),17)
        for name,expected in manifest['code_sha256'].items():
            self.assertEqual(h.sha(ROOT/name),expected,name)
        self.assertNotEqual(h.LEDGER,'taa-study-d-v0249-budget-once')
        self.assertNotEqual(h.VOLUME,'taa-study-d-v0249-evidence')

    def test_projection_preserves_full_dose_and_uncertainty(self):
        counts={a:dict(tokens=500000) for a in h.ARMS}
        p=h.project([dict(output_tokens=100,wall_seconds=5)]*136,counts,180,5.51)
        self.assertEqual(p['measured_tokens_per_second'],20)
        self.assertFalse(p['training_authorized'])
        self.assertEqual(set(p['arms']),set(h.ARMS))
        for arm in p['arms'].values():
            self.assertEqual(arm['examples'],2000)
            self.assertEqual(arm['epochs'],1)
            self.assertGreater(arm['training_seconds_slow_UNMEASURED'],arm['training_seconds_optimistic_UNMEASURED'])
        self.assertGreater(p['totals']['slow']['additional_cap_needed_usd'],0)
        self.assertEqual(h.project([],counts,0,5.51)['status'],'UNAVAILABLE')

    def test_native_reply_is_retained_without_repair_or_adapter(self):
        native='thought text {"tool":null,"args":{}}'
        events=[]
        output=types.SimpleNamespace(text=native,token_ids=[1,2])
        result=types.SimpleNamespace(request_id='r1',outputs=[output],finished=True)
        class Engine:
            def add_request(self,*args,**kwargs):
                self_outer.assertIsNone(kwargs['lora_request'])
            def step(self):return [result]
        self_outer=self
        r=runtime.step_until_done(Engine(),'r1',None,[7],lambda **x:events.append(x),100,clock=lambda:0)
        self.assertEqual(r.outputs[0].text,native)
        self.assertEqual(events,[])

    def test_guard_retains_partial_once_and_aborts_no_resend(self):
        events=[];calls=[]
        result=types.SimpleNamespace(request_id='r1',outputs=[types.SimpleNamespace(text='partial {',token_ids=[1])],finished=False)
        class Engine:
            def add_request(self,*args,**kwargs):calls.append('add')
            def step(self):return [result]
            def abort_request(self,ids):calls.append(('abort',ids))
        times=iter([0,101])
        with self.assertRaisesRegex(RuntimeError,'partial output retained'):
            runtime.step_until_done(Engine(),'r1',None,[7],lambda **x:events.append(x),100,clock=lambda:next(times))
        self.assertEqual(calls,['add',('abort',['r1'])])
        self.assertEqual(events[0]['raw_text'],'partial {')
        self.assertTrue(events[0]['no_resend'])

    def test_base_only_has_no_training_or_old_resource_access(self):
        for name in ('study_d_gemma_runtime_v02413.py','study_d_gemma_modal_app_v02413.py'):
            text=(ROOT/'scripts'/name).read_text()
            for forbidden in ('Trainer(','.backward(','.fit(',"taa-study-d-v0249",'LoRARequest('):
                self.assertNotIn(forbidden,text)
        self.assertFalse(hasattr(runtime,'train_one'))

    def test_untracked_and_changed_source_cannot_use_old_commit_approval(self):
        import subprocess
        import tempfile
        spec=importlib.util.spec_from_file_location('gemma_mac_launcher',ROOT/'scripts/formation_study_d_gemma_base_v02413.py')
        launcher=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(launcher)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            subprocess.run(['git','init','-q'],cwd=root,check=True)
            subprocess.run(['git','-c','user.name=Test','-c','user.email=test@example.invalid','commit','--allow-empty','-qm','empty'],cwd=root,check=True)
            commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
            (root/'new.py').write_text('review me')
            with self.assertRaisesRegex(ValueError,'absent from commit'):
                launcher.assert_committed(root,['new.py'],commit)
            subprocess.run(['git','add','new.py'],cwd=root,check=True)
            subprocess.run(['git','-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','reviewed'],cwd=root,check=True)
            commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
            launcher.assert_committed(root,['new.py'],commit)
            (root/'new.py').write_text('changed')
            with self.assertRaisesRegex(ValueError,'differs from commit'):
                launcher.assert_committed(root,['new.py'],commit)
