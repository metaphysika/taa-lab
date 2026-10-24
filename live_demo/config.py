"""Frozen input bindings. Never import the expected-answer catalog at runtime."""
import json
import random
from pathlib import Path
from live_demo.evidence import digest

ROOT = Path(__file__).resolve().parents[1]
FROZEN = Path(__file__).parent/'frozen'
ARMS = ('floor', 'static', 'taa')
MODEL = 'gpt-6-luna'
OUTPUT_TOKENS = 4096
MAX_TURNS = 12
SEED = 2026102403


def load(name):
    return json.loads((FROZEN/name).read_bytes())


def schedule():
    rows = [dict(program='T%02d'%n, arm=arm, repeat=1)
            for n in range(1, 11) for arm in ARMS]
    random.Random(SEED).shuffle(rows)
    return rows


def verify():
    pins = load('hashes.json')
    for name, sha in pins.items():
        if digest((ROOT/name).read_bytes()) != sha:
            raise ValueError('frozen input changed: '+name)
    if schedule() != load('run-order.json'):
        raise ValueError('committed schedule differs from seed')
    return pins
