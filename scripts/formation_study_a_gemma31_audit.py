"""Offline Gemma evidence/replay audit. Never obtains credentials or calls a model."""
import collections
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from formation.evaluation_gemma_v0222 import (MODEL, OUTPUT, PLAN_PATH, read, sha,
    check_plan, body_hash, name, GemmaChat)
from formation.evaluation_runner_v0218 import history_for_next, atomic
from formation.study_a import load_cases, replay_episode
from formation.study_a_pilot import SYSTEM


def audit(output=OUTPUT, plan_path=PLAN_PATH):
    plan = read(plan_path)
    check_plan(plan, ROOT)
    output = Path(output)
    status = read(output / 'controller-status.json')
    if status['state'] not in ('complete', 'stopped_for_review', 'waiting_pre_request_quota'):
        raise ValueError('audit only at a safe paused/terminal boundary')
    quota = read(output / 'gemma-quota.json')
    events = [json.loads(l) for l in (output / 'calls.jsonl').read_text().splitlines()] if (output / 'calls.jsonl').exists() else []
    starts = {e['id']: e for e in events if e['event'] == 'attempt_start'}
    ends = {e['id']: e for e in events if e['event'] == 'attempt_end'}
    assert len(starts) == sum(e['event'] == 'attempt_start' for e in events), 'duplicate generation ID'
    assert len(ends) == sum(e['event'] == 'attempt_end' for e in events), 'duplicate closure ID'
    native = {e['id']: e['response'] for e in events if e['event'] == 'native_response'}
    requests = {e['id']: e['body'] for e in events if e['event'] == 'native_request'}
    preflight = {e['id']: e for e in events if e['event'] == 'token_preflight'}
    logicals = {e['id']: e for e in events if e['event'] == 'logical_start'}
    receipts = [json.loads(l) for l in (output / 'token-counts.jsonl').read_text().splitlines()] if (output / 'token-counts.jsonl').exists() else []
    count_starts = collections.Counter(e['body_sha256'] for e in receipts if e['event'] == 'count_start')
    count_ends = collections.Counter(e['body_sha256'] for e in receipts if e['event'] in ('count_complete', 'count_error'))
    counted = {e['body_sha256']: e['totalTokens'] for e in receipts if e['event'] == 'count_complete'}
    cells = {(c['case_id'], c['repeat']): c for c in plan['cells']}
    cases = {c['id']: c for c in load_cases([ROOT / p for p in {c['path'] for c in plan['cells']}])}
    rows = []
    for checkpoint in sorted(output.glob('*-checkpoint.json')):
        state = read(checkpoint)
        if state['phase'] != 'complete':
            continue
        result = state['result']
        assert replay_episode(cases[result['case_id']], state['packets'])['score'] == result['score'], 'deterministic score differs'
        replacement = bool(result.get('replacement'))
        cell = dict(cells[(result['case_id'], result['repeat'])], replacement=replacement)
        saved = output / (name(cell) + '.json')
        assert saved.exists() and read(saved) == result, 'result/checkpoint mismatch'
        rows.append(dict(cell, score=result['score'], rate_lost=result.get('rate_lost', False),
                         identity_valid=result['identity_valid']))
    for aid, start in starts.items():
        ctx = logicals[start['logical_id']]['context']
        cell = dict(cells[(ctx['case_id'], ctx['repeat'])], replacement=ctx.get('replacement', False))
        checkpoint = read(output / (name(cell) + '-checkpoint.json'))
        packets = checkpoint['packets'][:ctx['turn'] - 1]
        history, _ = history_for_next(cases[cell['case_id']], cell['arm'], packets)
        body = GemmaChat.body(type('Settings', (), {'max_output_tokens': 2048})(), SYSTEM, history)
        assert requests[aid] == body, 'frozen full request history differs'
        p = preflight[aid]
        assert p['body_sha256'] == body_hash(body) and counted[body_hash(body)] == p['counted_prompt_tokens']
        assert p['counted_prompt_tokens'] + 2048 + 128 <= 16000 and len(json.dumps(body).encode()) <= 32000
        if aid in native:
            u = native[aid].get('usageMetadata') or {}
            if aid in ends and not ends[aid].get('error'):
                assert native[aid].get('modelVersion') == MODEL
                assert 0 <= u['promptTokenCount'] <= p['counted_prompt_tokens'] + 128
                assert ends[aid]['usage']['completion_tokens'] <= 2048
                assert ends[aid]['estimated_charge_dollars'] == 0
    primaries = [r for r in rows if not r['replacement']]
    replacements = [r for r in rows if r['replacement']]
    for replacement in replacements:
        assert any(r['case_id'] == replacement['case_id'] and r['repeat'] == replacement['repeat'] and r['rate_lost'] for r in primaries)
    gen_order = [logicals[e['logical_id']]['context'].get('replacement', False) for e in events if e['event'] == 'attempt_start']
    if True in gen_order:
        assert all(gen_order[gen_order.index(True):]), 'replacement before all primary requests finished'
        assert len(primaries) == 240
    failures = [e for e in ends.values() if e.get('error') or e.get('usage_missing') or e.get('model_mismatch')]
    groups = {}
    for r in primaries:
        key = r['arm'] + '_' + r['case_id'].split('_')[1][0]
        group = groups.setdefault(key, {'attempted': 0, 'correct': 0, 'outcomes': {}})
        group['attempted'] += 1
        outcome = r['score']['outcome']
        group['correct'] += outcome == 'correct'
        group['outcomes'][outcome] = group['outcomes'].get(outcome, 0) + 1
    ledger = read(ROOT / 'results/formation-spending-v021/google.json')
    assert ledger['estimated_api_dollars'] == plan['google_prior_dollars'], 'Google cumulative changed in amount'
    result = {'state': status['state'], 'frozen_files_verified': 59, 'pinned_files_verified': True,
              'primary_completed_cells': len(primaries), 'replacement_completed_cells': len(replacements),
              'issued_generation_requests': len(starts), 'native_responses': len(native),
              'generation_closures': len(ends), 'unclosed_generation_ids': sorted(set(starts) - set(ends)),
              'count_requests_closed': count_starts == count_ends and quota['metadata_inflight'] is None,
              'rate_errors': quota['rate_errors'], 'issued_failures': failures,
              'deterministic_replay_and_full_history_equal': True, 'primary_groups': groups,
              'Gemma_estimated_dollars': 0, 'Google_cumulative_dollars': ledger['estimated_api_dollars'],
              'P6_verdict': 'not computed; prospective amendment review remains pending',
              'sha256': {str(p.relative_to(ROOT)): sha(p) for p in output.iterdir() if p.is_file() and p.name != 'offline-audit.json'}}
    if status['state'] == 'complete':
        assert len(primaries) == 240 and len({(r['case_id'], r['repeat']) for r in primaries}) == 240
        assert not result['unclosed_generation_ids'] and result['count_requests_closed']
        assert all(e.get('status') == 429 for e in failures), 'completed with non-rate transport failure'
    atomic(output / 'offline-audit.json', result)
    return result


if __name__ == '__main__':
    result = audit()
    print('Gemma offline audit: %s; %d primary cells, %d replacements; $0; Google $%.8f' % (
        result['state'], result['primary_completed_cells'], result['replacement_completed_cells'], result['Google_cumulative_dollars']))
