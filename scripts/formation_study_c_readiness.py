"""Offline readiness only: no credentials, HTTP, metadata or model calls."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from formation import study_c_evaluation_v0239 as c
from formation.study_b_replay_v0234 import replay


def readiness():
    freeze, approval, cases, cells, seeds = c.check(c.ROOT, approved=True)
    fixtures = c.read(c.ROOT/'studies/formation-study-c-frozen-v0239/free-probe-fixtures.json')
    for fixture in fixtures:
        actual = replay(cases[fixture['probe_id']], fixture['packets'])['score']
        if actual != fixture['expected_score']:
            raise ValueError('frozen free fixture differs: '+fixture['probe_id'])
    maxima = {}; compared = 0
    for model in c.MODELS:
        opts = {'max_output_tokens':4096}
        if model == 'gpt-6-luna': opts['key_name'] = 'TAA_OPENAI_API_KEY'
        native = c.CLASSES[c.PROVIDERS[model]](model, type('OfflineRecorder',(),{'model':model})(), **opts)
        maximum = metadata_maximum = 0
        for cell in cells:
            case = cases[cell['probe_id']]
            fixture = next(x for x in fixtures if x['probe_id']==case['id'] and x['fixture_name']=='correct')
            for turn in range(len(fixture['packets'])):
                history = c.seeded_history(case,cell,fixture['packets'][:turn],seeds)
                body = native.body(c.SYSTEM,history)
                size = len(json.dumps(body).encode()); maximum = max(maximum,size); compared += 1
                if size > 32000: raise ValueError('canonical complete-history wire exceeds cap')
                if model == 'gemma-4-31b-it':
                    outer = len(json.dumps({'generateContentRequest':dict(body,model='models/gemma-4-31b-it')}).encode())
                    metadata_maximum = max(metadata_maximum,outer)
                    if outer > 32000: raise ValueError('canonical metadata full-wire exceeds cap')
        maxima[model] = {'maximum_canonical_generation_wire_bytes':maximum,
                         'maximum_canonical_countTokens_wire_bytes':metadata_maximum or None}
    comparison = c.read(c.ROOT/'studies/formation-study-c-frozen-v0239/history-length-comparison.json')
    if comparison['any_history_grew']: raise ValueError('owner Gemma waiver no longer applies')
    return dict(offline_only=True, model_calls=0, metadata_calls=0,
                original_environment='ccarenv_b64_Y2NhcmVudl81NmNiZDJjMjBjY2M4MTkxOWUxMjM5ZWE5Y2ExYWJiYQ',
                freeze_sha256=c.sha(c.ROOT/c.FREEZE), adapter_sha256=c.sha(c.ROOT/c.BINDING),
                free_fixtures_passed=len(fixtures), planned_primary_episodes=2160,
                rendered_canonical_turns=compared, wire_maxima=maxima,
                Gemma_prior_validated_prompt_upper=5965,
                Gemma_prior_prompt_plus_output_and_margin=10189,
                no_growth_owner_waiver=True,
                limitation='Prior measured canonical histories, not all future replies; exact runtime full-body counts and all guards remain mandatory.')


if __name__ == '__main__':
    result=readiness()
    path=c.ROOT/'studies/formation-study-c-readiness-v0239.json'
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
