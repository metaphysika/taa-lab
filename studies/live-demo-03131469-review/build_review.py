"""Offline results-only derivation. No model client, live driver or new episodes.

Reconstruct retained deltas; replay only recorded prefixes needed for six
adjudications. No expected answer is generated or frozen by this script.
"""
from pathlib import Path
from copy import deepcopy as cp
import argparse, hashlib, html, json, os, re, socket, sys, zipfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from replay.retained import apply, transitions
from replay.build import document, detail, esc
from live_demo.evidence import verify, encoded
from comparators import retained_actual, commit_oracle
from comparators.observed_world import view
from tests.trace_support import production_backend as core, mcp_backend as mcp
from taa_gateway_reference import refunds as ref
from conventional_gateway.policy import Policy


def jread(p):return json.loads(Path(p).read_bytes())
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,sort_keys=True,ensure_ascii=False)+'\n')
def packed(path, files):
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,blob in sorted(files.items()):
            info=zipfile.ZipInfo(name,(2026,10,25,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            z.writestr(info,blob,compresslevel=9)
    return {'sha256':sha(path.read_bytes()),'bytes':path.stat().st_size,'members':len(files)}

def rows(directory):return [(p.name,jread(p)) for p in sorted(directory.glob('[0-9]*.json'))]

def reconstruct(directory):
    rs=rows(directory);initial=rs[0][1]['value'];assert rs[0][1]['kind']=='initial_state'
    retained={'actual_initial':initial,'actual_transitions':[]};pre={};channels=cp(initial['channels']);log=cp(initial['event_log']);calls=[];step=0
    for name,r in rs:
        k,v=r['kind'],r['value']
        if k=='host_step':step=v['step'];t=v
        elif k in ('proposal','execution'):t=v['actual']
        else:continue
        if k=='proposal':
            pre[name]={**{k:cp(x['value']) for k,x in channels.items() if x['present']},'log':cp(log)}
            calls.append({'file':name,'step':step,'tool':v['tool'],'args':v['args'],'disposition':v['raw'].get('disposition'),'raw':v['raw'],'assessment':v['assessment']})
        retained['actual_transitions'].append(t)
        # Existing renderer validates before-values and presence markers.
        for key,d in t['actual_channels'].items():
            cur=channels.get(key,{'present':False})
            if 'before' in d and isinstance(d['before'],dict) and 'present' in d['before'] and set(d['before'])<={'present','value'}:
                assert cur==d['before'];channels[key]=cp(d['after'])
            else:channels[key]={'present':True,'value':apply(cur['value'],d)}
        log=apply(log,t['actual_event_log'])
    assert len(list(transitions(retained)))==len(retained['actual_transitions'])
    end=next(r['value'] for _,r in rs if r['kind']=='episode_end')
    return rs,pre,calls,end,channels,retained

def sql_snapshot(s):
    # Detached conventional-policy snapshot, not a conventional trajectory.
    # All business facts, version histories, current grant chains, notices,
    # allocations and independently reconstructed duties come from THIS state.
    result={'step':s['step'],'epoch':s['revision']}
    for key in ('records','grants','duties','allocations','orders','reports'):
        result[key]={k:cp(v) if key=='records' else [cp(v)] for k,v in s[key].items()}
    result['notices']={str(i):[cp(n['args'])] for i,n in enumerate(s['notices'])}
    result['cases']={k:[{'closed':v}] for k,v in s['cases'].items()}
    return result

def native_prefix(directory, program, targets):
    """Build native checkpoint via recorded inputs, comparing ALL retained channels/logs."""
    state=core.start(jread(ROOT/'live_demo/frozen/world.json'),program['setup'],defer_first_step=True)
    rs,pre,*_=reconstruct(directory);initial=rs[0][1]['value']
    assert retained_actual.initial(state)==initial,'initial mismatch'
    output={};last_handle=None;checked=0
    for name,r in rs:
        k,v=r['kind'],r['value']
        before=state
        if k=='host_step':
            state,_=core.enter_step(state,v['step'],v['inputs']['events']);wanted=v
        elif k=='proposal':
            if name in targets:
                assert retained_actual.initial(state)=={'channels':{k:retained_actual.value(pre[name],k) for k in retained_actual.CHANNELS},'event_log':pre[name]['log']}
                reference=ref.constraints(cp(v['assessment']['pre_commit_state']),'A',v['tool'],cp(v['args']))
                direct_state,direct=core.propose(cp(state),'A',v['tool'],cp(v['args']))
                wire_state,wire=mcp.propose(cp(state),'A',v['tool'],cp(v['args']))
                assert {k:x for k,x in direct.items() if k!='state_delta'}=={k:x for k,x in wire.items() if k!='state_delta'},'MCP/direct decision mismatch'
                assert retained_actual.initial(direct_state)['channels']==retained_actual.initial(wire_state)['channels'],'MCP/direct channel mismatch'
                # Also bind reference input to current retained actual view.
                actual_view=view(state);norm=v['assessment']['pre_commit_state']
                for key in ('world','records','grants','orders','cases'):
                    assert norm[key]==actual_view[key],('assessment business state mismatch',name,key)
                conventional=Policy(norm['world']).evaluate(sql_snapshot(norm),'A',v['tool'],cp(v['args']))
                output[name]={'reference':reference,'core':{k:val for k,val in direct.items() if k!='state_delta'},'mcp':{k:val for k,val in wire.items() if k!='state_delta'},'conventional':conventional,'business_state_equal':True,'native_pre_state_sha256':sha(encoded(state)),'retained_pre_state_sha256':sha(encoded(pre[name])),'reference_pre_state_sha256':sha(encoded(norm)),'native_pre_state':state,'retained_pre_state':pre[name]}
            state,raw=mcp.propose(state,'A',v['tool'],v['args']);last_handle=raw.get('token',raw.get('execution_intent'));wanted=v['actual']
            assert {k:x for k,x in raw.items() if k!='state_delta'}=={k:x for k,x in v['raw'].items() if k!='state_delta'},('proposal mismatch',name)
        elif k=='execution':
            state,raw=mcp.execute(state,'A',last_handle);wanted=v['actual']
            assert {k:x for k,x in raw.items() if k!='state_delta'}=={k:x for k,x in v['raw'].items() if k!='state_delta'},('execution mismatch',name)
        else:continue
        got=retained_actual.transition(before,state,wanted['phase'],wanted['inputs'])
        assert got==wanted,('transition mismatch',name)
        checked+=1
        if len(output)==len(targets):break
    assert len(output)==len(targets)
    return output,checked

def source_controller():
    p=ROOT/'docs/process/evidence/gateway-cross-arm-scoring-v02';v=jread(p/'validation.json');zpath=p/Path(v['archive']['path']).name
    assert sha(zpath.read_bytes())==v['archive']['sha256']
    selected=[]
    with zipfile.ZipFile(zpath) as z:
        assert sha(z.read('episodes.jsonl'))==v['archive']['files']['episodes.jsonl']
        for line in z.read('episodes.jsonl').splitlines():
            e=json.loads(line)
            if e['controller']!='correct' or e['arm'] not in ('floor','static','taa'):continue
            claim=jread(ROOT/'live_demo/frozen/programs.json')[e['case']]['brief']['claim']
            target=e['final_world']['records'][claim][-1]['fields']['claimant']
            ds={k:d for k,d in e['oracle_board'].items() if d['kind'] in ('refund','resolve') and e['final_world']['records'][d['claim']][-1]['fields']['claimant']==target}
            selected.append({'claim':'[Descriptive] Retained pre-live correct-controller result; not a new episode or a completeness proof.','program':e['case'],'arm':e['arm'],'last_step':max(t['step'] for t in e['actual_transitions']),'target_claimant_duties':ds,'frozen_lawful_completion_formula':bool(ds) and all(d['resolution']=='discharged' for d in ds.values()),'all_unresolved_duties':e['metrics']['unresolved_duties'],'committed_reference_policy':e['reference_policy_committed_acts'],'proposals':[{k:o[k] for k in ('actor','tool','args','result')} for o in e['observations'] if o['kind']=='proposal']})
    assert len(selected)==30
    return {'source_archive_sha256':v['archive']['sha256'],'source_journal_sha256':v['archive']['files']['episodes.jsonl'],'limitation':'Correct follows the independently authored key, including diagnostic attempts. It is not a general lawful-completion controller. Failure to finish its prescribed script does not prove infeasibility. Historical source includes trusted host events; it does not establish that an unbriefed model would know required arguments.','results':selected}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();out=a.out;out.mkdir(parents=True,exist_ok=True)
    socket.socket=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('offline audit: sockets denied'))
    scan=jread(out/'secret-scan.json');assert not scan['findings']
    files={}
    for name,h in scan['source_sha256'].items():
        b=(a.source/name).read_bytes();assert sha(b)==h;files['original/'+name]=b
    archives={'full-evidence.zip':packed(out/'full-evidence.zip',files)}
    for name in ('verification.json','RESULTS_FOR_REVIEW.md','over-refusals.json','results.json','accounting-observations.json','per-arm.csv','per-episode.csv'):
        (out/name).write_bytes((a.source/name).read_bytes())
    programs=jread(ROOT/'live_demo/frozen/programs.json');cases=[];pages={};summaries=[];turnlimits=[];checks={};diagnoses=[];page_contents={}
    for ep in sorted((a.source/'evidence').glob('episode-*')):
        checks[ep.name]=verify(ep)
        rs,pre,calls,end,channels,retained=reconstruct(ep);spec=end['spec'];program=spec['program'];arm=spec['arm']
        content='<p>[Descriptive] Retained live episode; external oracle is normative. No HMAC authentication is claimed. No policies are run by this page.</p>'+detail('[Descriptive] Episode result',end,True)+detail('[Descriptive] Initial actual channels and log',rs[0][1]['value'])
        # Retain exact proposals, assessment pre-states, execution checks and actual deltas.
        for name,r in rs:
            if r['kind'] in ('host_step','proposal','execution','tool_result','visible_result'):
                content+='<article class="row"><h3>[Descriptive] '+esc(name+' '+r['kind'])+'</h3>'+detail('[Descriptive] Exact retained payload',r['value'])+'</article>'
        content+=detail('[Descriptive] Reconstructed final actual channels',channels)
        page_contents[ep.name]=content
        pages[ep.name+'.html']=document('[Descriptive] '+ep.name+' '+program+' '+arm,content)
        summaries.append({'episode':ep.name,**spec,'stop':end['stop'],'calls':[{k:c[k] for k in ('file','step','tool','args','disposition')} for c in calls]})
        if arm=='taa' and end['stop']=='turn_limit':turnlimits.append(summaries[-1])
        for c in calls:
            if c['assessment']['disposition']=='PERMIT' and c['raw'].get('disposition')!='PERMIT':
                cases.append({'episode':ep.name,'program':program,'arm':arm,**c})
        # Diagnosis records ALL claimant duties, including unrelated same/other-claimant obligations, explicitly scoped.
        target=channels['records']['value'][programs[program]['brief']['claim']][-1]['fields']['claimant']
        duties=[]
        for did,d in end['metrics']['oracle_board'].items():
            if d['kind'] not in ('refund','resolve'):continue
            related=[c for c in calls if c['tool']!='read_record' and (c['args'].get('claim')==d['claim'] or c['args'].get('case')==d['claim'] or c['args'].get('duty')==did)]
            ds=[{'file':c['file'],'step':c['step'],'tool':c['tool'],'args':c['args'],'disposition':c['disposition']} for c in related]
            target_scope=channels['records']['value'][d['claim']][-1]['fields']['claimant']==target
            duties.append({'id':did,'kind':d['kind'],'claimant':d.get('claimant'),'claim':d['claim'],'target_claimant_in_frozen_completion':target_scope,'resolution':d['resolution'],'owner':d['owner'],'proof':d.get('coverage_proof',d.get('basis')),'duty':d,'last_relevant_attempt':ds[-1] if ds else None,'relevant_attempts':ds})
        diagnoses.append({'claim':'[Descriptive] Frozen final external duty board and exact attempted acts. Causes are separately labeled interpretive.','episode':ep.name,**spec,'stop':end['stop'],'turns':end['turns'],'lawful_completion':end['metrics']['lawful_completion'],'claimant_duties':duties})
    assert len(cases)==6 and len(turnlimits)==9
    checks['root']=verify(a.source/'evidence')
    mappings=[];adjudications=[];prefix_checks=0
    for epi in sorted(set(c['episode'] for c in cases)):
        subset=[c for c in cases if c['episode']==epi];replayed,n=native_prefix(a.source/'evidence'/epi,programs[subset[0]['program']],{c['file'] for c in subset});prefix_checks+=n
        for c in subset:
            local=sum(x['episode']==epi for x in mappings)+1;global_id=f"LD03131469-OR{len(mappings)+1:02}"
            original=f'{epi}-OR{local:02}'
            mappings.append({'run_unique_id':global_id,'original_report_case_id':original,'episode_local_label':f'OR{local:02}','episode':epi,'program':c['program'],'proposal_file':c['file'],'source_case_sha256':sha(encoded(jread(a.source/'over-refusals.json')[len(mappings)]))})
            payload={'claim':'[Descriptive] Exact recorded call and deterministic replay; rules/facts are INTERNAL REVIEW ONLY, never model-facing.','id':global_id,'source':mappings[-1], 'call':{k:c[k] for k in ('tool','args','step')},'stored_assessment':c['assessment'],'stored_core_result':c['raw'],'replay':replayed[c['file']]}
            write(out/'internal-adjudication'/f'{global_id}.json',payload)
            adjudications.append({'id':global_id,'episode':epi,'program':c['program'],'proposal':c['file'],'tool':c['tool'],'dispositions':{k:payload['replay'][k]['disposition'] for k in ('reference','core','mcp','conventional')},'business_state_equal':True})
    write(out/'case-id-mapping.json',{'claim':'[Descriptive] Non-destructive run-global aliases. Original JSON and evidence bytes unchanged. Original report already had episode-qualified IDs; short OR labels repeat across episodes.','mapping':mappings})
    write(out/'adjudication-summary.json',adjudications);write(out/'completion-facts.json',diagnoses);write(out/'taa-turn-limit-sequences.json',turnlimits)
    source=source_controller();write(out/'scripted-controller-results.json',source)
    by_program={p:[s for s in summaries if s['program']==p] for p in programs}
    for program,es in by_program.items():
        columns=''
        for arm in ('floor','static','taa'):
            e=next(x for x in es if x['arm']==arm)
            columns+='<section class="arm"><h2>[Descriptive] '+esc(arm)+' '+esc(e['episode'])+'</h2><a href="'+e['episode']+'.html">Full deterministic audit window</a>'+detail('[Descriptive] Exact tool sequence',e['calls'],True)+page_contents[e['episode']]+'</section>'
        pages[program+'.html']=document('[Descriptive] '+program+' side by side','<div class="columns">'+columns+'</div>')
    pages['index.html']=document('[Descriptive] Live demo 03131469 audit windows','<p>[Descriptive] 30 original episodes, grouped by program. Local assets only. The viewer executes no policy, oracle, tool or episode.</p><ul>'+''.join('<li><a href="'+p+'.html">'+p+' — floor / static / taa</a></li>' for p in programs)+'</ul>')
    pages['manifest.json']=(json.dumps({'claim':'[Descriptive] Deterministic derived pages; original evidence is unchanged.','files':{k:sha(v) for k,v in sorted(pages.items())}},indent=2)+'\n').encode()
    archives['audit-pages.zip']=packed(out/'audit-pages.zip',pages)
    write(out/'archive-hashes.json',archives)
    verification={'claim':'[Descriptive] Offline derivation checks only.','original_files_unchanged':len(files),'source_scan_findings':0,'chains':checks,'episodes':30,'pages':len(pages),'comparisons':10,'over_refusal_cases':6,'case_ids_unique':len(set(x['run_unique_id'] for x in mappings))==6,'native_reconstructed_transitions_equal_retained':prefix_checks,'exact_call_replays':24,'mcp_equals_direct':True,'reference_assessment_business_state_equals_retained':True,'network':'Sockets denied before replay; no adapter/respond/episode execution.','source_controller_records':30,'archives':archives}
    write(out/'offline-verification.json',verification)
    print(json.dumps({'adjudications':adjudications,'archives':archives,'native_prefix_transitions_checked':prefix_checks}))

if __name__=='__main__':main()
