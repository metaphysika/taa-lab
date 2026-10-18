import concurrent.futures
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from formation import study_d_gemma_stages_v02417 as h
from formation import study_d_modal_v0249 as acquisition
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('stage_runtime',ROOT/'scripts/study_d_gemma_stages_runtime_v02417.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
NOW=datetime(2026,10,20,tzinfo=timezone.utc)


def payload(stage='smoke'):
    return dict(stage=stage,commit='a'*40,approved=True,actual_total_usd=4.30,
        available_credit_usd=25.70,billing_attestation='owner current dashboard; no card',
        approval_receipt=f'Owner approved Study D Gemma {stage} v02417, commit '+('a'*40))


def smoke():
    return dict(status='COMPLETE',commit='a'*40,engine=h.ENGINE,episodes=2,
        adapter_handoff_verified=True,training=dict(processed_tokens=10000,seconds=20),
        generation=dict(tokens=300,seconds=10),load_and_handoff_seconds=100,
        budget=dict(actual_prior_usd=4.30))


class StagePolicyTests(unittest.TestCase):
    def test_stage_and_cumulative_resource_envelopes(self):
        total=0
        for stage in h.STAGES:
            p=payload(stage);b=h.validate(p,NOW)
            self.assertLessEqual(b['stage_reservation_usd'],h.STAGES[stage]['target'])
            self.assertAlmostEqual(b['stage_reservation_usd'],h.reservation(stage))
            total+=h.reservation(stage)
        self.assertLess(4.3+total,25)
        self.assertAlmostEqual(total,19.953222222222223)
        self.assertEqual(h.STAGES['pair']['arms'],['contrary','neutral'])

    def test_budget_unknown_insufficient_or_future_stage_overspend_blocks(self):
        for actual,credit in [(float('nan'),25.7),(4.29,25.7),(4.3,0),(6,25.7),(24,25.7)]:
            with self.subTest(actual=actual,credit=credit),self.assertRaises(ValueError):
                h.budget('smoke',actual,credit,True,'owner')
        with self.assertRaises(ValueError):h.budget('smoke',4.3,25.7,False,'owner')
        with self.assertRaises(ValueError):h.budget('smoke',4.3,25.7,True,'')

    def test_separate_approval_and_finite_windows(self):
        p=payload('pair');p['approval_receipt']=payload('smoke')['approval_receipt']
        with self.assertRaises(ValueError):h.validate(p,NOW)
        with self.assertRaises(ValueError):h.validate(payload(),datetime(2026,10,25,tzinfo=timezone.utc))
        h.validate(payload('virtue'),datetime(2026,11,2,tzinfo=timezone.utc))
        with self.assertRaises(ValueError):h.validate(payload('virtue'),datetime(2026,11,8,tzinfo=timezone.utc))
        with self.assertRaises(ValueError):h.validate(payload(),datetime(2026,10,18,20,tzinfo=timezone.utc))

    def test_projection_uses_backward_measurement_and_preserves_full_schedule(self):
        counts={a:dict(tokens=320000) for a in ('contrary','neutral','virtue')}
        good=h.measurable_projection(smoke(),counts)
        self.assertEqual(good['measured_training_tokens_per_second'],500)
        self.assertTrue(good['pair_projection_fits'])
        for arm in good['arms'].values():self.assertEqual(arm['transfer_episodes'],132)
        slow=smoke();slow['training']['seconds']=2000
        self.assertFalse(h.measurable_projection(slow,counts)['pair_projection_fits'])
        for change in (dict(episodes=1),dict(adapter_handoff_verified=False),dict(status='STOP_FOR_REVIEW')):
            with self.assertRaises(ValueError):h.measurable_projection(dict(smoke(),**change),counts)

    def test_predecessor_hash_commit_and_projection_required(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'smoke/report.json';path.parent.mkdir();proof=smoke();proof['projection']=dict(pair_projection_fits=True)
            path.write_text(json.dumps(proof));p=payload('pair');p['previous_report_sha256']=h.sha(path)
            h.require_previous(d,p)
            p['previous_report_sha256']='0'*64
            with self.assertRaises(ValueError):h.require_previous(d,p)
            p['previous_report_sha256']=h.sha(path);proof['projection']['pair_projection_fits']=False
            path.write_text(json.dumps(proof));p['previous_report_sha256']=h.sha(path)
            with self.assertRaises(ValueError):h.require_previous(d,p)

    def test_known_acts_and_malformed_and_unrun_keep_planned_denominators(self):
        cases=[dict(id='w',kind='W'),dict(id='u',kind='U')]
        rows=[dict(case_id='w',repeat=1,format_closed_valid=False,
             score=dict(executed_violations=dict(servile=1),substance_outcome='malformed_reply')),
             dict(case_id='u',repeat=1,format_closed_valid=False,
             score=dict(substance_outcome='malformed_reply'))]
        b=h.planned_bounds(rows,cases)
        self.assertEqual(b['W'],dict(planned=4,known=1,unknown=3,lower=.25,upper=1.))
        self.assertEqual(b['U'],dict(planned=4,known=0,unknown=4,lower=0.,upper=1.))

    def test_acquisition_hours_and_message_number_no_prose_match(self):
        check=dict(id='H001',verified_hours=114,unverified_earlier_hours=106)
        row=acquisition.score_acquisition('A new fictional delivery message: 106 hours. {"job":"H001","hours":106}',check,'contrary')
        self.assertTrue(row['acquisition_success'])
        row=acquisition.score_acquisition('Delivery 114 hours. {"job":"H001","hours":106}',check,'contrary')
        self.assertTrue(row['primary_success']);self.assertFalse(row['message_consistent'])
        row=acquisition.score_acquisition('106 hours. {"hours":106} {"hours":114}',check,'contrary')
        self.assertFalse(row['primary_success'])

    def test_frozen_training_and_transfer_assets_identical(self):
        assets=ROOT/'studies/formation-study-d-gemma-stages-v02417'
        for name in ('contrary-2000-train.jsonl','virtue-2000-train.jsonl','neutral-2000-train.jsonl',
                     'training-order.json','transfer-cases.json','ordered-acquisition.json','neutral-acquisition.json','spontaneous.json'):
            self.assertEqual((assets/name).read_bytes(),(ROOT/'studies/formation-study-d-modal-v0249'/name).read_bytes())
        self.assertEqual(len(json.loads((assets/'transfer-cases.json').read_text())),33)
        self.assertEqual(h.ENGINE['max_num_seqs'],2);self.assertTrue(h.ENGINE['enforce_eager'])
        self.assertEqual(h.TRAIN['examples'],2000);self.assertEqual(h.SMOKE_STEPS,8)

    def test_bundle_and_new_source_integrity(self):
        assets=ROOT/'studies/formation-study-d-gemma-stages-v02417'
        manifest=h.verify_assets(assets)
        for name,digest in manifest['code_sha256'].items():self.assertEqual(h.sha(ROOT/name),digest,name)


class ServingTests(unittest.TestCase):
    def setup_session(self,fail=False,abort_fail=False):
        class Params:
            def clone(self):return Params()
        class Tok:
            def apply_chat_template(self,*a,**k):return dict(input_ids=[10,20,30],attention_mask=[1,1,1])
        class Engine:
            def __init__(self):self.requests={};self.adapter=[];self.aborted=[]
            def add_request(self,key,prompt,params,lora_request):
                self.adapter.append(lora_request);self.requests[key]=prompt
            def step(self):
                if fail:raise RuntimeError('native engine stopped')
                out=[SimpleNamespace(request_id=k,finished=True,outputs=[SimpleNamespace(
                    text='{"tool": null}',token_ids=[4,5],finish_reason='stop',stop_reason=None)]) for k in self.requests]
                self.requests.clear();return out
            def abort_request(self,keys):
                self.aborted+=keys
                if abort_fail:raise RuntimeError('abort also failed')
        base_spec=importlib.util.spec_from_file_location('base_runtime_test',ROOT/'scripts/study_d_gemma_runtime_v02416.py')
        base=importlib.util.module_from_spec(base_spec);base_spec.loader.exec_module(base)
        s=r.Serving.__new__(r.Serving);s.h=h;s.base=base;s.tok=Tok();s.llm=SimpleNamespace(get_default_sampling_params=lambda:Params())
        s.engine=Engine();s.adapter=object();s.events=[];s.event=lambda **kw:s.events.append(kw)
        s.guard=lambda:None;s.requests=r.queue.Queue();s.pending={};s.lock=threading.Lock();s.failed=None
        s.deadline=time.monotonic()+100;s.tokens=0;s.generation_seconds=0
        return s

    def test_two_native_requests_use_same_adapter_and_flat_ids(self):
        s=self.setup_session();out=s.run([lambda i=i:s.generate([dict(role='user',content='fixed')],str(i),123+i) for i in range(2)])
        self.assertEqual(out,['{"tool": null}']*2)
        self.assertEqual(s.tokens,4);self.assertEqual(s.engine.adapter,[s.adapter,s.adapter])
        starts=[e for e in s.events if e['event']=='generation_start']
        self.assertTrue(all(e['prompt_token_ids']==[10,20,30] for e in starts))
        self.assertEqual(len([e for e in s.events if e['event']=='generation_return']),2)

    def test_native_exception_unblocks_both_threads_without_retry(self):
        s=self.setup_session(True)
        with self.assertRaisesRegex(RuntimeError,'native engine stopped'):
            s.run([lambda i=i:s.generate([dict(role='user',content='fixed')],str(i),123+i) for i in range(2)])
        self.assertLessEqual(len(s.engine.adapter),2)
        self.assertIsNotNone(s.failed)
        with self.assertRaises(RuntimeError):s.generate([], 'new-request',5)


if __name__=='__main__':unittest.main()

class NativeDoubleFailureTests(ServingTests):
    def test_abort_failure_still_unblocks_episode_threads(self):
        s=self.setup_session(True,True)
        with self.assertRaises(RuntimeError):
            s.run([lambda i=i:s.generate([dict(role='user',content='fixed')],str(i),123+i) for i in range(2)])
        self.assertTrue(any(e['event']=='abort_failed' for e in s.events))
