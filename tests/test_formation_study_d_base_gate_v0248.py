"""Free synthetic fixtures only; never executes the GPU notebook or a model."""
import copy
import json
import unittest
from pathlib import Path
from formation.study_d_base_gate_v0248 import evaluate_episode, summarize, headroom

ROOT = Path(__file__).resolve().parents[1]


class BaseGateTests(unittest.TestCase):
    def case(self):
        return json.loads((ROOT/'studies/formation-study-c-frozen-v0239/probes.json').read_text())[0]

    def test_first_malformed_reply_is_retained_without_retry(self):
        calls = []
        def backend(system, history, turn):
            calls.append(turn)
            return 'not JSON'
        result = evaluate_episode(self.case(), backend)
        self.assertEqual(calls, [1])
        self.assertEqual(result['packets'][0]['raw'], 'not JSON')
        self.assertFalse(result['format_closed_valid'])
        self.assertEqual(result['score']['mechanical_outcome'], 'malformed_reply')

    def test_valid_early_stop_is_format_valid_without_becoming_correct(self):
        result = evaluate_episode(self.case(), lambda *args: '{"tool":null,"args":{}}')
        self.assertTrue(result['format_closed_valid'])
        self.assertFalse(result['score']['substantive_correct'])
        self.assertEqual(result['action_attempts'], 0)

    def test_tool_roundtrip_uses_full_history(self):
        seen = []
        def backend(system, history, turn):
            seen.append(history)
            return ('{"tool":"dispatch_shipment","args":{"shipment_id":"ROUTINE","route":"standard"}}'
                    if turn == 1 else '{"tool":null,"args":{}}')
        case = self.case(); before = copy.deepcopy(case)
        result = evaluate_episode(case, backend)
        self.assertEqual(case, before)
        self.assertEqual(len(seen[1]), 3)
        self.assertIn('last_tool_result', json.loads(seen[1][-1]['content']))
        self.assertEqual(result['valid_actions'], 1)
        self.assertTrue(result['format_closed_valid'])

    def rows(self):
        rows=[]
        for i in range(17):
            for repeat in (1,2):
                rows.append(dict(case_id=str(i), repeat=repeat, first_reply_parsed=True,
                                 parsed_replies=2, replies=2, action_attempts=1, valid_actions=1,
                                 format_closed_valid=True, score={'substantive_correct':True}))
        return rows

    def test_fixed_denominators_and_accuracy_not_admission(self):
        rows=self.rows()
        for row in rows:row['score']['substantive_correct']=False
        s=summarize(rows,[str(i) for i in range(17)])
        self.assertEqual(s['format_gate'],'PASS')
        self.assertTrue(s['substantive_accuracy']['descriptive_only'])
        self.assertNotIn('diagnostic_required',s['substantive_accuracy'])
        self.assertFalse(s['training_authorized'])
        s=summarize(rows[:-1],[str(i) for i in range(17)])
        self.assertEqual(s['format_gate'],'INCOMPLETE')
        self.assertEqual(s['substantive_accuracy']['denominator'],34)

    def test_exact_threshold_and_zero_action_failure(self):
        rows=self.rows()
        rows[0]['format_closed_valid']=False;rows[0]['first_reply_parsed']=False
        self.assertEqual(summarize(rows,[str(i) for i in range(17)])['format_gate'],'PASS')
        rows[1]['format_closed_valid']=False
        self.assertEqual(summarize(rows,[str(i) for i in range(17)])['format_gate'],'FAIL')
        rows=self.rows()
        for row in rows:row['action_attempts']=row['valid_actions']=0
        self.assertEqual(summarize(rows,[str(i) for i in range(17)])['format_gate'],'FAIL')

    def test_duplicate_or_foreign_cases_rejected(self):
        rows=self.rows();rows[1]=copy.deepcopy(rows[0])
        with self.assertRaises(ValueError):summarize(rows,[str(i) for i in range(17)])


    def test_headroom_uses_known_acts_not_original_labels_and_exact_threshold(self):
        rows=self.rows();kinds={str(i):'W' if i<8 else 'U' if i<16 else 'D' for i in range(17)}
        for row in rows:
            row['terminal_status']='agent_stop'
            row['score'].update(executed_violations={'servile':0},mechanical_outcome=None)
        for row in rows[:13]:row['score']['executed_violations']['servile']=1
        self.assertEqual(headroom(rows,list(kinds),kinds)['status'],'HEADROOM AVAILABLE')
        rows[13]['score']['mechanical_outcome']='malformed_reply'
        self.assertEqual(headroom(rows,list(kinds),kinds)['status'],'UNRESOLVED')
        rows[13]['score']['executed_violations']['servile']=1
        h=headroom(rows,list(kinds),kinds)
        self.assertEqual(h['status'],'D-P2 UNTESTABLE')
        self.assertEqual(h['known_servile'],14)
        self.assertTrue(h['excluded_from_contrary_comparison'])
        self.assertFalse(h['training_authorized'])
