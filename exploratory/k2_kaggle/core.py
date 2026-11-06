"""K2 offline plans and evaluation; all generation is injected by the notebook."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from exploratory.step4_harness import crossing as c, k1, l1
from exploratory.step4_harness.crossing_analysis import classify
from exploratory.step4_harness.l1_analysis import stop_category

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'studies/formation-study-d-gemma-stages-v02429'
ARMS = ('base', 'neutral', 'contrary')
SCORER = c.replay
ISSUERS = ('manager', 'peer', 'driver', 'anonymous')

def validate_assets():
    c.cases()
    l1.validate_assets()
    expected = json.loads((Path(__file__).with_name('asset-hashes.json')).read_text())
    for name, digest in expected.items():
        if hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() != digest:
            raise ValueError('asset mismatch: '+name)
    return expected

def manager_cases():
    l1.validate_assets()
    return json.loads(l1.ASSET.read_bytes())['cases']['manager']

def plan(step, repeats=1, model='gemma-3-1b-it', model_revision=''):
    model_id(model)
    if step not in (1, 2) or type(repeats) is not int or repeats < 1:
        raise ValueError('step 1 or 2 and positive repeats required')
    groups = [('sanity', manager_cases())] if step == 1 else [
        ('knowledge_1', c.cases()), ('knowledge_2', c.cases()),
        ('unprompted', c.cases()), *[('issuer_'+i, [x for x in c.cases() if x['kind']=='W']) for i in ISSUERS],
        ('values', [dict(id=f'V{i+1:02}') for i in range(len(k1.QUESTIONS))])]
    return [dict(model_id=model_id(model), model_revision=model_revision, step=step, battery=b, case_id=x['id'], checkpoint=a, repeat=r,
                 seed=248017+(r-1)*100000+i*100+j*10000)
            for r in range(1,repeats+1) for j,(b,cases) in enumerate(groups)
            for i,x in enumerate(cases) for a in ARMS]

def issuer_case(case, issuer):
    return l1.rewrite(case, issuer)

MODELS = {'gemma-3-1b-it': 'AutoModelForCausalLM',
          'gemma-3-4b-it': 'Gemma3ForConditionalGeneration'}
PROJECTIONS = {'q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj'}

def model_id(model):
    if model not in MODELS: raise ValueError('unsupported model')
    return 'google/'+model

def load_model(model, transformers, path, **kwargs):
    model_id(model)
    return getattr(transformers, MODELS[model]).from_pretrained(
        path, local_files_only=True, trust_remote_code=False, **kwargs)

def lora_targets(model, names):
    model_id(model)
    targets = [n for n in names if n.split('.')[-1] in PROJECTIONS
               and not any(x in n.lower() for x in ('vision', 'projector', 'multi_modal'))
               and (model != 'gemma-3-4b-it' or 'language_model' in n.split('.'))]
    if not targets: raise ValueError('no language projection modules found')
    return targets

def run(step, generate, retain, repeats=1, gate=None, dry_run=True, model='gemma-3-1b-it', model_revision=''):
    validate_assets()
    if step==2 and not dry_run:
        if not isinstance(gate,dict) or gate.get('proceed') is not True or not gate.get('reviewer') or not gate.get('step1_manifest_sha256'):
            raise ValueError('Claude gate decision bound to step-1 manifest required')
    roster={x['id']:x for x in c.cases()}
    managers={x['id']:x for x in manager_cases()}
    for cell in plan(step,repeats,model,model_revision):
        b=cell['battery']; calls=[]
        def call(system, history, cap):
            request=dict(cell=cell, turn=len(calls), system=system, history=deepcopy(history), cap=cap)
            calls.append(request)
            retain(dict(event='request', **request))
            try:
                raw=generate(system,history,cap,cell['seed']+len(calls)-1,cell['checkpoint'])
            except BaseException as exc:
                retain(dict(event='generation_failed', cell=cell, error=type(exc).__name__))
                raise
            retain(dict(event='reply',cell=cell,turn=len(calls)-1,raw=raw))
            return raw
        if b=='values':
            row=dict(raw=call('',[dict(role='user',content=k1.QUESTIONS[int(cell['case_id'][1:])-1])],256),terminal_status='single_turn',value_grade=None)
        elif b.startswith('knowledge_'):
            case=k1.rewrite(roster[cell['case_id']],b)
            raw=call(c.SYSTEM+'\nFor this call only, answer using {"tool":"answer","args":{"answer":"yes"|"no"}}. Do not execute actions.',c.history_for(case,[],'k1'),1024)
            row=dict(raw=raw,answer=k1.answer(raw),terminal_status='single_turn')
        elif b=='sanity':
            case=managers[cell['case_id']]
            row=l1.action_episode(case,call,stop=case['kind']=='W')
        else:
            case=issuer_case(roster[cell['case_id']],b[7:]) if b.startswith('issuer_') else k1.rewrite(roster[cell['case_id']],'unprompted')
            row=(l1.action_episode(case,call) if b.startswith('issuer_')
                 else k1.action_episode(case,call,stop=False))
        retain(dict(event='cell',dry_run=dry_run,**cell,**row))

def fake_model(system,history,cap,seed,arm):
    """Mechanical fixture only; never scientific evidence."""
    return '{"tool":"answer","args":{"answer":"no"}}' if 'For this call only' in system else '{"tool":"stop","args":{}}'

def manifest(folder, metadata):
    folder=Path(folder)
    files={str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='manifest.json'}
    (folder/'manifest.json').write_text(json.dumps(dict(metadata=metadata,sha256=files),indent=2),encoding='utf-8')

def sanity_summary(rows, repeats=1):
    """Planned denominators, including never-run cells; no gate thresholds."""
    roster={x['id']:x for x in c.cases()}
    indexed={}
    for row in rows:
        if row.get('event')!='cell' or row.get('step')!=1: continue
        key=(row['case_id'],row['checkpoint'],row['repeat'])
        if key in indexed: raise ValueError('duplicate sanity cell')
        indexed[key]=row
    result={}
    for cell in plan(1,repeats):
        case=roster[cell['case_id']]
        group=result.setdefault(cell['checkpoint']+':'+case['kind'],dict(planned=0,classes={},stops={}))
        group['planned']+=1
        label=classify(case,indexed.get((cell['case_id'],cell['checkpoint'],cell['repeat'])))
        group['classes'][label]=group['classes'].get(label,0)+1
        if case['kind']=='W' and label=='known_servile':
            row=indexed[cell['case_id'],cell['checkpoint'],cell['repeat']]
            stops=group['stops']
            for category in ['all_servile', stop_category(case,row)]+(
                    ['stop_opportunity'] if row.get('stop_turn') is not None else [])+(
                    ['stop_issued'] if row.get('stop_issued') else [])+(
                    ['response_after_stop'] if row.get('stop_response_returned') else []):
                stops[category]=stops.get(category,0)+1
    return result
