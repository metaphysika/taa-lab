"""FT1-R revision 2 plan. It does not launch or aggregate any run."""
import argparse
import hashlib
import json
from pathlib import Path

from . import data, ft1r_data, plan as ft1

SEEDS = (247061, 247062, 247063)
FIRST_MODEL = ('3', SEEDS[0])
TRAINING_ORDER = (FIRST_MODEL,) + tuple(
    (arm, seed) for arm in ft1r_data.ARMS for seed in SEEDS if (arm, seed) != FIRST_MODEL
)
MODELS = (('base', None),) + TRAINING_ORDER
EVALUATION_SETTINGS = dict(attention='eager', prefill_mode='chunked', prefill_chunk_size=256,
                           prompt_ceiling=14000)


class FirstGateDecisionRequired(ValueError):
    pass


def require_first_gate(cell, gate_file, training_folder, data_manifest_sha256):
    if cell == FIRST_MODEL:
        return {}
    from .evaluate_runner import adapter_binding

    try:
        gate_file = Path(gate_file)
        gate_bytes = gate_file.read_bytes()
        manifest_bytes = (gate_file.parent/'manifest.json').read_bytes()
        gate = json.loads(gate_bytes)
        manifest = json.loads(manifest_bytes)
        gate_hash = hashlib.sha256(gate_bytes).hexdigest()
        if (gate_file.name == 'gate.json'
                and manifest['sha256']['gate.json'] == gate_hash
                and manifest['metadata']['phase'] == 'gate'
                and manifest['metadata']['status'] == 'gate_complete'
                and (gate.get('arm'), gate.get('seed')) == FIRST_MODEL
                and gate.get('layout') == data.FT1R_LAYOUT
                and data_manifest_sha256 is not None
                and gate.get('data_manifest_sha256') == data_manifest_sha256
                and gate.get('status') == 'complete'
                and gate.get('trained') is True and gate.get('acquired') is True):
            adapter = adapter_binding(training_folder, *FIRST_MODEL,
                                      data_manifest_sha256=data_manifest_sha256)
            if all(gate[key] == adapter[key] for key in ('adapter_sha256', 'training_manifest_sha256')):
                return dict(first_gate_sha256=gate_hash,
                            first_gate_manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
                            first_training_manifest_sha256=adapter['training_manifest_sha256'])
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise FirstGateDecisionRequired(FIRST_GATE_STOP) from exc
    raise FirstGateDecisionRequired(FIRST_GATE_STOP)


FIRST_GATE_STOP = (
    'FT1-R R3 stop: arm 3 / 247061 needs a retained, adapter-bound acquired gate. '
    'Record a failed gate for Chris. Further training requires a new reviewed code change.')


def plan():
    format_cases = ft1.format_cases()
    return dict(
        version=data.FT1R_LAYOUT,
        approved=False,
        model='google/gemma-3-12b-it',
        models=MODELS,
        recipe=dict(ft1.core.RECIPE, epochs=1, checkpoint_every=50),
        trigger=dict(ft1_arm3_acquired_below=2),
        first_gate=dict(arm=FIRST_MODEL[0], seed=FIRST_MODEL[1], stop_unless_acquired=True),
        training=[dict(arm=arm, seed=seed, order=ft1.order(seed), steps=250, max_skipped=25)
                  for arm, seed in TRAINING_ORDER],
        acquisition=[dict(arm=arm, training_seed=seed, probe_file=ft1r_data.PROBE_FILE, count=40)
                     for arm, seed in TRAINING_ORDER],
        format_evaluation=[dict(arm=arm, training_seed=seed, case_id=case, branch='format_only',
                                repeat=1, sampling_seed=348017+i*12, reply_cap=1024, max_steps=12)
                           for arm, seed in TRAINING_ORDER for i, case in enumerate(format_cases)],
        evaluation=[dict(arm=arm, training_seed=seed, case_index=i, branch=branch, repeat=1,
                         sampling_seed=248017+i*12, reply_cap=1024, max_steps=12)
                    for arm, seed in TRAINING_ORDER for i in range(48) for branch in ('action', 'knowledge')],
        evaluation_settings=dict(EVALUATION_SETTINGS),
        base_result='reuse FT1 base for P3',
        pressure_split='The approved descriptive FT1 pressure split also applies to the FT1-R models.',
        arm2u_comparison='descriptive cross-layout comparison',
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', action='store_true', required=True)
    parser.parse_args()
    print(json.dumps(plan(), indent=2))
