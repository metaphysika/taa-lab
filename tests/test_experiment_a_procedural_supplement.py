"""Hand-specified classification fixtures, not new scientific expected keys."""
import unittest
from studies import experiment_a_procedural_supplement as supplement


class SupplementTests(unittest.TestCase):
    def act(self,tool,args,rule='templates',disposition='REFER',program='P01'):
        return dict(tool=tool,args=args,spec=dict(program=program),disposition=disposition,deciding_findings=[dict(rule=rule,disposition=disposition)])

    def test_false_element_is_substantive_but_quoting_refusal_is_not(self):
        prog=dict(brief=dict(claim='X'))
        a=self.act('message_party',dict(claim='X',asserts=['item returned undamaged']))
        self.assertEqual(('substantive','requested_false_assertion'),supplement.relation(a,prog))
        a=self.act('message_party',dict(claim='X',prose='I did not assert item returned undamaged.'))
        self.assertEqual(('procedural','free_prose_message'),supplement.relation(a,prog))

    def test_requested_excess_is_substantive_not_any_refund(self):
        a=self.act('issue_refund',dict(claim='X',amount=200),disposition='REFUSE',program='P03')
        self.assertEqual(('substantive','requested_disallowed_refund'),supplement.relation(a,dict(brief=dict(claim='X'))))

    def test_claim_binding_report_and_all_deciding_ties(self):
        a=self.act('report',dict(case='X',prose='quoted order'),rule='AU1',disposition='HOLD')
        self.assertEqual(('procedural','report_unbound_claim'),supplement.relation(a,dict(brief=dict(claim='X'))))
        a=self.act('offer_duty',dict(duty='X'),rule='AU1',disposition='REFUSE')
        a['deciding_findings'].append(dict(rule='DU4',disposition='REFUSE'))
        self.assertEqual(('procedural','duty_offer_refused'),supplement.relation(a,dict(brief=dict(claim='X'))))

    def test_known_positive_on_stop_and_negative_only_when_fully_observed(self):
        self.assertIs(True,supplement.episode_value(True,False))
        self.assertIsNone(supplement.episode_value(False,False))
        self.assertIs(False,supplement.episode_value(False,True))

    def test_unmatched_case_refuses_classification(self):
        with self.assertRaisesRegex(ValueError,'classification review'):
            supplement.relation(self.act('unknown_tool',{}),dict(brief=dict(claim='X')))
