import importlib.util
import json
import shutil
import tempfile
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace as N
ROOT=Path(__file__).resolve().parents[1]
_spec=importlib.util.spec_from_file_location('completion_policy',ROOT/'formation/study_d_gemma_stages_v02426.py')
h=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(h)
ASSETS=ROOT/'studies/formation-study-d-gemma-stages-v02426'
SOURCE=ROOT/'studies/formation-study-d-gemma-pair-result-v02425/received-evidence-001/extracted'


def load(file):
    spec=importlib.util.spec_from_file_location('completion_test',ROOT/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


class CompletionTests(unittest.TestCase):
    def test_static_frozen_assets_and_sources(self):
        load('scripts/check_study_d_science_v02426.py').check()
        load('scripts/formation_study_d_gemma_stages_v02426.py').check_sources()

    def test_timing_regression_actual_event_does_not_wait_for_remote_commit(self):
        r=load('scripts/study_d_gemma_stages_runtime_v02426.py')
        entered=threading.Event();release=threading.Event();done=threading.Event()
        class Volume:
            def commit(self):entered.set();release.wait(5)
        batched=r.BatchedVolume(Volume(),interval=.01)
        try:
            self.assertTrue(entered.wait(2))
            with tempfile.TemporaryDirectory() as t:
                session=r.Serving.__new__(r.Serving);session.folder=Path(t);session.lock=threading.Lock();session.volume=batched
                def log():session.event(event='CPU_SCRIPTED_REGRESSION');done.set()
                with patch.object(r.os,'fsync',wraps=r.os.fsync) as fsync:
                    thread=threading.Thread(target=log);thread.start()
                    self.assertTrue(done.wait(2),'actual event blocked behind delayed remote commit')
                    self.assertTrue(session.lock.acquire(timeout=.1));session.lock.release()
                    self.assertEqual(fsync.call_count,1)
                release.set();thread.join()
        finally:release.set();batched.close()

    def test_timer_failure_and_final_commit_are_not_silent(self):
        r=load('scripts/study_d_gemma_stages_runtime_v02426.py');failed=threading.Event();calls=[]
        class Volume:
            def commit(self):calls.append(1);failed.set();raise OSError('scripted commit failure')
        v=r.BatchedVolume(Volume(),interval=.001)
        self.assertTrue(failed.wait(2));v.thread.join(2)
        with self.assertRaisesRegex(RuntimeError,'periodic'):v.check()
        with self.assertRaises(OSError):v.close()
        self.assertEqual(len(calls),2)

    def test_budget_stage_credit_and_guards(self):
        self.assertAlmostEqual(h.reservation('neutral-completion'),3.327888888888889)
        self.assertAlmostEqual(h.reservation('virtue'),8.483444444444444)
        b=h.budget('neutral-completion',18.52,3.33,True,'owner/current/no card')
        self.assertAlmostEqual(18.52+b['remaining_study_reservations_usd'],30.331333333333333)
        for actual,credit in [(18.51,11.48),(18.52,3.32),(25,11.48)]:
            with self.assertRaises(ValueError):h.budget('neutral-completion',actual,credit,True,'owner')
        self.assertEqual(h.STAGES['virtue']['software'],8800)

    def test_actual_untouched_completion_and_provenance_union(self):
        result=subprocess.run([sys.executable,'-I',str(ROOT/'scripts/study_d_gemma_completion_ci_v02426.py')],capture_output=True,text=True,timeout=120)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('PASS',result.stdout)

    def _scripted_completion(self):
        runtime=load('scripts/study_d_gemma_stages_runtime_v02426.py')
        base=load('scripts/study_d_gemma_runtime_v02416.py')
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'prior-pair').symlink_to(SOURCE,target_is_directory=True)
            folder=root/'neutral-completion/neutral';folder.mkdir(parents=True)
            binding=json.loads((ASSETS/'continuation-source-v02425.json').read_text())
            planned={(u['case_id'],u['repeat']):u for u in binding['units']}
            requests=[];commits=[]
            class Session:
                def run(self,jobs):return [job() for job in jobs]
                def generate(self,messages,key,seed,max_tokens=4096):
                    arm,cid,rep,turn=key.split('/');u=planned[cid,int(rep[1:])]
                    self_check.assertEqual(u['status'],'untouched')
                    self_check.assertEqual(seed,247053+u['schedule_index']+int(turn[1:])-1)
                    plan=json.loads((ASSETS/'plan.json').read_text());case=next(q['case'] for q in json.loads((ASSETS/'transfer-cases.json').read_text()) if q['case']['id']==cid)
                    eq=next(q['case'] for q in plan['cases'] if all(q['case'][k]==case[k] for k in ('family','theme','rung','kind')))
                    fixture=next(q for q in plan['fixture_keys'] if q['case_id']==eq['id'])
                    requests.append(key);return fixture['canonical_scripted_correct_packets'][int(turn[1:])-1]['raw']
            self_check=self
            with patch.object(runtime,'ROOT',root),patch.object(runtime,'ASSETS',ASSETS),patch.object(base,'ASSETS',ASSETS),patch.object(h,'__file__',str(ASSETS.parent/'policy.py')):
                # h locates assets relative to its remote policy path.
                with patch.object(h,'continuation_binding',return_value=binding):
                    # Temporary remote-style assets link for the union's fixed source lookup.
                    (root/'assets').symlink_to(ASSETS,target_is_directory=True)
                    with patch.object(h,'__file__',str(root/'policy.py')):
                        report=runtime.neutral_completion(Session(),base,h,folder,N(commit=lambda:commits.append(1)),{}, {},{'status':'REUSED'})
                        self.assertEqual(report['status'],'COMPLETE');self.assertEqual(report['transfer_episodes'],130)
                        self.assertEqual(report['missing'],2);self.assertEqual(len(report['episode_provenance']),132)
                        self.assertEqual(len(list((folder/'transfer').glob('*.json'))),34)
                        self.assertEqual(len(commits),35)
                        self.assertEqual({x['producer'] for x in report['episode_provenance']},{'v02425','v02426'})
                        extra=folder/'transfer/UNPLANNED-r1.json';extra.write_text('{}')
                        with self.assertRaisesRegex(ValueError,'roster'):h.neutral_union(root,folder)
            self.assertTrue(requests)

    def test_returned_first_reply_replay(self):
        result=load('scripts/audit_study_d_pair_v02425.py').audit(SOURCE,ASSETS)
        self.assertEqual(result['arms']['contrary']['bounds']['W']['known'],54)
        self.assertFalse(result['pair_closed'])


@unittest.skipUnless(importlib.util.find_spec('modal') and __import__('sys').version_info[:2]==(3,12),'pinned offline SDK')
class CompletionSerializationTests(unittest.TestCase):
    def test_no_hydration_or_backend(self):
        import modal
        from modal._serialization import serialize
        module=load('scripts/study_d_gemma_stages_app_v02426.py')
        with patch.object(modal.client._Client,'from_env',side_effect=AssertionError('backend forbidden')):
            for stage in ('neutral-completion','virtue'):
                app,worker,controller=module.define(stage)
                for f in (worker,controller):self.assertGreater(len(serialize(f._raw_f_)),100)
