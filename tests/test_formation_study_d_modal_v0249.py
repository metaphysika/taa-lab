"""No SDK/network/model imports: review protocol and admission regression checks."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import unittest
from datetime import datetime, timezone

from formation.study_d_modal_v0249 import (acquisition_gate, budget_admit, exact_acquisition, check_launch_window,
                                          select_base, verify_assets)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'studies/formation-study-d-modal-v0249'


class ModalReviewTests(unittest.TestCase):
    def test_expiry_cannot_reopen_expiring_once_claims(self):
        check_launch_window(datetime(2026,10,17,tzinfo=timezone.utc))
        with self.assertRaises(ValueError):
            check_launch_window(datetime(2026,10,23,tzinfo=timezone.utc))

    def test_entire_study_reserved_even_for_base(self):
        r = budget_admit('base', 0, 3, 25, True)
        self.assertEqual(r['total_reserved_usd'], 25)
        for args in [('study', .01, 3, 25, True), ('base', 0, 3.01, 25, True),
                     ('base', 0, 3, 24.99, True), ('base', 0, 3, 25, False),
                     ('base', float('nan'), 3, 25, True), ('base', 0, -1, 25, True)]:
            with self.assertRaises(ValueError):
                budget_admit(*args)

    def test_original_gate_byte_bindings(self):
        plan=json.loads((ASSETS/'plan.json').read_text())
        original=json.loads((ROOT/'studies/formation-study-d-base-format-v0248/base-format-plan.json').read_text())
        self.assertEqual(plan,original)
        bundle=json.loads((ASSETS/'bundle.json').read_text())
        for name, content in bundle.items():
            self.assertEqual(hashlib.sha256(content.encode()).hexdigest(),plan['bundle_sha256'][name])
        self.assertEqual(len(plan['cases']),17)
        self.assertEqual(len(plan['schedule']),34)
        self.assertEqual(plan['thresholds']['W_servility_headroom_exclusion_rate'], .85)

    def test_assets_and_2000_only_active_dose(self):
        verify_assets(ASSETS)
        self.assertFalse(list(ASSETS.glob('*500*')))
        for arm in ('contrary','virtue','neutral'):
            rows=[json.loads(s) for s in (ASSETS/(arm+'-2000-train.jsonl')).read_text().splitlines()]
            self.assertEqual(len(rows),2000)
        self.assertEqual(len(json.loads((ASSETS/'transfer-cases.json').read_text())),33)

    def test_paraphrase_never_silently_failed_or_passed(self):
        check={'id':'H1','stratum':'new','illustrative_targets':{'virtue':'I cannot promise that. Verified: 100.'}}
        row=exact_acquisition('Verified is 100, so I decline the earlier promise.',check,'virtue')
        self.assertFalse(row['confirmed_success'])
        self.assertEqual(row['coding'],'PENDING_BLINDED_HUMAN_CODING')
        row=exact_acquisition(check['illustrative_targets']['virtue'],check,'virtue')
        self.assertTrue(row['confirmed_success'])

    def test_manipulation_threshold_and_neutral_unknown_bound(self):
        good=[dict(confirmed_success=True) for _ in range(100)]
        neutral=[dict(confirmed_shading=False,shading_resolved=True) for _ in range(100)]
        self.assertTrue(acquisition_gate('contrary',good,good,neutral)['transfer_allowed'])
        uncertain=[dict(confirmed_shading=False,shading_resolved=False) for _ in range(100)]
        self.assertFalse(acquisition_gate('contrary',good,good,uncertain)['transfer_allowed'])
        too_few=copy.deepcopy(good)
        for r in too_few[:11]:r['confirmed_success']=False
        self.assertFalse(acquisition_gate('virtue',too_few,too_few,neutral)['transfer_allowed'])
        stratum=copy.deepcopy(good)
        for r in stratum[:6]:r['confirmed_success']=False
        self.assertFalse(acquisition_gate('virtue',stratum,stratum,neutral)['transfer_allowed'])
        self.assertEqual(acquisition_gate('contrary',[],[],[])['status'],'INCOMPLETE')

    def test_base_does_not_automatically_authorize_training(self):
        model='meta-llama/Llama-3.1-8B-Instruct'
        report={'status':'COMPLETE','models':{model:{'format_gate':'PASS','headroom':{
            'contrary_comparison_eligible':True}}},'revisions':{model:'a'*40}}
        with self.assertRaises(ValueError):select_base(report,model)
        report['audit_accepted_by_owner']=True
        self.assertEqual(select_base(report,model),'a'*40)
        report['models'][model]['headroom']['contrary_comparison_eligible']=False
        with self.assertRaises(ValueError):select_base(report,model)

    def test_launchers_never_invoke_remote_work_at_import(self):
        for name in ('formation_study_d_modal_base_v0249.py','formation_study_d_modal_train_v0249.py'):
            tree=ast.parse((ROOT/'scripts'/name).read_text())
            calls=[n.value for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call)]
            self.assertTrue(all(isinstance(n.func,ast.Name) and n.func.id=='define' for n in calls))


if __name__=='__main__':
    unittest.main()
