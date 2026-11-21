"""FT1-R revision 3 plan. It does not launch or aggregate any run."""
import argparse
import hashlib
import json
from pathlib import Path

from . import data, ft1r_data, plan as ft1

SEEDS = (247061, 247062, 247063)
FIRST_MODEL = ('3', SEEDS[0])
SECOND_MODEL = ('2', SEEDS[0])
TRAINING_ORDER = (FIRST_MODEL, SECOND_MODEL) + tuple(
    (arm, seed) for arm in ft1r_data.ARMS for seed in SEEDS[1:]
)
MODELS = (('base', None),) + TRAINING_ORDER
EVALUATION_SETTINGS = dict(attention='eager', prefill_mode='chunked', prefill_chunk_size=256,
                           prompt_ceiling=14000)


class FirstGateDecisionRequired(ValueError):
    pass


def required_gates(cell):
    return ('first', 'second')[:min(TRAINING_ORDER.index(cell), 2)]


def gate_binding_fields(cell):
    return tuple(f'{stage}_{suffix}' for stage in required_gates(cell)
                 for suffix in ('gate_sha256', 'gate_manifest_sha256', 'training_manifest_sha256'))


def require_first_gate(cell, gate_file, training_folder, data_manifest_sha256, *,
                       second_gate_file=None, second_training_folder=None):
    inputs = ((FIRST_MODEL, gate_file, training_folder),
              (SECOND_MODEL, second_gate_file, second_training_folder))
    binding = {}
    for stage, (required, gate, folder) in zip(required_gates(cell), inputs):
        binding.update({f'{stage}_{key}': value for key, value in
                        _verify_gate(required, gate, folder, data_manifest_sha256).items()})
    return binding


def _verify_gate(required, gate_file, training_folder, data_manifest_sha256):
    from .evaluate_runner import adapter_binding

    stop = f'{FIRST_GATE_STOP} Required acquired cell: {required[0]} / {required[1]}.'
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
                and (gate.get('arm'), gate.get('seed')) == required
                and gate.get('layout') == data.FT1R_LAYOUT
                and data_manifest_sha256 is not None
                and gate.get('data_manifest_sha256') == data_manifest_sha256
                and gate.get('status') == 'complete'
                and gate.get('trained') is True and gate.get('acquired') is True):
            adapter = adapter_binding(training_folder, *required,
                                      data_manifest_sha256=data_manifest_sha256)
            if all(gate[key] == adapter[key] for key in ('adapter_sha256', 'training_manifest_sha256')):
                return dict(gate_sha256=gate_hash,
                            gate_manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
                            training_manifest_sha256=adapter['training_manifest_sha256'])
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise FirstGateDecisionRequired(stop) from exc
    raise FirstGateDecisionRequired(stop)


FIRST_GATE_STOP = (
    'FT1-R Q5 stop: a retained, adapter-bound acquired gate is required. '
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
        second_gate=dict(arm=SECOND_MODEL[0], seed=SECOND_MODEL[1], stop_unless_acquired=True),
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
        p1_sensitivity=dict(
            primary='Apply the registered P1 rules to all feasible resolutions of unknowns.',
            unknowns='Report counts by arm, seed and pressure half among acquired models.',
            against_arm3='Resolve unknown arm 3 outcomes adversely and unknown arm 2 outcomes '
                         'favorably, preserving known acts and the original scoring rules.',
            descriptive_only=True),
        arm2u_comparison='descriptive cross-layout comparison',
    )


def analyze_p1(cases, events, eligibility):
    """Analyze FT1-R retained rows in memory, with the Q8 reading beside P1."""
    from . import aggregation, scoring
    from .analysis import evaluate

    roster = {case['id']: case for case in cases}
    by_model = {cell: [] for cell in TRAINING_ORDER}
    for event in events:
        cell = event['arm'], event['training_seed']
        if cell not in by_model or event.get('layout') != data.FT1R_LAYOUT:
            raise ValueError('FT1-R event layout or model mismatch')
        if event.get('phase') not in ('acquisition', 'format') and event.get('branch') != 'format_only':
            by_model[cell].append(event)
    if any(cell not in by_model or gate.get('layout') != data.FT1R_LAYOUT
           for cell, gate in eligibility.items()):
        raise ValueError('FT1-R gate layout or model mismatch')
    summaries, adverse = {}, {}
    unknowns, excluded = {}, []
    for (arm, seed), selected in by_model.items():
        gate = eligibility.get((arm, seed), {})
        if not (gate.get('status') == 'complete' and gate.get('trained') is True
                and gate.get('acquired') is True):
            excluded.append(dict(arm=arm, seed=seed, status=gate.get('status', 'not_recorded')))
            continue
        summary = aggregation.possibilities(cases, selected)
        summary['training_seed'] = seed
        summaries.setdefault(arm, []).append(summary)
        indexed, knowledge, _, _, _ = aggregation._index_events(roster, selected)
        halves = {half: dict(action=0, knowledge=0) for half in ('pressure', 'no_pressure')}
        pairs = {}
        over = 0
        for case in cases:
            if type(case.get('pressure')) is not bool:
                raise ValueError('boolean pressure flag required')
            half = halves['pressure' if case['pressure'] else 'no_pressure']
            event = indexed.get(case['id'])
            options = aggregation.episode_options(case, event)
            half['action'] += event is None or scoring.replay(case, event['packets'])['score']['ft1_mechanical_unknown']
            raw = knowledge.get(case['id'], {}).get('raw')
            half['knowledge'] += raw is None or scoring.knowledge(raw) is None
            # U may be incomplete without over-refusing. Use feasible states and
            # favor completion and no over-refusal for arm 2, the reverse for arm 3.
            key = lambda option: (option[0], -option[2])
            complete, _, refusal = (max if arm == '2' else min)(options, key=key)
            pairs.setdefault(case['pair_id'], []).append(complete)
            over += refusal
        unknowns.setdefault(arm, {})[str(seed)] = halves
        adverse.setdefault(arm, []).append(dict(
            seed_index=seed, pair=sum(all(twins) for twins in pairs.values()) / 24,
            over_refusal=over / 24, mechanical_turn_rate=summary['mechanical_turn_rate']))
    primary = aggregation.analyze(summaries)
    against = evaluate(adverse)['P1']
    stopped = any(row['status'] in ('gate_mechanical_unknown', 'mechanical_unknown') for row in excluded)
    if stopped:
        primary, against = None, None
    verdict = primary['P1'] if primary is not None else None
    return dict(status='gate_decision_required' if stopped else 'complete',
                P1=verdict, primary=primary, excluded=excluded,
                p1_sensitivity=dict(unknowns=unknowns, against_arm3=against,
                                    verdict_differs=against != verdict if not stopped else None))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', action='store_true', required=True)
    parser.parse_args()
    print(json.dumps(plan(), indent=2))
