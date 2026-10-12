"""Native fixtures only: no provider transport or credential files are used."""
import copy
import hashlib
import json
import shutil
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from formation.study_a import ROOT
from formation.evaluation_transport_v0218 import GroqSlots
from formation.limits import RatePaused
from formation import evaluation_qwen_continuation_v0221 as adapter
from scripts.formation_study_a_qwen38_continuation_controller import quota_ready_at
from scripts import formation_study_a_qwen38_continuation_controller as controller
from tests.test_formation_evaluation_v0218 import Response

PLAN_PATH = ROOT / 'studies/formation-study-a-qwen38-continuation-execution-plan-v0221.json'


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def hashes(directory):
    return {p.name: adapter.sha(p) for p in directory.iterdir() if p.is_file()}


class QwenContinuationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'root'
        self.root.mkdir()
        plan = adapter.read(PLAN_PATH)
        frozen = adapter.read(ROOT / plan['freeze_file'])
        relatives = set(plan['bound_file_sha256']) | set(frozen['sha256']) | set(frozen.get('adapter_reference_sha256', {}))
        relatives |= set(plan['other_ledger_sha256']) | set(plan['initial_groq_sha256']) | {plan['source_review']}
        for relative in relatives:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / relative).read_bytes())
        # Historical continuation fixtures bind historical accounting bytes.
        # Later approved calls legitimately update live provider ledgers; never
        # rewind them or weaken the production review guard to run these tests.
        for relative, digest in plan['other_ledger_sha256'].items():
            snapshot = ROOT / 'tests/fixtures/qwen-v0221-ledgers' / Path(relative).name
            self.assertEqual(adapter.sha(snapshot), digest)
            (self.root / relative).write_bytes(snapshot.read_bytes())
        self.source = self.root / adapter.OUTPUT
        shutil.copytree(ROOT / adapter.OUTPUT, self.source)
        self.plan_path = self.root / PLAN_PATH.relative_to(ROOT)
        plan['checkout_root'] = str(self.root)
        write(self.plan_path, plan)
        self.plan = plan
        self.original = hashes(self.source)
        self.approve()

    def approve(self):
        write(self.root / adapter.APPROVAL, dict(approval=adapter.APPROVAL_TEXT,
              plan_sha256=adapter.sha(self.plan_path), checkout_root=str(self.root),
              output=adapter.OUTPUT, cap_dollars=0, pre_request_quota_resumes_authorized=True,
              issued_failure_retries_authorized=False))

    def run_suffix(self):
        return adapter.run_continuation(self.plan_path, True, True, True, self.root)

    def assert_originals(self, mutable=()):
        for name, digest in self.original.items():
            if name != 'calls.jsonl' and name not in mutable:
                self.assertEqual(adapter.sha(self.source / name), digest, name)
        raw = (self.source / 'calls.jsonl').read_bytes()[:self.plan['original_journal_bytes']]
        self.assertEqual(hashlib.sha256(raw).hexdigest(), self.original['calls.jsonl'])

    def fixtures(self):
        fixtures = []
        for path in ('studies/formation-study-a-fixtures-v0213.json', 'studies/formation-study-a-pressure-fixtures-v0215.json'):
            fixtures += adapter.read(ROOT / path)['fixtures']
        return [packet['raw'] for cell in self.plan['pending_cells']
                for packet in next(f['packets'] for f in fixtures
                                   if f['case_id'] == cell['case_id'] and f['name'] == 'required_conduct')]

    def quota_class(self, allowance=None):
        state = adapter.read(self.root / 'results/formation-spending-v021/groq-rate.json')
        clock = [max(state.get('paused_until', 0), max(e[0] for e in state['events']) + 62) + 1]
        class FixtureQuota(GroqSlots):
            def __init__(self, path):
                super().__init__(path, now=lambda: clock[0])
                self.allowed = 0
            def before(self, hint):
                if allowance is not None and self.allowed >= allowance:
                    raise RatePaused('declared pre-request fixture pause')
                self.allowed += 1
                clock[0] += 62
                return super().before(hint)
        return FixtureQuota

    def test_approval_flags_and_receipt_before_credentials_transport_or_evidence(self):
        (self.root / adapter.APPROVAL).unlink()
        with patch.object(adapter, 'load_keys') as keys, patch('urllib.request.urlopen') as send:
            with self.assertRaisesRegex(ValueError, 'approval required'):
                adapter.run_continuation(self.plan_path, root=self.root)
            with self.assertRaisesRegex(ValueError, 'receipt absent'):
                self.run_suffix()
            keys.assert_not_called()
            send.assert_not_called()
        self.assertEqual(hashes(self.source), self.original)

    def test_source_review_exact_suffix_and_quota_reserve(self):
        plan = adapter.review_source(self.plan_path, self.root)
        self.assertEqual(len(plan['pending_cells']), 236)
        self.assertEqual(adapter.key(plan['pending_cells'][0]), ('A_R03', 1))
        self.assertNotIn(('A_R02', 1), {adapter.key(c) for c in plan['pending_cells']})
        self.assertEqual(adapter.read(self.root / 'results/formation-spending-v021/groq-rate.json')['events'][-1][1], 8000)
        self.assert_originals()

    def test_source_pending_cell_and_lock_tampering_block_without_transport(self):
        paths = [self.source / 'A_R03-r01-checkpoint.json', self.root / 'results/formation-spending-v021/run.lock']
        for path in paths:
            path.write_text('{}')
            with patch.object(adapter, 'load_keys') as keys, patch('urllib.request.urlopen') as send:
                with self.assertRaises(ValueError): self.run_suffix()
                keys.assert_not_called(); send.assert_not_called()
            path.unlink()
        for name in ('A_R02-r01-checkpoint.json', 'calls.jsonl', 'execution-manifest.json'):
            path = self.source / name
            before = path.read_bytes();path.write_bytes(before + b' ')
            with self.assertRaises(ValueError): adapter.review_source(self.plan_path, self.root)
            path.write_bytes(before)

    def test_same_root_output_settings_and_initial_ledger_quota_bindings(self):
        original = copy.deepcopy(self.plan)
        mutations = [('checkout_root', '/tmp/other-root'), ('output', 'results/other'),
                     ('cap_dollars', 1), ('model', 'other'), ('pending_cells', self.plan['pending_cells'][1:])]
        for field, value in mutations:
            plan = copy.deepcopy(original); plan[field] = value; write(self.plan_path, plan)
            with self.assertRaises(ValueError): adapter.review_source(self.plan_path, self.root)
        write(self.plan_path, original)
        for relative in ['results/formation-spending-v021/groq-rate.json', 'results/formation-spending-v021/groq.json', 'formation/evaluation_runner_v0218.py']:
            path = self.root / relative; before = path.read_bytes();path.write_bytes(before+b' ')
            with self.assertRaises(ValueError): adapter.review_source(self.plan_path, self.root)
            path.write_bytes(before)

    def test_all_236_native_fixtures_and_paused_resume_once_preserve_prefix(self):
        raws = self.fixtures(); iterator = iter(raws)
        with patch.object(adapter, 'load_keys') as keys, patch.dict('os.environ', {'GROQ_API_KEY': 'declared-fixture-only'}), \
             patch('urllib.request.urlopen', side_effect=lambda *a, **k: Response(adapter.MODEL, 'groq', next(iterator))) as send:
            with patch.object(adapter, 'GroqSlots', self.quota_class(2)):
                paused = self.run_suffix()
            self.assertEqual(paused['status'], 'paused');self.assertEqual(send.call_count, 2)
            completed_before = {p.name: adapter.sha(p) for p in self.source.glob('*-r*-checkpoint.json') if adapter.read(p)['phase']=='complete'}
            adapter.review_source(self.plan_path, self.root)
            with patch.object(adapter, 'GroqSlots', self.quota_class()):
                complete = self.run_suffix()
                self.assertEqual(complete['status'], 'complete')
                self.assertEqual(complete['completed_cells'], 236)
                self.assertEqual(len(complete['combined_records']), 240)
                self.assertEqual(sum(r['identity_valid'] for r in complete['combined_records']), 239)
                self.assertTrue(all(r['outcome']=='correct' for r in complete['records']))
                self.run_suffix()
            self.assertEqual(send.call_count, len(raws))
            self.assertTrue(keys.called)
            for name, digest in completed_before.items():self.assertEqual(adapter.sha(self.source/name),digest)
        self.assert_originals()
        events = [json.loads(line) for line in (self.source/'calls.jsonl').read_text().splitlines()]
        starts = [e for e in events if e['event']=='attempt_start']
        self.assertEqual(len(starts),20+len(raws))
        self.assertEqual(len({e['id'] for e in starts}),len(starts))
        self.assertEqual(complete['batch_estimated_dollars'],0)
        adapter.review_source(self.plan_path,self.root)
        # A same-boundary snapshot mismatch must block before credentials or transport.
        path=self.root/'results/formation-spending-v021/groq-rate.json';path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaises(ValueError):adapter.review_source(self.plan_path,self.root)

    def failure(self, response):
        with patch.object(adapter,'load_keys'),patch.dict('os.environ',{'GROQ_API_KEY':'declared-fixture-only'}), \
             patch.object(adapter,'GroqSlots',self.quota_class()),patch('urllib.request.urlopen',side_effect=response) as send:
            result=self.run_suffix()
            self.assertEqual(result['status'],'stopped');self.assertEqual(send.call_count,1)
            with self.assertRaises(ValueError):self.run_suffix()
            self.assertEqual(send.call_count,1)
        self.assert_originals()

    def test_issued_429_retained_without_retry_or_automatic_resume(self):
        self.failure(urllib.error.HTTPError('https://fixture.invalid',429,'fixture',{},None))

    def test_timeout_retained_without_retry_or_automatic_resume(self):
        self.failure(TimeoutError('declared fixture'))

    def test_wrong_identity_stops(self):
        self.failure(lambda *a,**k:Response('wrong-model','groq',self.fixtures()[0]))

    def test_missing_usage_and_over_reserve_stop(self):
        class BadUsage(Response):
            def read(self):
                response=json.loads(super().read());response['usage']={};return json.dumps(response).encode()
        self.failure(lambda *a,**k:BadUsage(adapter.MODEL,'groq',self.fixtures()[0]))

    def test_negative_usage_stops_immediately(self):
        class NegativeUsage(Response):
            def read(self):
                response=json.loads(super().read());response['usage']['completion_tokens']=-1;return json.dumps(response).encode()
        self.failure(lambda *a,**k:NegativeUsage(adapter.MODEL,'groq',self.fixtures()[0]))

    def test_over_8000_usage_stops(self):
        class OverReserve(Response):
            def read(self):
                response=json.loads(super().read());response['usage']['prompt_tokens']=8001;return json.dumps(response).encode()
        self.failure(lambda *a,**k:OverReserve(adapter.MODEL,'groq',self.fixtures()[0]))

    def test_pre_request_pause_sends_zero_and_inflight_blocks(self):
        with patch.object(adapter,'load_keys'),patch.dict('os.environ',{'GROQ_API_KEY':'declared-fixture-only'}), \
             patch.object(adapter,'GroqSlots',self.quota_class(0)),patch('urllib.request.urlopen') as send:
            paused=self.run_suffix();self.assertEqual(paused['status'],'paused');send.assert_not_called()
            path=self.source/'A_R03-r01-checkpoint.json';state=adapter.read(path);state['phase']='inflight';write(path,state)
            with self.assertRaises(ValueError):self.run_suffix()
            send.assert_not_called()

    def test_unclosed_new_attempt_blocks_before_credentials(self):
        with patch.object(adapter,'load_keys'),patch.dict('os.environ',{'GROQ_API_KEY':'declared-fixture-only'}), \
             patch.object(adapter,'GroqSlots',self.quota_class(0)),patch('urllib.request.urlopen'):
            self.run_suffix()
        with (self.source/'calls.jsonl').open('a') as out:
            out.write(json.dumps({'event':'attempt_start','id':'A000021','logical_id':'L000021'})+'\n')
        with patch.object(adapter,'load_keys') as keys,patch('urllib.request.urlopen') as send:
            with self.assertRaisesRegex(ValueError,'unclosed'):self.run_suffix()
            keys.assert_not_called();send.assert_not_called()

    def test_controller_approval_and_terminal_state_never_launch(self):
        base=self.root/'runtime';base.mkdir()
        with patch.object(controller,'ROOT',self.root),patch.object(controller,'BASE',base), \
             patch.object(controller,'review_source',side_effect=lambda path:adapter.review_source(path,self.root)), \
             patch.object(controller.subprocess,'run') as launch:
            with patch('sys.argv',['controller','--plan',str(self.plan_path)]):
                with self.assertRaises(ValueError):controller.main()
            status_path=self.source/controller.STATUS_NAME
            for state in ['stopped_for_review','running_approved_continuation','complete']:
                write(status_path,{'state':state})
                with patch('sys.argv',['controller','--plan',str(self.plan_path),'--approved-continuation','--reviewed-issued-failure','--confirm-groq-free']):
                    with self.assertRaises(ValueError):controller.main()
                self.assertEqual(adapter.read(status_path)['state'],state)
            launch.assert_not_called()

    def test_controller_waits_for_real_pause_and_owned_maintenance_hold(self):
        base=self.root/'runtime';base.mkdir();hold=base/'hold';hold.write_text('fixture owner')
        args=['controller','--plan',str(self.plan_path),'--approved-continuation','--reviewed-issued-failure','--confirm-groq-free']
        class EndWait(BaseException):pass
        with patch.object(controller,'ROOT',self.root),patch.object(controller,'BASE',base), \
             patch.object(controller,'HOLD',hold), \
             patch.object(controller,'review_source',side_effect=lambda path:adapter.review_source(path,self.root)), \
             patch.object(controller.time,'sleep',side_effect=EndWait), \
             patch.object(controller.subprocess,'run') as launch,patch('sys.argv',args):
            with self.assertRaises(EndWait):controller.main()
            launch.assert_not_called()
        self.assertTrue(hold.exists())
        self.assertEqual(adapter.read(self.source/controller.STATUS_NAME)['state'],'waiting_pre_request_quota')
        # The controller's own status is expected to change in this fixture.
        # Preserve all original request/checkpoint/ledger evidence assertions.
        self.assert_originals(mutable=(controller.STATUS_NAME,))

    def test_quota_wait_does_not_reset_persisted_state(self):
        state={'paused_until':400,'events':[[100,8000]]}
        before=copy.deepcopy(state)
        self.assertEqual(quota_ready_at(state,150),400)
        self.assertEqual(quota_ready_at(state,500),500)
        daily={'events':[[100+i,8000] for i in range(25)]}
        self.assertEqual(quota_ready_at(daily,200),86500)
        self.assertEqual(state,before)


if __name__=='__main__':unittest.main()
