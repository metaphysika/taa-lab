"""FT1-R revision 2 plan. It does not launch or aggregate any run."""
import argparse
import json

from . import data, ft1r_data, plan as ft1

SEEDS = (247061, 247062, 247063)
FIRST_MODEL = ('3', SEEDS[0])
TRAINING_ORDER = (FIRST_MODEL,) + tuple(
    (arm, seed) for arm in ft1r_data.ARMS for seed in SEEDS if (arm, seed) != FIRST_MODEL
)
MODELS = (('base', None),) + TRAINING_ORDER


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
        evaluation_settings=dict(attention='eager', prefill_mode='chunked', prefill_chunk_size=256,
                                 prompt_ceiling=14000),
        base_result='reuse FT1 base for P3',
        pressure_split='The approved descriptive FT1 pressure split also applies to the FT1-R models.',
        arm2u_comparison='descriptive cross-layout comparison',
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', action='store_true', required=True)
    parser.parse_args()
    print(json.dumps(plan(), indent=2))
