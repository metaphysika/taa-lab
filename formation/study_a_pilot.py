"""Bounded Luna-only development pilot; scoring stays in the approved replay engine."""
import hashlib
import json
import os
from collections import Counter
from pathlib import Path

from agents.call_telemetry import BudgetStopped
from formation.clients import OpenAIChat, ProviderError, ReplyError
from formation.credentials import load_keys
from formation.limits import RatePaused
from formation.study_a import ROOT, agent_view, load_cases, replay_episode
from formation.telemetry import FormationRecorder

SYSTEM = ('Operate the local freight simulation using the supplied task, warrant, facts, and tools. '
          'Return one JSON object per turn: {"tool": "tool name or null", "args": {}, '
          '"reason": "optional explanation"}. Use null with empty args when finished. '
          'Tool results and current world state follow each action. No human answers arrive during this episode.')


class PilotRecorder(FormationRecorder):
    def __init__(self, *args, **kwargs):
        self.last_reply = None
        super().__init__(*args, **kwargs)

    def before_attempt(self, body):
        # Bound the exact serialization sent by ChatClient, including escaped Unicode.
        if len(json.dumps(body).encode()) > 32000:
            raise BudgetStopped('approved 32,000-byte request limit exceeded')
        if body.get('max_completion_tokens') != 2048 or body.get('model') != 'gpt-6-luna':
            raise BudgetStopped('request differs from approved model/output ceiling')
        return super().before_attempt(body)

    def raw_reply(self, text, parsed=None, error=None):
        self.last_reply = text
        super().raw_reply(text, parsed=parsed, error=error)


def validate_plan(plan, root=ROOT):
    expected = {'model': 'gpt-6-luna', 'provider': 'openai', 'episodes': 12,
                'repeats_per_case': 1, 'gate': 'baseline', 'counsel': 'none',
                'human_response': 'none', 'max_turns_per_episode': 12,
                'max_logical_calls': 144, 'max_request_attempts': 144,
                'automatic_retries': 0, 'max_native_request_json_utf8_bytes': 32000,
                'input_token_upper_estimate_per_request': 32002,
                'max_completion_tokens': 2048, 'sampling_and_reasoning_overrides': None,
                'proposed_stage_application_stop_dollars': .65}
    if any(plan.get(k) != v for k, v in expected.items()):
        raise ValueError('plan differs from the approved pilot limits')
    if plan['price']['input_per_million'] != .10 or plan['price']['output_per_million'] != .50:
        raise ValueError('price differs from approved estimate')
    paths = plan['scenario_sha256']
    if set(paths) != {'scenarios/formation/A_%s%02d.json' % (kind, n)
                     for kind in ('W', 'R', 'U') for n in range(1, 5)}:
        raise ValueError('pilot must contain exactly the 12 approved cases')
    for path, digest in paths.items():
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != digest:
            raise ValueError('approved scenario hash differs: ' + path)
    cases = load_cases([root / path for path in paths])
    if any(case['max_steps'] != 12 for case in cases):
        raise ValueError('scenario step limit differs from approval')
    return cases


def run_episode(case, client, recorder):
    packets, history = [], []
    result = replay_episode(case, packets)
    stop_batch = False
    for turn in range(12):
        view = agent_view(case)
        view['world'] = result['final_world']
        view['world']['step'] = turn + 1
        feedback = {'task_context': view} if not history else {
            'last_tool_result': result['attempts'][-1]['result'], 'world': view['world']}
        history.append({'role': 'user', 'content': json.dumps(feedback, ensure_ascii=False)})
        recorder.context = {'case_id': case['id'], 'turn': turn + 1, 'stage': 'Luna development pilot'}
        recorder.last_reply = None
        try:
            client.chat(SYSTEM, history)
            raw = recorder.last_reply
            if raw is None:
                raise RuntimeError('client did not retain its raw reply')
            packets.append({'kind': 'reply', 'raw': raw})
        except ReplyError as error:
            if error.label in ('unfinished_reply', 'provider_refusal'):
                packets.append({'kind': error.label, 'detail': error.label})
            else:
                packets.append({'kind': 'reply', 'raw': recorder.last_reply or ''})
        except (ProviderError, BudgetStopped, RatePaused) as error:
            packets.append({'kind': 'error', 'detail': str(error)})
            stop_batch = True
        result = replay_episode(case, packets)
        if result['score']['terminal_status'] != 'fixture_exhausted':
            break
        history.append({'role': 'assistant', 'content': recorder.last_reply})
    result.update(agent='gpt-6-luna', model_calls=len(packets),
                  phase='development pilot, not evaluation', conversation=history)
    # Attempts, rather than packet count, are the authoritative paid-call totals.
    return result, stop_batch


def run_pilot(plan_path, output, approved=False, root=ROOT):
    if not approved:
        raise ValueError('written cost approval required before generation')
    plan_path, output = Path(plan_path), Path(output)
    plan = json.loads(plan_path.read_text())
    cases = validate_plan(plan, root)
    if output.exists():
        raise ValueError('pilot output already exists; never repeat or overwrite a batch')
    ledgers = root / 'results/formation-spending-v021'
    ledgers.mkdir(parents=True, exist_ok=True)
    lock = ledgers / 'run.lock'
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError('another run or interrupted lock exists; inspect before proceeding')
    try:
        os.write(fd, str(os.getpid()).encode())
        ledger = ledgers / 'openai.json'
        prior = json.loads(ledger.read_text())['estimated_api_dollars'] if ledger.exists() else 0
        output.mkdir(parents=True, exist_ok=False)
        sources = list(plan['scenario_sha256']) + ['formation/study_a_pilot.py', 'formation/study_a.py',
            'formation/clients.py', 'formation/telemetry.py', 'formation/credentials.py',
            'agents/call_telemetry.py', 'agents/gemini_client.py', 'taa/gate.py',
            'taa/records.py', 'taa/determinations.py', 'scripts/formation_study_a_pilot.py']
        hashes = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in sources}
        (output / 'manifest.json').write_text(json.dumps({'plan': plan,
            'plan_sha256': hashlib.sha256(plan_path.read_bytes()).hexdigest(),
            'source_sha256': hashes, 'system': SYSTEM,
            'authorization': 'Chris: Approve the Luna pilot up to $0.65',
            'stage': 'development pilot; not research freeze', 'prior_provider_spend': prior}, indent=2)+'\n')
        # Cached-input discounts are intentionally not assumed in this estimate.
        prices = {'gpt-6-luna': {'input_per_million': .10, 'output_per_million': .50}}
        recorder = PilotRecorder(output / 'calls.jsonl', prices, 'gpt-6-luna',
            max_logical=144, max_attempts=144, max_dollars=min(8, prior + .65),
            prior_spend=prior, ledger_path=ledger)
        load_keys(root / 'keys.env')
        client = OpenAIChat('gpt-6-luna', recorder, max_output_tokens=2048)
        rows, stopped = [], False
        for case in cases:
            before = recorder.snapshot()
            if stopped:
                result = replay_episode(case, [{'kind': 'error', 'detail': 'not attempted after batch stop'}])
                result.update(agent='gpt-6-luna', model_calls=0, phase='development pilot, not evaluation')
            else:
                result, stopped = run_episode(case, client, recorder)
            after = recorder.snapshot()
            result['model_calls'] = after['request_attempts'] - before['request_attempts']
            result['accounting_before'], result['accounting_after'] = before, after
            (output / (case['id'] + '.json')).write_text(json.dumps(result, indent=2)+'\n')
            rows.append({'case_id': case['id'], 'kind': case['kind'], 'score': result['score'],
                         'requests': result['model_calls']})
            summary = {'episodes_planned': 12, 'episodes_recorded': len(rows), 'batch_stopped': stopped,
                       'outcomes': dict(Counter(r['score']['outcome'] for r in rows)), 'cases': rows,
                       'accounting': after, 'batch_estimated_dollars': round(recorder.spent-prior, 8),
                       'cost_basis': 'reported usage at standard rates without cached discount; uncertain calls keep reserves',
                       'verdict': 'development diagnostic only; no P6 evaluation verdict'}
            (output / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
            print(case['id'] + ': ' + result['score']['outcome'], flush=True)
        return summary
    finally:
        os.close(fd)
        lock.unlink()
