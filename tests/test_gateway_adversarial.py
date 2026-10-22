"""Sol-authored adversarial/interface controls from W0; Claude review pending."""
from copy import deepcopy
import unittest
from tests.adversarial_support import controls,coverage,actor_program
from tests.trace_support import reference_runner as runner,production_backend as core
from tests.trace_support.bundle import world
from taa_gateway_reference import refunds as reference


class AdversarialTests(unittest.TestCase):
    def test_every_named_attack_path_has_existing_source_cases(self):
        mapping,missing=coverage()
        self.assertEqual(missing,{})
        self.assertGreaterEqual(len(mapping),22)
        self.assertTrue(all(ids for ids in mapping.values()))

    def test_attacker_input_is_independent_of_expected_outcomes(self):
        for c in controls():
            before=actor_program(c)
            changed=deepcopy(c)
            for e in changed['trace']['steps']:
                e['expect']={'disposition':'deliberately wrong answer'}
            changed['trace']['final']={'committed':['wrong answer']}
            self.assertEqual(actor_program(changed),before)
            self.assertNotIn('expect',repr(before))

    def test_three_controls_pass_both_backends_with_full_state_audits(self):
        for backend in (None,core):
            for c in controls():
                with self.subTest(backend=backend,case=c['id']):
                    rows=runner.run(c,backend=backend)
                    self.assertFalse([r for r in rows if r['status']!='pass'])
                    self.assertTrue(any(r['origin']=='state-audit' and r['assertion'].endswith('state_delta') for r in rows))

    def test_bad_arguments_reject_before_reporting_and_preserve_full_state(self):
        valid={'claim':'CL1','amount':120,'to':'K1_card','basis':'return'}
        bad=[dict(valid,issuer='F'),dict(valid,amount=True),dict(valid,asserts='return received'),dict(valid,basis='made-up'),
             {k:v for k,v in valid.items() if k!='amount'}]
        for backend in (reference,core):
            for args in bad:
                with self.subTest(backend=backend.__name__,args=args):
                    state=backend.start(world());before=deepcopy(state)
                    after,result=backend.propose(state,'A','issue_refund',args)
                    self.assertEqual(result['call_result'],'rejected_arguments')
                    self.assertFalse(result['evaluated'])
                    for key in before.keys()-{'log'}:
                        self.assertEqual(before[key],after[key],key)
                    self.assertGreater(len(after['log']),len(before['log']))

    def test_authenticated_issuer_and_source_boundary_controls_exist(self):
        from tests.test_gateway_foundation import FoundationTests
        self.assertTrue(callable(FoundationTests.test_order_issuer_is_authenticated_not_claimed))
        self.assertTrue(callable(FoundationTests.test_forged_session_and_wrong_source_rejected))
