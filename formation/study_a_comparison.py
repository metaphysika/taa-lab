"""The approved once-only baseline/pressure Luna development batch."""
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
from formation.study_a_pilot import PilotRecorder, SYSTEM
from formation.study_a_pressure import pressure_view

PLAN_PATH = ROOT / 'studies/formation-study-a-comparison-pilot-plan-2026-10-10.json'
APPROVED_PLAN_DIGEST = '15f053f0f3738b35d4290927c37245694b2cfc59ac2a733a359df1e557530ed3'
SOURCES = ('formation/study_a_comparison.py', 'formation/study_a_pilot.py',
    'formation/study_a_pressure.py', 'formation/study_a.py', 'formation/clients.py',
    'formation/telemetry.py', 'formation/credentials.py', 'formation/limits.py',
    'agents/call_telemetry.py', 'agents/gemini_client.py', 'taa/gate.py',
    'taa/records.py', 'taa/determinations.py', 'scripts/formation_study_a_comparison.py')


class ComparisonRecorder(PilotRecorder):
    def before_attempt(self, body):
        # Reserve every input token at the highest category price. Restore the
        # real category prices before settling usage; never charge the reserve rate.
        original = self.prices
        self.prices = {self.model: dict(original[self.model], input_per_million=.125)}
        try:
            return super().before_attempt(body)
        finally:
            self.prices = original


def validate_plan(plan, root=ROOT):
    digest = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
    if digest != APPROVED_PLAN_DIGEST:
        raise ValueError('plan differs from the exact approved batch')
    cases = {}
    for entry in plan['episode_order']:
        path = root / entry['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('approved case hash differs: ' + entry['case_id'])
        case = load_cases([path])[0]
        if case['id'] != entry['case_id'] or case['max_steps'] != 12:
            raise ValueError('case identity or step limit differs')
        cases[case['id']] = case
    return cases


def run_episode(case, arm, client, recorder):
    packets, history, deliveries, delivered = [], [], [], set()
    result = replay_episode(case, [])
    stopped = False
    for turn in range(12):
        recorder.context = {'case_id': case['id'], 'arm': arm, 'turn': turn+1,
                            'stage': 'Luna comparison development'}
        recorder.last_reply = None
        try:
            if arm == 'pressure':
                view, message = pressure_view(case, result)
            else:
                view, message = agent_view(case), None
                view['world'] = result['final_world']
            view['world']['step'] = turn+1
            feedback = {'task_context': view} if not history else {
                'last_tool_result': result['attempts'][-1]['result'], 'world': view['world']}
            if message and message['delivery_key'] not in delivered:
                feedback['issuer_followup'] = message['text']
                delivered.add(message['delivery_key'])
                deliveries.append(dict(message, before_reply_turn=turn+1))
            history.append({'role': 'user', 'content': json.dumps(feedback, ensure_ascii=False)})
            client.chat(SYSTEM, history)
            if recorder.last_reply is None:
                raise RuntimeError('missing recorded raw reply')
            packets.append({'kind': 'reply', 'raw': recorder.last_reply})
        except ReplyError as error:
            if error.label in ('unfinished_reply', 'provider_refusal'):
                packets.append({'kind': error.label, 'detail': error.label})
            else:
                packets.append({'kind': 'reply', 'raw': recorder.last_reply or ''})
        except (ProviderError, BudgetStopped, RatePaused) as error:
            packets.append({'kind': 'error', 'detail': str(error)})
            stopped = True
        except Exception as error:
            # Never interpolate arbitrary exception text that could contain secrets.
            packets.append({'kind': 'error', 'detail': 'unexpected harness failure: '+type(error).__name__})
            stopped = True
        result = replay_episode(case, packets)
        if result['score']['terminal_status'] != 'fixture_exhausted':
            break
        history.append({'role': 'assistant', 'content': recorder.last_reply})
    result.update(agent='gpt-6-luna', arm=arm, phase='development comparison, not evaluation',
                  conversation=history, issuer_message_deliveries=deliveries)
    return result, stopped


def summarize(rows, recorder, prior, stopped):
    return {'episodes_planned': 24, 'episodes_recorded': len(rows), 'batch_stopped': stopped,
            'outcomes_by_arm': {arm: dict(Counter(r['score']['outcome'] for r in rows if r['arm']==arm))
                                for arm in ('baseline','pressure')},
            'cases': rows, 'accounting': recorder.snapshot(),
            'batch_estimated_dollars': round(recorder.spent-prior, 8),
            'cost_basis': 'provider-reported input/cache-read/cache-write/output category prices; uncertain calls retain maximum-input-rate reserves',
            'verdict': 'exploratory development only; no P6 evaluation verdict'}


def run_comparison(plan_path, output, approved=False, root=ROOT):
    if not approved:
        raise ValueError('written $1.50 cost approval required before generation')
    plan_path, output = Path(plan_path), Path(output)
    plan = json.loads(plan_path.read_text())
    cases = validate_plan(plan, root)
    if output.exists():
        raise ValueError('batch output exists; never repeat or overwrite evidence')
    ledgers = root / 'results/formation-spending-v021'
    ledgers.mkdir(parents=True, exist_ok=True)
    lock = ledgers/'run.lock'
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError('another run or interrupted lock exists; inspect before proceeding')
    try:
        os.write(fd, str(os.getpid()).encode())
        ledger = ledgers/'openai.json'
        prior = json.loads(ledger.read_text())['estimated_api_dollars'] if ledger.exists() else 0
        output.mkdir(parents=True, exist_ok=False)
        paths = list(SOURCES)+[e['path'] for e in plan['episode_order']]
        hashes = {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
        (output/'manifest.json').write_text(json.dumps({'plan': plan,
            'plan_sha256': hashlib.sha256(plan_path.read_bytes()).hexdigest(),
            'source_sha256': hashes, 'system': SYSTEM, 'prior_provider_spend': prior,
            'authorization': 'Chris: Approve the baseline-and-pressure Luna pilot up to $1.50.',
            'stage': 'approved development comparison; not study freeze'}, indent=2)+'\n')
        prices = {'gpt-6-luna': {k: plan['price'][k] for k in
                  ('input_per_million','cached_input_per_million','cache_write_per_million','output_per_million')}}
        recorder = ComparisonRecorder(output/'calls.jsonl', prices, 'gpt-6-luna',
            max_logical=288, max_attempts=288, max_dollars=min(8, prior+1.50),
            prior_spend=prior, ledger_path=ledger)
        load_keys(root/'keys.env')
        client = OpenAIChat('gpt-6-luna', recorder, max_output_tokens=2048)
        rows, stopped = [], False
        for entry in plan['episode_order']:
            case = cases[entry['case_id']]
            before = recorder.snapshot()
            if stopped:
                result = replay_episode(case,[{'kind':'error','detail':'not attempted after batch stop'}])
                result.update(agent='gpt-6-luna', arm=entry['arm'],
                              phase='development comparison, not evaluation', issuer_message_deliveries=[])
            else:
                result, stopped = run_episode(case, entry['arm'], client, recorder)
            after = recorder.snapshot()
            result.update(model_calls=after['request_attempts']-before['request_attempts'],
                          accounting_before=before, accounting_after=after)
            (output/(case['id']+'.json')).write_text(json.dumps(result,indent=2)+'\n')
            rows.append({'case_id':case['id'],'kind':case['kind'],'arm':entry['arm'],
                         'requests':result['model_calls'],'score':result['score'],
                         'issuer_followups':len(result['issuer_message_deliveries'])})
            summary = summarize(rows, recorder, prior, stopped)
            (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
            print('%d/24 %s: %s' % (len(rows),case['id'],result['score']['outcome']),flush=True)
        return summary
    finally:
        os.close(fd)
        lock.unlink()
