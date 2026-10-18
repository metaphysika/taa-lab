"""Offline audit of the owner-returned zip; no SDK, network, GPU or model loading."""
import collections
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EVIDENCE = HERE/'evidence/base-boundary-2'
COMMIT = '249a8d0c9bc25cec6c42573c6106a09017f550ff'
def saved(path):
    return json.loads(path.read_text())
def blob(path):
    return subprocess.check_output(['git', 'show', COMMIT+':'+path], cwd=ROOT)
def digest(data):
    return hashlib.sha256(data).hexdigest()
def require(ok, message):
    if not ok:
        raise ValueError(message)

assets = 'studies/formation-study-d-modal-v0249/'
manifest = json.loads(blob(assets+'integrity.json'))
plan = json.loads(blob(assets+'plan.json'))
bundle = json.loads(blob(assets+'bundle.json'))
for name, expected in manifest['sha256'].items():
    require(digest(blob(assets+name)) == expected, 'reviewed asset: '+name)
for name, text in bundle.items():
    require(digest(text.encode()) == plan['bundle_sha256'][name], 'frozen source: '+name)
for key, source in [('helpers.py','formation/study_d_modal_v0249.py'),
                    ('runtime.py','scripts/study_d_modal_runtime_v0249.py')]:
    require(digest(blob(source)) == manifest['remote_code_sha256'][key], 'runtime source: '+key)
# Import ONLY the frozen evaluator from the committed bundle into a clean process.
tmp = tempfile.TemporaryDirectory(prefix='study-d-offline-audit-')
for name, text in bundle.items():
    target = Path(tmp.name)/name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
sys.path.insert(0,tmp.name)
from formation.study_d_base_gate_v0248 import SYSTEM, evaluate_episode, summarize
from formation.study_b_replay_v0234 import replay
from formation.study_b_parser_v0234 import parse_action
spec = importlib.util.spec_from_file_location('reviewed_modal_helpers', ROOT/'formation/study_d_modal_v0249.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
require(digest((ROOT/'formation/study_d_modal_v0249.py').read_bytes()) == manifest['remote_code_sha256']['helpers.py'], 'local projection helper differs')
cases = {row['case']['id']:row['case'] for row in plan['cases']}
kinds = {k:v['kind'] for k,v in cases.items()}
for fixture in plan['fixture_keys']:
    require(replay(cases[fixture['case_id']], fixture['canonical_scripted_correct_packets'])['score']['substance_outcome'] == fixture['expected_original_label'], 'fixture key replay')
combined = saved(EVIDENCE/'base/report.json')
reservation = saved(EVIDENCE/'base-reservation.json')
require(reservation['budget'] == helper.budget_admit('base',0,2.45,30,True), 'reservation reconciliation')
require(COMMIT in reservation['approval_receipt'], 'approval commit')
require(reservation['prelaunch_audit_receipt'].endswith('failed build charge $0.00'), 'prior-build attestation')
out = dict(source_commit=COMMIT, status='PASS: offline evidence consistency; both format gates FAIL',
           fixture_keys_replayed=len(plan['fixture_keys']),models={},
           scientific_training_result=False, training_approved=False,
           billing=dict(displayed_cycle_usage_usd=1.70, provenance='owner screenshot; rounded display, not invoice export',
             base_reservation_usd=6.25, displayed_below_reservation_usd=4.55,
             displayed_percent_of_base_reservation=27.2, code_total_reserved_usd=25,
             reservation_refund=False, prior_failed_build_usd=0,
             prior_failed_build_provenance='saved owner prelaunch audit receipt, not independent invoice',
             per_model_invoice_usd=None, exact_total_invoice_usd=None,
             note='Screenshot app view says Total usage this cycle; scope and precise final allocation not proven. No per-model or build-cost split invented.'),
           limitations=['No live Modal/ledger/account inspection.',
             'Recorded token IDs/counts reconciled; no tokenizer/weights downloaded, so independent token-ID decoding and training-file retokenization not performed.',
             'Source hashes bind saved manifests; remote execution provenance is self-recorded, not a signed hardware attestation.',
             'Seeds and sampling reconstructed from committed code/config; RNG state not independently observed.',
             'Training runtimes are the preregistered 1x–4x decode-throughput proxy, not measured backpropagation.'])
for model_id in helper.MODELS:
    slug = model_id.split('/')[-1]
    folder = EVIDENCE/'base'/slug
    require(saved(folder/'asset-integrity.json') == manifest, 'remote manifest '+slug)
    require(saved(folder/'frozen-base-plan.json') == plan, 'remote plan '+slug)
    report = saved(folder/'report.json')
    require(report['status']=='COMPLETE', 'worker not complete')
    env=saved(folder/'environment.json')
    require(env['precision']=='bf16, no quantization', 'precision differs')
    require(env['packages']=={'torch':'2.6.0','transformers':'4.51.3','accelerate':'1.6.0','huggingface-hub':'0.30.2','safetensors':'0.5.3','peft':'0.15.2'}, 'package versions')
    load = saved(folder/(slug+'-load.json'))
    require(load['model']==model_id and load['revision']==report['revision']==combined['revisions'][model_id], 'identity/revision mismatch')
    events=[json.loads(line) for line in (folder/'events.jsonl').read_text().splitlines()]
    require(all(a['elapsed_seconds']<=b['elapsed_seconds'] for a,b in zip(events,events[1:])), 'event time order')
    starts=[e for e in events if e['event']=='generation_start']
    returns=[e for e in events if e['event']=='generation_return']
    require(len(starts)==len(returns)==len({e['request_id'] for e in starts}), 'unclosed/duplicate request')
    require([x['event'] for x in events]==['load_start']+['generation_start','generation_return']*len(starts)+['base_exit'], 'unexpected event lifecycle')
    require('A100' in events[0]['gpu'] and 38*1024**3<=events[0]['gpu_bytes']<=45*1024**3, 'GPU identity')
    require(events[-1]['training_jobs']==0, 'unexpected training')
    idx=0;rows=[];null_string=0;parse_errors=collections.Counter();cap_hits=0
    for cell in plan['schedule']:
        path=folder/f"{cell['case_id']}-r{cell['repeat']}.json"
        row=saved(path);case=cases[cell['case_id']]
        def generate(system,history,turn):
            global idx,null_string,cap_hits
            start=starts[idx];ret=returns[idx];idx+=1
            require(start['request_id']==ret['request_id']==f"{model_id}/{case['id']}/r{cell['repeat']}/t{turn}", 'schedule/request identity')
            require(start['messages']==[dict(role='system',content=system)]+history and system==SYSTEM, 'full-history wire differs')
            require(len(start['prompt_token_ids'])==ret['input_tokens'], 'input count')
            require(ret['input_tokens']+4096<=16384, 'context guard')
            require(len(json.dumps(start['messages'],ensure_ascii=False).encode())<=128000, 'wire guard')
            require(len(ret['output_token_ids'])==ret['output_tokens']<=4096, 'output count/cap')
            require(not ret['time_guard'] and ret['cuda_seconds']>0 and ret['wall_seconds']>0, 'generation guard/timing')
            require(ret['native_text_with_boundary_tokens'].startswith(ret['raw_text']), 'native/raw prefix')
            cap_hits+=ret['output_tokens']==4096
            try:
                act=parse_action(ret['raw_text'])
                null_string+=act.get('tool')=='null'
            except ValueError as exc:
                parse_errors[str(exc)]+=1
            return ret['raw_text']
        recomputed=evaluate_episode(case,generate);recomputed['repeat']=cell['repeat']
        require(recomputed==row, 'full replay/result mismatch: '+path.name)
        rows.append(recomputed)
    require(idx==len(starts), 'extra or missing generation')
    require(len(list(folder.glob('*-r?.json')))==34, 'unexpected row file count')
    summary=summarize(rows,list(cases),kinds)
    require(summary==report['summary']==combined['models'][model_id], 'summary mismatch')
    load_seconds=report['throughput_and_training_projection']['arms']['contrary']['load_barrier_storage_seconds']-540
    projection=helper.throughput_projection(returns,report['training_token_counts'],load_seconds)
    require(projection==report['throughput_and_training_projection']==combined['throughput_and_training_projection'][model_id], 'projection mismatch')
    by_kind={kind:dict(episodes=sum(kinds[r['case_id']]==kind for r in rows),
        labels=dict(collections.Counter(r['score']['substance_outcome'] for r in rows if kinds[r['case_id']]==kind)),
        correct=sum(r['score']['substantive_correct'] for r in rows if kinds[r['case_id']]==kind),
        observed_requirements_completed=sum(r['score']['observed_substantive_requirements_completed'] is True for r in rows if kinds[r['case_id']]==kind),
        mechanical=sum(r['score']['mechanical_outcome'] is not None for r in rows if kinds[r['case_id']]==kind),
        routine_completed=sum(r['score']['flags']['legitimate_routine_work_completed'] is True for r in rows if kinds[r['case_id']]==kind),
        executed_servile_episodes=sum(r['score']['executed_violations']['servile']>0 for r in rows if kinds[r['case_id']]==kind)) for kind in sorted(set(kinds.values()))}
    out['models'][model_id]=dict(summary=summary, projection=projection, revision=load['revision'],
        observed_requirements_completed=sum(r['score']['observed_substantive_requirements_completed'] is True for r in rows),
        substantive_labels=dict(collections.Counter(r['score']['substance_outcome'] for r in rows)),
        mechanical_labels=dict(collections.Counter(str(r['score']['mechanical_outcome']) for r in rows)),
        by_kind=by_kind, executed_servile_acts=sum(r['score']['executed_violations']['servile'] for r in rows),
        flags={k:sum(r['score']['flags'][k] is True for r in rows) for k in rows[0]['score']['flags']},
        flag_unknowns={k:sum(r['score']['flags'][k] is None for r in rows) for k in rows[0]['score']['flags']},
        terminal_labels=dict(collections.Counter(r['terminal_status'] for r in rows)),
        repeated_string_null_actions=null_string, parser_failure_labels=dict(parse_errors),
        generation_cap_hits=cap_hits, first_reply_raw_replay_and_full_wire='PASS',
        native_event_closure='PASS', software_wall_seconds=events[-1]['software_wall_seconds'],
        initial_setup_and_load_seconds=load_seconds, started_utc=env['started_utc'],
        training_token_counts=report['training_token_counts'],
        known_servile_trace_ids=[f"{r['case_id']}-r{r['repeat']}" for r in rows if r['score']['executed_violations']['servile']>0])
require(combined['status']=='COMPLETE' and combined['parallel_A100_containers']==2, 'controller closure')
(HERE/'audit-results.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({m:{'format':v['summary']['format_gate'],'headroom':v['summary']['headroom'],
    'labels':v['substantive_labels'],'by_kind':v['by_kind'],'null_strings':v['repeated_string_null_actions'],
    'cap_hits':v['generation_cap_hits']} for m,v in out['models'].items()},indent=2))
