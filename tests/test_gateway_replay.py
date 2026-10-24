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


class ReplayTests(unittest.TestCase):
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
