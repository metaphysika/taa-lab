"""Owner-authorized evidence closure only; no runner, transport or state mutation."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal
from collections import Counter

sys.path.insert(0, '/workspace/taa-experiment-a-continuation2-be2b7c8e')
from live_demo.evidence import Evidence, encoded, verify
from experiment_a.continuation import Continuation

HERE = Path(__file__).parent
ROOT = HERE/'pilot'
STATE = Path('/workspace/taa-experiment-state')
TIP = '40f2c28cf127a8d75aaea14083d74b3ea3a9f524'
SOURCES = [Path('/workspace/taa-experiment-a-evidence/pilot-b871cee5-20261026/pilot'),
           Path('/workspace/taa-experiment-a-evidence/continuation1-480835a8-20261027/pilot'), ROOT]

def git(*args):
    return subprocess.check_output(['git','-C',str(STATE),*args],text=True).strip()

def prefix(root):
    head='0'*64; rows=[]
    for n,p in enumerate(sorted(root.glob('[0-9]*.json'))):
        b=p.read_bytes(); row=json.loads(b)
        assert p.name=='%06d.json'%n and row['sequence']==n and row['previous']==head
        assert b==encoded(row)+b'\n'
        rows.append(row);head=hashlib.sha256(b).hexdigest()
    return rows,dict(count=len(rows),head=head)

def stamp(p):
    return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                mtime_ns=p.stat().st_mtime_ns,
                modified_utc=datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat())

def write(name,obj):
    with (HERE/name).open('x') as f: json.dump(obj,f,indent=2,sort_keys=True);f.write('\n')

def main():
    # Inspect process argument vectors without exposing environment variables.
    processes=[]
    for p in Path('/proc').glob('[0-9]*/cmdline'):
        try:args=p.read_bytes().split(b'\0')
        except (FileNotFoundError,PermissionError,ProcessLookupError):continue
        if b'experiment_a.run' in args or b'experiment_a.check' in args:
            processes.append(int(p.parent.name))
    assert not processes, 'existing provider runner alive; do not touch evidence'
    assert not (ROOT/'checkpoint.json').exists(), 'already closed; do not repeat'
    assert git('rev-parse','HEAD')==TIP and not git('status','--porcelain')
    state_files={p:stamp(STATE/p) for p in git('ls-files').splitlines()}
    retained={str(p.relative_to(ROOT)):stamp(p) for p in sorted(ROOT.rglob('*')) if p.is_file()}
    latest=max(retained,key=lambda x:retained[x]['mtime_ns'])
    root_frames,root_prefix=prefix(ROOT)
    children=[]; open_children=[]
    for p in sorted(ROOT.glob('episode-*')):
        rows,cp=prefix(p)
        sealed=(p/'checkpoint.json').exists()
        if sealed: assert verify(p)==cp
        else:open_children.append(p)
        children.append(dict(directory=p.name,checkpoint_before=cp,sealed_before=sealed))
    assert [p.name for p in open_children]==['episode-0090']
    rr=[f['value'] for f in root_frames if f['kind']=='episode_summary']
    request=[f['value'] for f in root_frames if f['kind']=='request'][-1]
    assert len(rr)==36 and request['turn']==4 and request['spec']==dict(arm='taa',program='T09',provider='anthropic',repeat=3)
    child_frames,_=prefix(open_children[0])
    assert not any(f['kind'] in ('episode_end','closure') for f in child_frames)
    # Verify ALL native settlements and retained reserves under the committed auditor.
    claim=git('log','--format=%H','--diff-filter=A','--','run.once').splitlines()
    assert len(claim)==1
    baseline=claim[0]+'^'
    ledgers={'anthropic':'ledgers/claude.json','google':'ledgers/google.json'}
    totals={p:Decimal(str(json.loads(git('show',baseline+':'+f))['estimated_api_dollars'])) for p,f in ledgers.items()}
    step=Decimal(git('show',baseline+':step-budget.txt'));retry=0
    auditor=Continuation.__new__(Continuation)
    for source in SOURCES:
        fs,cp=prefix(source)
        if source!=ROOT:assert verify(source)==cp
        step,n=auditor._account(fs,totals,step);retry+=n
    actual={p:Decimal(str(json.loads((STATE/f).read_bytes())['estimated_api_dollars'])) for p,f in ledgers.items()}
    assert totals==actual and step==Decimal((STATE/'step-budget.txt').read_text())
    assert all(sum(f['kind']==k and f['value']['provider']==p for f in root_frames)==
               sum(f['kind']=='usage' and f['value']['provider']==p for f in root_frames)
               for p in ledgers for k in ('reservation','request'))
    assert sum(f['kind']=='native_reply' for f in root_frames)==sum(f['kind']=='usage' for f in root_frames)
    observation=dict(claim='[Descriptive] Read-only restored-workspace observations before owner-authorized closure.',
        process_alive=False,last_evidence_file=latest,last_evidence_file_before=retained[latest],
        root_prefix_before=root_prefix,children_before=children,last_recorded_request={k:request[k] for k in ('spec','turn','attempt')},
        state_commit=TIP,state_files_before=state_files,preserved_evidence_files_before=retained,
        accounting=dict(provider_totals={p:str(v) for p,v in totals.items()},step_total=str(step),retry_needed=retry,
                        native_settlements_match=True,no_open_pilot_reservation=True),
        completed_in_continuation2=len(rr),interrupted_index=90,
        missing_episode_end=True,missing_metrics_not_reconstructed=True)
    write('outage-before.json',observation)
    # Reattach ONLY the append-only writer, never the experiment runner or host.
    def writer(path):
        _,cp=prefix(path); e=Evidence.__new__(Evidence)
        e.directory=path;e.sequence=cp['count'];e.head=cp['head'];return e
    child_cp=writer(open_children[0]).close(dict(stop='executor_outage',guard_stop=True,
        owner='Chris',approval_date='2026-10-27',posthoc_closure=True,
        episode_index=90,last_recorded_request_turn=4,episode_end_absent=True,
        note='Retained records only; missing episode_end and metrics were not reconstructed. Never resumed.'))
    e=writer(ROOT)
    e.write('executor_outage_observation',dict(stop='executor_outage',owner='Chris',approval_date='2026-10-27',
        process_alive=False,interrupted_index=90,last_recorded_request_turn=4,
        observed_last_file=latest,observed_last_file_modified_utc=retained[latest]['modified_utc'],
        prefix_checkpoint=root_prefix,child_ending_checkpoint=child_cp,state_commit=TIP,
        completed_episode_summaries=36,missing_episode_metrics_not_reconstructed=True,
        active_lease_and_markers_unchanged=True))
    root_cp=e.close(dict(stop='executor_outage',guard_stop=True,posthoc_closure=True,
        completed_episode_summaries=36,interrupted_index=90,owner='Chris',approval_date='2026-10-27'))
    for name,entry in retained.items():assert stamp(ROOT/name)==entry
    assert state_files=={p:stamp(STATE/p) for p in state_files}
    allchains=[]
    for source in SOURCES:
        allchains.append(dict(directory=str(source),**verify(source)))
        for p in sorted(source.glob('episode-*')):allchains.append(dict(directory=str(p),**verify(p)))
    write('outage-verification.json',dict(claim='[Descriptive] Appended closures only; every retained byte and timestamp preserved.',
        chains=allchains,root_checkpoint=root_cp,child_checkpoint=child_cp,
        preserved_file_count=len(retained),all_retained_files_unchanged=True,
        state_all_tracked_bytes_and_timestamps_unchanged=True,accounting=observation['accounting'],state_commit=TIP))
    events=[dict(directory=str(source),sequence=f['sequence'],kind=f['kind'],value=f['value'])
        for source in SOURCES for f in prefix(source)[0]
        if f['kind'] in ('stranded_settlement','state_confirmation_wait','state_confirmation','state_repush','state_repush_result')]
    write('state-confirmations.json',events)
    print(json.dumps(dict(process_alive=False,last_evidence_file=latest,last_evidence_time=retained[latest]['modified_utc'],
        last_request=observation['last_recorded_request'],root_checkpoint=root_cp,verified_chains=len(allchains),
        accounting=observation['accounting'],state_unchanged=True)))

if __name__=='__main__': main()
