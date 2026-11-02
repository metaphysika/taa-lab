import copy
import json
from pathlib import Path
import tempfile
import unittest

from exploratory.audit_tool.modal_adapter import launch_guard, mock, sha, verify_checkpoint


class AdapterTests(unittest.TestCase):
    def test_mock_and_turn_limit(self):
        self.assertEqual(json.loads(mock().generate('system', [], 1))['tool'], None)
        with self.assertRaises(ValueError):
            mock().generate('', [], 13)

    def test_launch_barriers(self):
        for confirm, env in [(False, {}), (True, {'CI': 'true'}), (True, {'TAA_TEST': '1'})]:
            with self.assertRaises(ValueError):
                launch_guard(confirm, env)
        self.assertEqual(launch_guard(True, {}), 12)

    def test_checkpoint_corruption(self):
        for arm in ('neutral', 'contrary', 'virtue'):
            with self.subTest(arm=arm), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)/'science'/arm/'final'
                folder.mkdir(parents=True)
                files = {}
                for name in ('README.md', 'adapter_config.json', 'adapter_model.safetensors'):
                    path = folder/name
                    path.write_bytes(b'fixture')
                    files[name] = dict(sha256=sha(path), bytes=7)
                index = folder/'checkpoint-integrity.json'
                index.write_text(json.dumps(dict(arm=arm, complete=True, scientific_checkpoint=True,
                                                sha256={n: v['sha256'] for n, v in files.items()})))
                plan = dict(checkpoints=[dict(arm=arm, path='science/'+arm+'/final',
                            files=files, checkpoint_index_sha256=sha(index))])
                self.assertEqual(verify_checkpoint(tmp, arm, plan), folder)
                (folder/'adapter_model.safetensors').write_bytes(b'corrupt')
                with self.assertRaises(ValueError):
                    verify_checkpoint(tmp, arm, plan)
                (folder/'adapter_model.safetensors').write_bytes(b'fixture')
                index.write_text('{}')
                with self.assertRaises(ValueError):
                    verify_checkpoint(tmp, arm, plan)


if __name__ == '__main__':
    unittest.main()
