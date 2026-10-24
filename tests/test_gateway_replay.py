"""Read-only replay coverage, evidence attribution and adversarial text controls."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest
from replay import build as replay
from taa_gateway.eventlog import EventLog

ROOT=Path(__file__).resolve().parents[1]
VALIDATION=ROOT/'docs/process/evidence/gateway-cross-arm-scoring-v01-corrected/validation.json'


class ArchiveFixture(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        # Do not retain bulk replay data in the shared discovery process.
        # Later admission subprocesses inherit the parent resident footprint.
        for name in ("episodes", "manifest", "source", "schedules"):
            if name in cls.__dict__:delattr(cls,name)
        import gc
        gc.collect()


class ReplayTests(ArchiveFixture):
    @classmethod
    def setUpClass(cls):
        cls.episodes,cls.manifest,cls.source=replay.read_evidence(VALIDATION)
        cls.schedules=replay.schedules(ROOT,cls.manifest)

    def test_all_320_schedules_align_without_running_a_policy(self):
        count=0
        for e in self.episodes:
            rows,_=replay.timeline(e,self.schedules[e['case'],e['controller']])
            count+=len(rows)
            self.assertEqual([r['index'] for r in rows],list(range(len(rows))))
        self.assertEqual(count,2912)

    def test_same_retained_log_produces_identical_pages_and_source_is_immutable(self):
        es=[e for e in self.episodes if e['case']=='T03' and e['controller']=='correct' and e['arm'] in ('taa','conventional')]
        m=dict(self.manifest,arms=['taa','conventional']);before=deepcopy(es)
        a,ma=replay.build(es,m,self.source,self.schedules)
        b,mb=replay.build(es,m,self.source,self.schedules)
        self.assertEqual(a,b);self.assertEqual(ma,mb);self.assertEqual(es,before)
        self.assertEqual(ma['episode_pages'],2);self.assertEqual(ma['comparison_pages'],1)
        self.assertIn(b'data-column="conventional"',a['T03--correct.html'])

    def test_missing_token_states_and_oracle_reports_are_never_fabricated(self):
        e=next(e for e in self.episodes if e['case']=='T03' and e['controller']=='correct' and e['arm']=='taa')
        text=replay.column(e,self.schedules[e['case'],e['controller']])
        self.assertIn('not retained in this journal',text)
        self.assertIn('NOT dispatch artifacts',text)
        self.assertIn('refused_stale_revision',text)
        self.assertIn('Actual report-delivery aggregate retained:',text)
        self.assertIn('not the arm’s internal duty ledger',text)
        cautious=next(x for x in self.episodes if x['case']=='T03' and x['controller']=='cautious' and x['arm']=='taa')
        held=replay.column(cautious,self.schedules[cautious['case'],cautious['controller']])
        self.assertIn('agent withheld request — gateway not called',held)
        self.assertIn('no token was issued',held)
        wrong=deepcopy(e);wrong['observations'][0]['actor']='forged'
        with self.assertRaises(ValueError):replay.timeline(wrong,self.schedules[e['case'],e['controller']])

    def test_untrusted_text_is_escaped_and_network_code_is_absent(self):
        hostile='</script><img src="https://example.invalid/exfil" onerror="alert(1)">'
        doc=replay.document(hostile,replay.detail('record',{'value':hostile})).decode()
        self.assertNotIn('<img',doc);self.assertNotIn('onerror="alert',doc)
        self.assertIn('&lt;/script&gt;',doc);self.assertIn("default-src &#x27;none&#x27;",doc)
        self.assertNotIn('fetch(',doc)
        with self.assertRaises(ValueError):replay.filename('../escape')

    def test_native_chain_has_actual_token_and_report_events_and_rejects_edits_or_truncation(self):
        log=EventLog('replay-control',b'offline-replay-component-key-0000')
        for typ in ('token_issued','token_voided','duty_transition','report_sent','receipt'):
            log.append(1,typ,{'retained':typ})
        checkpoint=log.seal();blob=log.jsonl();doc=replay.native_document(blob,checkpoint)
        self.assertIn(b'token_voided',doc);self.assertIn(b'report_sent',doc)
        self.assertIn(b'HMAC authentication tag has not been verified',doc)
        mutated=blob.replace(b'"retained":"token_issued"',b'"retained":"edited"')
        with self.assertRaises(ValueError):replay.native_document(mutated,checkpoint)
        rows=blob.splitlines();truncated=b'\n'.join(rows[:-2]+rows[-1:])+b'\n'
        with self.assertRaises(ValueError):replay.native_document(truncated,checkpoint)


class RetainedReplayTests(ArchiveFixture):
    @classmethod
    def setUpClass(cls):
        cls.episodes,cls.manifest,cls.source=replay.read_evidence(ROOT/'docs/process/evidence/gateway-cross-arm-scoring-v02/validation.json')
        cls.schedules=replay.schedules(ROOT,cls.manifest)

    def test_all_actual_channels_reconstruct_and_align_with_2912_observations(self):
        from replay.retained import transitions
        count=0
        for e in self.episodes:
            rows,_=replay.timeline(e,self.schedules[e['case'],e['controller']])
            actual=list(transitions(e));actions=[t for t in actual if t['phase'] in ('proposal','agent_withholding','execution')]
            self.assertEqual(len(actions),len(rows));count+=len(actions)
            self.assertEqual([t['step'] for t in actions],[r['step'] for r in rows])
        self.assertEqual(count,2912)

    def test_actual_pages_are_deterministic_and_show_token_and_record_changes(self):
        es=[e for e in self.episodes if e['case']=='T03' and e['controller']=='correct' and e['arm'] in ('taa','conventional')]
        m=dict(self.manifest,arms=['taa','conventional']);before=deepcopy(es)
        a,proof=replay.build(es,m,self.source,self.schedules);b,again=replay.build(es,m,self.source,{})
        self.assertEqual(a,b);self.assertEqual(proof,again);self.assertEqual(es,before)
        self.assertEqual(proof['coverage_gaps'],[]);self.assertEqual(proof['retained_state_episodes'],2)
        page=a['T03--correct--taa.html'].decode()
        self.assertIn('Actual token, record, duty, report, notice and receipt changes',page)
        self.assertIn('Observed revision before / after',page)
        self.assertIn('HMAC authentication',page);self.assertNotIn('full native lifecycle not retained',page)
        self.assertIn('record_correction',page)

    def test_inconsistent_before_values_missing_channels_and_log_prefixes_fail_closed(self):
        from replay.retained import transitions
        original=next(e for e in self.episodes if e['case']=='T03' and e['controller']=='correct' and e['arm']=='taa')
        wrong=deepcopy(original)
        t=next(t for t in wrong['actual_transitions'] if 'revision' in t['actual_channels'])
        t['actual_channels']['revision']['before']=-1
        with self.assertRaises(ValueError):list(transitions(wrong))
        wrong=deepcopy(original);del wrong['actual_initial']['channels']['tokens']
        with self.assertRaises(ValueError):list(transitions(wrong))
        wrong=deepcopy(original);wrong['actual_transitions'][0]['actual_event_log']['before_length']+=1
        with self.assertRaises(ValueError):list(transitions(wrong))
        wrong=deepcopy(original);del wrong['actual_initial']
        with self.assertRaises(ValueError):replay.column(wrong,self.schedules[wrong['case'],wrong['controller']])
