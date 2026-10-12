"""Offline continuation replay, exact wire/retry history and native closure audit."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from formation.evaluation_gemma_continuation_v0223 import PLAN, review_source
from formation.evaluation_gemma_v0222 import MODEL, read, sha, name, body_hash, GemmaChat, atomic
from formation.evaluation_runner_v0218 import history_for_next
from formation.study_a import load_cases, replay_episode
from formation.study_a_pilot import SYSTEM


def audit(plan_path=PLAN, root=ROOT):
    # Terminal audit only: the runner must have released its own shared lock.
    plan = review_source(plan_path, root)
    out = root / plan['output']
    status = read(out/'continuation-controller-status.json')
    if status['state'] not in ('complete','stopped_for_review'):
        raise ValueError('terminal offline audit required; no active runner requests')
    events = [json.loads(l) for l in (out/'continuation-calls.jsonl').read_text().splitlines()]
    starts = {e['id']:e for e in events if e['event']=='attempt_start'}
    ends = {e['id']:e for e in events if e['event']=='attempt_end'}
    assert len(starts)==sum(e['event']=='attempt_start' for e in events)
    assert len(ends)==sum(e['event']=='attempt_end' for e in events)
    logicals = {e['id']:e for e in events if e['event']=='logical_start'}
    natives = {e['id']:e['response'] for e in events if e['event']=='native_response'}
    bodies = {e['id']:e['body'] for e in events if e['event']=='native_request'}
    preflights = {e['id']:e for e in events if e['event']=='token_preflight'}
    counted = {e['body_sha256']:e['totalTokens'] for e in (
        json.loads(l) for l in (out/'continuation-token-counts.jsonl').read_text().splitlines()) if e['event']=='count_complete'}
    allcells = plan['pending_cells'] + plan['initial_replacements']
    cells = {(c['case_id'],c['repeat']):c for c in allcells}
    cases = {c['id']:c for c in load_cases([root/p for p in {c['path'] for c in allcells}])}
    rows = []
    for checkpoint in out.glob('continuation-*-checkpoint.json'):
        state = read(checkpoint)
        if state['phase']!='complete':
            continue
        result = state['result']
        cell = dict(cells[(result['case_id'],result['repeat'])],replacement=result['replacement'])
        assert read(out/('continuation-'+name(cell)+'.json'))==result
        assert replay_episode(cases[cell['case_id']],state['packets'])['score']==result['score']
        rows.append(dict(cell,score=result['score'],transport_lost=result['transport_lost'],identity_valid=result['identity_valid']))
    for aid,start in starts.items():
        context = logicals[start['logical_id']]['context']
        cell = dict(cells[(context['case_id'],context['repeat'])],replacement=context.get('replacement',False))
        checkpoint = read(out/('continuation-'+name(cell)+'-checkpoint.json'))
        history,_ = history_for_next(cases[cell['case_id']],cell['arm'],checkpoint['packets'][:context['turn']-1])
        body = GemmaChat.body(type('Settings',(),{'max_output_tokens':2048})(),SYSTEM,history)
        assert bodies[aid]==body,'retry or continuation wire history changed'
        p = preflights[aid]
        assert p['body_sha256']==body_hash(body) and counted[body_hash(body)]==p['counted_prompt_tokens']
        assert p['counted_prompt_tokens']+2048+128<=16000 and len(json.dumps(body).encode())<=32000
        if aid in natives:
            assert natives[aid]['modelVersion']==MODEL
            assert natives[aid]['usageMetadata']['promptTokenCount']<=p['counted_prompt_tokens']+128
            assert ends[aid]['estimated_charge_dollars']==0
    retry = read(out/'continuation-retry-state.json')
    attempts = [json.loads(l) for l in (out/'continuation-transport-attempts.jsonl').read_text().splitlines()]
    barriers = set()
    for event in attempts:
        if event['event']=='received_reply_barrier':
            barriers.add(event['job'])
        if event['event']=='transport_attempt_start':
            assert event['job'] not in barriers,'request resent after any output'
            assert event['attempt']<=5
    primary = [r for r in rows if not r['replacement']]
    replacements = [r for r in rows if r['replacement']]
    for r in replacements:
        assert any(c['case_id']==r['case_id'] and c['repeat']==r['repeat'] for c in plan['initial_replacements']) or \
            any(p['case_id']==r['case_id'] and p['repeat']==r['repeat'] and p['transport_lost'] for p in primary)
    order = [logicals[e['logical_id']]['context'].get('replacement',False) for e in events if e['event']=='attempt_start']
    if True in order:
        assert all(order[order.index(True):]) and len(primary)==237
    result = {'state':status['state'],'source_evidence_unchanged':True,'frozen_files_verified':59,
        'completed_untouched_cells':len(primary),'completed_replacements':len(replacements),
        'combined_primary_cells':3+len(primary),'issued_generations':len(starts),'native_responses':len(natives),
        'generation_closures':len(ends),'unclosed_attempts':sorted(set(starts)-set(ends)),
        'requests_needing_retry':retry['requests_needing_retry'],'max_attempts':max((j['attempts'] for j in retry['jobs'].values()),default=0),
        'no_resend_after_received_output':True,'full_wire_history_and_deterministic_replay_equal':True,
        'primary_records':primary,'replacement_records':replacements,'Gemma_estimated_dollars':0,
        'Google_cumulative_dollars':read(root/'results/formation-spending-v021/google.json')['estimated_api_dollars'],
        'P6_verdict':'not computed; amendment review pending'}
    if status['state']=='complete':
        assert len(primary)==237 and len({(r['case_id'],r['repeat']) for r in primary})==237
        assert set(starts)==set(ends) and retry['stop'] is None and retry['requests_needing_retry']<=10
        assert not read(out/'continuation-quota.json')['metadata_inflight']
    atomic(out/'continuation-offline-audit.json',result)
    return result


if __name__=='__main__':
    result=audit()
    print('Gemma continuation audit: %s; %d/237 untouched, %d replacements; $0'%(
        result['state'],result['completed_untouched_cells'],result['completed_replacements']))
