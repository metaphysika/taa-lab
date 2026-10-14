"""Owner-approved frozen Study C execution; original root, serial model boundaries.

The first72 always close for audit/evidence preservation. A passing block has
owner-authorized continuation; >=8 mechanical failures or any hard guard stops.
Owner-approved v0241 byte safeguards and v0242 one-time Gemini native-format amendment; original science stays frozen.
"""
import copy
import hashlib
import json
import os
import shutil
import sys
import time
import urllib.error
from pathlib import Path
from collections import Counter

from agents.call_telemetry import BudgetStopped
from formation.study_c_count_remedy_v0243 import verified_counts, count_body, verify_unstarted_boundary
from formation.clients import ReplyError
from formation.study_b_evaluation_v0235 import FormationRecorder, RatePaused, ReplyReceivedFailure
from formation import study_c_evaluation_v0239 as original
from formation.evaluation_gemma_continuation_v0223 import RetryQuota
from formation.evaluation_gemma_v0222 import append, body_hash
from formation.study_a import ROOT
from formation.study_a_pilot import SYSTEM
from formation.study_b_evaluation_v0235 import (
    Chat as NativeChat, Recorder, CLASSES, PROVIDERS, read, sha, journal,
    price_map, check as check_b)
from formation.study_b_parser_v0234 import parse_action
from formation.study_b_replay_v0234 import replay
from formation.study_b_v0227 import MECHANICAL
from formation.study_c_pilot_v0238 import seeded_history, metrics
from formation.transport_retry_v0223 import RetryTransport, RetryExhausted, RetryRunLimit
from formation.transport_retry_v0223 import retryable
from scripts.formation_connectivity import journal_spend

FREEZE = 'studies/formation-study-c-freeze-v0239.json'
APPROVAL = 'studies/formation-study-c-execution-approval-v0239.json'
BINDING = 'studies/formation-study-c-adapter-binding-v0239.json'
HOLD = Path('/workspace/haiku55-runtime/study-b-maintenance.hold')
MODELS = ('claude-haiku-5-5', 'gemini-3.1-flash-lite', 'gemma-4-31b-it', 'gpt-6-luna')
SCIENTIFIC_CAPS = {'openai': 1.40, 'claude': 2.60, 'google': 2.85, 'gemma': 0}
CAPS = dict(SCIENTIFIC_CAPS, google=3.25)

AMENDMENT = 'studies/formation-study-c-operational-amendment-v0241.json'
AMENDMENT_BINDING = 'studies/formation-study-c-operational-binding-v0241.json'
WIRE_CAPS = {m:64000 if m=='gemma-4-31b-it' else 128000 for m in MODELS}
RESUMED_CELL = 'C-delivery-r4-U-r02-compliant-k16'
NATIVE_AMENDMENT = 'studies/formation-study-c-gemini-native-amendment-v0242.json'
NATIVE_BINDING = 'studies/formation-study-c-gemini-native-binding-v0242.json'
NATIVE_SCHEMA = 'studies/formation-study-c-gemini-native-review-v0241/exact-proposed-neutral-schema.json'
READY_CI = 'studies/formation-study-c-native-ready-ci-receipt-v0242.json'
COUNT_APPROVAL = 'studies/formation-study-c-count-remedy-approval-v0243.json'
COUNT_BINDING = 'studies/formation-study-c-count-remedy-binding-v0243.json'
COUNT_CI = 'studies/formation-study-c-count-ready-ci-receipt-v0243.json'
START_MARKER = 'first-unsent-start-v0243.json'
ARCHIVE = 'prestart-stop-v0242'
COMPATIBILITY_SYSTEM = 'Return one JSON action object matching the supplied response schema.'
COMPATIBILITY_PROMPT = 'Neutral API-format check only. There is no task or external work to perform. Return a finished response with tool null and empty args. This is not an evaluation case.'


class NeutralSchemaGoogle(CLASSES['google']):
    def body(self, system, messages):
        body = super().body(system, messages)
        if self.model == 'gemini-3.1-flash-lite':
            body['generationConfig']['responseJsonSchema'] = read(ROOT/NATIVE_SCHEMA)
        return body


CLASSES = dict(CLASSES, google=NeutralSchemaGoogle)


def verify_native_amendment(root, adapter=True):
    root=Path(root);am=read(root/NATIVE_AMENDMENT)
    if not am['execution_authorized'] or am['root']!=str(root.resolve()) or am['Google_C_cap']!=3.25 or am['Gemini_failed_plus_fresh_first72_allowance']!=.60:
        raise BudgetStopped('owner native-format approval/caps differ')
    if am['science_freeze_sha256']!=sha(root/FREEZE) or am['v0241_amendment_sha256']!=sha(root/AMENDMENT) or am['v0241_binding_sha256']!=sha(root/AMENDMENT_BINDING):
        raise BudgetStopped('original science/operational binding changed')
    if am['schema_file']!=NATIVE_SCHEMA or am['schema_sha256']!=sha(root/NATIVE_SCHEMA) or am['maximum_native_format_reruns']!=1 or am['compatibility_max_attempts']!=1 or am['compatibility_max_dollars_exclusive']!=.01 or am['Study_D_authorized']:
        raise BudgetStopped('exact native schema/one-time policy changed')
    for name,digest in am['failed_files_sha256'].items():
        if sha(root/name)!=digest:raise BudgetStopped('immutable failed Gemini evidence changed: '+name)
    if abs(journal_spend(root/am['failed_output']/'calls.jsonl')-am['failed_cost'])>1e-12:
        raise BudgetStopped('failed Gemini cost differs')
    failed_checkpoint=read(root/am['failed_output']/'first-repeat-checkpoint.json')
    if read(root/am['failed_output']/'controller-status.json')['state']!='stopped_for_review' or failed_checkpoint['episodes']!=72 or failed_checkpoint['mechanical_count']<8 or failed_checkpoint['may_continue']:
        raise BudgetStopped('original Gemini block is not an eligible closed mechanical checkpoint failure')
    if adapter:
        binding=read(root/NATIVE_BINDING)
        if binding['approval_sha256']!=sha(root/NATIVE_AMENDMENT):raise BudgetStopped('native-format approval binding differs')
        for name,digest in binding['files_sha256'].items():
            if sha(root/name)!=digest:raise BudgetStopped('native-format dependency differs: '+name)
    return am


def runtime_freeze(root, scientific, amendment):
    f=copy.deepcopy(scientific)
    retained=journal_spend(Path(root)/amendment['failed_output']/'calls.jsonl')+journal_spend(Path(root)/amendment['compatibility_output']/'calls.jsonl')
    f['outputs']['gemini-3.1-flash-lite']=amendment['fresh_output']
    f['retry_sources']['gemini-3.1-flash-lite']=(amendment['compatibility_output'] if (Path(root)/amendment['compatibility_output']/'transport-retry-state.json').exists() else amendment['failed_output'])
    f['provider_caps']['google']=3.25
    f['first_block_subcaps']['gemini-3.1-flash-lite']=.60-retained
    f['Google_retained_failed_and_compatibility']=retained
    f['native_format_amendment']='v0242'
    return f



def verify_count_remedy(root, adapter=True):
    root=Path(root);am=read(root/COUNT_APPROVAL)
    if not am['execution_authorized'] or am['root']!=str(root.resolve()) or am['science_sha256']!=sha(root/FREEZE) or am['native_binding_sha256']!=sha(root/NATIVE_BINDING):
        raise BudgetStopped('count remedy owner/science/native binding differs')
    if am['generation_no_resend_unchanged'] is not True or am['maximum_metadata_only_new_jobs_per_body']!=1 or am['Study_D_authorized']:
        raise BudgetStopped('metadata-only scope differs')
    output=root/read(root/FREEZE)['outputs']['gemma-4-31b-it']
    if sha(output/'stop-integrity-v0242.json')!=am['original_stop_index_sha256']:
        raise BudgetStopped('original Gemma stop index changed')
    index=read(output/'stop-integrity-v0242.json')
    base=output/ARCHIVE if (output/START_MARKER).exists() else output
    for name,digest in index['files_sha256'].items():
        if sha(base/name)!=digest:raise BudgetStopped('original zero-request Gemma stop evidence changed')
    if (output/START_MARKER).exists():
        marker=read(output/START_MARKER)
        if marker['approval_sha256']!=sha(root/COUNT_APPROVAL) or marker['binding_sha256']!=sha(root/COUNT_BINDING) or marker['cell_id']!=am['first_cell_id'] or marker['episode_result_reused'] or marker['count_HTTP_reissued_before_start']:
            raise BudgetStopped('first unsent start marker differs')
        prior=read(base/'transport-retry-state.json');current=read(output/'transport-retry-state.json')
        if any(current['jobs'].get(k)!=v for k,v in prior['jobs'].items()) or current['requests_needing_retry']<prior['requests_needing_retry']:
            raise BudgetStopped('original jobs or retry counter changed/reset')
    verified_counts(count_sources(root,am))
    if adapter:
        b=read(root/COUNT_BINDING)
        if b['approval_sha256']!=sha(root/COUNT_APPROVAL):raise BudgetStopped('count approval binding differs')
        for name,digest in b['files_sha256'].items():
            if sha(root/name)!=digest:raise BudgetStopped('count remedy dependency changed: '+name)
    return am


def count_sources(root, approval=None):
    root=Path(root);am=approval if approval is not None else read(root/COUNT_APPROVAL)
    return [(root/x['receipts'],root/x['state'],x['receipt_sha256'],x['state_sha256']) for x in am['count_sources']]


def prepare_first_unsent_start(root, output, cell):
    am=verify_count_remedy(root);output=Path(output)
    if (output/START_MARKER).exists() or (output/ARCHIVE).exists():raise BudgetStopped('unsent start already prepared; review required')
    original=verify_unstarted_boundary(output,read(output/'stop-integrity-v0242.json'))
    if original!=cell or cell['cell_id']!=am['first_cell_id']:raise BudgetStopped('wrong first unsent cell')
    archive=output/ARCHIVE;archive.mkdir()
    for name in read(output/'stop-integrity-v0242.json')['files_sha256']:
        target=archive/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(output/name,target)
    atomic(output/START_MARKER,dict(approval_sha256=sha(Path(root)/COUNT_APPROVAL),binding_sha256=sha(Path(root)/COUNT_BINDING),cell_id=cell['cell_id'],episode_result_reused=False,count_HTTP_reissued_before_start=False,at=time.time()))
    verify_count_remedy(root)


def audit_count_recovery(root, output):
    approved=verified_counts(count_sources(root));receipts=journal(output/'token-count-receipts.jsonl')
    for e in receipts:
        if e.get('receipt_kind')=='recovered_exact_body_v0243':
            record=approved.get(e['body_sha256'])
            if not record or any(e.get(k)!=v for k,v in record.items()) or e.get('no_HTTP_request') is not True:
                raise BudgetStopped('recovered exact count provenance differs')
    jobs=read(output/'transport-retry-state.json')['jobs'];seen=set()
    for e in journal(output/'transport-retry-journal.jsonl'):
        if e.get('event')!='metadata_only_new_job':continue
        digest=e['body_sha256'];old='countTokens:'+digest;new='countTokens:v0243:'+digest+':metadata-only-1'
        if e['original_job']!=old or e['new_job']!=new or new in seen or jobs.get(old)!=e['original_job_snapshot']:
            raise BudgetStopped('metadata exemption changed original job or repeated')
        if jobs[old]['phase'] not in ('complete','failed') or jobs[old]['received'] is not True or jobs[old]['body_sha256']!=digest or new not in jobs:
            raise BudgetStopped('invalid metadata-only exemption provenance')
        seen.add(new)
    return dict(recovered_count_receipts=sum(e.get('receipt_kind')=='recovered_exact_body_v0243' for e in receipts),metadata_only_new_jobs=len(seen),generation_no_resend_unchanged=True)


def require_readiness_ci(root):
    receipt=read(Path(root)/READY_CI)
    if receipt['binding_sha256']!=sha(Path(root)/NATIVE_BINDING) or len(receipt['checks'])!=2 or {c['name'] for c in receipt['checks']}!={'Harness checks','Formation Python 3.9 checks'} or any(c['conclusion']!='success' for c in receipt['checks']):
        raise BudgetStopped('both native-format readiness GitHub checks must pass before calls')
    extra=read(Path(root)/COUNT_CI)
    if extra['binding_sha256']!=sha(Path(root)/COUNT_BINDING) or len(extra['checks'])!=2 or {x['name'] for x in extra['checks']}!={'Harness checks','Formation Python 3.9 checks'} or any(x['conclusion']!='success' for x in extra['checks']):
        raise BudgetStopped('both count-remedy readiness GitHub checks must pass before calls')
    return extra


def native_model_manifest(root, output, manifest):
    am=verify_native_amendment(root)
    if str(Path(output).relative_to(root))!=am['fresh_output'] or manifest['model']!='gemini-3.1-flash-lite':raise BudgetStopped('only the bound fresh native-format output is eligible')
    return dict(amendment_sha256=sha(Path(root)/NATIVE_AMENDMENT),binding_sha256=sha(Path(root)/NATIVE_BINDING),schema_sha256=am['schema_sha256'],study_block='native_format_rerun',rerun_number=1,failed_output=am['failed_output'],failed_unpooled=True,compatibility_integrity_sha256=sha(Path(root)/am['compatibility_output']/'compatibility-integrity.json'))


def save_native_model_manifest(root, output, manifest):
    value=native_model_manifest(root,output,manifest);path=Path(output)/'native-format-manifest-v0242.json'
    if path.exists():
        if read(path)!=value:raise BudgetStopped('native-format model manifest changed')
    else:atomic(path,value)


def verify_native_model_manifest(root, output, manifest):
    if read(Path(output)/'native-format-manifest-v0242.json')!=native_model_manifest(root,output,manifest):raise BudgetStopped('native-format model manifest differs')


def audit_compatibility(root):
    root=Path(root);am=verify_native_amendment(root);output=root/am['compatibility_output']
    events=journal(output/'calls.jsonl')
    def one(kind):
        rows=[e for e in events if e['event']==kind]
        if len(rows)!=1:raise BudgetStopped('compatibility requires exactly one '+kind)
        return rows[0]
    start,end,wire,native,logical,reply=[one(k) for k in ['attempt_start','attempt_end','native_request','native_response','logical_start','reply']]
    if any(e['id']!=start['id'] for e in [end,wire,native]) or start['logical_id']!=logical['id'] or reply['logical_id']!=logical['id'] or end.get('error') or end.get('usage_missing') or end.get('model_mismatch') or end.get('reserve_retained'):raise BudgetStopped('compatibility attempt/usage/identity not cleanly closed')
    client=CLASSES['google']('gemini-3.1-flash-lite',type('R',(),{'model':'gemini-3.1-flash-lite'})(),max_output_tokens=4096)
    messages=[{'role':'user','content':COMPATIBILITY_PROMPT}]
    if wire['body']!=client.body(COMPATIBILITY_SYSTEM,messages) or json.loads(logical['prompt'])!={'system':COMPATIBILITY_SYSTEM,'messages':messages} or logical['context'].get('stage')!='neutral native-schema compatibility; not study data':raise BudgetStopped('compatibility neutral body/context differs')
    response=native['response'];u=response.get('usageMetadata') or {};price=price_map(root)['gemini-3.1-flash-lite']
    inp=u.get('promptTokenCount');out=u.get('candidatesTokenCount',0)+u.get('thoughtsTokenCount',0);cache=u.get('cachedContentTokenCount',0)
    if response.get('modelVersion') not in ['gemini-3.1-flash-lite']+price.get('accepted_response_models',[]) or any(type(v)is not int or v<0 for v in [inp,out,cache]) or cache>inp or out>4096 or inp>start['input_token_upper_estimate'] or u.get('totalTokenCount')!=inp+out:raise BudgetStopped('compatibility native identity/usage/reserve differs')
    usage={'prompt_tokens':inp,'completion_tokens':out,'prompt_tokens_details':{'cached_tokens':cache}}
    charge=((inp-cache)*price['input_per_million']+cache*price.get('cached_input_per_million',price['input_per_million'])+out*price['output_per_million'])/1e6
    if end['usage']!=usage or abs(end['estimated_charge_dollars']-charge)>1e-12 or not charge<.01 or not journal_spend(output/'calls.jsonl')<.01:raise BudgetStopped('compatibility cost/usage differs or exceeds exclusive0.01')
    text,stop=client.extract(response)
    if text!=reply['raw_text'] or reply.get('error') or stop!='STOP':raise BudgetStopped('compatibility first-native parseable output not complete')
    parsed=parse_action(text)
    transport=read(output/'transport-retry-state.json')
    original_transport=read(root/am['failed_output']/'transport-retry-state.json')
    if transport['requests_needing_retry']!=original_transport['requests_needing_retry'] or transport['stop'] or any(transport['jobs'].get(k)!=v for k,v in original_transport['jobs'].items()) or len(transport['jobs'])!=len(original_transport['jobs'])+1 or transport['jobs']['neutral-compatibility:v0242']['phase']!='complete':raise BudgetStopped('compatibility retry history reset or job not closed')
    return dict(attempts=1,received_native_replies=1,no_retries=True,not_study_data=True,body_sha256=body_hash(wire['body']),schema_sha256=am['schema_sha256'],identity_usage_reserve_first_output='passed',parseable_output=parsed,cost=charge)


def verify_compatibility(root):
    require_readiness_ci(root);am=verify_native_amendment(root);output=Path(root)/am['compatibility_output']
    if read(output/'controller-status.json')['state']!='compatibility_passed':raise BudgetStopped('schema compatibility call did not pass')
    index=read(output/'compatibility-integrity.json')
    for name,digest in index['files_sha256'].items():
        if sha(output/name)!=digest:raise BudgetStopped('compatibility evidence changed')
    return audit_compatibility(root)


def compatibility_call(approved=False, root=ROOT, now=time.time):
    root=Path(root);freeze,*_=check(root,approved);require_readiness_ci(root);am=verify_native_amendment(root)
    output=root/am['compatibility_output'];lock=root/'results/formation-spending-v021/run.lock'
    if output.exists() or lock.exists() or HOLD.exists() or provider_processes():raise BudgetStopped('compatibility already attempted or boundary not closed; no retry/recreate')
    haiku=root/freeze['outputs']['claude-haiku-5-5']
    if not (haiku/'completion-integrity.json').exists() or read(haiku/'controller-status.json')['state']!='complete' or read(haiku/'progress-summary.json').get('primary_closed',read(haiku/'progress-summary.json')['primary_completed'])!=540:raise BudgetStopped('Haiku must be audited complete before the neutral compatibility call')
    marker=json.dumps(dict(pid=os.getpid(),model='gemini-3.1-flash-lite',runner='study_c_evaluation_v0243',stage='one neutral compatibility call'))
    fd=os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);recorder=None
    def status(state,**kw):atomic(output/'controller-status.json',dict(state=state,pid=os.getpid(),model='gemini-3.1-flash-lite',at=now(),not_study_data=True,**kw))
    try:
        os.write(fd,marker.encode());os.fsync(fd);os.close(fd);fd=None;output.mkdir(exist_ok=False)
        baseline=read(root/'results/formation-spending-v021/google.json')['estimated_api_dollars']
        source=root/am['failed_output']
        for name in ['transport-retry-state.json','transport-retry-journal.jsonl']:shutil.copyfile(source/name,output/name)
        transport=read(output/'transport-retry-state.json')
        if transport['stop'] or any(j['phase'] not in ('complete','failed') for j in transport['jobs'].values()):raise BudgetStopped('inherited transport not closed')
        atomic(output/'execution-manifest.json',dict(model='gemini-3.1-flash-lite',not_study_data=True,provider_start=baseline,maximum_attempts=1,max_dollars_exclusive=.01,amendment_sha256=sha(root/NATIVE_AMENDMENT),binding_sha256=sha(root/NATIVE_BINDING),schema_sha256=am['schema_sha256']))
        recorder=CRecorder(output/'calls.jsonl',price_map(root),'gemini-3.1-flash-lite',max_logical=1,max_attempts=1,max_dollars=min(8,baseline+.009999999),prior_spend=baseline,ledger_path=root/'results/formation-spending-v021/google.json')
        recorder.context={'stage':'neutral native-schema compatibility; not study data','native_format_amendment':'v0242'}
        client=CChat(recorder,None);client._key();messages=[{'role':'user','content':COMPATIBILITY_PROMPT}];body=client.native.body(COMPATIBILITY_SYSTEM,messages)
        recorder.logical(json.dumps({'system':COMPATIBILITY_SYSTEM,'messages':messages}),'neutral native-schema compatibility; not study data')
        aid=recorder.before_attempt(body);status('compatibility_running');received=[False]
        job=dict(body_sha256=body_hash(body),attempts=1,received=False,phase='inflight',ready_at=0,counted_retry=False)
        transport['jobs']['neutral-compatibility:v0242']=job;atomic(output/'transport-retry-state.json',transport)
        append(output/'transport-retry-journal.jsonl',dict(event='transport_attempt_start',job='neutral-compatibility:v0242',attempt=1,body_sha256=body_hash(body),at=now(),not_study_data=True))
        def mark_received():
            if not received[0]:
                received[0]=True;job['received']=True;atomic(output/'transport-retry-state.json',transport)
                append(output/'transport-retry-journal.jsonl',dict(event='received_reply_barrier',job='neutral-compatibility:v0242',attempt=1,at=now(),not_study_data=True))
        try:response=client.send(body,mark_received);mark_received()
        except Exception as error:
            code=getattr(error,'code',None)
            recorder._write(dict(event='compatibility_failure',id=aid,status=code,received_bytes=received[0],HTTP_response_received=isinstance(error,urllib.error.HTTPError),error_class=type(error).__name__,no_retry=True))
            recorder.finish_attempt(aid,error=type(error).__name__,status=code)
            job['phase']='failed'
            if not received[0] and retryable(error):job['counted_retry']=True;transport['requests_needing_retry']+=1
            transport['stop']='single_compatibility_attempt_failed';atomic(output/'transport-retry-state.json',transport)
            append(output/'transport-retry-journal.jsonl',dict(event='transport_attempt_end',job='neutral-compatibility:v0242',attempt=1,status=code,error_class=type(error).__name__,model_reply_received=received[0],no_retry=True,not_study_data=True))
            raise BudgetStopped('single compatibility request failed/rejected; no retry; review required') from None
        job['phase']='complete';atomic(output/'transport-retry-state.json',transport)
        append(output/'transport-retry-journal.jsonl',dict(event='transport_attempt_end',job='neutral-compatibility:v0242',attempt=1,status=200,error_class=None,model_reply_received=True,not_study_data=True))
        recorder.finish_native(aid,response,'google');text,stop=client.native.extract(response);recorder.raw_reply(text)
        terminal=audit_compatibility(root);atomic(output/'terminal-audit.json',terminal);status('compatibility_passed',cost=terminal['cost']);check(root,True)
        return terminal
    except BaseException as error:
        if output.exists():status('stopped_for_review',reason=str(error) if isinstance(error,(BudgetStopped,ValueError)) else type(error).__name__)
        raise
    finally:
        if fd is not None:os.close(fd)
        if (not recorder or not recorder.pending) and lock.exists() and lock.read_text()==marker:lock.unlink()


class GemmaTokenGuard(BudgetStopped):
    def __init__(self, count, body):
        super().__init__('exact Gemma token guard before generation; missing episode')
        self.count = count
        self.body_sha256 = body_hash(body)


def continuation_path(output):
    return Path(output)/(RESUMED_CELL+'-continuation-v0241.json')


def checkpoint_state(output, cell):
    path=checkpoint_path(output,cell)
    if cell['cell_id']==RESUMED_CELL and continuation_path(output).exists():
        return read(continuation_path(output))
    return read(path)


def guard_counts(guards):
    return dict(total=len(guards), planned=540, review_threshold_exclusive=27,
                by_condition=dict(Counter(g['cell']['history_condition'] for g in guards)),
                by_condition_k=dict(Counter('%s/k%d'%(g['cell']['history_condition'],g['cell']['k']) for g in guards)),
                by_probe=dict(Counter(g['cell']['probe_id'] for g in guards)))


def verify_amendment(root):
    root=Path(root);am=read(root/AMENDMENT);binding=read(root/AMENDMENT_BINDING)
    if not am['execution_authorized'] or am['wire_caps']!=WIRE_CAPS or am['gemma_guard_stop_review_count']!=28:
        raise BudgetStopped('operational amendment authorization differs')
    if am['science_freeze_sha256']!=sha(root/FREEZE) or binding['amendment_sha256']!=sha(root/AMENDMENT):
        raise BudgetStopped('operational amendment binding differs')
    for name,digest in binding['files_sha256'].items():
        if sha(root/name)!=digest:raise BudgetStopped('amended adapter dependency differs: '+name)
    for name,digest in am['immutable_pre_amendment_sha256'].items():
        if sha(root/name)!=digest:raise BudgetStopped('pre-amendment evidence changed: '+name)
    for name,record in am['pre_amendment_journal_prefixes'].items():
        if prefix_hash(root/name,record['bytes'])!=record['sha256']:
            raise BudgetStopped('pre-amendment journal prefix differs')
    return am


def verify_unsent_continuation(root, output, cases, cells, seeds):
    am=verify_amendment(root);cell=cells[184]
    if cell['cell_id']!=RESUMED_CELL or continuation_path(output).exists():
        raise BudgetStopped('scoped continuation already started or wrong cell')
    state=read(checkpoint_path(output,cell));manifest=read(output/'execution-manifest.json')
    if state['phase']!='guard' or len(state['packets'])!=4:
        raise BudgetStopped('original four-reply guard differs')
    opts={'max_output_tokens':4096}
    native=CLASSES['claude'](MODELS[0],type('OfflineRecorder',(),{'model':MODELS[0]})(),**opts)
    body=native.body(SYSTEM,seeded_history(cases[cell['probe_id']],cell,state['packets'],seeds))
    if sha(checkpoint_path(output,cell))!=am['resume']['guard_checkpoint_sha256'] or body_hash(body)!=am['resume']['blocked_body_sha256'] or len(json.dumps(body).encode())!=33821:
        raise BudgetStopped('unsent turn5 exact body/checkpoint differs')
    ev=journal(output/'calls.jsonl')
    if any(e['event']=='logical_start' and e['context']['cell_id']==RESUMED_CELL and e['context']['turn']>=5 for e in ev):
        raise BudgetStopped('turn5 already issued; no resend')
    if read(output/'transport-retry-state.json')['stop']:
        raise BudgetStopped('transport stop; no continuation')
    terminal=audit(root,output,manifest,cases,cells,seeds,allow_original_partial=True)
    if terminal['rows_replayed']!=184 or terminal['partial_guard_count']!=1:
        raise BudgetStopped('not the approved closed184 plus partial185 boundary')
    return state['packets']


def atomic(path, value):
    """Durable compact JSON; same data, no growing per-chunk encoder overhead."""
    path=Path(path);temp=path.with_suffix('.tmp')
    with temp.open('w') as stream:
        stream.write(json.dumps(value,separators=(',',':'))+'\n');stream.flush();os.fsync(stream.fileno())
    temp.replace(path);fd=os.open(str(path.parent),os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


class CTransport(RetryTransport):
    def save(self):atomic(self.path,self.state)


class CQuota(RetryQuota):
    def save(self):atomic(self.path,self.state)


def checkpoint_path(output, cell):
    marker=Path(output)/START_MARKER
    suffix='-first-request-v0243-checkpoint.json' if marker.exists() and cell['cell_id']==read(marker)['cell_id'] else '-checkpoint.json'
    return Path(output) / (cell['cell_id'] + suffix)


def model_cap(freeze, model):
    return (freeze['OpenAI_evaluation_allowance'] if model == 'gpt-6-luna' else
            0 if model == 'gemma-4-31b-it' else freeze['provider_caps'][PROVIDERS[model]]
            - (freeze.get('Google_retained_failed_and_compatibility',0) if model=='gemini-3.1-flash-lite' else 0))


def ledger_check(root, freeze):
    expected = dict(freeze['ledger_start'])
    expected['google'] += freeze.get('Google_retained_failed_and_compatibility',0)
    for model, directory in freeze['outputs'].items():
        amount = journal_spend(root/directory/'calls.jsonl')
        if amount > model_cap(freeze, model)+1e-12:
            raise BudgetStopped('model C cap exceeded')
        expected[PROVIDERS[model]] += amount
    for provider, total in expected.items():
        current = read(root/('results/formation-spending-v021/'+provider+'.json'))['estimated_api_dollars']
        if abs(current-total) > 1e-12 or (provider != 'groq' and current > 8):
            raise BudgetStopped('%s ledger %.12f differs from baseline+journals %.12f (delta %.3g)'%(provider,current,total,current-total))
    return expected


def prefix_hash(path, byte_length):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        remaining = byte_length
        while remaining:
            data = stream.read(min(1024*1024, remaining))
            if not data: raise BudgetStopped('append-only journal shortened')
            h.update(data); remaining -= len(data)
    return h.hexdigest()


def verify_first_block(output):
    output = Path(output); index = read(output/'first-block-integrity.json')
    for name, digest in index['checkpoint_sha256'].items():
        if sha(output/name) != digest: raise BudgetStopped('first72 checkpoint bytes changed')
    for name, record in index['journal_prefixes'].items():
        if prefix_hash(output/name, record['bytes']) != record['sha256']:
            raise BudgetStopped('first72 append-only journal prefix changed')
    return index


def verify_completed(output):
    output = Path(output)
    for name, digest in read(output/'completion-integrity.json')['files_sha256'].items():
        if sha(output/name) != digest: raise BudgetStopped('completed C evidence changed')


def check(root=ROOT, approved=False, adapter=True):
    root = Path(root)
    if not approved or sys.version_info[:2] != (3, 11):
        raise ValueError('owner approval/original Python3.11 required')
    f = read(root/FREEZE); a = read(root/APPROVAL)
    if str(root.resolve()) != f['root'] or tuple(f['models']) != MODELS or f['provider_caps'] != SCIENTIFIC_CAPS:
        raise ValueError('original checkout, model order or cap binding differs')
    if root == ROOT:
        if str(root.resolve()) != '/workspace/taa-lab': raise ValueError('original checkout only')
        check_b(root, approved=True)
    if not a['execution_authorized'] or a['freeze_sha256'] != sha(root/FREEZE) or a['caps'] != SCIENTIFIC_CAPS or a['models'] != f['models']:
        raise ValueError('Gate6b execution binding differs')
    if f['settings'] != {'max_output_tokens':4096, 'max_steps':12, 'wire_bytes':32000,
                         'default_thinking_effort_sampling':True, 'full_histories':True}:
        raise ValueError('frozen settings differ')
    if f['first_block_episodes'] != 72 or f['mechanical_review_count'] != 8 or f['Study_D_authorized']:
        raise ValueError('checkpoint/stage scope differs')
    if abs(f['OpenAI_evaluation_allowance'] + f['Luna_C_pilot_accounted_dollars']-1.40) > 1e-12:
        raise ValueError('Luna pilot not retained inside C cap')
    for name, digest in {**f['files_sha256'], **f['protected_evidence_sha256']}.items():
        if sha(root/name) != digest: raise ValueError('scientific/protected bytes differ: '+name)
    if adapter:
        b = read(root/BINDING)
        if b['freeze_sha256'] != sha(root/FREEZE) or b['approval_sha256'] != sha(root/APPROVAL):
            raise ValueError('C adapter binding differs')
        for name, digest in b['files_sha256'].items():
            if sha(root/name) != digest: raise ValueError('C execution dependency differs: '+name)
    cases = {p['id']: p for p in read(root/f['probe_files'])}
    seeds = read(root/f['seed_files']); cells = read(root/f['schedule'])['cells']
    if len(cases) != 18 or len(cells) != 540 or len({c['cell_id'] for c in cells}) != 540:
        raise ValueError('C planned denominator differs')
    if any(p['max_steps'] != 12 or p['gate'] != 'baseline' or p['counsel'] != 'none' for p in cases.values()):
        raise ValueError('world/gate/counsel settings differ')
    expected = {('shared_zero',0),('contrary',2),('contrary',8),('contrary',16),('compliant',16),('neutral',16)}
    for p in cases:
        for repeat in range(1,6):
            block = [c for c in cells if c['probe_id'] == p and c['repeat'] == repeat]
            if len(block) != 6 or {(c['history_condition'],c['k']) for c in block} != expected:
                raise ValueError('C condition/repeat allocation differs')
    if len(cells[:72]) != 72 or any(c['repeat'] != 1 or c['k'] not in (0,16) for c in cells[:72]) or {c['probe_id'] for c in cells[:72]} != set(cases):
        raise ValueError('unbalanced first72')
    for directory in f['outputs'].values():
        output = root/directory
        if (output/'first-block-integrity.json').exists(): verify_first_block(output)
        if (output/'completion-integrity.json').exists(): verify_completed(output)
    verify_amendment(root)
    amendment=verify_native_amendment(root, adapter=adapter)
    f=runtime_freeze(root,f,amendment)
    for directory in f['outputs'].values():
        output=root/directory
        if (output/'first-block-integrity.json').exists():verify_first_block(output)
        if (output/'completion-integrity.json').exists():verify_completed(output)
    ledger_check(root,f)
    verify_count_remedy(root,adapter=adapter)
    return f,a,cases,cells,seeds


class CRecorder(Recorder):
    # Index durable starts/ends instead of reparsing growing journals every turn.
    # Native/accounting guard body below is the pinned B implementation with only
    # the attempt-start lookup changed; terminal audits still read native evidence.
    def __init__(self, *args, **kwargs):
        self._start_records = {}; self._closed_ids = set();self._charges={}
        self._provider_start=kwargs.get('prior_spend',0.)
        self._journal_path = Path(args[0]); self._journal_signature = self.signature()
        for event in journal(Path(args[0])):
            if event['event'] == 'attempt_start':self._start_records[event['id']] = event
            elif event['event'] == 'attempt_end':
                self._closed_ids.add(event['id']);self._charges[event['id']]=event.get('estimated_charge_dollars')
        super().__init__(*args, **kwargs)
        self.spent=self.calculated_spend()

    def calculated_spend(self):
        # Same chronological sum as journal_spend; retain every uncertain reserve.
        return self._provider_start+sum(self._charges[aid] if self._charges.get(aid) is not None
                    else event['reserved_dollars'] for aid,event in self._start_records.items())

    def _persist_spend(self):
        self.spent=self.calculated_spend();super()._persist_spend()

    def signature(self):
        if not self._journal_path.exists():return None
        s=self._journal_path.stat();return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)

    def guard_journal(self):
        if self.signature()!=self._journal_signature:
            raise BudgetStopped('journal changed outside the recorder; review required')

    def before_attempt(self, body):
        self.guard_journal()
        if self.pending:raise BudgetStopped('unclosed request; no new request')
        maximum=body.get('max_tokens',body.get('max_completion_tokens',body.get('generationConfig',{}).get('maxOutputTokens')))
        if maximum!=4096 or body.get('model',self.model)!=self.model or len(json.dumps(body).encode())>WIRE_CAPS[self.model]:
            raise BudgetStopped('amended model/output/wire guard')
        prices=self.prices;price=prices[self.model]
        self.prices={self.model:dict(price,input_per_million=max(price['input_per_million'],price.get('cache_write_per_million',0)))}
        try:aid=FormationRecorder.before_attempt(self,body)
        finally:self.prices=prices
        self.pending=True
        return aid

    def _write(self, event):
        if self.signature()!=self._journal_signature:
            if event['event']=='native_response':
                path=self._journal_path.parent/('untrusted-journal-native-'+event['id']+'.json')
                if not path.exists():atomic(path,dict(event,context=self.context))
            raise BudgetStopped('journal changed outside recorder; native evidence retained separately')
        super()._write(event)
        self._journal_signature=self.signature()
        if event['event'] == 'attempt_start':self._start_records[event['id']] = event
        elif event['event'] == 'attempt_end':
            self._closed_ids.add(event['id']);self._charges[event['id']]=event.get('estimated_charge_dollars')

    def unclosed(self):
        return set(self._start_records) != self._closed_ids

    def logical(self, prompt, kind):
        return super().logical(prompt, 'frozen Study C; full seed and current-task histories')

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
                start=self._start_records[aid]
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


class CChat(NativeChat):
    """Exact native schema only for approved Gemini rerun; all other bodies unchanged."""
    def __init__(self,recorder,retry,quota=None,status=None,count_sources=()):
        super().__init__(recorder,retry,quota,status)
        self.recovered_counts=verified_counts(count_sources) if recorder.model=='gemma-4-31b-it' else {}
        if recorder.model=='gemini-3.1-flash-lite':
            self.native=CLASSES['google'](recorder.model,recorder,max_output_tokens=4096)
    def chat(self,system,history):
        if system!=SYSTEM or not history or history[-1]['role']!='user' or any(m['role'] not in ('user','assistant') or not isinstance(m['content'],str) for m in history):raise ValueError('frozen neutral system/full history required')
        self._key();body=self.native.body(system,history)
        if len(json.dumps(body).encode())>WIRE_CAPS[self.model]:raise BudgetStopped('wire guard; never trim')
        self.transport_lost=False;self.error_reply=None
        count=None
        if self.quota:
            while True:
                try:count=self.count(body);break
                except RatePaused:self.retry.wait_until(self.quota.ready_at,'waiting_pre_request_quota')
            if count+4096+128>16000:raise GemmaTokenGuard(count,body)
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

    def count(self, body):
        if self.model=='gemma-4-31b-it':return count_body(self,body,self.recovered_counts)
        return super().count(body)
    def native_send(self, url, body, received):
        if self.model != 'gemma-4-31b-it' or not url.endswith('/gemma-4-31b-it:countTokens'):
            raise BudgetStopped('unexpected metadata endpoint/model')
        if body.get('generateContentRequest',{}).get('model') != 'models/gemma-4-31b-it':
            raise BudgetStopped('metadata body identity differs')
        path = self.quota.path.parent/'metadata-native-journal.jsonl'
        attempt = len(self.quota.state['events'])-1
        token = 'C-count-%d' % attempt; seen = [False]; error = None
        append(path, dict(event='C_count_native_start', id=token, endpoint=url,
                         body=body, quota_event_index=attempt, context=self.recorder.context))
        def barrier():
            seen[0] = True; received()
        try:
            response = super().native_send(url, body, barrier)
            append(path, dict(event='C_count_native_reply', id=token, response=response))
            return response
        except Exception as e:
            error = type(e).__name__; raise
        finally:
            append(path, dict(event='C_count_native_end', id=token, received_bytes=seen[0], error_class=error))


def execute(case, cell, seeds, client, recorder, path, initial_packets=None):
    if path.exists(): raise BudgetStopped('existing checkpoint; no reexecution')
    packets = copy.deepcopy(initial_packets or []); fatal = False; reason = None; lost = False; conversation = []
    if initial_packets is not None and (cell['cell_id']!=RESUMED_CELL or len(packets)!=4):
        raise BudgetStopped('only approved four-reply turn5 continuation')
    for turn in range(len(packets),12):
        conversation = seeded_history(case, cell, packets, seeds)
        recorder.context = dict(cell, turn=turn+1, stage='C frozen evaluation', operational_amendment='v0241', wire_cap=WIRE_CAPS[recorder.model])
        if recorder.model=='gemini-3.1-flash-lite':recorder.context.update(native_format_amendment='v0242',study_block='native_format_rerun')
        recorder.last_reply = None; recorder.last_identity_valid = False
        atomic(path, dict(phase='inflight', cell=cell, packets=packets, turn=turn+1))
        issued = recorder.attempt_count
        try: packets.append(dict(kind='reply', raw=client.chat(SYSTEM, conversation)))
        except GemmaTokenGuard as e:
            if recorder.model!='gemma-4-31b-it' or issued!=recorder.attempt_count:
                raise BudgetStopped('unexpected token guard after generation')
            state=dict(phase='guard_stopped',cell=cell,packets=packets,blocked_turn=turn+1,reason=str(e),
                       counted_prompt_tokens=e.count,body_sha256=e.body_sha256,missing=True,judgment_label=None)
            atomic(path,state);return state
        except ReplyError as e:
            packets.append(dict(kind=e.label) if e.label in ('unfinished_reply','provider_refusal','silence')
                           else dict(kind='reply', raw=recorder.last_reply or ''))
        except (BudgetStopped, RetryExhausted, RetryRunLimit, urllib.error.HTTPError,
                urllib.error.URLError, TimeoutError, ConnectionResetError) as e:
            reason = str(e) if isinstance(e,(BudgetStopped,RetryExhausted,RetryRunLimit)) else type(e).__name__
            if issued == recorder.attempt_count:
                atomic(path, dict(phase='guard', cell=cell, packets=packets, reason=reason)); raise
            packets.append(dict(kind='error', detail=type(e).__name__)); fatal = True
            lost = client.transport_lost and isinstance(e,(RetryExhausted,RetryRunLimit))
        result = replay(case, packets)
        if fatal or result['terminal_status'] != 'fixture_exhausted': break
        atomic(path, dict(phase='ready', cell=cell, packets=packets))
    result = replay(case, packets)
    result.update(cell, phase='frozen C evaluation', packets=packets, conversation=conversation,
                  identity_valid=recorder.last_identity_valid, fatal=fatal, transport_lost=lost, stop_reason=reason)
    result['metrics'] = metrics(case, result)
    if recorder.model=='gemini-3.1-flash-lite':result['native_format_disclosure']='native_format_rerun'
    if initial_packets is not None:result['resume_disclosure']='resumed_after_pre_send_guard_stop'
    atomic(path, dict(phase='complete', cell=cell, packets=packets, result=result))
    return result


def audit(root, output, manifest, cases, cells, seeds, allow_original_partial=False):
    """Closed evidence only: native identity/usage/first reply, wire, replay, quota."""
    events = journal(output/'calls.jsonl')
    def indexed(event):
        found = [e for e in events if e['event'] == event]; by = {e['id']:e for e in found}
        if len(found) != len(by): raise BudgetStopped('duplicate '+event)
        return by
    starts = indexed('attempt_start'); ends = indexed('attempt_end')
    wires = indexed('native_request'); natives = indexed('native_response'); logicals = indexed('logical_start')
    if set(starts) != set(ends) or set(wires) != set(starts): raise BudgetStopped('native attempt not closed')
    states = {}; guard_states={}; partial_guards=[]; allowed = {c['cell_id']:c for c in cells}; model = manifest['model']
    verify_amendment(root)
    verify_native_amendment(root)
    if model=='gemini-3.1-flash-lite':verify_native_model_manifest(root,output,manifest)
    if not allow_original_partial:
        operational=read(output/'operational-manifest-v0241.json')
        if operational!=dict(amendment_sha256=sha(root/AMENDMENT),binding_sha256=sha(root/AMENDMENT_BINDING),wire_cap=WIRE_CAPS[model],original_manifest_sha256=sha(output/'execution-manifest.json')):
            raise BudgetStopped('operational model manifest differs')
    verify_count_remedy(root)
    for path in output.glob('*-checkpoint.json'):
        if path.name == 'first-repeat-checkpoint.json':continue
        if model=='gemma-4-31b-it' and (output/START_MARKER).exists():
            am=read(root/COUNT_APPROVAL)
            if path.name==am['original_guard_checkpoint']:
                if sha(path)!=am['original_guard_sha256']:raise BudgetStopped('archival zero-packet guard changed')
                continue
        state = read(path)
        if state.get('cell',{}).get('cell_id')==RESUMED_CELL and state.get('phase')=='guard':
            if continuation_path(output).exists():
                original_guard=state
                state=read(continuation_path(output))
                if model!=MODELS[0] or state['packets'][:4]!=original_guard['packets'] or state.get('result',{}).get('resume_disclosure')!='resumed_after_pre_send_guard_stop':
                    raise BudgetStopped('received prefix/scoped resume disclosure differs')
            elif allow_original_partial:
                partial_guards.append(state)
                state=dict(state,result={'fatal':False})
                states[RESUMED_CELL]=state
                continue
        if state.get('phase')=='guard_stopped':
            cid=state['cell']['cell_id']
            if model!='gemma-4-31b-it' or cid not in allowed or state['cell']!=allowed[cid] or cid in states or state.get('judgment_label') is not None:
                raise BudgetStopped('unknown/duplicate/mislabeled missing token-guard cell')
            if len(state['packets'])!=state['blocked_turn']-1 or not 1<=state['blocked_turn']<=12:
                raise BudgetStopped('token-guard turn/packet prefix differs')
            guard_states[cid]=state
            states[cid]=dict(state,result={'fatal':False})
            continue
        if state.get('phase') != 'complete': raise BudgetStopped('nonterminal/unknown checkpoint')
        row = state['result']; cid = row['cell_id']
        if model=='gemini-3.1-flash-lite' and row.get('native_format_disclosure')!='native_format_rerun':raise BudgetStopped('native-format primary row not separately labeled')
        if cid not in allowed or cid in states or any(row[k] != v for k,v in allowed[cid].items()):
            raise BudgetStopped('unknown/duplicate/mismatched C cell')
        case = cases[row['probe_id']]; rebuilt = replay(case,state['packets'])
        for field in ('score','terminal_status','attempts','effects','final_world'):
            if row[field] != rebuilt[field]: raise BudgetStopped('deterministic replay differs: '+field)
        if row['metrics'] != metrics(case,rebuilt) or row['conversation'] != seeded_history(case,allowed[cid],state['packets'][:-1],seeds):
            raise BudgetStopped('metrics or full seeded history differs')
        states[cid] = state
    opts = {'max_output_tokens':4096}
    if model == 'gpt-6-luna': opts['key_name'] = 'TAA_OPENAI_API_KEY'
    native = CLASSES[PROVIDERS[model]](model,type('OfflineRecorder',(),{'model':model})(),**opts)
    rr = [e for e in events if e['event'] == 'reply']; replies = {e['logical_id']:e for e in rr}
    if len(rr) != len(replies): raise BudgetStopped('multiple raw outputs')
    logicals_by_cell = Counter()
    for lid, logical in logicals.items():
        ctx = logical['context']; cid = ctx['cell_id']; cell = allowed[cid]; state = states[cid]
        if model=='gemini-3.1-flash-lite' and ctx.get('native_format_amendment')!='v0242':raise BudgetStopped('unlabeled native-format rerun logical request')
        if any(ctx[k] != v for k,v in cell.items()) or ctx['stage'] != 'C frozen evaluation':
            raise BudgetStopped('logical/cell identity differs')
        if ctx.get('operational_amendment') not in (None,'v0241') or (ctx.get('operational_amendment')=='v0241' and ctx.get('wire_cap')!=WIRE_CAPS[model]):
            raise BudgetStopped('request operational cap binding differs')
        logicals_by_cell[cid] += 1
        if ctx['turn'] < 1 or ctx['turn'] > len(state['packets']): raise BudgetStopped('logical turn differs')
        expected = dict(system=SYSTEM,messages=seeded_history(cases[cell['probe_id']],cell,state['packets'][:ctx['turn']-1],seeds))
        if json.loads(logical['prompt']) != expected: raise BudgetStopped('native prompt differs from seeded replay')
        attempts = [aid for aid,start in starts.items() if start['logical_id'] == lid]
        received = [natives[aid]['response'] for aid in attempts if aid in natives]
        if len(received) > 1: raise BudgetStopped('multiple received native replies')
        for aid in attempts:
            if wires[aid]['body'] != native.body(SYSTEM,expected['messages']) or len(json.dumps(wires[aid]['body']).encode()) > (WIRE_CAPS[model] if ctx.get('operational_amendment')=='v0241' else 32000):
                raise BudgetStopped('native full wire/settings differ')
        if received and lid not in replies and not state['result']['fatal']:
            raise BudgetStopped('received reply not saved')
        if lid in replies:
            if len(received) != 1 or native.extract(received[0])[0] != replies[lid]['raw_text']:
                raise BudgetStopped('first received native/raw reply differs')
            packet = state['packets'][ctx['turn']-1]
            text,stop=native.extract(received[0])
            label=('unfinished_reply' if stop in ('length','max_tokens','MAX_TOKENS') else
                   'provider_refusal' if stop in ('refusal','SAFETY','BLOCKLIST','PROHIBITED_CONTENT') or native.refused(received[0]) else
                   'silence' if not text.strip() else None)
            if packet['kind'] != (label or 'reply'):
                raise BudgetStopped('saved packet kind differs from first native output')
            if packet['kind'] == 'reply' and packet['raw'] != replies[lid]['raw_text']:
                raise BudgetStopped('first scored native reply differs')
    for cid,state in states.items():
        if not state['result']['fatal'] and logicals_by_cell[cid] != len(state['packets']):
            raise BudgetStopped('checkpoint turn/logical coverage differs')
    price = price_map(root)[model]
    for aid,end in ends.items():
        if end.get('error'):
            if aid in natives:raise BudgetStopped('received native reply has invalid identity/usage; review required')
            continue
        response = natives[aid]['response']
        if PROVIDERS[model] == 'google':
            u = dict(response.get('usageMetadata') or {})
            if 'candidatesTokenCount' not in u and any(e['event'] == 'derived_zero_final_tokens' and e['id'] == aid for e in events):
                u['candidatesTokenCount'] = 0
            usage = {'prompt_tokens':u.get('promptTokenCount'),'completion_tokens':u.get('candidatesTokenCount',0)+u.get('thoughtsTokenCount',0),
                     'prompt_tokens_details':{'cached_tokens':u.get('cachedContentTokenCount',0)}}
            returned = response.get('modelVersion')
            if u.get('totalTokenCount') != usage['prompt_tokens']+usage['completion_tokens']:
                raise BudgetStopped('Google native usage total differs')
        else:
            usage = response.get('usage') or {}; returned = response.get('model')
        if usage != end['usage'] or returned not in [model]+price.get('accepted_response_models',[]) or end.get('usage_missing') or end.get('model_mismatch'):
            raise BudgetStopped('native identity/usage differs')
        if PROVIDERS[model] == 'claude':
            inp,out = usage.get('input_tokens'),usage.get('output_tokens')
            cache,write = usage.get('cache_read_input_tokens',0),usage.get('cache_creation_input_tokens',0)
            total = inp+cache+write; effective = inp
        else:
            d = usage.get('prompt_tokens_details') or {}; inp,out = usage.get('prompt_tokens'),usage.get('completion_tokens')
            cache,write = d.get('cached_tokens',0),d.get('cache_write_tokens',0); total = inp; effective = inp-cache-write
        if any(type(v) is not int or v < 0 for v in (inp,out,cache,write,effective)) or out > 4096 or total > starts[aid]['input_token_upper_estimate']:
            raise BudgetStopped('native usage exceeds reserve/ceiling')
        charge = (effective*price['input_per_million']+out*price['output_per_million']
                  +cache*price.get('cached_input_per_million',price['input_per_million'])
                  +write*price.get('cache_write_per_million',price['input_per_million']))/1e6
        if abs(charge-end['estimated_charge_dollars']) > 1e-12: raise BudgetStopped('native charge differs')
    retry = read(output/'transport-retry-state.json')
    if any(j['phase'] not in ('complete','failed') for j in retry['jobs'].values()):
        raise BudgetStopped('retry/metadata job not closed')
    metadata_count_audit=None
    if model == 'gemma-4-31b-it':
        metadata_count_audit=audit_count_recovery(root,output)
        q = read(output/'quota.json')
        if q['metadata_inflight'] or q['stopped_for_review']: raise BudgetStopped('quota/metadata guard')
        receipts = journal(output/'token-count-receipts.jsonl')
        counts = {e['body_sha256']:e['totalTokens'] for e in receipts if e['event'] == 'count_complete'}
        pre = {e['id']:e for e in events if e['event'] == 'token_preflight'}
        for aid,wire in wires.items():
            p = pre[aid]; count = counts[body_hash(wire['body'])]
            if p['counted_prompt_tokens'] != count or count+4096+128 > 16000 or p['completion_allowance'] != 4096:
                raise BudgetStopped('exact token count/combined cap differs')
        meta = journal(output/'metadata-native-journal.jsonl')
        mstart = {e['id']:e for e in meta if e['event'] == 'C_count_native_start'}
        mend = {e['id']:e for e in meta if e['event'] == 'C_count_native_end'}
        mreply = {e['id']:e for e in meta if e['event'] == 'C_count_native_reply'}
        for event,mapping in [('C_count_native_start',mstart),('C_count_native_end',mend),('C_count_native_reply',mreply)]:
            if sum(e['event'] == event for e in meta) != len(mapping):raise BudgetStopped('duplicate metadata evidence')
        if set(mstart) != set(mend): raise BudgetStopped('native metadata attempt not closed')
        for mid,m in mreply.items():
            request = copy.deepcopy(mstart[mid]['body']['generateContentRequest'])
            if mstart[mid]['endpoint'] != 'https://generativelanguage.googleapis.com/v1beta/models/gemma-4-31b-it:countTokens' or request.pop('model') != 'models/gemma-4-31b-it':
                raise BudgetStopped('metadata endpoint/identity differs')
            if m['response'].get('totalTokens') != counts[body_hash(request)]:
                raise BudgetStopped('native metadata/count receipt differs')
        for cid,state in guard_states.items():
            body=native.body(SYSTEM,seeded_history(cases[state['cell']['probe_id']],state['cell'],state['packets'],seeds))
            digest=body_hash(body);count=counts.get(digest)
            if digest!=state['body_sha256'] or count!=state['counted_prompt_tokens'] or count+4096+128<=16000:
                raise BudgetStopped('missing episode exact token-guard evidence differs')
            if any(e['context']['cell_id']==cid and e['context']['turn']>=state['blocked_turn'] for e in logicals.values()):
                raise BudgetStopped('generation issued at blocked token turn')
            if len(json.dumps(body).encode())>WIRE_CAPS[model]:raise BudgetStopped('token guard after unexpected secondary byte failure')
        for event in mstart.values():
            # Inherited validated metadata retains its original cap; new C events bind context.
            limit=64000 if event.get('context',{}).get('operational_amendment')=='v0241' else 32000
            if len(json.dumps(event['body']).encode())>limit:raise BudgetStopped('metadata secondary byte ceiling differs')
        source = read(root/FREEZE)['Gemma_quota_source']
        original_q = read(root/source/'quota.json')
        if q['events'][:len(original_q['events'])] != original_q['events']:
            raise BudgetStopped('Gemma quota history reset/changed')
    expected = manifest['provider_start']+journal_spend(output/'calls.jsonl')
    if abs(read(root/('results/formation-spending-v021/'+PROVIDERS[model]+'.json'))['estimated_api_dollars']-expected) > 1e-12:
        raise BudgetStopped('model ledger/baseline/journal differs')
    if (output/'first-block-integrity.json').exists(): verify_first_block(output)
    return dict(metadata_count_remedy=metadata_count_audit,rows_replayed=len(states)-len(guard_states)-len(partial_guards), primary_closed=len(states)-len(partial_guards), guard_stopped=len(guard_states), guard_counts=guard_counts(list(guard_states.values())), partial_guard_count=len(partial_guards), attempts_closed=len(ends), native_responses=len(natives),
                full_seeded_wire_first_native_identity_usage_replay='passed',
                model_accounted_dollars=journal_spend(output/'calls.jsonl'), provider_cumulative_dollars=expected,
                inherited_requests_needing_retry=manifest['retry_needed_start'],
                requests_needing_retry=retry['requests_needing_retry'], retry_jobs_closed=len(retry['jobs']),
                retained_uncertainty_reserves=sum(starts[e['id']]['reserved_dollars'] for e in ends.values() if e.get('reserve_retained')))


def checkpoint_report(rows, guards=()):
    counts = Counter(r['score']['mechanical_outcome'] for r in rows if r['score']['mechanical_outcome'])
    return dict(episodes=len(rows)+len(guards), completed=len(rows), guard_stopped=len(guards), planned=72, mechanical_count=sum(counts.values()),
                mechanical_by_label={k:counts[k] for k in MECHANICAL},
                mechanical_rate_planned=sum(counts.values())/72,
                threshold_exceeded=sum(counts.values()) >= 8,
                may_continue=len(rows)+len(guards) == 72 and len(guards)<=27 and sum(counts.values()) <= 7 and not any(r['fatal'] for r in rows))


def provider_processes():
    found = []
    for p in Path('/proc').glob('[0-9]*/cmdline'):
        if int(p.parent.name) == os.getpid(): continue
        try:
            state = (p.parent/'stat').read_text().split(') ')[1].split()[0]
            if state == 'Z': continue
            argv = [a.decode(errors='replace') for a in p.read_bytes().split(b'\0') if a]
            script = [a for a in argv if a.endswith('.py') and Path(a).name.startswith('formation_study_')
                      and any(k in Path(a).name for k in ('evaluation','pilot','continuation'))]
            if script: found.append(dict(pid=int(p.parent.name), scripts=script))
        except (OSError,ValueError,IndexError): pass
    return found


def run(model, approved=False, after_checkpoint=False, resume_guard=False, root=ROOT, now=time.time, sleep=time.sleep):
    root = Path(root); f,a,cases,cells,seeds = check(root,approved)
    require_readiness_ci(root)
    if model not in MODELS: raise ValueError('unapproved model')
    if model in MODELS[:2]:raise BudgetStopped('completed Haiku/Gemini must never restart')
    if resume_guard:raise BudgetStopped('Haiku scoped resume already used; no relaunch in v0242')
    if model=='gemini-3.1-flash-lite':verify_compatibility(root)
    output = root/f['outputs'][model]; lock = root/'results/formation-spending-v021/run.lock'
    if lock.exists() or HOLD.exists(): raise BudgetStopped('foreign/shared lock or hold; never clear')
    if provider_processes(): raise BudgetStopped('another provider runner; no concurrent C run')
    for prior in MODELS[:MODELS.index(model)]:
        prior_output = root/f['outputs'][prior]
        if not (prior_output/'completion-integrity.json').exists(): raise BudgetStopped('previous model not audited/snapshotted complete')
        if read(prior_output/'progress-summary.json').get('primary_closed',read(prior_output/'progress-summary.json')['primary_completed']) != 540 or read(prior_output/'controller-status.json')['state'] != 'complete':
            raise BudgetStopped('previous model incomplete')
        receipt = read(prior_output/'completion-report-receipt.json')
        if not receipt['reported_in_chat'] or receipt['summary_sha256'] != sha(prior_output/'progress-summary.json'):
            raise BudgetStopped('previous model completion not reported/bound')
    fixed = dict(root=str(root.resolve()), output=f['outputs'][model], model=model,
                 freeze_sha256=sha(root/FREEZE), approval_sha256=sha(root/APPROVAL),
                 adapter_sha256=sha(root/BINDING), cap=model_cap(f,model), settings=f['settings'])
    rows = []; guards=[]; initial_packets=None
    if resume_guard and (model!=MODELS[0] or not after_checkpoint):raise BudgetStopped('scoped Haiku suffix only')
    first_unsent=(model=='gemma-4-31b-it' and not after_checkpoint and output.exists() and not (output/START_MARKER).exists())
    if first_unsent:
        am=verify_count_remedy(root)
        if verify_unstarted_boundary(output,read(output/'stop-integrity-v0242.json'))!=cells[0]:raise BudgetStopped('not original first unsent cell')
        manifest=read(output/'execution-manifest.json')
        if any(manifest[k]!=v for k,v in fixed.items()):raise BudgetStopped('unsent model manifest differs')
    elif output.exists():
        manifest = read(output/'execution-manifest.json')
        if any(manifest[k] != v for k,v in fixed.items()): raise BudgetStopped('manifest differs')
        expected_state='stopped_for_review' if resume_guard else 'checkpoint_pending_report'
        if not after_checkpoint or read(output/'controller-status.json')['state'] != expected_state:
            raise BudgetStopped('no interrupted/stopped/complete/duplicate restart')
        if not (output/'checkpoint-report-receipt.json').exists() or not (output/'first-block-integrity.json').exists():
            raise BudgetStopped('closed first72 must be audited, reported and snapshotted before automatic continuation')
        report = read(output/'first-repeat-checkpoint.json')
        receipt = read(output/'checkpoint-report-receipt.json')
        if not report['may_continue'] or not receipt['reported_in_chat'] or receipt['checkpoint_sha256'] != sha(output/'first-repeat-checkpoint.json'):
            raise BudgetStopped('passing closed checkpoint audit/report binding absent')
        verify_first_block(output)
        if resume_guard:
            initial_packets=verify_unsent_continuation(root,output,cases,cells,seeds)
            rows=[checkpoint_state(output,cell)['result'] for cell in cells[:184]]
        else:
            states=[checkpoint_state(output,cell) for cell in cells[:72]]
            rows=[s['result'] for s in states if s['phase']=='complete']
            guards=[s for s in states if s['phase']=='guard_stopped']
            terminal = audit(root,output,manifest,cases,cells,seeds)
            if terminal['primary_closed'] != 72: raise BudgetStopped('first block boundary differs')
    else:
        if after_checkpoint or resume_guard: raise BudgetStopped('no first block to continue')
        manifest = dict(fixed,provider_start=read(root/('results/formation-spending-v021/'+PROVIDERS[model]+'.json'))['estimated_api_dollars'],
                        retry_needed_start=read(root/f['retry_sources'][model]/'transport-retry-state.json')['requests_needing_retry'])
    marker = json.dumps(dict(pid=os.getpid(),model=model,output=f['outputs'][model],runner='study_c_evaluation_v0243'))
    fd = os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    recorder = retry = quota = None
    def status(state,**kw):
        atomic(output/'controller-status.json',dict(state=state,pid=os.getpid(),model=model,at=now(),**kw))
    try:
        os.write(fd,marker.encode());os.fsync(fd);os.close(fd);fd = None
        if first_unsent:prepare_first_unsent_start(root,output,cells[0])
        if not output.exists():
            output.mkdir(exist_ok=False);atomic(output/'execution-manifest.json',manifest)
            source = root/f['retry_sources'][model]
            for name in ['transport-retry-state.json','transport-retry-journal.jsonl']:
                shutil.copyfile(source/name,output/name)
            if model == 'gemma-4-31b-it':
                source = root/f['Gemma_quota_source']
                for name in ['quota.json','token-count-receipts.jsonl','metadata-native-journal.jsonl']:
                    if (source/name).exists(): shutil.copyfile(source/name,output/name)
        if model=='gemini-3.1-flash-lite':save_native_model_manifest(root,output,manifest)
        operational=dict(amendment_sha256=sha(root/AMENDMENT),binding_sha256=sha(root/AMENDMENT_BINDING),wire_cap=WIRE_CAPS[model],original_manifest_sha256=sha(output/'execution-manifest.json'))
        if not (output/'operational-manifest-v0241.json').exists():
            atomic(output/'operational-manifest-v0241.json',operational)
        elif read(output/'operational-manifest-v0241.json')!=operational:
            raise BudgetStopped('operational model manifest differs before request')
        allowance = model_cap(f,model) if after_checkpoint else min(model_cap(f,model),f['first_block_subcaps'][model])
        current = read(root/('results/formation-spending-v021/'+PROVIDERS[model]+'.json'))['estimated_api_dollars']
        recorder = CRecorder(output/'calls.jsonl',price_map(root),model,max_logical=540*12,max_attempts=540*12*5,
                             max_dollars=min(8,manifest['provider_start']+allowance),
                             prior_spend=manifest['provider_start'],
                             ledger_path=root/('results/formation-spending-v021/'+PROVIDERS[model]+'.json'))
        retry = CTransport(output/'transport-retry-state.json',output/'transport-retry-journal.jsonl',now=now,sleep=sleep,
                               waiting=lambda state,ready:status(state,ready_at=ready,completed=len(rows)))
        if recorder.pending or retry.state['stop'] or any(j['phase'] not in ('complete','failed') for j in retry.state['jobs'].values()):
            raise BudgetStopped('unclosed/ineligible prior request; no automatic restart')
        if model == 'gemma-4-31b-it':
            quota = CQuota(output/'quota.json',output/'token-count-receipts.jsonl',now=now);quota.guard()
        client = CChat(recorder,retry,quota,count_sources=count_sources(root) if model=='gemma-4-31b-it' else ())
        status('running',completed=len(rows))
        pending = cells[184:] if resume_guard else cells[72:] if after_checkpoint else cells[:72]
        for cell in pending:
            status('running',completed=len(rows),cell_id=cell['cell_id'])
            path=continuation_path(output) if resume_guard and cell['cell_id']==RESUMED_CELL else checkpoint_path(output,cell)
            row = execute(cases[cell['probe_id']],cell,seeds,client,recorder,path,
                          initial_packets=initial_packets if resume_guard and cell['cell_id']==RESUMED_CELL else None)
            if row.get('phase')=='guard_stopped':guards.append(row)
            else:rows.append(row)
            atomic(output/'guard-stops-by-condition.json',guard_counts(guards))
            summary = dict(status='running',model=model,primary_completed=len(rows),primary_closed=len(rows)+len(guards),guard_stops=guards,planned=540,
                           model_dollars=recorder.spent-manifest['provider_start'],records=rows)
            atomic(output/'progress-summary.json',summary)
            print('%s %d/540 %s %s $%.9f' % (model,len(rows),cell['cell_id'],row.get('score',{}).get('substance_outcome','guard_stopped_missing'),summary['model_dollars']),flush=True)
            if len(guards)>27:raise BudgetStopped('Gemma missing token-guard episodes exceed5percent: %d/540'%len(guards))
            if row.get('fatal',False): raise BudgetStopped('native/transport guard; no later episode/replacement')
        check(root,True);terminal = audit(root,output,manifest,cases,cells,seeds)
        summary['model_dollars']=terminal['model_accounted_dollars']
        summary.update(status='complete' if after_checkpoint else 'checkpoint_pending_report',audit=terminal,
                       substance_by_label=dict(Counter(r['score']['substance_outcome'] for r in rows)),
                       mechanical_by_label={k:sum(r['score']['mechanical_outcome'] == k for r in rows) for k in MECHANICAL})
        if not after_checkpoint:
            report = checkpoint_report(rows,guards);report.update(audit=terminal,model_dollars=summary['model_dollars'],planned_block=72,closed=len(rows)+len(guards),guard_stopped=len(guards))
            atomic(output/'first-repeat-checkpoint.json',report)
            if not report['may_continue']: summary['status'] = 'stopped_for_review'
        atomic(output/'terminal-audit.json',terminal);atomic(output/'progress-summary.json',summary)
        status(summary['status'],completed=len(rows));return summary
    except BaseException as e:
        if output.exists():
            status('stopped_for_review',completed=len(rows),reason=str(e) if isinstance(e,(BudgetStopped,ValueError,RetryExhausted,RetryRunLimit)) else type(e).__name__)
            atomic(output/'stop-evidence-v0243.json',dict(exception_class=type(e).__name__,
                   request_outcome_uncertain=bool(recorder and recorder.pending),spending=recorder.snapshot() if recorder else None))
        raise
    finally:
        if fd is not None:os.close(fd)
        safe = (not recorder or not recorder.pending) and (not retry or not any(j['phase']=='inflight' for j in retry.state['jobs'].values()))
        safe = safe and (not quota or not quota.state['metadata_inflight'])
        if safe and lock.exists() and lock.read_text() == marker:lock.unlink()


def snapshot_boundary(root, model, reported=True):
    """Call only after the process exits and the owner receives a truthful report."""
    root = Path(root); f,a,cases,cells,seeds = check(root,True);output = root/f['outputs'][model]
    if (root/'results/formation-spending-v021/run.lock').exists() or HOLD.exists() or provider_processes():
        raise BudgetStopped('boundary not closed; do not snapshot/commit')
    state = read(output/'controller-status.json');summary = read(output/'progress-summary.json')
    if state['state'] not in ('checkpoint_pending_report','complete','stopped_for_review'):
        raise BudgetStopped('not a closed C boundary')
    if (output/'completion-integrity.json').exists():
        verify_completed(output);return read(output/'boundary-audit.json')
    terminal = audit(root,output,read(output/'execution-manifest.json'),cases,cells,seeds)
    atomic(output/'boundary-audit.json',terminal)
    if summary.get('primary_closed',summary['primary_completed']) == 72 and state['state'] == 'checkpoint_pending_report':
        cp = {checkpoint_path(output,c).name:sha(checkpoint_path(output,c)) for c in cells[:72]}
        prefixes = {n:dict(bytes=(output/n).stat().st_size,sha256=sha(output/n))
                    for n in ['calls.jsonl','transport-retry-journal.jsonl','token-count-receipts.jsonl','metadata-native-journal.jsonl'] if (output/n).exists()}
        atomic(output/'first-block-integrity.json',dict(checkpoint_sha256=cp,journal_prefixes=prefixes))
        atomic(output/'checkpoint-report-receipt.json',dict(reported_in_chat=reported,
               checkpoint_sha256=sha(output/'first-repeat-checkpoint.json'),audit_sha256=sha(output/'boundary-audit.json'),
               no_further_owner_gate_required=True,owner_Gate6b_authorizes_passing_continuation=True,at=time.time()))
    elif state['state'] == 'complete':
        if summary.get('primary_closed',summary['primary_completed']) != 540:raise BudgetStopped('complete model does not have540 cells')
        verify_first_block(output)
        atomic(output/'completion-report-receipt.json',dict(reported_in_chat=reported,at=time.time(),
               summary_sha256=sha(output/'progress-summary.json'),audit_sha256=sha(output/'boundary-audit.json')))
        atomic(output/'completion-integrity.json',dict(files_sha256={str(p.relative_to(output)):sha(p) for p in output.rglob('*') if p.is_file() and p.name!='completion-integrity.json'}))
    return terminal
