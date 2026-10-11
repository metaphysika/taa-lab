"""Approved Qwen suffix only; retain the issued 429 and all original evidence."""
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

from agents.call_telemetry import BudgetStopped
from formation.credentials import load_keys
from formation.evaluation_runner_v0218 import atomic, execute_cell, history_for_next
from formation.evaluation_transport_v0218 import GroqSlots, QuotaRecorder, make_client
from formation.study_a import ROOT, load_cases, replay_episode
from scripts.formation_study_a_gate3 import verify_freeze
from scripts.formation_connectivity import journal_spend

MODEL = 'qwen/qwen3.8-27b'
OUTPUT = 'results/2026-10-11 v0.22.0 qwen38-none r10 study-a evaluation'
MANIFEST = 'continuation-execution-manifest.json'
SUMMARY = 'continuation-progress-summary.json'
APPROVAL = 'studies/formation-study-a-qwen38-continuation-execution-approval-2026-10-11.json'
APPROVAL_TEXT = ('Approve Qwen 3.8 27B’s remaining 236 frozen Study A episodes on Groq Free at $0; '
                 'retain A_R02 repeat 1 without retrying; allow resumes only after pre-request quota pauses.')
ADAPTERS = ('formation/evaluation_qwen_continuation_v0221.py',
            'scripts/formation_study_a_qwen38_continuation.py',
            'scripts/formation_study_a_qwen38_continuation_controller.py')


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def key(cell):
    return cell['case_id'], cell['repeat']


def usage_valid(usage):
    prompt = usage.get('prompt_tokens')
    output = usage.get('completion_tokens')
    cached = usage.get('prompt_tokens_details', {}).get('cached_tokens', 0)
    return (all(type(n) is int and n >= 0 for n in (prompt, output, cached))
            and cached <= prompt and prompt - cached + output <= 8000)


class ContinuationRecorder(QuotaRecorder):
    """Reject invalid native usage immediately, after preserving its journal evidence."""
    def finish_native(self, aid, response, provider, status=200):
        super().finish_native(aid, response, provider, status)
        if not usage_valid(response.get('usage') or {}):
            self.last_identity_valid = False
            raise BudgetStopped('invalid native Groq usage; stop without retry')


def review_source(plan_path, root=ROOT):
    """Pure offline checks; no credential loading, lock clearing or provider access."""
    root = Path(root).resolve()
    plan = read(plan_path)
    require(str(root) == plan['checkout_root'] and plan['output'] == OUTPUT,
            'original checkout and output required')
    require(sys.version_info[:2] == (3, 11), 'original Python 3.11 runtime required')
    require(plan['model'] == MODEL and plan['provider'] == 'groq'
            and plan['cap_dollars'] == plan['maximum_additional_dollars'] == 0
            and plan['free_tier_required'] is True, 'Free Qwen $0 policy differs')
    source = root / OUTPUT
    require(source.is_dir(), 'original output unavailable; never recreate it')
    require(not os.path.lexists(root / 'results/formation-spending-v021/run.lock'),
            'shared run lock exists; never clear automatically')
    require(verify_freeze(root / plan['freeze_file']) == 59, 'frozen file count differs')
    # Also verify against the selected root when exercising temporary offline fixtures.
    frozen = read(root / plan['freeze_file'])
    entries = dict(frozen['sha256'], **frozen.get('adapter_reference_sha256', {}))
    for relative, digest in entries.items():
        require(sha(root / relative) == digest, 'frozen input differs: ' + relative)
    for relative, digest in plan['bound_file_sha256'].items():
        require(sha(root / relative) == digest, 'bound adapter/plan differs: ' + relative)
    review_path = root / plan['source_review']
    require(sha(review_path) == plan['source_review_sha256'], 'review evidence differs')
    reviewed = read(review_path)
    original_plan = read(root / 'studies/formation-study-a-qwen38-evaluation-cost-plan-v0220.json')
    original_approval = read(root / 'studies/formation-study-a-qwen38-evaluation-approval-2026-10-11.json')
    require(original_approval['cost_plan_sha256'] == sha(root / 'studies/formation-study-a-qwen38-evaluation-cost-plan-v0220.json'), 'original approval binding differs')
    rows = read(source / 'progress-summary.json')['records']
    require(len(rows) == 240 and plan['pending_cells'] == original_plan['cells'][4:]
            and reviewed['pending_cells'] == plan['pending_cells'], 'reviewed suffix differs')
    for cell, row in zip(original_plan['cells'], rows):
        require(all(row[k] == v for k, v in cell.items()), 'original row order differs')
    for name, digest in reviewed['source_sha256'].items():
        if name != 'calls.jsonl':
            require(sha(source / name) == digest, 'original evidence differs: ' + name)
    raw = (source / 'calls.jsonl').read_bytes()
    prefix_size = plan['original_journal_bytes']
    require(hashlib.sha256(raw[:prefix_size]).hexdigest() == reviewed['source_sha256']['calls.jsonl'],
            'original journal prefix changed')
    require(raw.endswith(b'\n'), 'journal is truncated')
    require(read(source / 'controller-status.json')['state'] == 'stopped_for_review',
            'original controller must stay stopped')
    runtime = read(source / 'runtime-receipt.json')
    # Production binds the persisted external controller; fixtures verify its archived method.
    require(sha(root / plan['controller_archive']) == plan['controller_sha256'], 'original controller archive changed')
    if root == Path('/workspace/taa-lab'):
        require(sha(runtime['controller_path']) == plan['controller_sha256'], 'original controller changed')
        pid = read(source / 'controller-status.json')['pid']
        proc = Path('/proc') / str(pid) / 'cmdline'
        require(not (proc.exists() and b'qwen38_controller.py' in proc.read_bytes()), 'original controller still active')
    ledger_dir = root / 'results/formation-spending-v021'
    require(read(ledger_dir / 'groq.json')['estimated_api_dollars'] == 0, 'Groq ledger must remain $0')
    for relative, digest in plan['other_ledger_sha256'].items():
        require(sha(root / relative) == digest, 'other provider ledger changed')
    for index, cell in enumerate(original_plan['cells'][:4]):
        name = '%s-r%02d' % key(cell)
        result = read(source / (name + '.json'))
        checkpoint = read(source / (name + '-checkpoint.json'))
        require(checkpoint['phase'] == 'complete' and checkpoint['result'] == result,
                'retained result/checkpoint differs')
        replay = replay_episode(load_cases([root / cell['path']])[0], checkpoint['packets'])
        require(all(replay[k] == result[k] for k in ('score', 'attempts', 'effects', 'final_world')),
                'retained replay differs')
        require(result['identity_valid'] == (index < 3), 'retained identity differs')
        require(bool(result.get('fatal_transport')) == (index == 3), 'retained fatal evidence differs')
    events = [json.loads(line) for line in raw.splitlines()]
    starts = [e for e in events if e['event'] == 'attempt_start']
    ends = [e for e in events if e['event'] == 'attempt_end']
    require(len(starts) == len(ends) and {e['id'] for e in starts} == {e['id'] for e in ends},
            'unclosed request; separate review required')
    require([e['id'] for e in starts] == ['A%06d' % i for i in range(1, len(starts) + 1)], 'attempt IDs differ')
    require(len({e['id'] for e in ends}) == len(ends), 'duplicate closure')
    logical = [e for e in events if e['event'] == 'logical_start']
    require([e['id'] for e in logical] == ['L%06d' % i for i in range(1, len(logical) + 1)], 'logical IDs differ')
    contexts = {e['id']: e['context'] for e in logical}
    responses = {e['id']: e for e in events if e['event'] == 'native_response'}
    require(len(responses) == sum(e['event'] == 'native_response' for e in events), 'duplicate native response')
    for end in ends:
        if end['id'] == 'A000020':
            require(end['error'] == 'HTTP 429' and end['reserve_retained'], 'reviewed failure differs')
            continue
        require(not end.get('error') and not end.get('model_mismatch') and not end.get('usage_missing')
                and end.get('model_returned') == MODEL and end.get('estimated_charge_dollars') == 0,
                'new issued/identity/usage/cost failure; separate review required')
        response = responses.get(end['id'], {}).get('response', {})
        require(response.get('model') == MODEL and response.get('usage') == end['usage']
                and usage_valid(end['usage']), 'native usage exceeds reserve or is invalid')
    suffix_cells = {key(c): c for c in plan['pending_cells']}
    counts = Counter()
    for start in starts[20:]:
        context = contexts[start['logical_id']]
        require(key(context) in suffix_cells, 'issued cell outside reviewed suffix')
        cell = suffix_cells[key(context)]
        require(all(context.get(k) == v for k, v in cell.items()), 'issued cell context differs')
        counts[key(context)] += 1
        require(context.get('turn') == counts[key(context)], 'issued turn order differs; no retries')
    require(len(starts) <= 20 + 236 * 12 and all(n <= 12 for n in counts.values()), 'request ceiling exceeded')
    requests = [e for e in events if e['event'] == 'native_request']
    require(len(requests) == len(starts) and len({e['id'] for e in requests}) == len(starts), 'native request closure differs')
    system = read(root / 'studies/formation-study-a-evaluation-plan-v0217.json')['system']
    for request in requests[20:]:
        context = contexts[next(e['logical_id'] for e in starts if e['id'] == request['id'])]
        checkpoint = read(source / ('%s-r%02d-checkpoint.json' % key(context)))
        case = load_cases([root / context['path']])[0]
        history, _ = history_for_next(case, context['arm'], checkpoint['packets'][:context['turn'] - 1])
        expected = {'model': MODEL, 'max_completion_tokens': 2048,
                    'messages': [{'role': 'system', 'content': system}] + history}
        require(request['body'] == expected and len(json.dumps(expected).encode()) <= 32000,
                'native request settings/history differ')

    require(journal_spend(source / 'calls.jsonl') == 0, 'nonzero journal spend')
    manifest_path = source / MANIFEST
    if manifest_path.exists():
        require(read(manifest_path) == expected_manifest(plan_path, plan), 'continuation manifest differs')
        progress = read(source / SUMMARY)
        require(progress['status'] in ('paused', 'complete'), 'prior continuation stop; separate review required')
        require(progress['quota_sha256'] == sha(ledger_dir / 'groq-rate.json')
                and progress['ledger_sha256'] == sha(ledger_dir / 'groq.json')
                and progress['journal_sha256'] == sha(source / 'calls.jsonl'), 'continuation boundary snapshot differs')
        require(len(progress['records']) == 236, 'continuation summary incomplete')
        paused = 0
        boundary = False
        for cell, row in zip(plan['pending_cells'], progress['records']):
            require(all(row[k] == v for k, v in cell.items()), 'continuation row order differs')
            name = '%s-r%02d' % key(cell)
            checkpoint = source / (name + '-checkpoint.json')
            result_path = source / (name + '.json')
            if row['status'] == 'complete':
                require(not boundary, 'completed cell after pending boundary')
                state = read(checkpoint)
                require(state['phase'] == 'complete' and state['result'] == read(result_path)
                        and not state['result'].get('fatal_transport') and state['result']['identity_valid'], 'fatal/invalid checkpoint')
                result = replay_episode(load_cases([root / cell['path']])[0], state['packets'])
                require(all(result[k] == state['result'][k] for k in ('score', 'attempts', 'effects', 'final_world')), 'continuation replay differs')
            elif row['status'] == 'paused':
                require(not boundary and not result_path.exists(), 'multiple/invalid paused boundary')
                boundary = True
                paused += 1
                require(read(checkpoint)['phase'] == 'paused', 'guard/inflight checkpoint; review required')
            else:
                boundary = True
                require(row['status'] == 'not_attempted' and not row['attempted']
                        and not checkpoint.exists() and not result_path.exists(), 'unexpected pending evidence')
        require((progress['status'] == 'complete' and not boundary)
                or (progress['status'] == 'paused' and paused == 1), 'only pre-request pauses may resume')
    else:
        require(len(starts) == 20, 'new journal events without continuation manifest')
        for relative, digest in plan['initial_groq_sha256'].items():
            require(sha(root / relative) == digest, 'initial quota/ledger differs; review required')
        for cell in plan['pending_cells']:
            name = '%s-r%02d' % key(cell)
            require(not (source / (name + '.json')).exists()
                    and not (source / (name + '-checkpoint.json')).exists(), 'pending cell already has evidence')
        require(not (source / SUMMARY).exists(), 'unexpected continuation summary')
    return plan


def expected_manifest(plan_path, plan):
    return {'plan_sha256': sha(plan_path), 'model': MODEL, 'provider': 'groq', 'budget': 0,
            'cells': plan['pending_cells'], 'retained_failure': 'A_R02 repeat 1 / A000020',
            'original_journal_bytes': plan['original_journal_bytes'], 'no_retry': True}


def verify_approval(plan_path, root, approved, reviewed_failure, confirm_free):
    require(approved and reviewed_failure and confirm_free, 'separate written continuation approval required')
    path = root / APPROVAL
    require(path.is_file(), 'separate execution approval receipt absent')
    approval = read(path)
    require(approval['approval'] == APPROVAL_TEXT and approval['plan_sha256'] == sha(plan_path)
            and approval['checkout_root'] == str(root) and approval['output'] == OUTPUT
            and approval['cap_dollars'] == 0 and approval['pre_request_quota_resumes_authorized'] is True
            and approval['issued_failure_retries_authorized'] is False, 'execution approval differs')


def run_continuation(plan_path, approved=False, reviewed_failure=False, confirm_free=False, root=ROOT):
    root = Path(root).resolve()
    # Approval must fail before credentials, clients, locks or evidence creation.
    verify_approval(plan_path, root, approved, reviewed_failure, confirm_free)
    plan = review_source(plan_path, root)
    source = root / OUTPUT
    lock = root / 'results/formation-spending-v021/run.lock'
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError('shared run lock exists; inspect before continuing') from None
    try:
        os.write(fd, str(os.getpid()).encode())
        # Verify evidence again under our own lock without bypassing the public lock guard.
        # The first review and exclusive acquisition cannot race another authorized writer:
        # it must hold this same lock. Recheck the boundary hashes after acquiring it.
        for name, digest in read(root / plan['source_review'])['source_sha256'].items():
            if name != 'calls.jsonl':
                require(sha(source / name) == digest, 'source changed during lock acquisition')
        if (source / MANIFEST).exists():
            prior_boundary = read(source / SUMMARY)
            expected = {'journal_sha256': source / 'calls.jsonl',
                        'quota_sha256': root / 'results/formation-spending-v021/groq-rate.json',
                        'ledger_sha256': root / 'results/formation-spending-v021/groq.json'}
        else:
            prior_boundary = {'journal_sha256': plan['original_journal_sha256']}
            expected = {'journal_sha256': source / 'calls.jsonl'}
            for relative, digest in plan['initial_groq_sha256'].items():
                require(sha(root / relative) == digest, 'quota changed during lock acquisition')
        require(all(sha(path) == prior_boundary[field] for field, path in expected.items()), 'boundary changed during lock acquisition')
        if (source / SUMMARY).exists() and read(source / SUMMARY)['status'] == 'complete':
            return read(source / SUMMARY)
        if not (source / MANIFEST).exists():
            atomic(source / MANIFEST, expected_manifest(plan_path, plan))
        ledger = root / 'results/formation-spending-v021/groq.json'
        prices = read(root / plan['price_file'])['models']
        recorder = ContinuationRecorder(source / 'calls.jsonl', prices, MODEL, max_logical=20 + 236 * 12,
                                 max_attempts=20 + 236 * 12, max_dollars=0,
                                 prior_spend=0, ledger_path=ledger)
        require(not recorder.pending and not recorder.missing_usage, 'unusable journal; review required')
        quota = GroqSlots(root / 'results/formation-spending-v021/groq-rate.json')
        recorder.quota = quota
        client = make_client(MODEL, 'groq', recorder, quota)
        load_keys(root / 'keys.env')
        rows = []
        status = 'complete'
        stop = False
        for cell in plan['pending_cells']:
            if stop:
                rows.append(dict(cell, outcome='error', attempted=False, identity_valid=False, status='not_attempted'))
                continue
            name = '%s-r%02d' % key(cell)
            state_path = source / (name + '-checkpoint.json')
            result, status = execute_cell(cell, load_cases([root / cell['path']])[0], client, recorder, state_path)
            if result is None:
                packets = read(state_path)['packets']
                rows.append(dict(cell, outcome='error', attempted=bool(packets), identity_valid=bool(packets), status=status))
                stop = True
            else:
                # Completed result bytes are never rewritten during quota resumes.
                path = source / (name + '.json')
                if path.exists():
                    require(read(path) == result, 'completed result differs')
                else:
                    atomic(path, result)
                rows.append(dict(cell, outcome=result['score']['outcome'], attempted=result['attempted'],
                                 identity_valid=result['identity_valid'], status='complete'))
                if result.get('fatal_transport'):
                    status = 'stopped'
                    stop = True
        original = read(source / 'progress-summary.json')['records'][:4]
        summary = {'model': MODEL, 'status': status, 'planned_cells': 236,
                   'completed_cells': sum(r['status'] == 'complete' for r in rows),
                   'records': rows, 'combined_records': original + rows,
                   'batch_estimated_dollars': journal_spend(source / 'calls.jsonl'),
                   'additional_estimated_dollars': 0, 'retained_failure': 'A_R02 repeat 1 / A000020',
                   'journal_sha256': sha(source / 'calls.jsonl'), 'quota_sha256': sha(quota.path),
                   'ledger_sha256': sha(ledger), 'accounting': recorder.snapshot()}
        atomic(source / SUMMARY, summary)
        return summary
    finally:
        owned = os.fstat(fd)
        os.close(fd)
        if lock.exists() and lock.stat().st_ino == owned.st_ino and lock.stat().st_dev == owned.st_dev:
            lock.unlink()
