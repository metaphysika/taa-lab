"""Test-only immutable provider-ledger snapshots; no live ledger reads/writes."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'results/formation-spending-v021/'
SNAPSHOTS = ROOT / 'tests/fixtures/formation-ledger-snapshots'


def snapshot_path(relative, expected_sha256):
    allowed = {PREFIX + n for n in ('openai.json', 'claude.json', 'google.json', 'groq.json', 'groq-rate.json')}
    if relative not in allowed or len(expected_sha256) != 64 or any(c not in '0123456789abcdef' for c in expected_sha256):
        raise AssertionError('invalid pinned ledger snapshot request')
    source = SNAPSHOTS / (expected_sha256 + '.json')
    if hashlib.sha256(source.read_bytes()).hexdigest() != expected_sha256:
        raise AssertionError('immutable ledger snapshot hash differs: ' + relative)
    return source


def install_snapshots(test_root, bindings):
    root = Path(test_root).resolve()
    if root == ROOT.resolve() or root == (ROOT / 'results/formation-spending-v021').resolve():
        raise AssertionError('never install historical ledgers into the production checkout')
    for relative, digest in bindings.items():
        source = snapshot_path(relative, digest)
        target = root / relative
        if (ROOT / 'results/formation-spending-v021').resolve() in target.resolve().parents:
            raise AssertionError('snapshot destination resolves to production ledger')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
