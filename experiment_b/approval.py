"""Gate 1b exact-commit validation. No credentials are inspected here."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.parse import urlsplit

from experiment_b.fixtures import ROOT, MODELS, verify, digest, schedule
from experiment_b.host import Stop


WORKFLOW = ROOT / '.github/workflows/experiment-b-step1.yml'
NOTEBOOK = ROOT / 'LAB_NOTEBOOK.md'


def text_hash(path):
    return hashlib.sha256(path.read_text(encoding='utf-8').encode()).hexdigest()


def money(value):
    try:
        result = Decimal(str(value))
    except InvalidOperation as error:
        raise Stop('invalid_budget') from error
    if not result.is_finite() or result <= 0:
        raise Stop('invalid_budget')
    return result


def git(*arguments):
    return subprocess.check_output(['git', *arguments], cwd=ROOT, text=True).strip()


def validate(approval):
    pins = verify()
    if approval.get('gate') != '1b' or approval.get('approved_by') != 'Chris Lahn':
        raise Stop('gate1b_required')
    if approval.get('commit') != git('rev-parse', 'HEAD') or git('status', '--porcelain'):
        raise Stop('unapproved_or_dirty_commit')
    if approval.get('inputs_sha256') != pins['inputs_sha256']:
        raise Stop('unapproved_inputs')
    if approval.get('schedule_sha256') != digest(schedule()):
        raise Stop('unapproved_schedule')
    if approval.get('workflow_sha256') != text_hash(WORKFLOW) or approval.get('notebook_sha256') != text_hash(NOTEBOOK):
        raise Stop('unapproved_workflow_or_notebook')
    try:
        actions = approval['actions']
        if (not actions['repository'] or not actions['workflow_ref'] or
                type(actions['run_number']) is not int or actions['run_number'] <= 0 or
                type(actions['run_attempt']) is not int or actions['run_attempt'] != 1):
            raise Stop('actions_run_binding_required')
        expires = datetime.fromisoformat(approval['expires_utc'])
        if expires.tzinfo is None or expires <= datetime.now(timezone.utc):
            raise Stop('expired_approval')
        configuration = approval['configuration']
        if json.dumps(configuration, sort_keys=True) not in NOTEBOOK.read_text(encoding='utf-8'):
            raise Stop('configuration_not_preregistered_in_notebook')
        if not approval['predictions'] or approval['predictions'] not in NOTEBOOK.read_text(encoding='utf-8'):
            raise Stop('predictions_not_preregistered')
        if configuration['episode_count'] != 84 or configuration['max_requests'] != 12 or configuration['max_steps'] != 20:
            raise Stop('unapproved_schedule_limits')
        if configuration['parallel_tool_calls'] is not True:
            raise Stop('parallel_calls_must_remain_on')
        if type(configuration['runtime_bound_seconds']) is not int or not 0 < configuration['runtime_bound_seconds'] <= 19800:
            raise Stop('actions_runtime_bound')
        caps = configuration['caps']
        if money(caps['probe']) > 8 or money(caps['combined_remaining']) > 12 or money(caps['monthly_remaining']) > 50:
            raise Stop('budget_ceiling')
        if set(configuration['providers']) != set(MODELS):
            raise Stop('unknown_models')
        for label, provider in configuration['providers'].items():
            if provider['protocol'] != ('responses' if label == 'Luna' else 'anthropic'):
                raise Stop('no_endpoint_fallback')
            url = urlsplit(provider['endpoint'])
            if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
                raise Stop('invalid_approved_route')
            if any(type(provider[field]) is not str or not provider[field]
                   for field in ('model_id', 'key_env', 'auth_header')):
                raise Stop('identity_and_keys_required')
            if type(provider['auth_prefix']) is not str or type(provider['headers']) is not dict:
                raise Stop('invalid_auth_convention')
            if any(type(key) is not str or type(value) is not str or '\n' in key + value or '\r' in key + value
                   for key, value in provider['headers'].items()):
                raise Stop('invalid_approved_headers')
            settings = provider['settings']
            if type(settings) is not dict:
                raise Stop('invalid_model_settings')
            if label == 'Haiku 5.5' and (
                    settings.get('thinking') != {'type': 'adaptive'} or
                    settings.get('output_config') != {'effort': 'medium'} or
                    provider['headers'].get('anthropic-version') != '2023-06-01'):
                raise Stop('haiku_settings_required')
            output_field = 'max_output_tokens' if label == 'Luna' else 'max_tokens'
            if (type(settings[output_field]) is not int or
                    settings[output_field] != provider['output_token_bound']):
                raise Stop('output_bound_mismatch')
            for field in ('input_token_bound', 'output_token_bound', 'input_token_overhead', 'timeout_seconds'):
                if type(provider[field]) is not int or provider[field] <= 0:
                    raise Stop('invalid_request_bound')
            if provider['input_token_bound'] > 96000:
                raise Stop('input_byte_ceiling')
            for field in ('input_dollars_per_million_upper', 'output_dollars_per_million_upper', 'remaining_dollars'):
                money(provider[field])
            if money(provider['remaining_dollars']) > 4:
                raise Stop('provider_run_ceiling')
            if provider['protocol'] == 'responses' and not provider['endpoint'].rstrip('/').endswith('/responses'):
                raise Stop('responses_route_required')
        return configuration
    except (KeyError, TypeError, ValueError) as error:
        raise Stop('incomplete_gate1b_approval') from error


def claim_approval(path):
    path = Path(path).resolve()
    approval = json.loads(path.read_text(encoding='utf-8'))
    configuration = validate(approval)
    try:
        with path.with_name(path.name + '.used').open('x', encoding='utf-8') as handle:
            handle.write(json.dumps(dict(commit=approval['commit'], schedule=digest(schedule()))))
    except FileExistsError as error:
        raise Stop('approval_already_used_no_retry') from error
    return approval, configuration
