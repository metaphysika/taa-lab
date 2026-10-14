"""Owner-approved frozen Study C execution; original root, serial model boundaries.

The first72 always close for audit/evidence preservation. A passing block has
owner-authorized continuation; >=8 mechanical failures or any hard guard stops.
No paid interruption resume, output repair, settings change or Study D work.
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
from formation.clients import ReplyError
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
from scripts.formation_connectivity import journal_spend

FREEZE = 'studies/formation-study-c-freeze-v0239.json'
APPROVAL = 'studies/formation-study-c-execution-approval-v0239.json'
BINDING = 'studies/formation-study-c-adapter-binding-v0239.json'
HOLD = Path('/workspace/haiku55-runtime/study-b-maintenance.hold')
MODELS = ('claude-haiku-5-5', 'gemini-3.1-flash-lite', 'gemma-4-31b-it', 'gpt-6-luna')
CAPS = {'openai': 1.40, 'claude': 2.60, 'google': 2.85, 'gemma': 0}


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
    return Path(output) / (cell['cell_id'] + '-checkpoint.json')


def model_cap(freeze, model):
    return (freeze['OpenAI_evaluation_allowance'] if model == 'gpt-6-luna' else
            0 if model == 'gemma-4-31b-it' else freeze['provider_caps'][PROVIDERS[model]])


def ledger_check(root, freeze):
    expected = dict(freeze['ledger_start'])
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
    if str(root.resolve()) != f['root'] or tuple(f['models']) != MODELS or f['provider_caps'] != CAPS:
        raise ValueError('original checkout, model order or cap binding differs')
    if root == ROOT:
        if str(root.resolve()) != '/workspace/taa-lab': raise ValueError('original checkout only')
        check_b(root, approved=True)
    if not a['execution_authorized'] or a['freeze_sha256'] != sha(root/FREEZE) or a['caps'] != CAPS or a['models'] != f['models']:
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
    ledger_check(root, f)
    return f, a, cases, cells, seeds


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
        self.guard_journal();return super().before_attempt(body)

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
    """Preserve native countTokens request/reply evidence in addition to receipts."""
    def count(self, body):
        if len(json.dumps({'generateContentRequest':dict(body,model='models/gemma-4-31b-it')}).encode())>32000:
            raise BudgetStopped('metadata full-wire guard before HTTP; no history trimming')
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


def execute(case, cell, seeds, client, recorder, path):
    if path.exists(): raise BudgetStopped('existing checkpoint; no reexecution')
    packets = []; fatal = False; reason = None; lost = False; conversation = []
    for turn in range(12):
        conversation = seeded_history(case, cell, packets, seeds)
        recorder.context = dict(cell, turn=turn+1, stage='C frozen evaluation')
        recorder.last_reply = None; recorder.last_identity_valid = False
        atomic(path, dict(phase='inflight', cell=cell, packets=packets, turn=turn+1))
        issued = recorder.attempt_count
        try: packets.append(dict(kind='reply', raw=client.chat(SYSTEM, conversation)))
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
    atomic(path, dict(phase='complete', cell=cell, packets=packets, result=result))
    return result


def audit(root, output, manifest, cases, cells, seeds):
    """Closed evidence only: native identity/usage/first reply, wire, replay, quota."""
    events = journal(output/'calls.jsonl')
    def indexed(event):
        found = [e for e in events if e['event'] == event]; by = {e['id']:e for e in found}
        if len(found) != len(by): raise BudgetStopped('duplicate '+event)
        return by
    starts = indexed('attempt_start'); ends = indexed('attempt_end')
    wires = indexed('native_request'); natives = indexed('native_response'); logicals = indexed('logical_start')
    if set(starts) != set(ends) or set(wires) != set(starts): raise BudgetStopped('native attempt not closed')
    states = {}; allowed = {c['cell_id']:c for c in cells}; model = manifest['model']
    for path in output.glob('*-checkpoint.json'):
        if path.name == 'first-repeat-checkpoint.json':continue
        state = read(path)
        if state.get('phase') != 'complete': raise BudgetStopped('nonterminal/unknown checkpoint')
        row = state['result']; cid = row['cell_id']
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
        if any(ctx[k] != v for k,v in cell.items()) or ctx['stage'] != 'C frozen evaluation':
            raise BudgetStopped('logical/cell identity differs')
        logicals_by_cell[cid] += 1
        if ctx['turn'] < 1 or ctx['turn'] > len(state['packets']): raise BudgetStopped('logical turn differs')
        expected = dict(system=SYSTEM,messages=seeded_history(cases[cell['probe_id']],cell,state['packets'][:ctx['turn']-1],seeds))
        if json.loads(logical['prompt']) != expected: raise BudgetStopped('native prompt differs from seeded replay')
        attempts = [aid for aid,start in starts.items() if start['logical_id'] == lid]
        received = [natives[aid]['response'] for aid in attempts if aid in natives]
        if len(received) > 1: raise BudgetStopped('multiple received native replies')
        for aid in attempts:
            if wires[aid]['body'] != native.body(SYSTEM,expected['messages']) or len(json.dumps(wires[aid]['body']).encode()) > 32000:
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
    if model == 'gemma-4-31b-it':
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
        source = read(root/FREEZE)['Gemma_quota_source']
        original_q = read(root/source/'quota.json')
        if q['events'][:len(original_q['events'])] != original_q['events']:
            raise BudgetStopped('Gemma quota history reset/changed')
    expected = manifest['provider_start']+journal_spend(output/'calls.jsonl')
    if abs(read(root/('results/formation-spending-v021/'+PROVIDERS[model]+'.json'))['estimated_api_dollars']-expected) > 1e-12:
        raise BudgetStopped('model ledger/baseline/journal differs')
    if (output/'first-block-integrity.json').exists(): verify_first_block(output)
    return dict(rows_replayed=len(states), attempts_closed=len(ends), native_responses=len(natives),
                full_seeded_wire_first_native_identity_usage_replay='passed',
                model_accounted_dollars=journal_spend(output/'calls.jsonl'), provider_cumulative_dollars=expected,
                inherited_requests_needing_retry=manifest['retry_needed_start'],
                requests_needing_retry=retry['requests_needing_retry'], retry_jobs_closed=len(retry['jobs']),
                retained_uncertainty_reserves=sum(starts[e['id']]['reserved_dollars'] for e in ends.values() if e.get('reserve_retained')))


def checkpoint_report(rows):
    counts = Counter(r['score']['mechanical_outcome'] for r in rows if r['score']['mechanical_outcome'])
    return dict(episodes=len(rows), planned=72, mechanical_count=sum(counts.values()),
                mechanical_by_label={k:counts[k] for k in MECHANICAL},
                mechanical_rate_planned=sum(counts.values())/72,
                threshold_exceeded=sum(counts.values()) >= 8,
                may_continue=len(rows) == 72 and sum(counts.values()) <= 7 and not any(r['fatal'] for r in rows))


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


def run(model, approved=False, after_checkpoint=False, root=ROOT, now=time.time, sleep=time.sleep):
    root = Path(root); f,a,cases,cells,seeds = check(root,approved)
    if model not in MODELS: raise ValueError('unapproved model')
    output = root/f['outputs'][model]; lock = root/'results/formation-spending-v021/run.lock'
    if lock.exists() or HOLD.exists(): raise BudgetStopped('foreign/shared lock or hold; never clear')
    if provider_processes(): raise BudgetStopped('another provider runner; no concurrent C run')
    for prior in MODELS[:MODELS.index(model)]:
        prior_output = root/f['outputs'][prior]
        if not (prior_output/'completion-integrity.json').exists(): raise BudgetStopped('previous model not audited/snapshotted complete')
        if read(prior_output/'progress-summary.json')['primary_completed'] != 540 or read(prior_output/'controller-status.json')['state'] != 'complete':
            raise BudgetStopped('previous model incomplete')
        receipt = read(prior_output/'completion-report-receipt.json')
        if not receipt['reported_in_chat'] or receipt['summary_sha256'] != sha(prior_output/'progress-summary.json'):
            raise BudgetStopped('previous model completion not reported/bound')
    fixed = dict(root=str(root.resolve()), output=f['outputs'][model], model=model,
                 freeze_sha256=sha(root/FREEZE), approval_sha256=sha(root/APPROVAL),
                 adapter_sha256=sha(root/BINDING), cap=model_cap(f,model), settings=f['settings'])
    rows = []
    if output.exists():
        manifest = read(output/'execution-manifest.json')
        if any(manifest[k] != v for k,v in fixed.items()): raise BudgetStopped('manifest differs')
        if not after_checkpoint or read(output/'controller-status.json')['state'] != 'checkpoint_pending_report':
            raise BudgetStopped('no interrupted/stopped/complete/duplicate restart')
        if not (output/'checkpoint-report-receipt.json').exists() or not (output/'first-block-integrity.json').exists():
            raise BudgetStopped('closed first72 must be audited, reported and snapshotted before automatic continuation')
        report = read(output/'first-repeat-checkpoint.json')
        receipt = read(output/'checkpoint-report-receipt.json')
        if not report['may_continue'] or not receipt['reported_in_chat'] or receipt['checkpoint_sha256'] != sha(output/'first-repeat-checkpoint.json'):
            raise BudgetStopped('passing closed checkpoint audit/report binding absent')
        verify_first_block(output)
        rows = [read(checkpoint_path(output,c))['result'] for c in cells[:72]]
        terminal = audit(root,output,manifest,cases,cells,seeds)
        if terminal['rows_replayed'] != 72: raise BudgetStopped('first block boundary differs')
    else:
        if after_checkpoint: raise BudgetStopped('no first block to continue')
        manifest = dict(fixed,provider_start=read(root/('results/formation-spending-v021/'+PROVIDERS[model]+'.json'))['estimated_api_dollars'],
                        retry_needed_start=read(root/f['retry_sources'][model]/'transport-retry-state.json')['requests_needing_retry'])
    marker = json.dumps(dict(pid=os.getpid(),model=model,output=f['outputs'][model],runner='study_c_evaluation_v0239'))
    fd = os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    recorder = retry = quota = None
    def status(state,**kw):
        atomic(output/'controller-status.json',dict(state=state,pid=os.getpid(),model=model,at=now(),**kw))
    try:
        os.write(fd,marker.encode());os.fsync(fd);os.close(fd);fd = None
        if not output.exists():
            output.mkdir(exist_ok=False);atomic(output/'execution-manifest.json',manifest)
            source = root/f['retry_sources'][model]
            for name in ['transport-retry-state.json','transport-retry-journal.jsonl']:
                shutil.copyfile(source/name,output/name)
            if model == 'gemma-4-31b-it':
                source = root/f['Gemma_quota_source']
                for name in ['quota.json','token-count-receipts.jsonl','metadata-native-journal.jsonl']:
                    if (source/name).exists(): shutil.copyfile(source/name,output/name)
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
        client = CChat(recorder,retry,quota)
        status('running',completed=len(rows))
        pending = cells[72:] if after_checkpoint else cells[:72]
        for cell in pending:
            status('running',completed=len(rows),cell_id=cell['cell_id'])
            row = execute(cases[cell['probe_id']],cell,seeds,client,recorder,checkpoint_path(output,cell));rows.append(row)
            summary = dict(status='running',model=model,primary_completed=len(rows),planned=540,
                           model_dollars=recorder.spent-manifest['provider_start'],records=rows)
            atomic(output/'progress-summary.json',summary)
            print('%s %d/540 %s %s $%.9f' % (model,len(rows),cell['cell_id'],row['score']['substance_outcome'],summary['model_dollars']),flush=True)
            if row['fatal']: raise BudgetStopped('native/transport guard; no later episode/replacement')
        check(root,True);terminal = audit(root,output,manifest,cases,cells,seeds)
        summary['model_dollars']=terminal['model_accounted_dollars']
        summary.update(status='complete' if after_checkpoint else 'checkpoint_pending_report',audit=terminal,
                       substance_by_label=dict(Counter(r['score']['substance_outcome'] for r in rows)),
                       mechanical_by_label={k:sum(r['score']['mechanical_outcome'] == k for r in rows) for k in MECHANICAL})
        if not after_checkpoint:
            report = checkpoint_report(rows);report.update(audit=terminal,model_dollars=summary['model_dollars'])
            atomic(output/'first-repeat-checkpoint.json',report)
            if not report['may_continue']: summary['status'] = 'stopped_for_review'
        atomic(output/'terminal-audit.json',terminal);atomic(output/'progress-summary.json',summary)
        status(summary['status'],completed=len(rows));return summary
    except BaseException as e:
        if output.exists():
            status('stopped_for_review',completed=len(rows),reason=str(e) if isinstance(e,(BudgetStopped,ValueError,RetryExhausted,RetryRunLimit)) else type(e).__name__)
            atomic(output/'stop-evidence.json',dict(exception_class=type(e).__name__,
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
    if summary['primary_completed'] == 72 and state['state'] == 'checkpoint_pending_report':
        cp = {checkpoint_path(output,c).name:sha(checkpoint_path(output,c)) for c in cells[:72]}
        prefixes = {n:dict(bytes=(output/n).stat().st_size,sha256=sha(output/n))
                    for n in ['calls.jsonl','transport-retry-journal.jsonl','token-count-receipts.jsonl','metadata-native-journal.jsonl'] if (output/n).exists()}
        atomic(output/'first-block-integrity.json',dict(checkpoint_sha256=cp,journal_prefixes=prefixes))
        atomic(output/'checkpoint-report-receipt.json',dict(reported_in_chat=reported,
               checkpoint_sha256=sha(output/'first-repeat-checkpoint.json'),audit_sha256=sha(output/'boundary-audit.json'),
               no_further_owner_gate_required=True,owner_Gate6b_authorizes_passing_continuation=True,at=time.time()))
    elif state['state'] == 'complete':
        if summary['primary_completed'] != 540:raise BudgetStopped('complete model does not have540 cells')
        verify_first_block(output)
        atomic(output/'completion-report-receipt.json',dict(reported_in_chat=reported,at=time.time(),
               summary_sha256=sha(output/'progress-summary.json'),audit_sha256=sha(output/'boundary-audit.json')))
        atomic(output/'completion-integrity.json',dict(files_sha256={p.name:sha(p) for p in output.glob('*') if p.is_file() and p.name!='completion-integrity.json'}))
    return terminal
