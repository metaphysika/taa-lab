"""Actions orchestration fixtures are engineering only; provider sockets denied."""
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from experiment_a import actions, runtime_guard
from experiment_a.state import State
from experiment_a.run import run
from live_demo.adapter import Stop
from live_demo.evidence import Evidence, verify
from tests.experiment_state_support import GitStateFixture


class ActionsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.receipt = dict(owner='Chris', commit='a'*40, launch_approved=True,
                            step='experiment-a-v01', provider='anthropic', check_attempt=1)
        self.addCleanup(setattr, runtime_guard, 'deadline', None)

    def test_exact_commit_and_receipt_both_required(self):
        actions.validate('a'*40, self.receipt, 'neutral check', 'a'*40)
        for commit, head in [('b'*40, 'b'*40), ('a'*40, 'b'*40)]:
            with self.assertRaisesRegex(Stop, 'runner_approval_mismatch'):
                actions.validate(commit, self.receipt, 'neutral check', head)

    def test_paid_requires_launch_approval_but_dry_run_does_not(self):
        self.receipt['launch_approved'] = False
        with self.assertRaises(Stop):
            actions.validate('a'*40, self.receipt, 'neutral check', 'a'*40)
        actions.validate('a'*40, self.receipt, 'neutral check', 'a'*40, dry_run=True)

    def test_continuation_source_ids_are_bound_and_not_paths(self):
        self.receipt.update(continuation=1, source_runs=['b'*64], source_checkpoints=['c'*64])
        actions.validate('a'*40, self.receipt, 'pilot continuation', 'a'*40)
        for ids in [['../escape'], [], ['b'*64, 'b'*64]]:
            self.receipt['source_runs'] = ids
            with self.assertRaisesRegex(Stop, 'runner_source_binding'):
                actions.validate('a'*40, self.receipt, 'pilot continuation', 'a'*40)

    def test_dry_run_echo_uses_real_standin_and_zero_network(self):
        def git(*args):
            return 'a'*40 if args[1:]==('rev-parse', 'HEAD') else ''
        with patch.object(actions, 'git', side_effect=git), patch('socket.socket.connect', side_effect=AssertionError('network forbidden')):
            result = actions.execute('a'*40, self.receipt, 'neutral check', self.base/'dry', dry_run=True)
        self.assertEqual('complete', result['stop'])
        verify(self.base/'dry/run');verify(self.base/'dry/automation')
        self.assertFalse((self.base/'dry/state').exists())

    def test_timeout_closes_root_and_episode_without_a_request(self):
        runtime_guard.deadline = 0
        with patch('socket.socket.connect', side_effect=AssertionError('network forbidden')):
            result = run(self.base/'timeout')
        self.assertEqual('runner_timeout', result['stop'])
        verify(self.base/'timeout');verify(self.base/'timeout/episode-0000')
        frames=[json.loads(p.read_bytes()) for p in (self.base/'timeout').glob('[0-9]*.json')]
        self.assertFalse(any(f['kind']=='request' for f in frames))
        self.assertEqual('runner_timeout', result['episodes'][0]['stop'])

    def test_held_out_refuses_before_any_provider_or_H_read(self):
        with patch('experiment_a.adapter.http', side_effect=AssertionError('provider forbidden')):
            with self.assertRaisesRegex(Stop, 'held_out_sealed'):
                actions.dispatch('held-out run', self.receipt, self.base/'held')
        self.assertFalse((self.base/'held').exists())

    def test_secret_in_log_prevents_upload_scan_success(self):
        p=self.base/'log';p.mkdir();(p/'process.log').write_text('sk-ant-'+'A'*40)
        with self.assertRaisesRegex(Stop, 'evidence_credential_scan_failed'):
            actions.scan_files(p)

    def test_environment_and_actual_Chris_run_approval_required(self):
        env=dict(protection_rules=[dict(type='required_reviewers', reviewers=[dict(type='User',reviewer=dict(login='metaphysika'))])])
        phrase=actions.approval_phrase(self.receipt,'2')
        approved=[dict(state='approved',user=dict(login='metaphysika'),comment='ok, '+phrase,environments=[dict(name='experiment-a-live')])]
        def call(reviews, receipt=self.receipt):
            return actions.environment_review('metaphysika/taa-lab','test',receipt,opener=lambda req,**kw:io.BytesIO(json.dumps(reviews if '/approvals' in req.full_url else env).encode()))
        with patch.dict('os.environ', {'GITHUB_RUN_ID':'12','GITHUB_RUN_ATTEMPT':'2'}):
            call(approved)
            other_receipt=dict(self.receipt,check_attempt=2)
            stale_attempt=[dict(approved[0],comment=actions.approval_phrase(self.receipt,'1'))]
            for bad,receipt in [([],self.receipt),
                                ([dict(approved[0],user=dict(login='someone-else'))],self.receipt),
                                ([dict(approved[0],comment=None)],self.receipt),
                                (stale_attempt,self.receipt),
                                (approved,other_receipt),
                                (approved,None)]:
                with self.assertRaisesRegex(Stop, 'runner_environment_unverified'):
                    call(bad,receipt)

    def test_real_local_git_worktrees_use_same_state_and_evidence_history(self):
        f=GitStateFixture(self.base/'git');f.evidence_worktree()
        dest=self.base/'new';dest.mkdir()
        state,evidence=actions.worktrees(f.repo,dest)
        self.assertEqual(f.git('rev-parse','HEAD',cwd=f.state),f.git('rev-parse','HEAD',cwd=state))
        self.assertEqual(f.git('rev-parse','HEAD',cwd=f.root/'evidence'),f.git('rev-parse','HEAD',cwd=evidence))
        State(state,run_root=f.repo)

    def test_restore_only_verified_public_chain_bytes(self):
        original=Evidence(self.base/'original');child=Evidence(original.directory/'episode-0000')
        child.write('engineering',{});child.close(dict(stop='model_done'));original.close(dict(stop='engineering'))
        ev=self.base/'ev';source=ev/'runs'/('b'*64);source.mkdir(parents=True)
        shutil.copytree(original.directory,source/'root')
        shutil.rmtree(source/'root/episode-0000')
        shutil.copytree(child.directory,source/'episode-0000')
        dest=self.base/'restored';dest.mkdir()
        receipt=dict(source_runs=['b'*64],source_checkpoints=[verify(original.directory)['head']])
        roots=actions.restore_sources(ev,receipt,dest)
        self.assertEqual(verify(original.directory),verify(roots[0]))
        self.assertEqual(child.directory.joinpath('000000.json').read_bytes(),roots[0].joinpath('episode-0000/000000.json').read_bytes())

    def test_workflow_separates_dry_job_and_gated_secret_job(self):
        import yaml
        workflow=yaml.load((actions.config.ROOT/'.github/workflows/experiment-a-live.yml').read_text(),Loader=yaml.BaseLoader)
        self.assertEqual(['workflow_dispatch'],list(workflow['on']))
        self.assertEqual('false',workflow['concurrency']['cancel-in-progress'])
        self.assertIn('github.run_id',workflow['env']['EVIDENCE_DIRECTORY'])
        self.assertIn('github.run_attempt',workflow['env']['EVIDENCE_DIRECTORY'])
        dry=workflow['jobs']['dry-run'];live=workflow['jobs']['live']
        self.assertNotIn('environment',dry)
        self.assertNotIn('secrets.',json.dumps(dry))
        self.assertEqual('experiment-a-live',live['environment'])
        self.assertLess(int(live['timeout-minutes']),360)
        self.assertIn('unshare --net',json.dumps(dry))
        self.assertIn("steps.scan.outcome == 'success'",json.dumps(live))

    def test_closed_pilot_refuses_before_source_restore_or_dispatch(self):
        self.receipt.update(continuation=1, source_runs=['b'*64], source_checkpoints=['c'*64])
        def git(repo,*args):
            return 'a'*40 if args==('rev-parse','HEAD') else 'closure-commit' if args[0]=='log' else ''
        env=dict(GITHUB_ACTIONS='true',TAA_ACTIONS_APPROVED_ENVIRONMENT='experiment-a-live',
                 ANTHROPIC_API_KEY='engineering-placeholder-only',GEMINI_API_KEY='engineering-placeholder-only',
                 GITHUB_WORKFLOW_SHA='a'*40,GITHUB_REPOSITORY='metaphysika/taa-lab',
                 GITHUB_WORKFLOW_REF='metaphysika/taa-lab/.github/workflows/experiment-a-live.yml@refs/heads/x')
        with patch.object(actions,'git',side_effect=git),patch.object(actions,'environment_review'),patch.object(actions,'worktrees',return_value=(self.base/'state',self.base/'evidence')),patch.object(actions,'restore_sources')as restore,patch.object(actions,'dispatch')as dispatch,patch.dict('os.environ',env):
            result=actions.execute('a'*40,self.receipt,'pilot continuation',self.base/'closed')
        self.assertEqual('pilot_closed',result['stop']);restore.assert_not_called();dispatch.assert_not_called()

    def test_unapproved_environment_never_prepares_state_or_dispatches(self):
        def git(repo,*args):return 'a'*40 if args==('rev-parse','HEAD') else ''
        with patch.object(actions,'git',side_effect=git),patch.dict('os.environ',{'GITHUB_ACTIONS':'false'}),patch.object(actions,'worktrees')as prepare,patch.object(actions,'dispatch')as dispatch:
            result=actions.execute('a'*40,self.receipt,'neutral check',self.base/'unapproved')
        self.assertEqual('runner_environment_unverified',result['stop']);prepare.assert_not_called();dispatch.assert_not_called()

    def test_workflow_identity_must_be_the_approved_commit(self):
        good={'GITHUB_WORKFLOW_SHA':'a'*40,'GITHUB_REPOSITORY':'metaphysika/taa-lab',
              'GITHUB_WORKFLOW_REF':'metaphysika/taa-lab/.github/workflows/experiment-a-live.yml@refs/heads/x'}
        actions.workflow_identity('a'*40,good)
        for change in [{'GITHUB_WORKFLOW_SHA':'b'*40},{'GITHUB_WORKFLOW_SHA':''},
                       {'GITHUB_WORKFLOW_REF':'metaphysika/taa-lab/.github/workflows/other.yml@refs/heads/x'},
                       {'GITHUB_WORKFLOW_REF':'someone/fork/.github/workflows/experiment-a-live.yml@refs/heads/x'}]:
            with self.assertRaisesRegex(Stop,'runner_workflow_mismatch'):
                actions.workflow_identity('a'*40,dict(good,**change))

    def test_mismatched_workflow_stops_before_review_state_or_dispatch(self):
        def git(repo,*args):return 'a'*40 if args==('rev-parse','HEAD') else ''
        env=dict(GITHUB_ACTIONS='true',TAA_ACTIONS_APPROVED_ENVIRONMENT='experiment-a-live',GITHUB_WORKFLOW_SHA='b'*40)
        with patch.object(actions,'git',side_effect=git),patch.dict('os.environ',env),patch.object(actions,'environment_review')as review,patch.object(actions,'worktrees')as prepare,patch.object(actions,'dispatch')as dispatch:
            result=actions.execute('a'*40,self.receipt,'neutral check',self.base/'wf')
        self.assertEqual('runner_workflow_mismatch',result['stop']);review.assert_not_called();prepare.assert_not_called();dispatch.assert_not_called()

    def test_third_party_actions_are_pinned_and_scan_sees_github_token(self):
        text=(actions.config.ROOT/'.github/workflows/experiment-a-live.yml').read_text()
        import re
        uses=re.findall(r'uses:\s*(\S+)',text)
        self.assertTrue(uses)
        for u in uses:
            self.assertRegex(u,r'@[0-9a-f]{40}$')
        import yaml
        workflow=yaml.load(text,Loader=yaml.BaseLoader)
        scan=[s for s in workflow['jobs']['live']['steps'] if s.get('id')=='scan'][0]
        self.assertIn('GITHUB_TOKEN',scan['env'])
        self.assertEqual('announce',workflow['jobs']['live']['needs'])
        self.assertNotIn('secrets.',json.dumps(workflow['jobs']['announce']))

    def test_github_tokens_are_caught_by_pattern_and_exact_value(self):
        from experiment_a.credentials import scan
        for raw in [b'x github_pat_'+b'A'*30, b'x ghs_'+b'B'*30]:
            with self.assertRaisesRegex(Stop,'evidence_credential_scan_failed'):
                scan('process.log',raw)
        value='opaque-token-value-without-known-prefix'
        with patch.dict('os.environ',{'GITHUB_TOKEN':value}):
            with self.assertRaisesRegex(Stop,'evidence_credential_scan_failed'):
                scan('process.log',b'leak '+value.encode())
            scan('process.log',b'no leak here')

    def test_run_kind_marker_is_restored_after_execute(self):
        import os
        def git(repo,*args):return 'a'*40 if args==('rev-parse','HEAD') else ''
        with patch.object(actions,'git',side_effect=git),patch.dict('os.environ',{'GITHUB_ACTIONS':'false'}):
            os.environ.pop('TAA_RUN_KIND',None)
            actions.execute('a'*40,self.receipt,'held-out run',self.base/'kind')
            self.assertNotIn('TAA_RUN_KIND',os.environ)

    def test_held_out_kind_refuses_public_publication(self):
        from experiment_a.publication import Publisher
        with patch.dict('os.environ',{'TAA_RUN_KIND':'held-out run'}):
            with self.assertRaisesRegex(Stop,'held_out_public_publication_refused'):
                Publisher(self.base/'anywhere')

    def test_private_destination_check_fails_closed(self):
        from experiment_a.private_evidence import verify_private_destination
        def opener(data):
            return lambda req,**kw:io.BytesIO(json.dumps(data).encode())
        ok=dict(private=True,visibility='private',full_name='metaphysika/taa-lab-private')
        self.assertEqual('metaphysika/taa-lab-private',verify_private_destination('metaphysika/taa-lab-private','t','metaphysika/taa-lab',opener(ok)))
        for repo,data in [('metaphysika/taa-lab',ok),('metaphysika/taa-lab-private',dict(ok,private=False,visibility='public')),
                          ('metaphysika/taa-lab-private',dict(ok,full_name='someone/else')),('bad name',ok)]:
            with self.assertRaisesRegex(Stop,'held_out_private_destination_unverified'):
                verify_private_destination(repo,'t','metaphysika/taa-lab',opener(data))
        def broken(req,**kw):raise OSError('down')
        with self.assertRaisesRegex(Stop,'held_out_private_destination_unverified'):
            verify_private_destination('metaphysika/taa-lab-private','t','metaphysika/taa-lab',broken)


if __name__ == '__main__':
    unittest.main()

