"""Frozen Study B native execution. First H55 block exits for an owner checkpoint.

Historical clients/scorers and both pilots remain byte-identical. No quality retry,
credential files, sampling override, history trimming, or other-study execution.
"""
import json
import os
import sys
import time
import urllib.error
from pathlib import Path
from collections import Counter
from agents.call_telemetry import BudgetStopped, CallRecorder
from formation.telemetry import FormationRecorder
from formation.clients import ClaudeChat, GeminiChat, OpenAIChat, ReplyError
from formation.study_b_pilot_v0231 import journal, read, sha, PilotChat
from formation.study_b_replay_v0234 import history_for
from formation.study_a import ROOT
from formation.study_a_pilot import SYSTEM
from formation.study_b_v0227 import MECHANICAL
from formation.study_b_replay_v0234 import replay
from formation.study_b_parser_v0234 import parse_action
from formation.evaluation_runner_v0218 import atomic
from formation.transport_retry_v0223 import RetryTransport, RetryExhausted, RetryRunLimit, ReplyReceivedFailure
from formation.evaluation_gemma_continuation_v0223 import RetryQuota, RetryGemmaChat
from formation.evaluation_gemma_v0222 import body_hash
from formation.limits import RatePaused
from scripts.formation_study_a_gate3 import verify_freeze
from scripts.formation_connectivity import journal_spend

FREEZE='studies/formation-study-b-freeze-v0234.json'
APPROVAL='studies/formation-study-b-execution-approval-v0234.json'
BINDING='studies/formation-study-b-adapter-binding-v0234.json'
SLUGS={'claude-haiku-5-5':'haiku55','gpt-6-luna':'luna','gemini-3.1-flash-lite':'gemini31flashlite','gemma-4-31b-it':'gemma31'}
PROVIDERS={'claude-haiku-5-5':'claude','gpt-6-luna':'openai','gemini-3.1-flash-lite':'google','gemma-4-31b-it':'google'}
CLASSES={'claude':ClaudeChat,'openai':OpenAIChat,'google':GeminiChat}


def output_name(model):
    return 'results/2026-10-12 v0.23.4 %s-none r10 study-b evaluation'%SLUGS[model]


def check(root=ROOT,approved=False,adapter=True):
    if not approved:raise ValueError('owner Gate5b approval required before credentials/evidence')
    root=Path(root);f=read(root/FREEZE);a=read(root/APPROVAL)
    if str(root.resolve())!=f['root'] or sys.version_info[:2]!=(3,11):raise ValueError('original checkout/Python3.11 required')
    if a['freeze_sha256']!=sha(root/FREEZE) or a['models']!=f['models'] or a['caps']!=f['provider_caps']:raise ValueError('execution approval binding differs')
    for path,digest in {**f['files_sha256'],**f['protected_evidence_sha256']}.items():
        if sha(root/path)!=digest:raise ValueError('frozen/protected bytes differ: '+path)
    if adapter:
        b=read(root/BINDING)
        if b['freeze_sha256']!=sha(root/FREEZE) or b['approval_sha256']!=sha(root/APPROVAL):raise ValueError('adapter binding differs')
        for path,digest in b['files_sha256'].items():
            if sha(root/path)!=digest:raise ValueError('execution adapter differs: '+path)
    if root==ROOT:
        if verify_freeze()!=59:raise ValueError('Study A59 freeze differs')
        old=root/f['prior_failed_H55_attempt']
        if read(old/'controller-status.json')['state']!='stopped_for_review' or read(old/'progress-summary.json')['primary_completed']!=72 or abs(journal_spend(old/'calls.jsonl')-f['prior_failed_H55_attempt_dollars'])>1e-12:raise ValueError('retained failed attempt/cap accounting differs')
    if f['settings']!={'max_output_tokens':4096,'max_steps':12,'wire_bytes':32000,'default_sampling_thinking_effort':True,'full_histories':True}:raise ValueError('frozen settings differ')
    if set(f['models'])!=set(SLUGS) or f['provider_caps']!={'openai':.75,'claude':2.025,'google':2.75,'gemma':0}:raise ValueError('model/cap scope differs')
    cases={read(root/p)['id']:read(root/p) for p in f['case_files']}
    schedule=read(root/'studies/formation-study-b-schedule-v0233.json')['cells']
    if len(cases)!=72 or len(schedule)!=720:raise ValueError('case/schedule size differs')
    for rep in range(1,11):
        block=[c for c in schedule if c['repeat']==rep]
        if len(block)!=72 or {c['case_id'] for c in block}!=set(cases) or any(c['label']!='primary' for c in block):raise ValueError('repeat schedule differs')
    return f,a,cases,schedule


def price_map(root):
    prices=read(root/'studies/formation-study-a-prices-v0217.json')['models']
    prices['gemma-4-31b-it']={'provider':'google','input_per_million':0,'output_per_million':0,'cached_input_per_million':0,'cache_write_per_million':0}
    return prices


class Recorder(FormationRecorder):
    """Full-body conservative monetary reserves and strict native usage validation."""
    def __init__(self,*a,**kw):
        self.last_reply=None;self.last_identity_valid=False;self.pending=False
        super().__init__(*a,**kw)
        self.pending=self.unclosed()
    def unclosed(self):
        events=journal(self.path)
        return {e['id'] for e in events if e['event']=='attempt_start'}!={e['id'] for e in events if e['event']=='attempt_end'}
    def _write(self,e):
        super()._write(e)
        with self.path.open('a') as f:os.fsync(f.fileno())
    def before_attempt(self,body):
        if self.pending:raise BudgetStopped('unclosed request; no new request')
        maximum=body.get('max_tokens',body.get('max_completion_tokens',body.get('generationConfig',{}).get('maxOutputTokens')))
        if maximum!=4096 or body.get('model',self.model)!=self.model or len(json.dumps(body).encode())>32000:raise BudgetStopped('frozen model/output/wire guard')
        prices=self.prices;price=prices[self.model]
        self.prices={self.model:dict(price,input_per_million=max(price['input_per_million'],price.get('cache_write_per_million',0)))}
        try:aid=super().before_attempt(body)
        finally:self.prices=prices
        self.pending=True
        return aid
    def finish_attempt(self,*a,**kw):
        try:return super().finish_attempt(*a,**kw)
        finally:self.pending=self.unclosed()
    def raw_reply(self,text,parsed=None,error=None):
        self.last_reply=text
        super().raw_reply(text,parsed,error)
    def finish_native(self,aid,response,provider,status=200):
        self._write({'event':'native_response','id':aid,'response':response})
        normalized=None;u={}
        if isinstance(response,dict):
            normalized=dict(response)
            if provider=='google':
                u=dict(response.get('usageMetadata') or {})
                # Preserve Google's documented absent zero final count on thought-only replies.
                if 'candidatesTokenCount' not in u:
                    final=any(p.get('text') and not p.get('thought') for c in response.get('candidates',[]) for p in c.get('content',{}).get('parts',[]))
                    if not final and all(type(u.get(k)) is int and u[k]>=0 for k in ('promptTokenCount','thoughtsTokenCount','totalTokenCount')) and u['totalTokenCount']==u['promptTokenCount']+u['thoughtsTokenCount']:
                        u['candidatesTokenCount']=0
                        self._write({'event':'derived_zero_final_tokens','id':aid,'basis':'no final parts; total equals prompt plus thoughts'})
                names=('promptTokenCount','candidatesTokenCount','totalTokenCount')
                if all(type(u.get(k)) is int and u[k]>=0 for k in names) and type(u.get('thoughtsTokenCount',0)) is int and u.get('thoughtsTokenCount',0)>=0 and u['totalTokenCount']==u['promptTokenCount']+u['candidatesTokenCount']+u.get('thoughtsTokenCount',0):
                    normalized.update(usage={'prompt_tokens':u['promptTokenCount'],'completion_tokens':u['candidatesTokenCount']+u.get('thoughtsTokenCount',0),'prompt_tokens_details':{'cached_tokens':u.get('cachedContentTokenCount',0)}},model=response.get('modelVersion'),id=response.get('responseId'),stop_reason=((response.get('candidates') or [{}])[0]).get('finishReason'))
                else:normalized=None
            if normalized:
                u=normalized.get('usage') or {}
                if provider=='claude':
                    tokens=[u.get('input_tokens'),u.get('output_tokens'),u.get('cache_read_input_tokens',0),u.get('cache_creation_input_tokens',0)]
                    total_input=sum(x for x in (tokens[0],tokens[2],tokens[3]) if type(x) is int)
                else:
                    d=u.get('prompt_tokens_details') or {}
                    tokens=[u.get('prompt_tokens'),u.get('completion_tokens'),d.get('cached_tokens',0),d.get('cache_write_tokens',0)]
                    total_input=tokens[0]
                valid=all(type(x) is int and x>=0 for x in tokens)
                valid=valid and tokens[1]<=4096
                start=next(e for e in reversed(journal(self.path)) if e['event']=='attempt_start' and e['id']==aid)
                valid=valid and total_input<=start['input_token_upper_estimate']
                valid=valid and (provider=='claude' or tokens[2]+tokens[3]<=tokens[0])
                if not valid:normalized=None
        if normalized is None:
            self.finish_attempt(aid,error='native_shape_or_usage_guard',status=status);self.missing_usage=True
            raise BudgetStopped('invalid/missing/over-reserve native usage; evidence/reserve retained')
        returned=normalized.get('model')
        if returned in self.prices[self.model].get('accepted_response_models',[]):normalized['model']=self.model
        self.finish_attempt(aid,response=normalized,status=status)
        if not returned or normalized.get('model')!=self.model:
            self.missing_usage=True;self._write({'event':'identity_missing','id':aid})
            raise BudgetStopped('pinned identity missing/different; review required')
        self.last_identity_valid=True
        if self.spent>self.max_dollars:raise BudgetStopped('settled budget exceeded')


class Chat:
    """Use original native bodies/extractors and approved shared retry transport."""
    def __init__(self,recorder,retry,quota=None,status=None):
        self.recorder=recorder;self.retry=retry;self.quota=quota;self.status=status
        provider=PROVIDERS[recorder.model]
        opts={'max_output_tokens':4096}
        if provider=='openai':opts['key_name']='TAA_OPENAI_API_KEY'
        self.native=CLASSES[provider](recorder.model,recorder,**opts)
        self.model=recorder.model;self.url=self.native.url;self.transport_lost=False;self.error_reply=None
        self.hold=Path('/workspace/haiku55-runtime/study-b-maintenance.hold')
    def _key(self):return self.native._key()
    def headers(self,key):return self.native.headers(key)
    send=PilotChat.send
    def native_send(self,url,body,received):
        old=self.url
        try:self.url=url;return self.send(body,received)
        finally:self.url=old
    def reserve(self,kind,tokens=0):
        if self.hold.exists():
            self.quota.ready_at=self.quota.now()+30
            raise RatePaused('maintenance hold; no HTTP issued')
        return self.quota.reserve(kind,tokens)
    count=RetryGemmaChat.count
    def chat(self,system,history):
        if system!=SYSTEM or not history or history[-1]['role']!='user' or any(m['role'] not in ('user','assistant') or not isinstance(m['content'],str) for m in history):raise ValueError('frozen neutral system/full history required')
        self._key();body=self.native.body(system,history)
        if len(json.dumps(body).encode())>32000:raise BudgetStopped('wire guard; never trim')
        self.transport_lost=False;self.error_reply=None
        count=None
        if self.quota:
            while True:
                try:count=self.count(body);break
                except RatePaused:self.retry.wait_until(self.quota.ready_at,'waiting_pre_request_quota')
            if count+4096+128>16000:raise BudgetStopped('combined token guard; no trimming/settings change')
        logical_started=[False]
        def begin():
            if self.quota:self.reserve('generation',count+128)
            elif self.hold.exists():raise BudgetStopped('foreign maintenance hold; no request')
            if not logical_started[0]:
                self.recorder.logical(json.dumps({'system':system,'messages':history}),'frozen Study B')
                logical_started[0]=True
            aid=self.recorder.before_attempt(body)
            if self.quota:self.recorder._write({'event':'token_preflight','id':aid,'body_sha256':body_hash(body),'counted_prompt_tokens':count,'framing_buffer':128,'completion_allowance':4096})
            return aid
        def failed(aid,meta,received,reply):
            self.recorder._write(dict(event='transport_failure',id=aid,model_reply_received=received,outcome_uncertain=meta['status'] is None,**meta))
            self.transport_lost=not received
            if self.quota:self.quota.failure(meta,'generation')
            if reply is not None:
                self.error_reply=reply;self.recorder.finish_native(aid,reply,PROVIDERS[self.model],meta['status'])
            else:self.recorder.finish_attempt(aid,error=meta['error_class'],status=meta['status'])
        job='generation:'+json.dumps(self.recorder.context,sort_keys=True)
        while True:
            try:
                response=self.retry.execute(job,body,begin,lambda received:self.send(body,received),failed,quota_ready=(lambda:max(self.quota.ready_at,self.quota.state['paused_until'])) if self.quota else None)
                break
            except RatePaused:self.retry.wait_until(self.quota.ready_at,'waiting_pre_request_quota')
            except ReplyReceivedFailure:
                if self.error_reply is None:raise BudgetStopped('partial/undecodable reply; never resend') from None
                response=self.error_reply;break
        if self.error_reply is None:self.recorder.finish_native('A%06d'%self.recorder.attempt_count,response,PROVIDERS[self.model])
        if self.quota:self.quota.success(response['usageMetadata']['promptTokenCount'])
        self.transport_lost=False
        text,stop=self.native.extract(response)
        label='unfinished_reply' if stop in ('length','max_tokens','MAX_TOKENS') else 'provider_refusal' if stop in ('refusal','SAFETY','BLOCKLIST','PROHIBITED_CONTENT') or self.native.refused(response) else 'silence' if not text.strip() else None
        self.recorder.raw_reply(text,error=label)
        if label:raise ReplyError(label)
        try:parse_action(text)
        except ValueError as e:raise ReplyError(str(e)) from None
        return text


def checkpoint_path(output,cell):
    return output/('%s-r%02d-%s-checkpoint.json'%(cell['case_id'],cell['repeat'],cell['label']))


def execute(case,cell,client,recorder,path):
    if path.exists():
        s=read(path)
        if s['phase']=='complete':return s['result']
        raise BudgetStopped('unclosed/guard/ready checkpoint; review required')
    packets=[];fatal=False;lost=False;history=[];guard=None
    for turn in range(12):
        history=history_for(case,packets)
        recorder.context=dict(cell,turn=turn+1,stage='B frozen evaluation')
        recorder.last_reply=None;recorder.last_identity_valid=False
        atomic(path,{'phase':'inflight','packets':packets,'turn':turn+1,'cell':cell})
        issued=recorder.attempt_count
        try:packets.append({'kind':'reply','raw':client.chat(SYSTEM,history)})
        except ReplyError as e:packets.append({'kind':e.label} if e.label in ('unfinished_reply','provider_refusal','silence') else {'kind':'reply','raw':recorder.last_reply or ''})
        except (BudgetStopped,RetryExhausted,RetryRunLimit,urllib.error.HTTPError,urllib.error.URLError,TimeoutError,ConnectionResetError) as e:
            if recorder.attempt_count==issued:
                atomic(path,{'phase':'guard','packets':packets,'cell':cell,'reason':str(e) if isinstance(e,BudgetStopped) else type(e).__name__});raise
            packets.append({'kind':'error','detail':type(e).__name__});fatal=True
            lost=client.transport_lost and isinstance(e,(RetryExhausted,RetryRunLimit))
            guard=str(e) if isinstance(e,(BudgetStopped,RetryExhausted,RetryRunLimit)) else type(e).__name__
        result=replay(case,packets)
        if fatal or result['terminal_status']!='fixture_exhausted':break
        atomic(path,{'phase':'ready','cell':cell,'packets':packets})
    result=replay(case,packets)
    result.update(**cell,phase='frozen evaluation',packets=packets,conversation=history,identity_valid=recorder.last_identity_valid,fatal=fatal,transport_lost=lost,stop_reason=guard)
    atomic(path,{'phase':'complete','packets':packets,'cell':cell,'result':result})
    return result


def checkpoint_report(rows):
    prim=[r for r in rows if r['label']=='primary' and r['repeat']==1]
    counts=Counter(r['score']['mechanical_outcome'] for r in prim if r['score']['mechanical_outcome'])
    return {'episodes':len(prim),'planned':72,'mechanical_by_label':{k:counts[k] for k in MECHANICAL},'mechanical_count':sum(counts.values()),'mechanical_rate_planned':sum(counts.values())/72,'threshold_exceeded':sum(counts.values())>=8,'other_stop':any(r['fatal'] for r in prim),'may_continue':len(prim)==72 and sum(counts.values())<=7 and not any(r['fatal'] for r in prim)}


def audit(root,output,manifest,cases):
    events=journal(output/'calls.jsonl');starts={e['id']:e for e in events if e['event']=='attempt_start'}
    ends=[e for e in events if e['event']=='attempt_end']
    if len(starts)!=len(ends) or set(starts)!={e['id'] for e in ends}:raise BudgetStopped('attempt closure audit failed')
    model=manifest['model'];rows=[];states={}
    for p in output.glob('*-r??-*-checkpoint.json'):
        state=read(p)
        if state['phase']!='complete':raise BudgetStopped('nonterminal checkpoint; no resume')
        row=state['result'];states[(row['case_id'],row['repeat'],row['label'])]=state;rows.append(row)
        rebuilt=replay(cases[row['case_id']],state['packets'])
        if rebuilt['score']!=row['score'] or row['conversation']!=history_for(cases[row['case_id']],state['packets'][:-1]):raise BudgetStopped('replay/full saved history differs')
    if len(states)!=len(rows):raise BudgetStopped('duplicate cell')
    logicals={e['id']:e for e in events if e['event']=='logical_start'}
    natives={e['id']:e['response'] for e in events if e['event']=='native_response'}
    wires={e['id']:e['body'] for e in events if e['event']=='native_request'}
    replies={e['logical_id']:e for e in events if e['event']=='reply'}
    opts={'max_output_tokens':4096}
    if PROVIDERS[model]=='openai':opts['key_name']='TAA_OPENAI_API_KEY'
    native=CLASSES[PROVIDERS[model]](model,type('OfflineRecorder',(),{'model':model})(),**opts)
    for lid,l in logicals.items():
        ctx=l['context'];s=states[(ctx['case_id'],ctx['repeat'],ctx['label'])]
        expected={'system':SYSTEM,'messages':history_for(cases[ctx['case_id']],s['packets'][:ctx['turn']-1])}
        if json.loads(l['prompt'])!=expected:raise BudgetStopped('wire differs from deterministic prefix')
        attempts=[aid for aid,start in starts.items() if start['logical_id']==lid]
        for aid in attempts:
            if wires.get(aid)!=native.body(SYSTEM,expected['messages']):raise BudgetStopped('full native settings/history differs')
        received=[natives[aid] for aid in attempts if aid in natives]
        if len(received)>1:raise BudgetStopped('multiple native replies for logical request')
        if lid in replies:
            if len(received)!=1 or native.extract(received[0])[0]!=replies[lid]['raw_text']:raise BudgetStopped('first native/raw reply differs')
            packet=s['packets'][ctx['turn']-1]
            if packet['kind']=='reply' and packet['raw']!=replies[lid]['raw_text']:raise BudgetStopped('scored reply differs')
    for e in ends:
        if not e.get('error'):
            response=natives.get(e['id'])
            if not isinstance(response,dict):raise BudgetStopped('native evidence absent')
            if PROVIDERS[model]=='google':
                u=dict(response.get('usageMetadata') or {})
                if 'candidatesTokenCount' not in u and any(x.get('event')=='derived_zero_final_tokens' and x.get('id')==e['id'] for x in events):u['candidatesTokenCount']=0
                expected_usage={'prompt_tokens':u.get('promptTokenCount'),'completion_tokens':u.get('candidatesTokenCount',0)+u.get('thoughtsTokenCount',0),'prompt_tokens_details':{'cached_tokens':u.get('cachedContentTokenCount',0)}}
                returned=response.get('modelVersion')
                if u.get('totalTokenCount')!=expected_usage['prompt_tokens']+expected_usage['completion_tokens']:raise BudgetStopped('native total usage differs')
            else:
                expected_usage=response.get('usage') or {};returned=response.get('model')
            if e['usage']!=expected_usage or returned not in [model]+price_map(root)[model].get('accepted_response_models',[]):raise BudgetStopped('native/normalized usage or identity differs')
            u=e['usage'];price=price_map(root)[model]
            if PROVIDERS[model]=='claude':
                inp=u['input_tokens'];out=u['output_tokens'];cache=u.get('cache_read_input_tokens',0);write=u.get('cache_creation_input_tokens',0);total_input=inp+cache+write;effective=inp
            else:
                inp=u['prompt_tokens'];out=u['completion_tokens'];cache=(u.get('prompt_tokens_details') or {}).get('cached_tokens',0);write=(u.get('prompt_tokens_details') or {}).get('cache_write_tokens',0);total_input=inp;effective=inp-cache-write
            if any(type(x) is not int or x<0 for x in (inp,out,cache,write,effective)) or out>4096 or total_input>starts[e['id']]['input_token_upper_estimate']:raise BudgetStopped('native usage reserve audit failed')
            charge=(effective*price['input_per_million']+out*price['output_per_million']+cache*price.get('cached_input_per_million',price['input_per_million'])+write*price.get('cache_write_per_million',price['input_per_million']))/1e6
            if abs(charge-e['estimated_charge_dollars'])>1e-12:raise BudgetStopped('native charge audit differs')
        if not e.get('error') and (e.get('model_returned')!=model or e.get('usage_missing') or e.get('model_mismatch')):raise BudgetStopped('identity/usage audit failed')
    retry=read(output/'transport-retry-state.json')
    if any(j['phase']=='inflight' for j in retry['jobs'].values()):raise BudgetStopped('retry job inflight')
    if model=='gemma-4-31b-it':
        q=read(output/'quota.json');receipts=journal(output/'token-count-receipts.jsonl')
        if q['metadata_inflight'] or q['stopped_for_review']:raise BudgetStopped('metadata/quota guard')
        counts={e['body_sha256']:e['totalTokens'] for e in receipts if e['event']=='count_complete'}
        pre={e['id']:e for e in events if e['event']=='token_preflight'}
        for aid,body in wires.items():
            e=pre[aid];count=counts[body_hash(body)]
            if e['counted_prompt_tokens']!=count or count+4096+128>16000 or e['completion_allowance']!=4096:raise BudgetStopped('exact token receipt differs')
    expected_spend=manifest['provider_start']+journal_spend(output/'calls.jsonl')
    ledger=root/('results/formation-spending-v021/%s.json'%PROVIDERS[model])
    if abs(read(ledger)['estimated_api_dollars']-expected_spend)>1e-12:raise BudgetStopped('cumulative ledger/journal differs')
    return {'attempts_closed':len(ends),'native_responses':len(natives),'rows_replayed':len(rows),'full_wire_first_reply_audit':'passed','model_accounted_dollars':journal_spend(output/'calls.jsonl'),'provider_cumulative_dollars':expected_spend,'retained_uncertainty_reserves':sum(starts[e['id']]['reserved_dollars'] for e in ends if e.get('reserve_retained'))}


def run(model='claude-haiku-5-5',approved=False,after_checkpoint=False,root=ROOT,now=time.time,sleep=time.sleep):
    root=Path(root);f,a,cases,schedule=check(root,approved)
    if model not in f['models']:raise ValueError('unapproved model')
    output=root/output_name(model);ledger=root/('results/formation-spending-v021/%s.json'%PROVIDERS[model])
    lock=root/'results/formation-spending-v021/run.lock'
    if lock.exists():raise BudgetStopped('shared run lock exists; never clear automatically')
    fixed={'root':str(root.resolve()),'output':output_name(model),'model':model,'freeze_sha256':sha(root/FREEZE),'approval_sha256':sha(root/APPROVAL),'adapter_binding_sha256':sha(root/BINDING),'batch_cap':0 if model=='gemma-4-31b-it' else f['provider_caps'][PROVIDERS[model]]-(f['prior_failed_H55_attempt_dollars'] if model=='claude-haiku-5-5' else 0)}
    rows=[]
    if output.exists():
        manifest=read(output/'execution-manifest.json')
        if any(manifest.get(k)!=v for k,v in fixed.items()):raise ValueError('same root/output/bindings differ')
        audit(root,output,manifest,cases)
        state=read(output/'controller-status.json')['state']
        if state=='complete':return read(output/'progress-summary.json')
        if model!='claude-haiku-5-5' or state!='checkpoint_pending_report' or not after_checkpoint:raise BudgetStopped('stopped/interrupted run; no automatic restart')
        report=read(output/'first-repeat-checkpoint.json');receipt=read(output/'checkpoint-report-receipt.json')
        if not report['may_continue'] or receipt['checkpoint_sha256']!=sha(output/'first-repeat-checkpoint.json') or not receipt['reported_to_owner']:raise BudgetStopped('checkpoint not reported/eligible')
        rows=read(output/'progress-summary.json')['records']
    else:
        if after_checkpoint:raise ValueError('no first block evidence')
        manifest=dict(fixed,provider_start=read(ledger)['estimated_api_dollars'],started_at=now())
        if abs(manifest['provider_start']-f['ledger_start'][PROVIDERS[model]])>1e-12:
            # Google is shared: a completed Gemini B audit may precede Gemma.
            prior=root/output_name('gemini-3.1-flash-lite')
            if model!='gemma-4-31b-it' or not prior.exists() or read(prior/'controller-status.json')['state']!='complete':raise ValueError('provider baseline changed without declared prior completed B batch')
            audit(root,prior,read(prior/'execution-manifest.json'),cases)
        if model!='claude-haiku-5-5':
            h=root/output_name('claude-haiku-5-5')
            if not h.exists() or read(h/'controller-status.json')['state']!='complete':raise BudgetStopped('finish reviewed H55 checkpoint and batch before other model')
    if Path('/workspace/haiku55-runtime/study-b-maintenance.hold').exists():raise BudgetStopped('foreign maintenance hold; do not clear')
    marker=json.dumps({'pid':os.getpid(),'output':output_name(model),'runner':'study_b_evaluation_v0234'})
    fd=os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.write(fd,marker.encode());os.fsync(fd);os.close(fd)
    recorder=None;retry=None;quota=None;summary=None
    try:
        output.mkdir(parents=True,exist_ok=True);atomic(output/'execution-manifest.json',manifest)
        def status(state,**extra):atomic(output/'controller-status.json',dict(state=state,pid=os.getpid(),updated_at=now(),**extra))
        status('running')
        recorder=Recorder(output/'calls.jsonl',price_map(root),model,max_logical=17280,max_attempts=86400,max_dollars=min(8,manifest['provider_start']+fixed['batch_cap']),prior_spend=manifest['provider_start']+journal_spend(output/'calls.jsonl'),ledger_path=ledger)
        retry=RetryTransport(output/'transport-retry-state.json',output/'transport-retry-journal.jsonl',now=now,sleep=sleep,waiting=lambda state,ready:status(state,ready_at=ready))
        if model=='gemma-4-31b-it':
            if not (output/'quota.json').exists():
                prior_quota=root/'results/2026-10-11 v0.22.2 gemma31-none r10 study-a evaluation/continuation-quota.json'
                carried=read(prior_quota)
                if carried['metadata_inflight'] or carried['stopped_for_review']:raise BudgetStopped('prior Gemma quota unsafe')
                carried['carried_from_sha256']=sha(prior_quota)
                atomic(output/'quota.json',carried)
            quota=RetryQuota(output/'quota.json',output/'token-count-receipts.jsonl',now=now)
        client=Chat(recorder,retry,quota,status)
        limit=72 if model=='claude-haiku-5-5' and not after_checkpoint else 720
        for cell in schedule[:limit]:
            p=checkpoint_path(output,cell)
            if p.exists():continue # Audit above proves these are closed complete checkpoints.
            status('running',cell=cell,completed=len(rows))
            row=execute(cases[cell['case_id']],cell,client,recorder,p);rows.append(row)
            summary={'status':'stopped_for_review' if row['fatal'] else 'running','primary_completed':len(rows),'planned_primary':720,'records':rows,'replacement_records':[],'pending_transport_replacements':[dict(case_id=x['case_id'],repeat=x['repeat']) for x in rows if x['transport_lost']],'spending':recorder.snapshot(),'batch_dollars':journal_spend(output/'calls.jsonl'),'output_limit':4096}
            atomic(output/'progress-summary.json',summary)
            if row['fatal']:break
        if summary is None:summary=read(output/'progress-summary.json')
        if summary['status']!='stopped_for_review':
            summary['status']='checkpoint_pending_report' if limit==72 else 'complete'
        summary['audit']=audit(root,output,manifest,cases)
        if limit==72:
            report=checkpoint_report(rows);report['audit']=summary['audit'];atomic(output/'first-repeat-checkpoint.json',report)
            if not report['may_continue']:summary['status']='stopped_for_review'
        if summary['pending_transport_replacements']:summary['status']='stopped_for_review' # Exhaustion/limit requires new review before replacements.
        atomic(output/'progress-summary.json',summary);status(summary['status'],completed=len(rows))
        return summary
    except BaseException as e:
        if output.exists():
            status('stopped_for_review',reason=str(e) if isinstance(e,(ValueError,BudgetStopped,RetryExhausted,RetryRunLimit)) else type(e).__name__)
            atomic(output/'stop-evidence.json',{'exception_class':type(e).__name__,'request_outcome_uncertain':bool(recorder and recorder.pending),'spending':recorder.snapshot() if recorder else None})
        raise
    finally:
        safe=not recorder or not recorder.pending
        safe=safe and (not retry or not any(j['phase']=='inflight' for j in retry.state['jobs'].values())) and (not quota or not quota.state['metadata_inflight'])
        if safe and lock.exists() and lock.read_text()==marker:lock.unlink()
