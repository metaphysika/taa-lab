"""Reviewed-timeout continuation; only never-attempted frozen cells may run."""
import hashlib
import json
import os
from pathlib import Path
from agents.call_telemetry import BudgetStopped
from formation.clients import ProviderError,ReplyError
from formation.credentials import load_keys
from formation.limits import RatePaused
from formation.study_a import ROOT,agent_view,load_cases,replay_episode
from formation.study_a_pressure import pressure_view
from formation.study_a_pilot import SYSTEM
from formation.evaluation_transport_v0218 import QuotaRecorder,GroqSlots,make_client
from scripts.formation_study_a_gate3 import verify_freeze
from scripts.formation_connectivity import journal_spend

PLAN_PATH=ROOT/'studies/formation-study-a-evaluation-plan-v0217.json'
FREEZE_PATH=ROOT/'studies/formation-study-a-freeze-v0217.json'
ADAPTERS=('formation/evaluation_transport_v0218.py','formation/evaluation_runner_v0218.py',
          'formation/evaluation_continuation_v0219.py','scripts/formation_study_a_continuation.py')


def atomic(path,data):
    path=Path(path);temp=path.with_suffix('.tmp')
    with temp.open('w') as out:
        json.dump(data,out,indent=2);out.write('\n');out.flush();os.fsync(out.fileno())
    temp.replace(path)
    fd=os.open(str(path.parent),os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


def history_for_next(case,arm,packets):
    history,deliveries,seen=[],[],set()
    for turn in range(len(packets)+1):
        prior=replay_episode(case,packets[:turn])
        if prior['score']['terminal_status']!='fixture_exhausted':break
        if arm=='pressure':view,message=pressure_view(case,prior)
        else:view,message=agent_view(case),None;view['world']=prior['final_world']
        view['world']['step']=turn+1
        feedback={'task_context':view} if not history else {
            'last_tool_result':prior['attempts'][-1]['result'],'world':view['world']}
        if message and message['delivery_key'] not in seen:
            feedback['issuer_followup']=message['text'];seen.add(message['delivery_key'])
            deliveries.append(dict(message,before_reply_turn=turn+1))
        history.append({'role':'user','content':json.dumps(feedback,ensure_ascii=False)})
        if turn<len(packets) and packets[turn]['kind']=='reply':history.append({'role':'assistant','content':packets[turn]['raw']})
    return history,deliveries


def finish_cell(cell,case,client,recorder,state_path,packets,history,deliveries,fatal):
    result=replay_episode(case,packets)
    result.update(agent=client.model,arm=cell['arm'],repeat=cell['repeat'],
        phase='frozen evaluation',conversation=history,issuer_message_deliveries=deliveries,
        attempted=bool(packets),identity_valid=recorder.last_identity_valid and not any(p['kind']=='error' for p in packets),
        fatal_transport=fatal)
    atomic(state_path,{'phase':'complete','packets':packets,'result':result})
    return result,'stopped' if fatal else 'complete'


def execute_cell(cell,case,client,recorder,state_path):
    state=json.loads(state_path.read_text()) if state_path.exists() else {'phase':'ready','packets':[]}
    if state['phase']=='stopped':raise BudgetStopped('prior guard stop; manual budget/size review required')
    if state['phase']=='inflight':raise BudgetStopped('uncertain interrupted cell; manual evidence review required')
    if state['phase']=='complete':return state['result'],'complete'
    packets=state['packets']
    if replay_episode(case,packets)['score']['terminal_status']!='fixture_exhausted':
        history,deliveries=history_for_next(case,cell['arm'],packets)
        return finish_cell(cell,case,client,recorder,state_path,packets,history,deliveries,any(p['kind']=='error' for p in packets))
    while replay_episode(case,packets)['score']['terminal_status']=='fixture_exhausted':
        history,deliveries=history_for_next(case,cell['arm'],packets)
        recorder.context=dict(cell,turn=len(packets)+1)
        recorder.last_reply=None
        recorder.last_identity_valid=False
        atomic(state_path,{'phase':'inflight','packets':packets})
        issued_before=recorder.attempt_count
        fatal=False
        try:
            client.chat(SYSTEM,history)
            if recorder.last_reply is None:raise RuntimeError('missing raw reply')
            packets.append({'kind':'reply','raw':recorder.last_reply})
        except RatePaused as error:
            if recorder.attempt_count==issued_before:
                atomic(state_path,{'phase':'paused','packets':packets,'reason':str(error)})
                return None,'paused'
            packets.append({'kind':'error','detail':'issued request rate rejected; no retry'})
            fatal=True
        except ReplyError as error:
            if error.label in ('unfinished_reply','provider_refusal'):
                packets.append({'kind':error.label,'detail':error.label})
            else:packets.append({'kind':'reply','raw':recorder.last_reply or ''})
        except (ProviderError,BudgetStopped) as error:
            if recorder.attempt_count==issued_before:
                atomic(state_path,{'phase':'stopped','packets':packets,'reason':str(error)})
                return None,'stopped'
            packets.append({'kind':'error','detail':str(error)});fatal=True
        except Exception as error:
            packets.append({'kind':'error','detail':'harness '+type(error).__name__});fatal=True
        atomic(state_path,{'phase':'ready','packets':packets})
        result=replay_episode(case,packets)
        if fatal or result['score']['terminal_status']!='fixture_exhausted':
            # Avoid reconstructing error packets as successful assistant messages.
            if result['score']['terminal_status']=='agent_stop':
                history,deliveries=history_for_next(case,cell['arm'],packets)
            return finish_cell(cell,case,client,recorder,state_path,packets,history,deliveries,fatal)
    raise RuntimeError('unexpected pre-completed checkpoint')



def review_source(source,root=ROOT):
    source=Path(source)
    plan=json.loads((root/'studies/formation-study-a-evaluation-plan-v0217.json').read_text())
    cost=json.loads((root/'studies/formation-study-a-luna-evaluation-cost-plan-v0218.json').read_text())
    manifest=json.loads((source/'execution-manifest.json').read_text())
    summary=json.loads((source/'progress-summary.json').read_text())
    cells=[c for c in plan['cells'] if c['model']=='gpt-6-luna']
    if manifest['model']!='gpt-6-luna' or manifest['budget']!=1 or manifest['cells']!=cells:
        raise ValueError('source does not match approved Luna batch')
    for path,digest in cost['adapter_sha256'].items():
        if hashlib.sha256((root/path).read_bytes()).hexdigest()!=digest:
            raise ValueError('original execution adapter changed')
    if manifest['adapter_sha256']!=cost['adapter_sha256'] or manifest['freeze_sha256']!=cost['freeze_sha256']:
        raise ValueError('source fingerprints differ from approved cost plan')
    rows=summary['records']
    if len(rows)!=len(cells):raise ValueError('source has missing planned cells')
    completed=[];pending=[];evidence={}
    for cell,row in zip(cells,rows):
        if any(row[k]!=v for k,v in cell.items()):raise ValueError('source cell order differs')
        if row['status']=='not_attempted' and row['attempted'] is False:
            name='%s-r%02d'%(cell['case_id'],cell['repeat'])
            if (source/(name+'-checkpoint.json')).exists() or (source/(name+'.json')).exists():
                raise ValueError('pending cell has execution evidence; inspect manually')
            pending.append(cell);continue
        if pending or row['status']!='complete' or not row['attempted']:
            raise ValueError('source must have an attempted prefix followed by unattempted cells')
        name='%s-r%02d'%(cell['case_id'],cell['repeat'])
        path=source/(name+'.json');checkpoint=source/(name+'-checkpoint.json')
        result=json.loads(path.read_text());state=json.loads(checkpoint.read_text())
        if state['phase']!='complete' or state['result']!=result:raise ValueError('source result/checkpoint differs')
        if result['score']['outcome']!=row['outcome'] or result['identity_valid']!=row['identity_valid']:
            raise ValueError('source row differs from result')
        completed.append(result)
        for p in (path,checkpoint):evidence[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
    if not completed or not pending:raise ValueError('no stopped source prefix or pending cells')
    fatal=[r for r in completed if r.get('fatal_transport')]
    if len(fatal)!=1 or fatal[0]!=completed[-1] or fatal[0]['score']['terminal_detail']!='timeout; request outcome uncertain; inspect journal before retry':
        raise ValueError('only a final reviewed timeout may be bypassed')
    if any(not r['identity_valid'] for r in completed[:-1]):raise ValueError('earlier invalid identity requires separate review')
    events=[json.loads(line) for line in (source/'calls.jsonl').read_text().splitlines()]
    starts=[e for e in events if e['event']=='attempt_start'];ends=[e for e in events if e['event']=='attempt_end']
    if {e['id'] for e in starts}!={e['id'] for e in ends} or len(starts)!=len(ends):
        raise ValueError('unclosed source attempt requires review')
    if not ends or ends[-1].get('error')!='timeout' or not ends[-1].get('reserve_retained'):
        raise ValueError('source does not retain the uncertain timeout reserve')
    if any(e.get('error') or e.get('model_mismatch') or e.get('model_returned')!='gpt-6-luna' or e.get('usage_missing') for e in ends[:-1]):
        raise ValueError('earlier source attempt needs separate review')
    spent=journal_spend(source/'calls.jsonl')
    if spent!=summary['batch_estimated_dollars'] or not 0<spent<1:raise ValueError('source spending does not match')
    for name in ('calls.jsonl','execution-manifest.json','progress-summary.json'):
        evidence[name]=hashlib.sha256((source/name).read_bytes()).hexdigest()
    return {'source':str(source.resolve()),'source_sha256':evidence,
        'original_cap_dollars':1.0,'source_estimated_dollars':spent,
        'remaining_cap_dollars':1.0-spent,'retained_timeout_case':fatal[0]['case_id'],
        'retained_timeout_repeat':fatal[0]['repeat'],'pending_cells':pending,
        'policy':'Keep the timeout; do not retry any issued or prior cell. P6 remains inconclusive under frozen identity rules.'}


def run_continuation(source,output,approved=False,reviewed_timeout=False,root=ROOT):
    if not approved or not reviewed_timeout:raise ValueError('written continuation approval and timeout review required')
    source=Path(source)
    reviewed=review_source(source,root)
    model='gpt-6-luna';budget=reviewed['remaining_cap_dollars'];confirm_groq_free=False
    verify_freeze()
    plan=json.loads((root/'studies/formation-study-a-evaluation-plan-v0217.json').read_text())
    item=next((m for m in plan['models'] if m['model']==model),None)
    if item is None:raise ValueError('unknown frozen model')
    if budget<0 or budget>8 or (item['provider']!='groq' and budget<=0):raise ValueError('invalid application budget')
    if item['provider']=='groq' and (not confirm_groq_free or budget!=0):raise ValueError('Groq must remain confirmed Free with zero cost')
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    cells=reviewed['pending_cells']
    hashes={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in ADAPTERS}
    manifest={'model':model,'provider':item['provider'],'budget':budget,'cells':cells,
        'freeze_sha256':hashlib.sha256((root/'studies/formation-study-a-freeze-v0217.json').read_bytes()).hexdigest(),
        'adapter_sha256':hashes,'no_retry':True,'reviewed_source':reviewed,'groq_full_slot_policy':False}
    fingerprint=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    manifest['fingerprint']=fingerprint
    path=output/'execution-manifest.json'
    if path.exists():
        if json.loads(path.read_text())!=manifest:raise ValueError('resume manifest differs; never expand or alter a batch')
    else:atomic(path,manifest)
    ledgers=root/'results/formation-spending-v021';ledgers.mkdir(parents=True,exist_ok=True)
    lock=ledgers/'run.lock'
    try:fd=os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError:raise ValueError('run lock exists; inspect before continuing')
    try:
        os.write(fd,str(os.getpid()).encode())
        prices=json.loads((root/plan['price_file']).read_text())['models']
        ledger=ledgers/(item['provider']+'.json');prior=json.loads(ledger.read_text())['estimated_api_dollars'] if ledger.exists() else 0
        journal=output/'calls.jsonl';spent=journal_spend(journal)
        recorder=QuotaRecorder(journal,prices,model,max_logical=len(cells)*12,max_attempts=len(cells)*12,
            max_dollars=min(8,prior+max(0,budget-spent)),prior_spend=prior,ledger_path=ledger)
        if recorder.pending or recorder.missing_usage:raise BudgetStopped('journal has uncertain or unusable response; manual review required')
        quota=GroqSlots(ledgers/'groq-rate.json') if item['provider']=='groq' else None
        recorder.quota=quota
        client=make_client(model,item['provider'],recorder,quota)
        load_keys(root/'keys.env')
        rows=[];status='complete'
        stop=False
        for cell in cells:
            name='%s-r%02d'%(cell['case_id'],cell['repeat']);state_path=output/(name+'-checkpoint.json')
            if stop:
                rows.append(dict(cell,outcome='error',attempted=False,identity_valid=False,status='not_attempted'))
                continue
            case=load_cases([root/cell['path']])[0]
            result,status=execute_cell(cell,case,client,recorder,state_path)
            if result is None:
                partial=json.loads(state_path.read_text())['packets']
                rows.append(dict(cell,outcome='error',attempted=bool(partial),identity_valid=bool(partial),status=status));stop=True
            else:
                atomic(output/(name+'.json'),result)
                rows.append(dict(cell,outcome=result['score']['outcome'],attempted=result['attempted'],
                    identity_valid=result['identity_valid'],status='complete'))
                if result.get('fatal_transport'):stop=True
            summary={'model':model,'status':status,'completed_cells':sum(r['status']=='complete' for r in rows),
                'planned_cells':len(cells),'records':rows,'accounting':recorder.snapshot(),
                'batch_estimated_dollars':journal_spend(journal),'fingerprint':fingerprint}
            atomic(output/'progress-summary.json',summary)
        # Include every pending cell, not just the prefix at the first pause.
        summary.update(records=rows,analysis_records=[r for r in rows if r['status']=='complete'],
                       completed_cells=sum(r['status']=='complete' for r in rows))
        atomic(output/'progress-summary.json',summary)
        return summary
    finally:os.close(fd);lock.unlink()
