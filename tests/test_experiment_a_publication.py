"""Local Git publication and bounded standing authority; sockets forbidden."""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch
import unittest

from experiment_a import config
from experiment_a.continuation import Continuation
from experiment_a.run import run,run_standing
from experiment_a.standin import reply
from experiment_a.standing import binding,successor
from experiment_a.publication import Publisher
from experiment_a.state import State
from live_demo.evidence import Evidence,encoded,verify
from live_demo.adapter import Stop
from tests import test_experiment_a_continuation as existing

class PublicationTests(unittest.TestCase):
    setUp=existing.ContinuationTests.setUp
    state=existing.ContinuationTests.state
    publisher=existing.ContinuationTests.publisher
    approval=existing.ContinuationTests.approval
    source=existing.ContinuationTests.source

    def test_episode_is_on_origin_before_next_episode_request(self):
        calls=[]
        def transport(provider,body):
            if calls:
                paths=self.fixture.git('ls-tree','-r','--name-only','experiment-a-evidence',cwd=self.fixture.remote).splitlines()
                self.assertTrue(any(p.endswith('/episode-%04d/checkpoint.json'%(len(calls)-1)) for p in paths))
                self.assertTrue(any('/root/' in p for p in paths))
            calls.append(provider);return encoded(reply(provider))
        with patch('experiment_a.adapter.http',side_effect=transport):
            result=run(self.root/'ordered',launch=True,approved_commit='a'*40,approval=self.approval())
        self.assertEqual('complete',result['stop']);self.assertEqual(4,len(calls))
        verify(self.root/'ordered/publication')

    def test_credential_in_encoded_reply_stops_without_publication_or_next_call(self):
        pub=self.publisher();before=pub._git('rev-parse','HEAD')
        response=reply('anthropic');response['content']=[dict(type='text',text='sk-ant-'+'A'*40)]
        with patch('experiment_a.adapter.http',return_value=encoded(response)) as transport:
            result=run(self.root/'credential-stop',launch=True,approved_commit='a'*40,approval=self.approval())
        self.assertEqual('evidence_credential_scan_failed',result['stop']);self.assertEqual(1,transport.call_count)
        self.assertEqual(before,pub._git('rev-parse','HEAD'));self.assertTrue((self.fixture.state/'active-run.json').exists())

    def small_publication(self):
        root=Evidence(self.root/'small');root.write('run',dict(engineering=True))
        child=Evidence(root.directory/'episode-0000');child.write('fixture',{});child.close(dict(stop='model_done'))
        return self.publisher(),root,child.directory

    def test_evidence_same_commit_repush_second_round_and_at_most_three(self):
        pub,root,child=self.small_publication();git=pub._git;pushes=[]
        def flaky(*args,**kwargs):
            if args[0]=='push':
                pushes.append(args[2])
                if len(pushes)<3:raise Stop('state_git_failure')
            return git(*args,**kwargs)
        with patch.object(pub,'_git',side_effect=flaky):pub.publish_episode(child,root)
        self.assertEqual(3,len(pushes));self.assertEqual(1,len(set(pushes)))
        self.assertEqual(git('rev-parse','HEAD'),self.fixture.git('rev-parse','experiment-a-evidence',cwd=self.fixture.remote))
        fs=[json.loads(p.read_bytes()) for p in sorted(root.directory.glob('[0-9]*.json'))]
        self.assertEqual([10,30],[f['value']['delay_seconds'] for f in fs if f['kind']=='evidence_confirmation_wait'])

    def test_evidence_three_repushes_then_stops(self):
        pub,root,child=self.small_publication();git=pub._git;pushes=[]
        def fail(*args,**kwargs):
            if args[0]=='push':pushes.append(args[2]);raise Stop('state_git_failure')
            return git(*args,**kwargs)
        with patch.object(pub,'_git',side_effect=fail):
            with self.assertRaisesRegex(Stop,'evidence_publication_failed'):pub.publish_episode(child,root)
        self.assertEqual(4,len(pushes));self.assertEqual(1,len(set(pushes)))

    def test_foreign_evidence_tip_stops_with_no_repush(self):
        pub,root,child=self.small_publication();git=pub._git;pushes=[]
        foreign=self.root/'foreign-evidence'
        self.fixture.git('worktree','add','--detach',str(foreign),'origin/experiment-a-evidence')
        self.fixture.git('commit','--allow-empty','-m','Foreign fixture writer',cwd=foreign)
        self.fixture.git('push','origin','HEAD:refs/heads/experiment-a-evidence',cwd=foreign)
        # Simulate the concurrent writer becoming visible only after our commit.
        original=pub.require_current
        with patch.object(pub,'require_current',return_value=None):
            def failed_push(*args,**kwargs):
                if args[0]=='push':pushes.append(args);raise Stop('state_git_failure')
                return git(*args,**kwargs)
            with patch.object(pub,'_git',side_effect=failed_push):
                with self.assertRaisesRegex(Stop,'evidence_publication_failed'):pub.publish_episode(child,root)
        self.assertEqual(1,len(pushes))

    def standing_approval(self,source):
        result=self.approval(1,[source],2)
        result['standing']=dict(max_continuations=3,allowed_stop_reasons=['executor_outage','state_publication_failed'])
        return result

    def stop_next(self,source,approval,*,reason='state_publication_failed'):
        state=self.state();publish=state.publish
        def stopped(description,paths):
            publish(description,paths)
            if description.startswith('settlement '):state.failed=True;raise Stop(reason)
        dest=self.root/('segment-'+str(approval['continuation']))
        with patch('experiment_a.run.State',return_value=state),patch.object(state,'publish',side_effect=stopped),patch('experiment_a.adapter.http',side_effect=lambda p,b:encoded(reply(p))):
            result=run(dest,launch=True,approved_commit='a'*40,approval=approval,continue_from=source,continuation=approval['continuation'])
        self.assertEqual(reason,result['stop'])
        return dest

    def test_standing_automatic_segments_keep_stopped_indices_and_refuse_fourth(self):
        self.schedule[:]=self.original_load('pilot-order.json')[:8]
        source,_=self.source();a=self.standing_approval(source);new=[]
        def factory(**kwargs):
            state=self.state(**kwargs);publish=state.publish
            def stopped(description,paths):
                publish(description,paths)
                if description.startswith('settlement '):state.failed=True;raise Stop('state_publication_failed')
            state.publish=stopped;return state
        def transport(p,b):new.append(p);return encoded(reply(p))
        with patch('experiment_a.run.State',side_effect=factory),patch('experiment_a.adapter.http',side_effect=transport):
            run_standing(self.root/'standing',launch=True,approved_commit='a'*40,approval=a,continue_from=[source],continuation=1)
        self.assertEqual(3,len(new))
        roots=[self.root/'standing',self.root/'standing-continuation-000002',self.root/'standing-continuation-000003']
        indices=[]
        for n,root in enumerate(roots,1):
            verify(root)
            indices.extend(int(p.name.split('-')[1]) for p in root.glob('episode-*'))
            marker=json.loads((self.fixture.state/('continuation-%06d.once'%n)).read_text())
            self.assertEqual(n,marker['standing_segment']);self.assertEqual(binding(a)['receipt_sha256'],marker['standing_receipt_sha256'])
        self.assertEqual([2,3,4],indices);self.assertFalse((self.fixture.state/'continuation-000004.once').exists())
        latest=json.loads((roots[-1]/'000000.json').read_text())['value']['approval']
        with self.assertRaisesRegex(Stop,'standing_limit_or_binding'):successor(latest,[source]+roots)

    def test_standing_disallowed_stop_and_changed_commit_refuse(self):
        source,_=self.source();a=self.standing_approval(source)
        stopped=self.stop_next([source],a,reason='cap_stop')
        with self.assertRaisesRegex(Stop,'standing_stop_not_allowed'):successor(a,[source,stopped])
        bad=deepcopy(a);bad['standing']['allowed_stop_reasons']=['cap_stop']
        with self.assertRaisesRegex(Stop,'standing_not_approved'):binding(bad)

    def test_standing_failed_chain_and_mismatched_accounting_refuse_before_request(self):
        source,_=self.source();a=self.standing_approval(source);stopped=self.stop_next([source],a)
        b=successor(a,[source,stopped])
        path=self.fixture.state/'ledgers/claude.json';data=json.loads(path.read_text());data['estimated_api_dollars']=9
        path.write_text(json.dumps(data));self.fixture.git('add','ledgers/claude.json',cwd=self.fixture.state)
        self.fixture.git('commit','-m','Engineering mismatch',cwd=self.fixture.state);self.fixture.git('push','origin','HEAD:refs/heads/experiment-state',cwd=self.fixture.state)
        with patch('experiment_a.adapter.http') as request:
            with self.assertRaisesRegex(Stop,'continuation_evidence_or_accounting_mismatch'):
                run(self.root/'mismatch',launch=True,approved_commit='a'*40,approval=b,continue_from=[source,stopped],continuation=2)
            request.assert_not_called()
        (stopped/'episode-0002/000000.json').write_bytes(b'{}\n')
        with self.assertRaisesRegex(Stop,'standing_evidence_invalid'):successor(a,[source,stopped])

    def test_standing_changed_commit_and_open_reservation_refuse(self):
        source,_=self.source();a=self.standing_approval(source);stopped=self.stop_next([source],a)
        b=successor(a,[source,stopped]);bad=deepcopy(b);bad['commit']='b'*40
        with self.assertRaisesRegex(Stop,'standing_limit_or_binding'):binding(bad)
        # The same settlement auditor must reject a retained, unissued reserve.
        totals={'anthropic':__import__('decimal').Decimal(0),'google':__import__('decimal').Decimal(0)}
        fs=[dict(kind='reservation',value=dict(provider='google',dollars='1')),
            dict(kind='ledger_change',value=dict(provider='google',delta='1',prior='0',after='1',step_prior='0',step_after='1'))]
        with self.assertRaisesRegex(ValueError,'open reservation'):
            Continuation([source],a)._account(fs,totals,__import__('decimal').Decimal(0),require_settled=True)

    def test_standing_failed_publication_journal_refuses(self):
        source,_=self.source();a=self.standing_approval(source);stopped=self.stop_next([source],a)
        b=successor(a,[source,stopped])
        (stopped/'publication/000000.json').write_bytes(b'{}\n')
        with self.assertRaisesRegex(Stop,'standing_evidence_invalid'):successor(a,[source,stopped])
        with patch('experiment_a.adapter.http') as transport:
            with self.assertRaisesRegex(Stop,'continuation_evidence_or_accounting_mismatch'):
                run(self.root/'invalid-publication',launch=True,approved_commit='a'*40,approval=b,continue_from=[source,stopped],continuation=2)
            transport.assert_not_called()

    def test_accepted_outage_child_without_score_advances_cursor_and_is_never_rerun(self):
        source,_=self.source();a=self.standing_approval(source);out=self.root/'outage'
        close=Evidence.close
        def interrupted_close(e,value):
            if value.get('stop')=='review_required':return None
            return close(e,value)
        with patch('experiment_a.run.episode',side_effect=SystemExit('engineering executor loss')),patch.object(Evidence,'close',interrupted_close):
            with self.assertRaises(SystemExit):
                run(out,launch=True,approved_commit='a'*40,approval=a,continue_from=[source],continuation=1)
        def append(path):
            from experiment_a.continuation import frames
            # Simulated executor died before it could close the root.
            ps=sorted(path.glob('[0-9]*.json'));e=Evidence.__new__(Evidence);e.directory=path
            e.sequence=len(ps);e.head=__import__('hashlib').sha256(ps[-1].read_bytes()).hexdigest() if ps else '0'*64
            return e
        child=out/'episode-0002';append(child).close(dict(stop='executor_outage',episode_end_absent=True))
        append(out).close(dict(stop='executor_outage',interrupted_index=2))
        b=successor(a,[source,out]);self.assertEqual(3,b['start_index'])
        with patch('experiment_a.adapter.http',side_effect=lambda p,body:encoded(reply(p))) as transport:
            result=run(self.root/'after-outage',launch=True,approved_commit='a'*40,approval=b,continue_from=[source,out],continuation=2)
        self.assertEqual([self.schedule[3]],[r['spec'] for r in result['episodes']]);self.assertEqual(1,transport.call_count)
        self.assertFalse(any(json.loads(p.read_bytes())['kind']=='episode_end' for p in child.glob('[0-9]*.json')))
