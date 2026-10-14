"""Offline review packet. Reads evidence; writes proposal directory ONLY. No HTTP."""
import collections
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from formation import study_c_evaluation_v0243 as c
from formation import study_c_usage_proposal_v0244 as policy

ROOT=Path('/workspace/taa-lab')
PACKET='studies/formation-study-c-gemma-usage-remedy-proposal-v0244'


def build(root=ROOT):
    f,a,cases,cells,seeds=c.check(root,approved=True)
    if c.provider_processes() or c.HOLD.exists() or (root/'results/formation-spending-v021/run.lock').exists():
        raise ValueError('offline review requires stopped original environment')
    output=root/f['outputs'][policy.MODEL];directory=root/PACKET
    directory.mkdir(exist_ok=True)
    stop=c.read(output/'native-usage-stop-integrity-v0243.json')
    for name,digest in stop['files_sha256'].items():
        if c.sha(output/name)!=digest:raise ValueError('stop evidence changed: '+name)
    rows=c.read(output/'progress-summary.json')['records']
    protected={}
    for row in rows[:350]:
        cell=next(cell for cell in cells if cell['cell_id']==row['cell_id'])
        path=c.checkpoint_path(output,cell)
        state=c.read(path);replay=c.replay(cases[row['probe_id']],state['packets'])
        for field in ['score','terminal_status','attempts','effects','final_world']:
            if replay[field]!=row[field]:raise ValueError('completed replay changed')
        protected[str(path.relative_to(root))]=c.sha(path)
    ledger_hashes={str(p.relative_to(root)):c.sha(p) for p in (root/'results/formation-spending-v021').glob('*.json')}
    events=c.journal(output/'calls.jsonl')
    native=[e for e in events if e['event']=='native_response']
    missing_ids=[e['id'] for e in native
                 if 'candidatesTokenCount' not in (e['response'].get('usageMetadata') or {})]
    if missing_ids != ['A001453']:
        raise ValueError('initial missing-usage event count differs')
    received=native[-1];preflight=next(e for e in events if e['event']=='token_preflight' and e['id']==received['id'])
    raw,finish=c.CLASSES['google'].extract(None,received['response'])
    parsed=c.parse_action(raw)
    booking=policy.conservative_booking(policy.MODEL,received['response'],preflight['counted_prompt_tokens'])
    sidecar=policy.book_once({},received['id'],booking)
    prefix=rows[-1]['packets'][:2]+[dict(kind='reply',raw=raw)]
    rebuilt=c.replay(cases[rows[-1]['probe_id']],prefix)
    quota=c.read(output/'quota.json')
    source=c.read(root/f['Gemma_quota_source']/'quota.json')
    generations=[e for e in quota['events'][len(source['events']):] if e['kind']=='generation']
    if len(generations)!=len(native):raise ValueError('native/quota generation mismatch')
    historical=[];peak=0;peak_id=None
    for q,n in zip(generations,native):
        u=n['response']['usageMetadata']
        completion=u['candidatesTokenCount']+u.get('thoughtsTokenCount',0) if 'candidatesTokenCount'in u else 4096
        historical.append(dict(at=q['at'],tokens=q['tokens']+completion,attempt_id=n['id']))
        used=sum(x['tokens'] for x in historical if q['at']-x['at']<61)
        if used>peak:peak,peak_id=used,n['id']
    clock=[0.];reserved=[];max_total=max_input=max_http=0
    with tempfile.TemporaryDirectory() as folder:
        quota_test=c.CQuota(Path(folder)/'quota.json',Path(folder)/'counts.jsonl',now=lambda:clock[0])
        for i in range(1000):
            count=[0,1028,2452,8000,11776][i%5]
            while True:
                clock[0]=policy.combined_ready_at(reserved,count,clock[0])
                try:quota_test.reserve('countTokens',0);break
                except c.RatePaused:clock[0]=quota_test.ready_at
            while True:
                clock[0]=policy.combined_ready_at(reserved,count,clock[0])
                try:quota_test.reserve('generation',count+128);break
                except c.RatePaused:clock[0]=quota_test.ready_at
            reserved=policy.reserve_combined(reserved,count,clock[0],str(i))
            window=[e for e in quota_test.state['events'] if clock[0]-e['at']<61]
            max_total=max(max_total,sum(e['tokens'] for e in reserved if clock[0]-e['at']<61))
            max_input=max(max_input,sum(e['tokens'] for e in window));max_http=max(max_http,len(window))
            if max_total>16000 or max_input>14400 or max_http>24:raise ValueError('pacing exceeded')
            clock[0]+=.01
    report=dict(execution_authorized=False,live_HTTP_calls=0,completed_350_replayed=True,
                immutable_checkpoint_sha256=protected,ledger_sha256=ledger_hashes,
                full_stop_index_sha256=c.sha(output/'native-usage-stop-integrity-v0243.json'),
                stopped_attempt_id=received['id'],stopped_cell=rows[-1]['cell_id'],
                all_missing_output_usage_attempts=missing_ids,
                original_checkpoint_sha256=c.sha(c.checkpoint_path(output,cells[350])),
                exact_received_text=raw,exact_received_text_sha256=c.hashlib.sha256(raw.encode()).hexdigest(),
                frozen_parser_action=parsed,finish_reason=finish,proposed_usage_sidecar=sidecar,
                proposed_three_packet_prefix=prefix,prefix_replay_terminal=rebuilt['terminal_status'],
                prefix_effects=rebuilt['effects'],next_turn=4,
                historical_combined_max61=peak,historical_peak_attempt=peak_id,
                stopped_window_combined_with_missing_reserve=sum(e['tokens'] for e in historical if historical[-1]['at']-e['at']<61),
                prospective_simulated_generations=1000,prospective_max_total61=max_total,
                prospective_max_input61=max_input,prospective_max_HTTP61=max_http,
                longest_admitted_prompt_tokens=11776,source_check='passed',
                original_stop_full_terminal_audit='NOT_CERTIFIED; prospective amendment required')
    for file,digest in {**protected,**ledger_hashes}.items():
        if c.sha(root/file)!=digest:raise ValueError('offline review mutated evidence')
    (directory/'offline-review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['completed_350_replayed','live_HTTP_calls','next_turn','historical_combined_max61','stopped_window_combined_with_missing_reserve','prospective_max_total61','prospective_max_input61','prospective_max_HTTP61']}))
    return report


if __name__=='__main__':build()
