"""EXPLORATORY step 4; imports and mock mode allocate no resources."""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT/'studies/formation-study-d-analysis-v02430/private-adapter-deletion-plan.json'
TIMEOUT, IDLE = 21600, 300
CAP = math.ceil((TIMEOUT + IDLE + 120) / 3600 * 3.20 + .40)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_checkpoint(root, arm, plan=None):
    """Mirror verify_reused_adapter checks, bound to published final hashes."""
    plan = json.loads(PLAN.read_text()) if plan is None else plan
    entry, = [r for r in plan['checkpoints'] if r['arm'] == arm]
    root = Path(root)
    folder = root/entry['path']
    if not root.is_dir():
        raise ValueError('missing checkpoint mount')
    for path in (root/'science', root/'science'/arm, folder):
        if path.is_symlink() or not path.is_dir():
            raise ValueError('missing/symlink checkpoint directory')
    index = folder/'checkpoint-integrity.json'
    if index.is_symlink() or sha(index) != entry['checkpoint_index_sha256']:
        raise ValueError('checkpoint index hash mismatch')
    data = json.loads(index.read_text())
    expected = {n: v['sha256'] for n, v in entry['files'].items()}
    if (data.get('arm') != arm or data.get('complete') is not True
            or data.get('scientific_checkpoint') is not True or data.get('sha256') != expected):
        raise ValueError('checkpoint identity/integrity mismatch')
    if {p.name for p in folder.iterdir()} != set(expected) | {index.name}:
        raise ValueError('checkpoint roster mismatch')
    for name, digest in expected.items():
        path = folder/name
        if (Path(name).name != name or path.is_symlink() or not path.is_file()
                or sha(path) != digest or path.stat().st_size != entry['files'][name]['bytes']):
            raise ValueError('checkpoint file mismatch: '+name)
    return folder


class Adapter:
    def __init__(self, transport):
        self.transport = transport

    def generate(self, system, history, turn):
        if not 1 <= turn <= 12:
            raise ValueError('turn limit')
        return self.transport(system, history, turn)


def mock():
    return Adapter(lambda system, history, turn: '{"tool": null, "args": {}}')


def launch_guard(confirm, environ):
    if not confirm or any(environ.get(k) for k in ('CI', 'GITHUB_ACTIONS', 'PYTEST_CURRENT_TEST', 'TAA_TEST')):
        raise ValueError('explicit --confirm-spend required; CI/tests forbidden')
    reservation = (TIMEOUT + IDLE + 120) / 3600 * 3.20 + .40
    if reservation > CAP:
        raise ValueError(f'worst-case reservation exceeds ${CAP}')
    return CAP
