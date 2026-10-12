"""Prospective wording only: preserve completed pilot and paired evidence."""
import hashlib
from tests.ledger_snapshots import PREFIX, snapshot_path
import json
import unittest
from pathlib import Path
from scripts.formation_study_b_review_v0230 import build_cases, RULES, COMMON
from scripts.formation_study_b_gate5a_v0228 import build_cases as old_cases, PRESSURE, dry_run
from formation.study_b_v0227 import visible
ROOT = Path(__file__).resolve().parents[1]

class ProspectiveWordingTests(unittest.TestCase):
    def test_twins_differ_only_in_deciding_evidence(self):
        cases = build_cases()
        self.assertEqual(len(cases),72)
        for pair in {c['pair_id'] for c in cases}:
            masked=[]
            for c in [x for x in cases if x['pair_id']==pair]:
                masked.append(json.dumps(visible(c),sort_keys=True).replace(json.dumps(c['deciding_evidence'])[1:-1],'<EVIDENCE>'))
            self.assertEqual(*masked)

    def test_prerequisites_are_rung_scoped_and_report_is_conditional(self):
        for c in build_cases():
            if c['family'] != 'WU': continue
            parent=c['answer_key']['rung4_source'] if c['rung']==4 else c['rung']
            r=c['world']['records']['PRIMARY']
            self.assertEqual(r['release_rule'],RULES[c['theme']][parent])
            self.assertEqual(r['common_prerequisites'],COMMON[c['theme']][parent])
            if c['rung']<4:
                self.assertIn('If you identify a problem with the primary order',c['task'])
                self.assertNotIn('Report any primary-order issue',c['task'])
                self.assertIn(r['common_prerequisites'],c['task'])
            else:
                self.assertNotIn(r['common_prerequisites'],c['task'])
                self.assertNotIn(c['deciding_evidence'],c['task'])
            if parent==3: self.assertIn('requires',r['release_rule'])

    def test_only_authorized_visible_fields_change(self):
        for new,old in zip(build_cases(),old_cases()):
            self.assertEqual(new['deciding_evidence'],old['deciding_evidence'])
            self.assertEqual(new['answer_key'],old['answer_key'])
            self.assertEqual(new['task'].count(PRESSURE),int(new['pressure']))
            a,b=visible(new),visible(old)
            if new['family']=='WU':
                a['task']=b['task']
                a['world']['records']['PRIMARY']['release_rule']=b['world']['records']['PRIMARY']['release_rule']
                del a['world']['records']['PRIMARY']['common_prerequisites']
            self.assertEqual(a,b)

    def test_parent_records_identical_and_all_labels_reachable(self):
        cases=build_cases()
        for c in cases:
            if c['family']=='WU' and c['rung']==4:
                parent=next(x for x in cases if x['theme']==c['theme'] and x['kind']==c['kind'] and x['pressure']==c['pressure'] and x['rung']==c['answer_key']['rung4_source'])
                self.assertEqual(c['world']['records'],parent['world']['records'])
        self.assertEqual(len(dry_run(cases)),89)

    def test_saved_cases_and_unapproved_new_cost_plan(self):
        plan=json.loads((ROOT/'studies/formation-study-b-luna-pilot-cost-plan-v0230.json').read_text())
        for path,digest in plan['case_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest)
        self.assertEqual(plan['settings']['max_output_tokens'],2048)
        self.assertEqual(plan['proposed_batch_cap_dollars'],0.25)
        self.assertAlmostEqual(plan['OpenAI_cumulative_start_dollars'],0.256613715)
        self.assertIn('PROPOSED ONLY',plan['status'])
        self.assertNotEqual(plan['output'],'results/2026-10-12 v0.22.8 luna-none r1 study-b pilot')

    def test_completed_pilot_snapshot_unchanged(self):
        index=json.loads((ROOT/'results/2026-10-12 v0.22.8 luna-none r1 study-b pilot/integrity-snapshot.json').read_text())
        for path,digest in index['sha256'].items():
            self.assertNotIn('keys.env',path)
            source=snapshot_path(path,digest) if path.startswith(PREFIX) else ROOT/path
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),digest,path)

if __name__=='__main__': unittest.main()
