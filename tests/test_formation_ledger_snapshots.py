"""Pinned test ledgers do not depend on changing production spending."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tests.ledger_snapshots import ROOT, PREFIX, SNAPSHOTS, install_snapshots, snapshot_path

class LedgerSnapshotTests(unittest.TestCase):
    def test_all_historical_bindings_verified_without_reading_live_ledgers(self):
        manifest=json.loads((SNAPSHOTS/'manifest.json').read_text())['sha256_to_original_bindings']
        original=Path.read_bytes
        def guarded(path):
            if (ROOT/'results/formation-spending-v021').resolve() in path.resolve().parents:
                raise AssertionError('test must not read current production ledger')
            return original(path)
        with tempfile.TemporaryDirectory() as folder,patch.object(Path,'read_bytes',guarded):
            for digest,bindings in manifest.items():
                for b in bindings:
                    install_snapshots(folder,{b['ledger_path']:digest})
                    self.assertEqual(hashlib.sha256((Path(folder)/b['ledger_path']).read_bytes()).hexdigest(),digest)
    def test_corrupt_snapshot_and_production_destination_rejected(self):
        digest=next(iter(json.loads((SNAPSHOTS/'manifest.json').read_text())['sha256_to_original_bindings']))
        binding=json.loads((SNAPSHOTS/'manifest.json').read_text())['sha256_to_original_bindings'][digest][0]
        with self.assertRaises(AssertionError):install_snapshots(ROOT,{binding['ledger_path']:digest})
        with patch.object(Path,'read_bytes',return_value=b'corrupt'):
            with self.assertRaises(AssertionError):snapshot_path(binding['ledger_path'],digest)
