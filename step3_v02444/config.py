"""Only the two identities/routes already pinned in notebook v0.24.36."""
from copy import deepcopy
from decimal import Decimal

MODELS = ('Luna', 'Haiku 5.5')
HARD_CAP = Decimal('1.00')


def configuration():
    common = dict(input_token_bound=96000, input_token_overhead=2000, output_token_bound=8192,
                  input_dollars_per_million_upper='0.125', output_dollars_per_million_upper='0.625',
                  remaining_dollars='1.00', timeout_seconds=300)
    return dict(episode_count=96, max_requests=6, max_steps=8, runtime_bound_seconds=7200,
                caps=dict(probe='1.00', combined_remaining='1.00', monthly_remaining='1.00'), providers={
        'Luna': dict(deepcopy(common), protocol='responses', model_id='gpt-6-luna',
                     endpoint='https://api.openai.com/v1/responses', key_env='LUNA_API_KEY',
                     auth_header='Authorization', auth_prefix='Bearer ', headers={}, settings=dict(max_output_tokens=8192)),
        'Haiku 5.5': dict(deepcopy(common), protocol='anthropic', model_id='claude-haiku-5-5',
                          endpoint='https://api.anthropic.com/v1/messages', key_env='ANTHROPIC_API_KEY',
                          auth_header='x-api-key', auth_prefix='', headers={'anthropic-version': '2023-06-01'},
                          settings=dict(max_tokens=8192, thinking=dict(type='adaptive'), output_config=dict(effort='medium')))})


def estimate():
    per_request = (Decimal(4000) * Decimal('0.125') + Decimal(1000) * Decimal('0.625')) / Decimal(1000000)
    reserved = (Decimal(96000) * Decimal('0.125') + Decimal(8192) * Decimal('0.625')) / Decimal(1000000)
    return dict(configured_models=list(MODELS), configured_episodes=96, requested_episodes=144,
                missing_models=1, prices_source='LAB_NOTEBOOK.md v0.24.36; not live-verified',
                assumptions=dict(requests_per_episode=3, input_tokens_per_request=4000, output_tokens_per_request=1000),
                dollars_per_request=str(per_request), estimate_144=str(144 * 3 * per_request),
                estimate_96=str(96 * 3 * per_request), range_144_2_to_6_requests=[str(144 * count * per_request) for count in (2, 6)],
                worst_case_reservation_per_request=str(reserved), worst_case_144=str(144 * 6 * reserved),
                hard_cap=str(HARD_CAP), completion_guaranteed=False, paid_run_approved=False)
