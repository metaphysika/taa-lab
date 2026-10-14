"""Bound local Gemma adoption/accounting state. No HTTP or credential access."""
import copy
import json
import shutil
from pathlib import Path

from agents.call_telemetry import BudgetStopped
from formation.study_c_usage_proposal_v0244 import (
    conservative_booking, book_once, require_calls_allowed,
    combined_ready_at, reserve_combined)

APPROVAL='studies/formation-study-c-usage-approval-v0244.json'
BINDING='studies/formation-study-c-usage-binding-v0244.json'
CI='studies/formation-study-c-usage-ready-ci-v0244.json'
MARKER='received-reply-adoption-v0244.json'
ARCHIVE='usage-stop-archive-v0244'
BOOKINGS='usage-bookings-v0244.json'
PACING='combined-pacing-v0244.json'
CELL='C-brake-r3-W-r04-contrary-k02'
ATTEMPT='A001453'
SIDECAR=CELL+'-received-continuation-v0244.json'


def verify(c,root,adapter=True):
    root=Path(root);am=c.read(root/APPROVAL)
    if not am['execution_authorized'] or am['root']!=str(root.resolve()) or am['reserve']!=4096 or am['review_after']!=5 or am['paid_models_exempt'] or am['Study_D_authorized']:
        raise BudgetStopped('usage owner scope differs')
    if am['science_sha256']!=c.sha(root/c.FREEZE) or am['count_binding_sha256']!=c.sha(root/c.COUNT_BINDING):
        raise BudgetStopped('usage science/original adapter changed')
    output=root/am['output'];active=(output/MARKER).exists()
    if c.sha(output/'native-usage-stop-integrity-v0243.json')!=am['stop_index_sha256']:
        raise BudgetStopped('original usage stop index changed')
    for name,digest in c.read(output/'native-usage-stop-integrity-v0243.json')['files_sha256'].items():
        path=output/ARCHIVE/name if active else output/name
        if c.sha(path)!=digest:raise BudgetStopped('original usage stop archive changed: '+name)
    for name,digest in am['completed_checkpoint_sha256'].items():
        if c.sha(root/name)!=digest:raise BudgetStopped('completed350 or original351 checkpoint changed')
    for name,record in am['journal_prefixes'].items():
        if c.prefix_hash(output/name,record['bytes'])!=record['sha256']:
            raise BudgetStopped('pre-usage append-only prefix changed')
    if active:
        marker=c.read(output/MARKER)
        if marker!=dict(approval_sha256=c.sha(root/APPROVAL),binding_sha256=c.sha(root/BINDING),cell_id=CELL,attempt_id=ATTEMPT,next_turn=4):
            raise BudgetStopped('one-shot adoption marker changed')
        old=c.read(output/ARCHIVE/'transport-retry-state.json');current=c.read(output/'transport-retry-state.json')
        if any(current['jobs'].get(k)!=v for k,v in old['jobs'].items()) or current['requests_needing_retry']<old['requests_needing_retry']:
            raise BudgetStopped('prior jobs/counters changed')
    if adapter:
        binding=c.read(root/BINDING)
        if binding['approval_sha256']!=c.sha(root/APPROVAL):raise BudgetStopped('usage approval binding differs')
        for name,digest in binding['files_sha256'].items():
            if c.sha(root/name)!=digest:raise BudgetStopped('usage dependency changed: '+name)
    return am


def require_ci(c,root):
    receipt=c.read(Path(root)/CI)
    if receipt['binding_sha256']!=c.sha(Path(root)/BINDING) or {x['name'] for x in receipt['checks']}!={'Harness checks','Formation Python 3.9 checks'} or len(receipt['checks'])!=2 or any(x['conclusion']!='success' for x in receipt['checks']):
        raise BudgetStopped('both usage-readiness GitHub checks required')


def saved_prefix(c,root,output,cases,cells):
    am=verify(c,root)
    if (output/MARKER).exists() or (output/SIDECAR).exists() or c.read(output/'controller-status.json')['state']!='stopped_for_review':
        raise BudgetStopped('exact usage stop only; never relaunch adoption')
    row=c.read(output/'progress-summary.json')['records'][-1]
    if len(c.read(output/'progress-summary.json')['records'])!=351 or row['cell_id']!=CELL or not row['fatal'] or len(row['packets'])!=3 or row['packets'][2]['kind']!='error':
        raise BudgetStopped('wrong stopped episode/packet boundary')
    events=c.journal(output/'calls.jsonl')
    native=next(e for e in reversed(events) if e['event']=='native_response')
    pre=next(e for e in events if e['event']=='token_preflight' and e['id']==ATTEMPT)
    logical=next(e for e in events if e['event']=='logical_start' and e['id']==am['logical_id'])
    wire=next(e for e in events if e['event']=='native_request' and e['id']==ATTEMPT)
    if native['id']!=ATTEMPT or c.body_hash(wire['body'])!=am['received_body_sha256'] or logical['context']['cell_id']!=CELL or logical['context']['turn']!=3:
        raise BudgetStopped('saved native body/cell/turn differs')
    booking=conservative_booking('gemma-4-31b-it',native['response'],pre['counted_prompt_tokens'])
    raw,_=c.CLASSES['google'].extract(None,native['response']);c.parse_action(raw)
    if c.hashlib.sha256(raw.encode()).hexdigest()!=am['received_text_sha256']:
        raise BudgetStopped('saved native text differs')
    packets=copy.deepcopy(row['packets'][:2])+[dict(kind='reply',raw=raw)]
    if c.replay(cases[row['probe_id']],packets)['terminal_status']!='fixture_exhausted':
        raise BudgetStopped('adopted prefix not at approved next turn4')
    return packets,booking,logical


def initialize(c,root,output,packets,booking,logical):
    am=verify(c,root)
    if (output/MARKER).exists() or (output/ARCHIVE).exists():raise BudgetStopped('usage adoption already prepared')
    archive=output/ARCHIVE;archive.mkdir()
    for name in c.read(output/'native-usage-stop-integrity-v0243.json')['files_sha256']:
        target=archive/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(output/name,target)
    c.atomic(output/MARKER,dict(approval_sha256=c.sha(Path(root)/APPROVAL),binding_sha256=c.sha(Path(root)/BINDING),cell_id=CELL,attempt_id=ATTEMPT,next_turn=4))
    c.atomic(output/BOOKINGS,book_once({},ATTEMPT,booking))
    # Include the original chronology; expired windows expire normally, no reset.
    native={e['id']:e['response'] for e in c.journal(output/'calls.jsonl') if e['event']=='native_response'}
    old_quota=c.read(output/'quota.json')['events']
    source=c.read(Path(root)/c.read(Path(root)/c.FREEZE)['Gemma_quota_source']/'quota.json')
    generations=[e for e in old_quota[len(source['events']):] if e['kind']=='generation']
    if len(generations)!=len(native):raise BudgetStopped('original quota/native sequence differs')
    history=[]
    for q,(aid,response) in zip(generations,native.items()):
        u=response['usageMetadata'];output_tokens=u['candidatesTokenCount']+u.get('thoughtsTokenCount',0) if 'candidatesTokenCount'in u else 4096
        history.append(dict(at=q['at'],tokens=q['tokens']+output_tokens,attempt_id=aid,historical=True))
    c.atomic(output/PACING,dict(events=history,first_new_event=len(history),historical_peak_disclosed=am['historical_combined_peak']))
    return packets
