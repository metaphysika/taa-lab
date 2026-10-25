"""The Q18 source exception cannot admit unverified or unrelated changes."""
from pathlib import Path
import hashlib,importlib.util,json,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('preservation_guard',ROOT/'scripts/check_live_demo_preservation.py')
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)


class Q18PreservationGuard(unittest.TestCase):
    def test_default_has_no_policy_exception(self):
        self.assertEqual(guard.policy_delta(None),{})

    def test_verified_exact_files_only_and_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);hashes={}
            for name in guard.Q18_POLICY_FILES:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('synthetic policy fixture\n')
                hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
            row=dict(owner='Chris',ruling='Q18',frozen_acceptance_pass=True,comparison_pass=True,changed_scores=0,source_sha256=hashes)
            record=root/'record.json'
            def save():record.write_text(json.dumps({'q18_policy_delta':row}))
            save();self.assertEqual(guard.policy_delta(record,root),hashes)
            target=root/'taa_gateway/refunds.py';target.write_text('different source\n')
            with self.assertRaises(ValueError):guard.policy_delta(record,root)
            target.write_text('synthetic policy fixture\n')
            row['source_sha256']={**hashes,'comparators/commit_oracle.py':'not permitted'};save()
            with self.assertRaises(ValueError):guard.policy_delta(record,root)
            row['source_sha256']=hashes;row['comparison_pass']=False;save()
            with self.assertRaises(ValueError):guard.policy_delta(record,root)
            row['comparison_pass']=True;row['changed_scores']=1;save()
            with self.assertRaises(ValueError):guard.policy_delta(record,root)
            row['changed_scores']=False;save()
            with self.assertRaises(ValueError):guard.policy_delta(record,root)
