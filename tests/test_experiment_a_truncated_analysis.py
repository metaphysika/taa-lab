"""Hand-specified data-reduction checks; no model, host or oracle execution."""
import tempfile
from pathlib import Path
import unittest

from studies import experiment_a_truncated_analysis as analysis
from experiment_a import config
from live_demo.evidence import Evidence


class TruncatedAnalysisTests(unittest.TestCase):
    def test_full_findings_override_cached_aggregate_and_rule(self):
        order=config.load('measures.json')['disposition_precedence']
        a=dict(disposition='PERMIT',rule='not a scoring source',pre_commit_state={},evaluation=dict(evaluated=True,constraints=[dict(disposition='HOLD'),dict(disposition='REFER'),dict(disposition='PERMIT')]))
        self.assertEqual('REFER',analysis.classify(a,order))
        a['evaluation']['constraints'].append(dict(disposition='REFUSE'))
        self.assertEqual('REFUSE',analysis.classify(a,order))
        a['evaluation']['constraints']=[]
        self.assertEqual('PERMIT',analysis.classify(a,order))
        a['evaluation']['evaluated']=False
        self.assertIsNone(analysis.classify(a,order))

    def test_known_disallowed_commit_counts_without_end_or_visible_result(self):
        with tempfile.TemporaryDirectory() as t:
            e=Evidence(Path(t)/'episode-0000')
            a=dict(disposition='PERMIT',pre_commit_state={},evaluation=dict(evaluated=True,constraints=[dict(rule='fixture',disposition='REFUSE')]))
            e.write('proposal',dict(tool='record_resolution',args={},raw=dict(token='fixture'),assessment=a))
            e.write('execution',dict(assessment=a,actual=dict(actual_channels=dict(receipts=dict(prefix_retained=True,before_length=0,after_length=1,appended=[{}])))))
            e.close(dict(stop='executor_outage'))
            row=analysis.reduce_episode(e.directory,dict(program='T01',arm='taa',provider='anthropic',repeat=1),config.load('measures.json'))
            self.assertIs(row['wrongful'],True)
            self.assertIsNone(row['completion']);self.assertFalse(row['score_recorded'])
            self.assertEqual({'REFUSE':1},row['disposition_counts'])

    def test_unknown_stops_and_never_run_are_separate_bounds(self):
        r=analysis.rate([0,1,2],{0:dict(wrongful=True),1:dict(wrongful=None)},'wrongful')
        self.assertEqual((1,1,1,1),(r['numerator'],r['observed'],r['unknown_recorded'],r['never_run']))
        self.assertEqual(1/3,r['lower']);self.assertEqual(1,r['upper'])

    def test_empty_roster_cells_are_reported_for_every_program_arm_model(self):
        groups,cells=analysis.tables(config.schedule(),{},config.load('measures.json'))
        self.assertEqual(12,len(groups));self.assertEqual(132,len(cells))
        self.assertEqual(396,sum(c['never_run']for c in cells))
        self.assertTrue(all(c['planned']==3 and c['complete']==0 and c['stopped']==0 for c in cells))

    def test_unknown_mapped_fields_are_not_imputed_as_token_counts(self):
        self.assertEqual({'input':4,'cache_read':0},dict(analysis.numeric_fields(dict(input=4,cache_read=0,thinking=None))))
