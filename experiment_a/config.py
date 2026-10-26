"""Prospective bindings, with explicit unapproved-guide and pricing blockers."""
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = Path(__file__).parent / 'inputs'
STEP = 'experiment-a-v01'
ARMS = ('model_alone', 'conventional', 'taa')
MODELS = {'anthropic': 'claude-sonnet-5-5', 'google': 'gemini-3-flash'}
OUTPUT_TOKENS = {'anthropic': 32768, 'google': 65536}
KEY_VARIABLES = {'anthropic': 'ANTHROPIC_API_KEY', 'google': 'GEMINI_API_KEY'}
PROVIDER_CAPS = {'anthropic': '25', 'google': '8'}
STEP_CAP = '25'
REPEATS = 3
MAX_TURNS = 12
SEED = 2026102501


def load(name):
    return json.loads((INPUTS / name).read_bytes())


def verify():
    pins = load('hashes.json')
    for name, digest in pins.items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError('experiment input changed: ' + name)
    if load('pilot-order.json') != schedule():
        raise ValueError('pilot schedule differs from committed seed')
    return pins


def schedule():
    trials = [dict(program=identity,arm=arm,repeat=repeat)
              for identity in ['T%02d'%n for n in range(1,11)]+['P%02d'%n for n in range(1,13)]
              for arm in ARMS for repeat in range(1,REPEATS+1)]
    random.Random(SEED).shuffle(trials)
    return [dict(row,provider=provider) for row in trials for provider in MODELS]


def system():
    # The identical guide accompanies the identical system text in every arm.
    return ((ROOT / 'live_demo/frozen/system.txt').read_text() + '\n\n' +
            (INPUTS / 'policy-guide.txt').read_text())


def launch_ready(*, neutral=False):
    from live_demo.adapter import Stop
    if not neutral:
        reviews = load('reviews.json')
        required = dict(policy_guide='approved', policy_guide_astra_hint_review='accepted',
                        conventional_astra_review='accepted', blind_expected_key='accepted',
                        measures_astra_review='accepted', build_claude_review='accepted', design='approved')
        if reviews != required:
            raise Stop('experiment_review_pending')
