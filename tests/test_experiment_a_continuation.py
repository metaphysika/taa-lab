"""Disposable local Git state and mocked replies; no live experiment mutation."""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from experiment_a import config
from experiment_a.adapter import Adapter, authorized
from experiment_a.analysis import outcomes
from experiment_a.continuation import Continuation
from experiment_a.run import run
from experiment_a.state import State
from experiment_a.standin import reply
from live_demo.adapter import Stop, TransportFailure
from live_demo.evidence import encoded, verify
from tests.experiment_state_support import GitStateFixture


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.fixture=GitStateFixture(self.root/'fixture')
        self.schedule=config.schedule()[:4]
        original_load=config.load
        self.original_load=original_load
        for context in (
            patch.object(socket,'socket',side_effect=AssertionError('network forbidden')),
            patch.object(config,'load',side_effect=lambda name:self.schedule if name=='pilot-order.json' else original_load(name)),
            patch.object(config,'schedule',return_value=self.schedule),
            patch.object(config,'verify',return_value={}),
            patch('experiment_a.adapter.authorized'),
            patch('experiment_a.run.authorized'),
            patch('experiment_a.run.State',side_effect=self.state),
            patch('experiment_a.run.Publisher',side_effect=self.publisher),
        ):
            context.start();self.addCleanup(context.stop)

    def state(self, **kwargs):return State(self.fixture.state,run_root=self.fixture.repo,sleeper=lambda seconds:None,**kwargs)

    def publisher(self):
        from experiment_a.publication import Publisher
        return Publisher(self.fixture.evidence_worktree(),run_root=self.fixture.repo,sleeper=lambda seconds:None)

    def approval(self, number=None, sources=None, start=None):
        a=dict(owner='Chris',commit='a'*40,step=config.STEP,launch_approved=True,model_returned=dict(config.MODELS))
        if number is not None:
            a.update(continuation=number,source_checkpoints=[verify(p)['head'] for p in sources],start_index=start)
        return a

    def source(self):
        state=self.state();original=state.publish
        def stop_after_published_reply(description,paths):
            original(description,paths)
            if description=='settlement google':
                # Reproduce the old stop with an arrived reply and a published
                # settlement, before in-memory Budget counters can update.
                state.failed=True
                raise Stop('state_publication_failed')
        directory=self.root/'source'
        with patch('experiment_a.run.State',return_value=state),patch.object(state,'publish',side_effect=stop_after_published_reply),patch('experiment_a.adapter.http',side_effect=lambda p,b:encoded(reply(p))):
            report=run(directory,launch=True,approved_commit='a'*40,approval=self.approval())
        self.assertEqual('state_publication_failed',report['stop'])
        self.assertEqual(self.schedule[:2],[r['spec'] for r in report['episodes']])
        self.assertTrue((state.root/'active-run.json').exists())
        return directory,report

    def test_stopped_reply_never_replaced_suffix_only_and_original_bytes_unchanged(self):
        source,old=self.source()
        hashes={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*.json')}
        approval=self.approval(1,[source],2)
        out=self.root/'continuation'
        with patch('experiment_a.adapter.http',side_effect=lambda p,b:encoded(reply(p))) as transport:
            report=run(out,launch=True,approved_commit='a'*40,approval=approval,continue_from=[source],continuation=1)
        self.assertEqual('complete',report['stop'])
        self.assertEqual(self.schedule[2:],[r['spec'] for r in report['episodes']])
        self.assertEqual(2,transport.call_count)
        self.assertEqual(2,report['start_index'])
        self.assertEqual('state_publication_failed',old['episodes'][-1]['stop'])
        self.assertEqual({'wrongful':None,'completion':None},outcomes(old['episodes'][-1],self.original_load('measures.json')))
        self.assertEqual(hashes,{str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*.json')})
        self.assertTrue((self.fixture.state/'run.once').exists())
        self.assertTrue((self.fixture.state/'continuation-000001.once').exists())
        self.assertFalse((self.fixture.state/'active-run.json').exists())
        verify(out)

    def test_continuation_refuses_completed_or_stopped_index(self):
        source,_=self.source()
        for start in (0,1):
            with patch('experiment_a.adapter.http') as transport:
                with self.assertRaisesRegex(Stop,'continuation_evidence_or_accounting_mismatch'):
                    run(self.root/('bad-'+str(start)),launch=True,approved_commit='a'*40,
                        approval=self.approval(1,[source],start),continue_from=[source],continuation=1)
                transport.assert_not_called()
        self.assertFalse((self.fixture.state/'continuation-000001.once').exists())

    def test_second_continuation_needs_new_number_and_new_approval(self):
        source,_=self.source();a=self.approval(1,[source],2)
        state=self.state();original=state.publish
        def stop(description,paths):
            original(description,paths)
            if description=='settlement anthropic':
                state.failed=True;raise Stop('state_publication_failed')
        first=self.root/'first'
        with patch('experiment_a.run.State',return_value=state),patch.object(state,'publish',side_effect=stop),patch('experiment_a.adapter.http',side_effect=lambda p,b:encoded(reply(p))):
            result=run(first,launch=True,approved_commit='a'*40,approval=a,continue_from=[source],continuation=1)
        self.assertEqual(1,len(result['episodes']))
        with patch('experiment_a.adapter.http') as transport:
            with self.assertRaisesRegex(Stop,'continuation_not_approved'):
                run(self.root/'bad-second',launch=True,approved_commit='a'*40,approval=a,continue_from=[source,first],continuation=2)
            with self.assertRaisesRegex(Stop,'continuation_evidence_or_accounting_mismatch'):
                run(self.root/'repeat-first',launch=True,approved_commit='a'*40,approval=a,continue_from=[source],continuation=1)
            transport.assert_not_called()
        second_approval=self.approval(2,[source,first],3)
        binding=dict(commit=state._git('rev-parse','HEAD'),parent=state._git('rev-parse','HEAD^'),checkpoint=verify(first)['head'],start_index=3,provider='anthropic')
        with patch('experiment_a.continuation.STRANDED_SETTLEMENT',binding),patch('experiment_a.adapter.http',side_effect=lambda p,b:encoded(reply(p))) as transport:
            result=run(self.root/'second',launch=True,approved_commit='a'*40,approval=second_approval,continue_from=[source,first],continuation=2)
        self.assertEqual([self.schedule[3]],[r['spec'] for r in result['episodes']])
        self.assertEqual(1,transport.call_count)
        self.assertTrue((self.fixture.state/'continuation-000002.once').exists())

    def stranded_sources(self):
        # Engineering-only replies over the exact first 56 schedule indices.
        # Stops bind index22 and index53; neither outcome is scientifically scored.
        self.schedule[:] = self.original_load('pilot-order.json')[:56]
        state=self.state();original_publish=state.publish;calls=[]
        def first_stop(description,paths):
            original_publish(description,paths)
            if len(calls)==23 and description.startswith('settlement '):
                state.failed=True;raise Stop('state_publication_failed')
        def canned(provider,body):calls.append(provider);return encoded(reply(provider))
        source=self.root/'source-23'
        with patch('experiment_a.run.State',return_value=state),patch.object(state,'publish',side_effect=first_stop),patch('experiment_a.adapter.http',side_effect=canned):
            result=run(source,launch=True,approved_commit='a'*40,approval=self.approval())
        self.assertEqual(23,len(result['episodes']))
        state=self.state();git=state._git;calls.clear();blocked=[]
        def strand(*args,**kwargs):
            if args[0]=='push' and len(calls)==31 and git('log','-1','--format=%s')=='Experiment A: settlement google':
                blocked.append(args);raise Stop('state_git_failure')
            return git(*args,**kwargs)
        first=self.root/'source-54'
        with patch('experiment_a.run.State',return_value=state),patch.object(state,'_git',side_effect=strand),patch('experiment_a.adapter.http',side_effect=canned):
            result=run(first,launch=True,approved_commit='a'*40,approval=self.approval(1,[source],23),continue_from=[source],continuation=1)
        self.assertEqual(31,len(result['episodes']));self.assertEqual(4,len(blocked))
        self.assertEqual(self.schedule[53],result['episodes'][-1]['spec'])
        self.assertEqual('state_publication_failed',result['episodes'][-1]['stop'])
        commit=git('rev-parse','HEAD');parent=git('rev-parse',commit+'^')
        self.assertEqual(parent,self.fixture.git('rev-parse','experiment-state',cwd=self.fixture.remote))
        binding=dict(commit=commit,parent=parent,checkpoint=verify(first)['head'],start_index=54,provider='google')
        return [source,first],binding

    def test_stranded_settlement_published_before_request_and_index53_never_repeated(self):
        sources,binding=self.stranded_sources()
        hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for root in sources for p in root.rglob('*.json')}
        observed=[]
        def transport(provider,body):
            remote=self.fixture.git('rev-parse','experiment-state',cwd=self.fixture.remote)
            self.assertEqual(0,__import__('subprocess').run(['git','-C',str(self.fixture.remote),'merge-base','--is-ancestor',binding['commit'],remote],capture_output=True).returncode)
            self.assertEqual(self.fixture.git('show',remote+':step-budget.txt',cwd=self.fixture.remote),(self.fixture.state/'step-budget.txt').read_text().strip())
            observed.append(provider);return encoded(reply(provider))
        out=self.root/'second'
        with patch('experiment_a.continuation.STRANDED_SETTLEMENT',binding),patch('experiment_a.adapter.http',side_effect=transport):
            report=run(out,launch=True,approved_commit='a'*40,approval=self.approval(2,sources,54),continue_from=sources,continuation=2)
        self.assertEqual('complete',report['stop']);self.assertEqual(2,len(observed))
        self.assertEqual(self.schedule[54:],[r['spec'] for r in report['episodes']])
        self.assertEqual(hashes,{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for root in sources for p in root.rglob('*.json')})
        fs=[json.loads(p.read_bytes()) for p in sorted(out.glob('[0-9]*.json'))]
        settled=next(i for i,f in enumerate(fs) if f['kind']=='state_confirmation' and f['value']['outcome']=='exact_commit')
        request=next(i for i,f in enumerate(fs) if f['kind']=='request')
        self.assertLess(settled,request)
        self.assertEqual([binding['commit']],[f['value']['commit'] for f in fs if f['kind']=='state_repush'])
        self.assertTrue((self.fixture.state/'continuation-000002.once').exists());verify(out)

    def test_stranded_foreign_tip_refuses_without_push_or_request(self):
        sources,binding=self.stranded_sources();second=self.fixture.second()
        (second/'reconstruction.json').write_text('{"fixture":"foreign"}\n')
        self.fixture.git('add','reconstruction.json',cwd=second);self.fixture.git('commit','-m','Foreign fixture writer',cwd=second)
        self.fixture.git('push','origin','HEAD:refs/heads/experiment-state',cwd=second)
        original=State._git;pushes=[]
        def observed(state,*args,**kwargs):
            if args[0]=='push':pushes.append(args)
            return original(state,*args,**kwargs)
        with patch('experiment_a.continuation.STRANDED_SETTLEMENT',binding),patch.object(State,'_git',observed),patch('experiment_a.adapter.http') as transport:
            with self.assertRaisesRegex(Stop,'state_publication_failed'):
                run(self.root/'bad-second',launch=True,approved_commit='a'*40,approval=self.approval(2,sources,54),continue_from=sources,continuation=2)
            transport.assert_not_called()
        self.assertEqual([],pushes)
        self.assertFalse((self.fixture.state/'continuation-000002.once').exists())

    def test_source_tampering_after_one_new_reply_blocks_next_request(self):
        source,_=self.source();calls=[]
        def transport(p,b):
            calls.append(p)
            (source/'episode-0000/000000.json').write_bytes(b'{}\n')
            return encoded(reply(p))
        with patch('experiment_a.adapter.http',side_effect=transport):
            result=run(self.root/'out',launch=True,approved_commit='a'*40,approval=self.approval(1,[source],2),continue_from=[source],continuation=1)
        self.assertEqual(['anthropic'],calls)
        self.assertEqual('continuation_evidence_or_accounting_mismatch',result['stop'])

    def test_accounting_mismatch_refuses_without_any_mutation_or_request(self):
        source,_=self.source();state=self.state()
        path=state.ledgers['anthropic'];data=json.loads(path.read_bytes());data['estimated_api_dollars']='1';path.write_text(json.dumps(data)+'\n')
        self.fixture.git('add','ledgers/claude.json',cwd=state.root)
        self.fixture.git('commit','-m','Synthetic unreconciled total',cwd=state.root)
        self.fixture.git('push','origin','HEAD:refs/heads/experiment-state',cwd=state.root)
        before=state._git('rev-parse','HEAD')
        with patch('experiment_a.adapter.http') as transport:
            with self.assertRaisesRegex(Stop,'continuation_evidence_or_accounting_mismatch'):
                run(self.root/'bad',launch=True,approved_commit='a'*40,approval=self.approval(1,[source],2),continue_from=[source],continuation=1)
            transport.assert_not_called()
        self.assertEqual(before,state._git('rev-parse','HEAD'))

    def test_receipt_binds_exact_commit_number_checkpoints_and_index(self):
        source,_=self.source();a=self.approval(1,[source],2)
        for changes in ({'commit':'b'*40},{'continuation':2},{'start_index':0},{'source_checkpoints':['0'*63]}):
            bad=deepcopy(a);bad.update(changes)
            with patch('experiment_a.adapter.subprocess.check_output',side_effect=['a'*40,'']):
                with self.assertRaisesRegex(Stop,'launch_not_approved'):authorized('anthropic',True,'a'*40,bad)
        with patch('experiment_a.adapter.subprocess.check_output',side_effect=['a'*40,'']):
            authorized('anthropic',True,'a'*40,a)

    def test_unreported_child_and_unapproved_checkpoint_refuse(self):
        source,_=self.source();a=self.approval(1,[source],2)
        (source/'episode-0002').mkdir()
        with self.assertRaisesRegex(Stop,'continuation_evidence_or_accounting_mismatch'):Continuation([source],a).validate(self.state())
        (source/'episode-0002').rmdir()
        a['source_checkpoints']=['0'*64]
        with self.assertRaisesRegex(Stop,'continuation_evidence_or_accounting_mismatch'):Continuation([source],a).validate(self.state())

    def test_transport_reserves_and_retry_counter_survive_all_failure_classes(self):
        cases=[('partial',TransportFailure(partial=b'{'),0),
               ('nonretryable',TransportFailure(401),0),
               ('exhausted',TransportFailure(503),1)]
        for name,error,expected in cases:
            with self.subTest(name=name):
                self.fixture=GitStateFixture(self.root/('transport-'+name))
                source=self.root/('source-'+name)
                def transport(provider,body):
                    if provider=='google':raise error
                    return encoded(reply(provider))
                def adapter(*args,**kwargs):return Adapter(*args,**kwargs,sleeper=lambda seconds:None)
                with patch('experiment_a.adapter.http',side_effect=transport),patch('experiment_a.run.Adapter',side_effect=adapter):
                    report=run(source,launch=True,approved_commit='a'*40,approval=self.approval())
                self.assertEqual(expected,report['retry_needed'])
                plan=Continuation([source],self.approval(1,[source],2))
                plan.validate(self.state())
                self.assertEqual(expected,plan.retry_needed)
                self.assertGreater(Decimal(json.loads((self.fixture.state/'ledgers/google.json').read_bytes())['estimated_api_dollars']),0)


if __name__=='__main__':unittest.main()
