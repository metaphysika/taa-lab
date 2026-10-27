"""Real local Git transactions and mocked transport; no public state mutation."""
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import Mock, patch

from experiment_a import config
from experiment_a.adapter import Adapter
from experiment_a.budget import Budget
from experiment_a.cases import encode_program
from experiment_a.check import INSTRUCTION, TOOLS
from experiment_a.driver import program
from experiment_a.state import State
from experiment_a.standin import reply
from live_demo.adapter import Stop
from live_demo.evidence import Evidence, encoded, verify
from tests.experiment_state_support import GitStateFixture


class GitState(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.network=patch.object(socket,'socket',side_effect=AssertionError('network forbidden'))
        self.network.start();self.addCleanup(self.network.stop)
        self.sleeper=Mock()
        self.fixture=GitStateFixture(self.root/'fixture')

    def state(self, root=None):
        state=State(root or self.fixture.state,run_root=self.fixture.repo,sleeper=self.sleeper)
        state.evidence=Evidence(self.root/('state-evidence-%d'%len(list(self.root.glob('state-evidence-*')))))
        return state

    def approval(self):
        return dict(owner='Chris',commit='a'*40,step=config.STEP,launch_approved=True,
                    provider='anthropic',check_attempt=2,model_returned=None)

    def adapter(self,state):
        evidence=Evidence(self.root/'evidence')
        budget=Budget('anthropic',state.ledgers['anthropic'],state.step_ledger,evidence,state=state)
        return Adapter('anthropic',budget,evidence,system=INSTRUCTION,tools=TOOLS,launch=True,
                       approved_commit='a'*40,approval=self.approval(),neutral=True)

    def remote_amount(self,name):
        raw=self.fixture.git('show','experiment-state:'+name,cwd=self.fixture.remote)
        return Decimal(json.loads(raw)['estimated_api_dollars']) if name.endswith('.json') else Decimal(raw)

    def test_second_worktree_sees_used_attempts_and_spend(self):
        state=self.state();second=self.fixture.second()
        with state.locked(self.root/'first'):
            state.claim_check('anthropic',self.approval(),self.root/'first')
            budget=self.adapter(state).budget
            budget.reserve({'synthetic':True})
            spent=budget.read_step()
        with self.assertRaisesRegex(Stop,'state_worktree_stale'):self.state(second)
        self.fixture.refresh(second)
        fresh=self.state(second)
        self.assertEqual(spent,Decimal(fresh.step_ledger.read_text()))
        self.assertEqual(spent,self.remote_amount('step-budget.txt'))
        with fresh.locked(self.root/'second'):
            with self.assertRaisesRegex(Stop,'check_attempt_used'):
                fresh.claim_check('anthropic',self.approval(),self.root/'second')
        self.assertEqual('',self.fixture.git('status','--porcelain'))

    def test_reconstructed_totals_and_both_used_markers(self):
        other=GitStateFixture(self.root/'reconstructed',reconstructed=True)
        state=State(other.state,run_root=other.repo)
        self.assertEqual(Decimal('6.201251249999988'),Decimal(json.loads(state.ledgers['anthropic'].read_text())['estimated_api_dollars']))
        self.assertEqual(Decimal('3.6689896000000046'),Decimal(json.loads(state.ledgers['google'].read_text())['estimated_api_dollars']))
        self.assertEqual(Decimal('0.39615025'),Decimal(state.step_ledger.read_text()))
        for provider in config.MODELS:
            with state.locked(self.root/provider):
                with self.assertRaisesRegex(Stop,'check_attempt_used'):
                    state.claim_check(provider,{'check_attempt':1},self.root/provider)

    def test_dirty_wrong_branch_and_missing_state_refuse(self):
        (self.fixture.state/'uncommitted.txt').write_text('fixture')
        with self.assertRaisesRegex(Stop,'state_worktree_dirty'):self.state()
        (self.fixture.state/'uncommitted.txt').unlink()
        self.fixture.git('switch','-c','wrong-state-branch',cwd=self.fixture.state)
        with self.assertRaisesRegex(Stop,'durable_state_missing_or_invalid'):self.state()
        with self.assertRaisesRegex(Stop,'durable_state_missing_or_invalid'):self.state(self.root/'absent')

    def test_stale_remote_is_checked_before_every_request(self):
        state=self.state()
        with state.locked(self.root/'out'):
            state.claim_check('anthropic',self.approval(),self.root/'out')
            adapter=self.adapter(state)
            # A detached copy simulates an external maintenance commit.
            second=self.fixture.second()
            (second/'reconstruction.json').write_text('{"fixture":"remote advancement"}\n')
            self.fixture.git('add','reconstruction.json',cwd=second)
            self.fixture.git('commit','-m','Remote fixture update',cwd=second)
            self.fixture.git('push','origin','HEAD:refs/heads/experiment-state',cwd=second)
            with patch('experiment_a.adapter.authorized'),patch('experiment_a.adapter.http') as transport:
                with self.assertRaisesRegex(Stop,'state_worktree_stale'):
                    adapter.respond([dict(kind='user',text='synthetic')],{},1)
                transport.assert_not_called()
            # No automatic recovery/lease release from stale state.
            state.failed=True
        self.assertTrue((state.root/'active-run.json').exists())

    def test_every_request_observes_published_claim_reservation_and_prior_settlement(self):
        state=self.state();requests=[]
        with state.locked(self.root/'out'):
            state.claim_check('anthropic',self.approval(),self.root/'out')
            adapter=self.adapter(state)
            def transport(provider,body):
                self.assertEqual(state._git('rev-parse','HEAD'),self.fixture.git('rev-parse','experiment-state',cwd=self.fixture.remote))
                self.assertEqual('',state._git('status','--porcelain'))
                marker=json.loads(self.fixture.git('show','experiment-state:check-anthropic-000002.once',cwd=self.fixture.remote))
                self.assertTrue(marker['used'])
                self.assertEqual(adapter.budget.read_provider(),self.remote_amount('ledgers/claude.json'))
                requests.append(body)
                return encoded(reply(provider))
            with patch('experiment_a.adapter.authorized'),patch('experiment_a.adapter.http',side_effect=transport):
                adapter.respond([dict(kind='user',text='synthetic')],{},1)
                first=adapter.budget.read_provider()
                self.assertGreater(first,0)
                self.assertEqual(first,self.remote_amount('ledgers/claude.json'))
                adapter.respond([dict(kind='user',text='synthetic')],{},2)
            self.assertEqual(2,len(requests))
            messages=state._git('log','--format=%s').splitlines()
            self.assertEqual(2,messages.count('Experiment A: reservation anthropic'))
            self.assertEqual(2,messages.count('Experiment A: settlement anthropic'))
        self.assertEqual('',self.fixture.git('status','--porcelain'))
        self.assertEqual('',state._git('status','--porcelain'))

    def test_failed_lease_push_stops_without_request(self):
        state=self.state();original=state._git
        def fail(*args,**kwargs):
            if args[0]=='push':raise Stop('state_git_failure')
            return original(*args,**kwargs)
        with patch.object(state,'_git',side_effect=fail),patch('experiment_a.adapter.http') as transport:
            with self.assertRaisesRegex(Stop,'state_publication_failed'):
                with state.locked(self.root/'out'):self.fail('unpublished lease admitted')
            transport.assert_not_called()
        self.assertTrue((state.root/'active-run.json').is_file())
        with self.assertRaisesRegex(Stop,'state_worktree_stale'):self.state()

    def test_failed_claim_push_stops_without_request(self):
        state=self.state()
        with state.locked(self.root/'out'):
            original=state._git
            def fail(*args,**kwargs):
                if args[0]=='push':raise Stop('state_git_failure')
                return original(*args,**kwargs)
            with patch.object(state,'_git',side_effect=fail),patch('experiment_a.adapter.http') as transport:
                with self.assertRaisesRegex(Stop,'state_publication_failed'):
                    state.claim_check('anthropic',self.approval(),self.root/'out')
                transport.assert_not_called()
        self.assertTrue((state.root/'check-anthropic-000002.once').exists())
        self.assertEqual(0,self.remote_amount('step-budget.txt'))

    def test_failed_reservation_push_stops_without_request_and_keeps_ahead_commit(self):
        state=self.state()
        with state.locked(self.root/'out'):
            state.claim_check('anthropic',self.approval(),self.root/'out')
            adapter=self.adapter(state);original=state._git
            def fail(*args,**kwargs):
                if args[0]=='push':raise Stop('state_git_failure')
                return original(*args,**kwargs)
            with patch.object(state,'_git',side_effect=fail),patch('experiment_a.adapter.authorized'),patch('experiment_a.adapter.http') as transport:
                with self.assertRaisesRegex(Stop,'state_publication_failed'):
                    adapter.respond([dict(kind='user',text='synthetic')],{},1)
                transport.assert_not_called()
        self.assertGreater(adapter.budget.read_provider(),0)
        self.assertEqual(0,self.remote_amount('ledgers/claude.json'))
        self.assertEqual('Experiment A: reservation anthropic',state._git('log','-1','--format=%s'))

    def test_failed_settlement_push_blocks_the_next_request(self):
        state=self.state()
        with state.locked(self.root/'out'):
            state.claim_check('anthropic',self.approval(),self.root/'out')
            adapter=self.adapter(state);original=state._git
            def fail(*args,**kwargs):
                if args[0]=='push' and original('log','-1','--format=%s')=='Experiment A: settlement anthropic':
                    raise Stop('state_git_failure')
                return original(*args,**kwargs)
            with patch.object(state,'_git',side_effect=fail),patch('experiment_a.adapter.authorized'),patch('experiment_a.adapter.http',return_value=encoded(reply('anthropic'))) as transport:
                with self.assertRaisesRegex(Stop,'state_publication_failed'):
                    adapter.respond([dict(kind='user',text='synthetic')],{},1)
                with self.assertRaisesRegex(Stop,'state_publication_failed'):
                    adapter.respond([dict(kind='user',text='synthetic')],{},2)
                self.assertEqual(1,transport.call_count)
            self.assertGreater(self.remote_amount('ledgers/claude.json'),adapter.budget.read_provider())

    def test_actual_remote_push_rejection_stops_before_request(self):
        state=self.state()
        with state.locked(self.root/'out'):
            state.claim_check('anthropic',self.approval(),self.root/'out')
            adapter=self.adapter(state)
            hook=self.fixture.remote/'hooks/pre-receive'
            hook.write_text('#!/bin/sh\nexit 1\n');hook.chmod(0o755)
            with patch('experiment_a.adapter.authorized'),patch('experiment_a.adapter.http') as transport:
                with self.assertRaisesRegex(Stop,'state_publication_failed'):
                    adapter.respond([dict(kind='user',text='synthetic')],{},1)
                transport.assert_not_called()
            self.assertEqual(0,self.remote_amount('step-budget.txt'))

    def test_published_push_with_lost_acknowledgement_continues_without_repush(self):
        state=self.state();original=state._git;pushes=[]
        def lose_ack(*args,**kwargs):
            result=original(*args,**kwargs)
            if args[0]=='push':
                pushes.append(args)
                self.assertFalse(any(arg.startswith('--force') for arg in args))
                raise Stop('state_git_failure')
            return result
        with patch.object(state,'_git',side_effect=lose_ack):
            with state.locked(self.root/'out'):
                state.claim_check('anthropic',self.approval(),self.root/'out')
                adapter=self.adapter(state)
                with patch('experiment_a.adapter.authorized'),patch('experiment_a.adapter.http',return_value=encoded(reply('anthropic'))) as transport:
                    adapter.respond([dict(kind='user',text='synthetic')],{},1)
                    adapter.respond([dict(kind='user',text='synthetic')],{},2)
                    self.assertEqual(2,transport.call_count)
                    self.assertEqual(adapter.budget.read_provider(),self.remote_amount('ledgers/claude.json'))
        self.assertFalse(state.failed)
        self.assertEqual(7,len(pushes)) # lease, claim, two reserve/settle, release

    def test_post_push_confirmation_failure_recovers_only_exact_commit(self):
        state=self.state();original=state._git;fail_fetch=[False];pushes=[]
        def confirmation(*args,**kwargs):
            if args[0]=='fetch' and fail_fetch[0]:
                fail_fetch[0]=False
                raise Stop('state_git_failure')
            result=original(*args,**kwargs)
            if args[0]=='push':
                pushes.append(args);fail_fetch[0]=True
            return result
        with patch.object(state,'_git',side_effect=confirmation):
            with state.locked(self.root/'out'):
                state.claim_check('anthropic',self.approval(),self.root/'out')
        self.assertFalse(state.failed)
        self.assertEqual(3,len(pushes))
        self.assertEqual(state.base,self.fixture.git('rev-parse','experiment-state',cwd=self.fixture.remote))

    def test_remote_tip_race_rejects_reservation_push_before_request(self):
        state=self.state()
        with state.locked(self.root/'out'):
            state.claim_check('anthropic',self.approval(),self.root/'out')
            adapter=self.adapter(state);original=state._git
            second=self.fixture.second()
            def race(*args,**kwargs):
                if args[0]=='push':
                    (second/'reconstruction.json').write_text('{"fixture":"concurrent tip"}\n')
                    self.fixture.git('add','reconstruction.json',cwd=second)
                    self.fixture.git('commit','-m','Concurrent fixture commit',cwd=second)
                    self.fixture.git('push','origin','HEAD:refs/heads/experiment-state',cwd=second)
                return original(*args,**kwargs)
            with patch.object(state,'_git',side_effect=race),patch('experiment_a.adapter.authorized'),patch('experiment_a.adapter.http') as transport:
                with self.assertRaisesRegex(Stop,'state_publication_failed'):
                    adapter.respond([dict(kind='user',text='synthetic')],{},1)
                transport.assert_not_called()
            self.assertEqual(0,self.remote_amount('step-budget.txt'))

    def confirmation_events(self,state):
        return [json.loads(p.read_bytes())['value'] for p in sorted(state.evidence.directory.glob('[0-9]*.json'))
                if json.loads(p.read_bytes())['kind']=='state_confirmation']

    def test_confirmation_success_on_second_observation_records_both_attempts(self):
        state=self.state();original=state._git;pushes=[];pending=[0]
        with state.locked(self.root/'out'):
            def transient(*args,**kwargs):
                if args[0]=='fetch' and pending[0]:
                    pending[0]-=1;raise Stop('state_git_failure')
                result=original(*args,**kwargs)
                if args[0]=='push':
                    pushes.append(args);pending[0]=1;raise Stop('state_git_failure')
                return result
            with patch.object(state,'_git',side_effect=transient):
                state.claim_check('anthropic',self.approval(),self.root/'out')
            self.assertEqual(1,len(pushes))
            self.assertEqual([10,30],[c.args[0] for c in self.sleeper.call_args_list])
            events=self.confirmation_events(state)
            self.assertEqual([(1,'unavailable'),(2,'exact_commit')],[(v['attempt'],v['outcome']) for v in events])
            self.assertEqual(events[0]['commit'],events[1]['commit'])
            self.assertEqual(events[1]['commit'],self.fixture.git('rev-parse','experiment-state',cwd=self.fixture.remote))
        state.evidence.close({'fixture':'second confirmation'});verify(state.evidence.directory)

    def test_confirmation_different_tip_stops_immediately_without_second_push(self):
        state=self.state();original=state._git;pushes=[]
        with state.locked(self.root/'out'):
            def rejected(*args,**kwargs):
                if args[0]=='push':
                    pushes.append(args);raise Stop('state_git_failure')
                return original(*args,**kwargs)
            with patch.object(state,'_git',side_effect=rejected),patch('experiment_a.adapter.http') as transport:
                with self.assertRaisesRegex(Stop,'state_publication_failed'):
                    state.claim_check('anthropic',self.approval(),self.root/'out')
                transport.assert_not_called()
        self.assertEqual(1,len(pushes))
        self.assertEqual([10],[c.args[0] for c in self.sleeper.call_args_list])
        self.assertEqual([(1,'different_tip')],[(v['attempt'],v['outcome']) for v in self.confirmation_events(state)])
        self.assertTrue((state.root/'active-run.json').exists())
        state.evidence.close({'fixture':'different tip'});verify(state.evidence.directory)

    def test_three_unavailable_confirmations_stop_and_preserve_attempts(self):
        state=self.state();original=state._git;pushes=[];failed_push=[False]
        with state.locked(self.root/'out'):
            def unavailable(*args,**kwargs):
                if args[0]=='push':
                    pushes.append(args);failed_push[0]=True;raise Stop('state_git_failure')
                if args[0]=='fetch' and failed_push[0]:raise Stop('state_git_failure')
                return original(*args,**kwargs)
            with patch.object(state,'_git',side_effect=unavailable),patch('experiment_a.adapter.http') as transport:
                with self.assertRaisesRegex(Stop,'state_publication_failed'):
                    state.claim_check('anthropic',self.approval(),self.root/'out')
                transport.assert_not_called()
        self.assertEqual(1,len(pushes))
        self.assertEqual([10,30,60],[c.args[0] for c in self.sleeper.call_args_list])
        self.assertEqual([(n,'unavailable') for n in (1,2,3)],[(v['attempt'],v['outcome']) for v in self.confirmation_events(state)])
        self.assertTrue(state.failed)
        self.assertTrue((state.root/'active-run.json').exists())
        state.evidence.close({'fixture':'three failed confirmations'});verify(state.evidence.directory)

    def test_confirmation_evidence_write_failure_stops_before_observation(self):
        state=self.state();original=state._git;pushes=[]
        with state.locked(self.root/'out'):
            def rejected(*args,**kwargs):
                if args[0]=='push':
                    pushes.append(args);raise Stop('state_git_failure')
                return original(*args,**kwargs)
            with patch.object(state,'_git',side_effect=rejected),patch.object(state.evidence,'write',side_effect=OSError('withheld')),patch('experiment_a.adapter.http') as transport:
                with self.assertRaisesRegex(Stop,'state_publication_failed'):
                    state.claim_check('anthropic',self.approval(),self.root/'out')
                transport.assert_not_called()
        self.assertEqual(1,len(pushes))
        self.sleeper.assert_not_called()
        self.assertTrue(state.failed)
        self.assertTrue((state.root/'active-run.json').exists())

    def test_interrupted_confirmation_preserves_lease_without_cleanup_push(self):
        state=self.state();original=state._git;pushes=[]
        with self.assertRaises(KeyboardInterrupt):
            with state.locked(self.root/'out'):
                def rejected(*args,**kwargs):
                    if args[0]=='push':
                        pushes.append(args);raise Stop('state_git_failure')
                    return original(*args,**kwargs)
                with patch.object(state,'_git',side_effect=rejected),patch.object(state,'sleeper',side_effect=KeyboardInterrupt):
                    state.claim_check('anthropic',self.approval(),self.root/'out')
        self.assertEqual(1,len(pushes))
        self.assertTrue(state.failed)
        self.assertTrue((state.root/'active-run.json').exists())
        state.evidence.close({'fixture':'interrupted confirmation'});verify(state.evidence.directory)

    def test_live_adapter_cannot_use_an_unpublished_fixture_budget(self):
        state=self.state()
        with state.locked(self.root/'out'):
            state.claim_check('anthropic',self.approval(),self.root/'out')
            adapter=self.adapter(state);adapter.budget.state=None
            with patch('experiment_a.adapter.authorized'),patch('experiment_a.adapter.http') as transport:
                with self.assertRaisesRegex(Stop,'durable_state_required'):
                    adapter.respond([dict(kind='user',text='synthetic')],{},1)
                transport.assert_not_called()
            self.assertEqual(0,self.remote_amount('step-budget.txt'))

    def test_direct_adapter_cannot_reuse_a_claim_from_an_earlier_lease(self):
        state=self.state()
        with state.locked(self.root/'first'):
            state.claim_check('anthropic',self.approval(),self.root/'first')
        fresh=self.state()
        with fresh.locked(self.root/'second'):
            adapter=self.adapter(fresh)
            with patch('experiment_a.adapter.authorized'),patch('experiment_a.adapter.http') as transport:
                with self.assertRaisesRegex(Stop,'state_claim_required'):
                    adapter.respond([dict(kind='user',text='synthetic')],{},1)
                transport.assert_not_called()

    def test_local_foreign_commit_is_not_published_with_a_reservation(self):
        state=self.state()
        with state.locked(self.root/'out'):
            state.claim_check('anthropic',self.approval(),self.root/'out')
            adapter=self.adapter(state);original=state._git
            def foreign_commit(*args,**kwargs):
                if args[0]=='commit':
                    (state.root/'reconstruction.json').write_text('{"fixture":"foreign local commit"}\n')
                    self.fixture.git('add','reconstruction.json',cwd=state.root)
                    self.fixture.git('commit','-m','Foreign local fixture commit',cwd=state.root)
                return original(*args,**kwargs)
            with patch.object(state,'_git',side_effect=foreign_commit),patch('experiment_a.adapter.authorized'),patch('experiment_a.adapter.http') as transport:
                with self.assertRaisesRegex(Stop,'state_publication_failed'):
                    adapter.respond([dict(kind='user',text='synthetic')],{},1)
                transport.assert_not_called()
            self.assertEqual(0,self.remote_amount('step-budget.txt'))

    def test_pilot_loader_never_reads_held_out_files(self):
        with patch.object(Path,'read_bytes',side_effect=AssertionError('H read forbidden')):
            for number in range(1,13):
                with self.assertRaisesRegex(Stop,'held_out_sealed'):program('H%02d'%number)
        self.assertFalse(any(row['program'].startswith('H') for row in config.load('pilot-order.json')))
        self.assertTrue(all(not name.startswith('H') for name in self.fixture.git('ls-tree','-r','--name-only','HEAD',cwd=self.fixture.state).splitlines()))

    def test_p_encoder_deterministic_and_matches_existing_bytes(self):
        path=config.INPUTS/'P/P01.json'
        definition=json.loads(path.read_bytes())
        first=encode_program(definition);second=encode_program(definition)
        self.assertEqual(first,second)
        self.assertEqual(path.read_bytes(),first)
        self.assertEqual('7ba16c288655fd943e5ac2fd113e190d22006cacfc06d98dc775c7d45c2cbbad',hashlib.sha256(first).hexdigest())


if __name__=='__main__':unittest.main()
