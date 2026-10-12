"""Owner-approved Luna-only B development pilot; native evidence, no quality retries."""
import copy
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from agents.call_telemetry import BudgetStopped
from formation.clients import OpenAIChat, ReplyError
from formation.evaluation_runner_v0218 import atomic
from formation.evaluation_transport_v0218 import EvaluationRecorder
from formation.transport_retry_v0223 import RetryTransport, RetryExhausted, RetryRunLimit, ReplyReceivedFailure
from formation.study_a import ROOT
from formation.study_a_pilot import SYSTEM
from formation.study_b_v0227 import visible, replay, parse_action
from scripts.formation_study_a_gate3 import verify_freeze
from scripts.formation_connectivity import journal_spend

MODEL='gpt-6-luna'
PLAN='studies/formation-study-b-luna-pilot-cost-plan-v0230.json'
APPROVAL='studies/formation-study-b-luna-corrected-pilot-execution-approval-v0231.json'
APPROVAL_TEXT=('Approve the corrected Luna-only Study B pilot: 72 conditions, one repeat each, up to $0.25 '
               'at the existing 2,048-token output ceiling, under the approved transport policy.')

def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def journal(p):return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []

def check(root,approved):
    if not approved:raise ValueError('separate written Luna pilot approval required before credentials/evidence')
    root=Path(root);plan=read(root/PLAN);approval=read(root/APPROVAL)
    if str(root.resolve())!=plan['root'] or sys.version_info[:2]!=(3,11):raise ValueError('same checkout and Python3.11 required')
    if approval['approval']!=APPROVAL_TEXT or approval['plan_sha256']!=sha(root/PLAN):raise ValueError('pilot approval binding differs')
    for name,digest in approval['bound_sha256'].items():
        if sha(root/name)!=digest:raise ValueError('pinned pilot dependency differs: '+name)
    for name,digest in approval['protected_sha256'].items():
        if sha(root/name)!=digest:raise ValueError('protected original evidence/ledger differs: '+name)
    for name,digest in plan['case_sha256'].items():
        if sha(root/name)!=digest:raise ValueError('approved case differs: '+name)
    if sha(root/plan['plan'])!=plan['plan_sha256'] or sha(root/plan['transport_policy'])!=plan['transport_policy_sha256']:
        raise ValueError('approved plan or retry policy differs')
    if root==ROOT and verify_freeze()!=59:raise ValueError('original freeze differs')
    if plan['model']!=MODEL or plan['conditions']!=72 or plan['repeats']!=1 or plan['proposed_batch_cap_dollars']!=.25 or plan['settings']['max_output_tokens']!=2048:
        raise ValueError('pilot scope/settings/cap differs')
    cases={read(root/path)['id']:read(root/path) for path in plan['case_sha256']}
    if len(cases)!=72 or set(cases)!=set(plan['case_order']) or len(plan['case_order'])!=72:raise ValueError('pilot cells differ')
    if any(c['max_steps']!=12 or c['gate']!='baseline' or c['counsel']!='none' for c in cases.values()):raise ValueError('world execution settings differ')
    if plan['output']!='results/2026-10-12 v0.23.0 luna-none r1 study-b corrected pilot':raise ValueError('corrected output differs')
    if any(c['version']!='0.23.0-draft' for c in cases.values()):raise ValueError('corrected draft version differs')
    return plan,approval,cases

class PilotRecorder(EvaluationRecorder):
    def before_attempt(self,body):
        aid=super().before_attempt(body)
        self.pending=True
        return aid

    def finish_attempt(self,*args,**kwargs):
        try:return super().finish_attempt(*args,**kwargs)
        finally:
            events=journal(self.path)
            self.pending={e['id'] for e in events if e['event']=='attempt_start'}!={e['id'] for e in events if e['event']=='attempt_end'}

    def finish_native(self,aid,response,provider,status=200):
        if not isinstance(response,dict):
            self._write({'event':'native_response','id':aid,'response':response})
            self.finish_attempt(aid,error='native_shape_guard',status=status)
            raise BudgetStopped('native response shape invalid; reserve retained')
        u=response.get('usage') or {};d=u.get('prompt_tokens_details') or {}
        values=[u.get('prompt_tokens'),u.get('completion_tokens'),d.get('cached_tokens',0),d.get('cache_write_tokens',0)]
        starts=[e for e in journal(self.path) if e['event']=='attempt_start' and e['id']==aid]
        valid=all(type(x) is int and x>=0 for x in values)
        valid=valid and values[2]+values[3]<=values[0] and values[1]<=2048 and values[0]<=starts[-1]['input_token_upper_estimate']
        if not valid:
            self._write({'event':'native_response','id':aid,'response':response})
            self.finish_attempt(aid,error='native_usage_guard',status=status)
            self.missing_usage=True
            raise BudgetStopped('invalid/missing/over-reserve native usage; evidence retained')
        try:super().finish_native(aid,response,provider,status)
        finally:
            events=journal(self.path)
            self.pending={e['id'] for e in events if e['event']=='attempt_start'}!={e['id'] for e in events if e['event']=='attempt_end'}
        self.last_identity_valid=True
        if self.spent>self.max_dollars:raise BudgetStopped('settled budget exceeded; no further request')

class PilotChat(OpenAIChat):
    def __init__(self,recorder,retry):
        super().__init__(MODEL,recorder,key_name='TAA_OPENAI_API_KEY',max_output_tokens=2048)
        self.retry=retry
        self.error_reply=None
        self.transport_lost=False

    def send(self,body,received):
        request=urllib.request.Request(self.url,data=json.dumps(body).encode(),headers=self.headers(self._key()))
        chunks=[]
        with urllib.request.urlopen(request,timeout=120) as response:
            while True:
                try:chunk=response.read1(65536) if hasattr(response,'read1') else response.read(65536)
                except Exception as e:
                    partial=getattr(e,'partial',b'')
                    if partial:received();chunks.append(partial)
                    if chunks:self.recorder._write({'event':'partial_native_response','logical_id':self.recorder.logical_id,'raw_utf8':b''.join(chunks).decode('utf-8',errors='replace')})
                    raise
                if not chunk:break
                received();chunks.append(chunk)
                if sum(map(len,chunks))>2*1024*1024:raise ReplyReceivedFailure('native size guard')
            raw=b''.join(chunks)
            try:return json.loads(raw)
            except (ValueError,UnicodeDecodeError):
                self.recorder._write({'event':'malformed_native_response','logical_id':self.recorder.logical_id,'raw_utf8':raw.decode('utf-8',errors='replace')})
                raise ReplyReceivedFailure('native decode guard') from None

    def chat(self,system,history):
        self.error_reply=None;self.transport_lost=False
        if system!=SYSTEM or not history or history[-1]['role']!='user' or any(m['role'] not in ('user','assistant') or not isinstance(m['content'],str) for m in history):raise ValueError('neutral system/full history required')
        body=self.body(system,history)
        self._key() # No file loading: managed Cloud binding only; never journal headers.
        self.recorder.logical(json.dumps({'system':system,'messages':history}),'Luna StudyB development pilot')
        job='generation:'+json.dumps(self.recorder.context,sort_keys=True)
        def failed(aid,meta,received,reply):
            self.recorder._write(dict(event='transport_failure',id=aid,model_reply_received=received,outcome_uncertain=meta['status'] is None,**meta))
            self.transport_lost=not received
            if reply is not None:
                self.error_reply=reply
                self.recorder.finish_native(aid,reply,'openai',meta['status'])
            else:self.recorder.finish_attempt(aid,error=meta['error_class'],status=meta['status'])
        try:
            response=self.retry.execute(job,body,lambda:self.recorder.before_attempt(body),lambda received:self.send(body,received),failed)
        except ReplyReceivedFailure:
            if self.error_reply is None:raise BudgetStopped('partial/undecodable native reply; no resend, review required') from None
            response=self.error_reply
        else:self.recorder.finish_native('A%06d'%self.recorder.attempt_count,response,'openai')
        text,stop=self.extract(response)
        label='unfinished_reply' if stop=='length' else 'provider_refusal' if stop=='refusal' or self.refused(response) else 'silence' if not text.strip() else None
        self.recorder.raw_reply(text,error=label)
        if label:raise ReplyError(label)
        # Strict B parser; raw first reply is always retained, never repaired/resent.
        try:parse_action(text)
        except ValueError as e:raise ReplyError(str(e)) from None
        return text

def history_for(case,packets):
    history=[]
    for turn in range(len(packets)+1):
        prior=replay(case,packets[:turn])
        if prior['terminal_status'] not in ('fixture_exhausted','step_limit'):break
        view=visible(case);view['world']=prior['final_world'];view['world']['step']=turn+1
        feedback={'task_context':view} if not history else {'last_tool_result':prior['attempts'][-1]['result'],'world':view['world']}
        history.append({'role':'user','content':json.dumps(feedback,ensure_ascii=False)})
        if turn<len(packets):
            if packets[turn]['kind']!='reply':break
            history.append({'role':'assistant','content':packets[turn]['raw']})
    return history

def execute(case,label,client,recorder,path):
    if path.exists():
        state=read(path)
        if state['phase']=='complete':return state['result'],False
        raise BudgetStopped('incomplete/guard/inflight checkpoint requires separate review')
    packets=[];fatal=False;lost=False;history=[]
    for turn in range(12):
        history=history_for(case,packets)
        recorder.context={'case_id':case['id'],'repeat':1,'label':label,'turn':turn+1,'stage':'B development pilot'}
        recorder.last_reply=None;recorder.last_identity_valid=False
        atomic(path,{'phase':'inflight','packets':packets,'turn':turn+1})
        issued=recorder.attempt_count
        try:
            raw=client.chat(SYSTEM,history)
            packets.append({'kind':'reply','raw':raw})
        except ReplyError as e:
            packets.append({'kind':e.label} if e.label in ('unfinished_reply','provider_refusal','silence') else {'kind':'reply','raw':recorder.last_reply or ''})
        except (BudgetStopped,RetryExhausted,RetryRunLimit,urllib.error.HTTPError,urllib.error.URLError,TimeoutError,ConnectionResetError) as e:
            if recorder.attempt_count==issued:
                atomic(path,{'phase':'guard','packets':packets,'reason':str(e)})
                raise
            packets.append({'kind':'error','detail':type(e).__name__})
            fatal=True;lost=client.transport_lost and isinstance(e,(RetryExhausted,RetryRunLimit))
        result=replay(case,packets)
        if fatal or result['terminal_status']!='fixture_exhausted':break
        atomic(path,{'phase':'ready','packets':packets})
    result=replay(case,packets)
    result.update(case_id=case['id'],repeat=1,label=label,phase='development pilot; not frozen evaluation',packets=packets,conversation=history,identity_valid=recorder.last_identity_valid,fatal=fatal,transport_lost=lost)
    atomic(path,{'phase':'complete','packets':packets,'result':result})
    return result,fatal

def audit(root,output,manifest,cases):
    events=journal(output/'calls.jsonl');starts={e['id']:e for e in events if e['event']=='attempt_start'}
    ends=[e for e in events if e['event']=='attempt_end']
    if len(starts)!=len(ends) or set(starts)!={e['id'] for e in ends}:raise BudgetStopped('native request closure differs')
    for e in ends:
        if not e.get('error') and (e.get('model_returned')!=MODEL or e.get('usage_missing') or e.get('model_mismatch')):raise BudgetStopped('native identity/usage audit failed')
    logicals={e['id']:e for e in events if e['event']=='logical_start'}
    for e in [x for x in events if x['event']=='native_request']:
        logical=logicals[starts[e['id']]['logical_id']]
        prompt=json.loads(logical['prompt'])
        expected={'model':MODEL,'messages':[{'role':'system','content':SYSTEM}]+prompt['messages'],'max_completion_tokens':2048}
        if prompt['system']!=SYSTEM or e['body']!=expected or len(json.dumps(e['body']).encode())>32000:raise BudgetStopped('full native wire history/settings audit differs')
    for path in output.glob('*-checkpoint.json'):
        state=read(path)
        if state['phase']!='complete':continue
        row=state['result']
        if replay(cases[row['case_id']],state['packets'])['score']!=row['score']:raise BudgetStopped('deterministic replay differs')
        if row['conversation']!=history_for(cases[row['case_id']],state['packets'][:-1]):raise BudgetStopped('saved full history differs')
    # Bind the wire to deterministic case history, not only its self-recorded prompt.
    replies={e['logical_id']:e for e in events if e['event']=='reply'}
    natives={e['id']:e['response'] for e in events if e['event']=='native_response'}
    for lid,logical in logicals.items():
        ctx=logical['context'];case=cases[ctx['case_id']]
        if ctx['repeat']!=1 or ctx['label']!='primary':raise BudgetStopped('primary context differs')
        state=read(output/(case['id']+'-checkpoint.json'))
        prefix=state['packets'][:ctx['turn']-1]
        prompt=json.loads(logical['prompt'])
        if prompt!={'system':SYSTEM,'messages':history_for(case,prefix)}:raise BudgetStopped('native history differs from replay prefix')
        received=[natives[a] for a,start in starts.items() if start['logical_id']==lid and a in natives]
        if len(received)>1:raise BudgetStopped('request has multiple received replies')
        if lid in replies:
            if len(received)!=1 or OpenAIChat.extract(None,received[0])[0]!=replies[lid]['raw_text']:raise BudgetStopped('first native reply differs')
            packet=state['packets'][ctx['turn']-1]
            if packet['kind']=='reply' and packet['raw']!=replies[lid]['raw_text']:raise BudgetStopped('scored first reply differs')
    expected=manifest['provider_start']+journal_spend(output/'calls.jsonl')
    if abs(read(root/'results/formation-spending-v021/openai.json')['estimated_api_dollars']-expected)>1e-12:raise BudgetStopped('provider ledger differs from attempt ledger')
    return {'attempts_closed':len(ends),'native_responses':sum(e['event']=='native_response' for e in events),'frozen_files':59,'replay':'passed','accounted_pilot_dollars':journal_spend(output/'calls.jsonl'),'provider_cumulative_dollars':expected}

def run(approved=False,root=ROOT,now=time.time,sleep=time.sleep):
    root=Path(root);plan,approval,cases=check(root,approved)
    output=root/plan['output'];ledger=root/'results/formation-spending-v021/openai.json'
    fixed={'plan_sha256':sha(root/PLAN),'approval_sha256':sha(root/APPROVAL),'root':str(root.resolve()),'output':plan['output'],'model':MODEL,'cap':.25}
    if output.exists():
        manifest=read(output/'execution-manifest.json')
        if any(manifest[k]!=v for k,v in fixed.items()):raise ValueError('same-root/output manifest differs')
        audit(root,output,manifest,cases)
        if read(output/'controller-status.json')['state']=='complete':return read(output/'progress-summary.json')
        raise BudgetStopped('interrupted/stopped pilot requires separate review; never automatically resume')
    if abs(read(ledger)['estimated_api_dollars']-plan['OpenAI_cumulative_start_dollars'])>1e-12:raise ValueError('OpenAI starting cumulative amount differs')
    lock=root/'results/formation-spending-v021/run.lock'
    marker=json.dumps({'pid':os.getpid(),'output':plan['output'],'runner':'study_b_pilot_v0231'})
    fd=os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    os.write(fd,marker.encode());os.fsync(fd);os.close(fd)
    recorder=None;retry=None;summary=None
    try:
        output.mkdir(parents=True)
        manifest=dict(fixed,provider_start=read(ledger)['estimated_api_dollars'])
        atomic(output/'execution-manifest.json',manifest)
        def status(state,**extra):atomic(output/'controller-status.json',dict(state=state,pid=os.getpid(),updated_at=now(),**extra))
        status('running')
        prices=read(root/'studies/formation-study-a-prices-v0217.json')['models']
        recorder=PilotRecorder(output/'calls.jsonl',prices,MODEL,max_logical=864,max_attempts=4320,max_dollars=min(8,manifest['provider_start']+.25),prior_spend=manifest['provider_start'],ledger_path=ledger)
        retry=RetryTransport(output/'transport-retry-state.json',output/'transport-retry-journal.jsonl',now=now,sleep=sleep,waiting=lambda state,ready:status(state,ready_at=ready))
        client=PilotChat(recorder,retry);rows=[]
        for cid in plan['case_order']:
            status('running',case_id=cid,completed=len(rows))
            row,fatal=execute(cases[cid],'primary',client,recorder,output/(cid+'-checkpoint.json'))
            rows.append(row)
            summary={'status':'stopped_for_review' if fatal else 'running','primary_completed':len(rows),'planned_primary':72,'records':rows,'replacement_records':[],'pending_transport_replacements':[x['case_id'] for x in rows if x['transport_lost']],'spending':recorder.snapshot(),'pilot_dollars':recorder.spent-manifest['provider_start'],'output_limit':2048}
            atomic(output/'progress-summary.json',summary)
            if fatal:break
        if summary['status']!='stopped_for_review':summary['status']='complete'
        summary['audit']=audit(root,output,manifest,cases)
        atomic(output/'progress-summary.json',summary);status(summary['status'],completed=len(rows))
        return summary
    except BaseException as e:
        if output.exists():
            atomic(output/'controller-status.json',{'state':'stopped_for_review','pid':os.getpid(),'reason':str(e) if isinstance(e,(ValueError,BudgetStopped,RetryExhausted,RetryRunLimit)) else type(e).__name__,'updated_at':now()})
            atomic(output/'stop-evidence.json',{'exception_class':type(e).__name__,'request_outcome_uncertain':bool(recorder and recorder.pending),'spending':recorder.snapshot() if recorder else None})
        raise
    finally:
        safe=not recorder or not recorder.pending
        safe=safe and (not retry or not any(j['phase']=='inflight' for j in retry.state['jobs'].values()))
        if safe and lock.exists() and lock.read_text()==marker:lock.unlink()
