"""Build offline pages without running an episode, policy, model or oracle.

Historical v0.1 journals expose selected observations; v0.2 also retains actual
state changes and projected event rows. Missing channels remain explicit.
Oracle obligations never become deliveries.
"""
import argparse
from collections import defaultdict
import hashlib
import html
import json
from itertools import groupby
from pathlib import Path
import re
import zipfile

VERSION = '0.2.0'
GAPS = ('Complete native token status history was not retained in the scored journal.',
        'Complete native duty/report/correction events were not retained; external oracle histories are labeled separately.')
CSS = '''body{margin:0;background:#eef1f5;color:#17212e;font:16px system-ui,sans-serif}header,main{padding:1.5rem;max-width:1600px;margin:auto}h1{font-size:1.8rem}h2{font-size:1.2rem}a{color:#164f93}nav,label{margin-right:1rem}.notice{border-left:5px solid #b16b14;background:#fff4db;padding:1rem}.columns{display:flex;gap:1rem;align-items:flex-start;overflow:auto}.arm{min-width:390px;flex:1;background:white;padding:1rem;border:1px solid #c9d1dc}.row{border-top:3px solid #6383a6;margin-top:1rem;padding-top:.5rem}pre{font:12px ui-monospace,monospace;white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f6f9;padding:.7rem}summary{cursor:pointer;padding:.4rem}small,.muted{color:#4a596b}table{border-collapse:collapse}td,th{border:1px solid #ccd;padding:.4rem;text-align:left}.tag{font-size:.85rem;background:#dfebf7;padding:.2rem .4rem}button,select{font:inherit;padding:.3rem}input{margin-right:.4rem} [hidden]{display:none!important}'''
JS = '''document.querySelectorAll('input[data-arm]').forEach(function(box){box.addEventListener('change',function(){document.querySelectorAll('[data-column]').forEach(function(col){if(col.dataset.column===box.dataset.arm)col.hidden=!box.checked;});});});document.querySelectorAll('[data-step-filter]').forEach(function(s){s.addEventListener('change',function(){document.querySelectorAll('[data-step]').forEach(function(row){row.hidden=s.value!=='all'&&row.dataset.step!==s.value;});});});'''


def canonical(v):
    return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def sha(blob): return hashlib.sha256(blob).hexdigest()
def esc(v): return html.escape(str(v), quote=True)
def detail(title, value, opened=False):
    return '<details'+(' open' if opened else '')+'><summary>'+esc(title)+'</summary><pre>'+esc(json.dumps(value,sort_keys=True,indent=2,allow_nan=False))+'</pre></details>'


def document(title, content):
    import base64
    hashes=[base64.b64encode(hashlib.sha256(s.encode()).digest()).decode() for s in (CSS,JS)]
    csp="default-src 'none'; style-src 'sha256-"+hashes[0]+"'; script-src 'sha256-"+hashes[1]+"'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="'+esc(csp)+'"><title>'+esc(title)+'</title><style>'+CSS+'</style><header><a href="index.html">TAA retained-log audit</a><h1>'+esc(title)+'</h1><p>Offline development evidence · renderer '+VERSION+' · no policies or episodes are executed</p></header><main>'+content+'</main><script>'+JS+'</script></html>\n').encode()


def read_evidence(validation_path):
    validation_path=Path(validation_path)
    v=json.loads(validation_path.read_text())
    archive=validation_path.parent/Path(v['archive']['path']).name
    if sha(archive.read_bytes())!=v['archive']['sha256']:raise ValueError('archive checksum mismatch')
    with zipfile.ZipFile(archive) as z:
        for name,digest in v['archive']['files'].items():
            if sha(z.read(name))!=digest:raise ValueError('archive member checksum mismatch: '+name)
        manifest=json.loads(z.read('manifest.json'))
        episodes=[json.loads(line) for line in z.read('episodes.jsonl').splitlines()]
    identities={(e['case'],e['arm'],e['controller']) for e in episodes}
    if len(episodes)!=320 or len(identities)!=320:raise ValueError('expected complete 320-episode journal')
    expected={(c,a,k) for c in manifest['programs'] for a in manifest['arms'] for k in manifest['controllers']}
    if identities!=expected:raise ValueError('episode grid mismatch')
    return episodes,manifest,v['archive']['sha256']


def schedules(root, manifest):
    """Decode hash-pinned INPUT schedules, not outcomes. Never run a backend.

    These supplementary inputs were not serialized into episodes.jsonl. Refuse
    to use changed sources rather than silently substitute another schedule.
    """
    for name,digest in manifest['source_sha256'].items():
        if name.startswith(('agents/refunds/','worlds/refunds/','tests/expected_traces/','tests/trace_support/bundle.py')):
            if sha((Path(root)/name).read_bytes())!=digest:raise ValueError('input schedule source changed: '+name)
    from agents.refunds import CONTROLLERS
    from worlds.refunds.catalog import catalog,inputs_only
    from worlds.refunds.token_bindings import prepare
    result={}
    for case in catalog():
        source,_=prepare(case)
        for name in manifest['controllers']:
            program=CONTROLLERS[name]().program(source if name=='correct' else inputs_only(source))
            result[case['id'],name]=inputs_only(program)['trace']['steps']
    return result


def timeline(episode, schedule):
    actions=[];inputs=[]
    for step,group in groupby(enumerate(schedule),key=lambda x:x[1]['step']):
        entries=list(group)
        for index,entry in entries:
            if entry.get('events'):inputs.append(dict(entry_index=index,step=step,events=entry['events'],provenance='Hash-pinned input schedule; event outcomes not retained here.'))
        for kind in ('propose','execute'):
            for index,entry in entries:
                if kind in entry:actions.append((index,step,kind,entry[kind]))
    if len(actions)!=len(episode['observations']):raise ValueError('schedule/observation length mismatch')
    rows=[]
    for number,((index,step,kind,request),o) in enumerate(zip(actions,episode['observations'])):
        if kind!=('propose' if o['kind']=='proposal' else 'execute') or request['actor']!=o['actor']:raise ValueError('schedule/observation identity mismatch')
        if kind=='propose' and (request['tool']!=o['tool'] or request['args']!=o['args']):raise ValueError('proposal input mismatch')
        pre=o.get('supplementary_assessment')
        if pre and pre['pre_commit_state']['step']!=step:raise ValueError('retained actual pre-state step differs from schedule')
        rows.append(dict(index=number,entry_index=index,step=step,observation=o))
    return rows,inputs


def duty_table(duties):
    fields=('id','claimant','owner','resolution','due','overdue','recipient')
    rows=['<table><tr>'+''.join('<th>'+esc(k)+'</th>' for k in fields)+'</tr>']
    for did,d in sorted(duties.items()):
        rows.append('<tr>'+''.join('<td>'+esc(d.get(k,'not retained') if k!='id' else did)+'</td>' for k in fields)+'</tr>')
    return ''.join(rows)+'</table>'


def oracle_history(duties):
    rows=[]
    for did,d in sorted(duties.items()):
        for i,event in enumerate(d.get('history',[])):
            match=re.search(r'@(\d+)$',event) if isinstance(event,str) else None
            rows.append((int(match[1]) if match else -1,did,i,event))
    return [dict(step=step if step>=0 else 'not retained',duty=did,transition=event) for step,did,i,event in sorted(rows)]


def historical_column(episode,schedule):
    rows,inputs=timeline(episode,schedule)
    arm=episode['arm'];parts=['<section class="arm" data-column="'+esc(arm)+'"><h2>'+esc({'conventional':'independently implemented conventional arm','tracegrant':'TraceGrant reconstruction with fixed W0 contracts and documented adaptations'}.get(arm,arm))+'</h2>']
    parts.append('<p class="notice">Incomplete historical event coverage. No native token state or physical report delivery is inferred from an oracle obligation.</p>')
    parts.append(detail('Retained protocol metrics (keyed metrics are conditional)',episode['metrics']))
    parts.append(detail('Committed acts disallowed by the reference policy — post-v0 development only',episode.get('reference_policy_committed_acts',episode.get('supplementary_harm'))))
    parts.append(detail('Input events and scheduled clock steps (not observed outcomes)',inputs))
    for row in rows:
        o=row['observation'];r=o['result'];withheld=o['kind']=='proposal' and o['withheld'];prefix=episode['case']+'-'+episode['controller']+'-'+arm+'-'+str(row['index'])
        parts+=['<article class="row" data-step="'+str(row['step'])+'" id="'+esc(prefix)+'"><span class="tag">scheduled step '+str(row['step'])+' · observation '+str(row['index'])+'</span><h3>'+esc(('agent withheld request — gateway not called' if withheld else o['kind'])+' · '+str(o['tool']))+'</h3>',
            detail('Agent input / proposal origin',dict(actor=o['actor'],tool=o['tool'],arguments=o['args'],origin_key=o['key'],program_entry=row['entry_index']),True)]
        if 'checks' in r:parts.append(detail('Gateway checks: rules, record versions, facts and dispositions',r['checks'],True))
        parts.append(detail('Retained agent-withholding result' if withheld else 'Returned gateway decision / execution result (retained; state audits below)',r))
        parts.append(detail('Observed committed record effects',dict(receipted_commit=o['committed'],effects=o['effects']),bool(o['effects'])))
        if withheld:
            parts.append('<p>Agent withheld this request; the gateway was not called and no token was issued.</p>')
        elif o['kind']=='proposal':
            parts.append(detail('Token issuance summary (returned fields; full native lifecycle not retained)',{k:r[k] for k in ('token','token_expires_at','executable','state_revision') if k in r}))
        else:
            parts.append('<p class="muted">Token consumption/voiding state history: not retained in this journal. Execution outcome above is a returned summary, not a reconstructed token ledger.</p>')
        if o.get('supplementary_assessment'):
            pre=o['supplementary_assessment']
            parts.append('<h4>External oracle duty board at retained pre-commit snapshot</h4>'+duty_table(pre['pre_commit_state']['duties']))
            parts.append(detail('Independent oracle at actual pre-commit state — not the arm’s internal duty ledger',pre))
        parts.append(detail('Frozen source-key assessment / context', {k:o[k] for k in ('semantic_label','label_source','context','v0_context')}))
        parts.append('</article>')
    parts.append(detail('Final actual world: records and retained versions, grants, notices and cases',episode['final_world']))
    parts.append('<h3>Final external oracle duty board</h3>'+duty_table(episode['oracle_board']))
    parts.append(detail('Chronological external oracle transitions — not physical dispatches or historical owner reconstruction',oracle_history(episode['oracle_board']),True))
    parts.append(detail('External oracle duty / report histories — normative obligations, NOT dispatch artifacts',episode['oracle_board'],True))
    parts.append('<p>Actual report-delivery aggregate retained: <strong>'+str(episode['metrics']['reports_delivered'])+'</strong>. Per-delivery native envelopes and recipients were not retained in the scored journal.</p>')
    parts.append(detail('Common state audits',episode['assertions']))
    parts.append('</section>')
    return ''.join(parts)


def column(episode,schedule):
    if ('actual_initial' in episode)!=('actual_transitions' in episode):raise ValueError('incomplete retained-state channels')
    if 'actual_initial' in episode:
        from replay.retained import render
        actions=[t for t in episode['actual_transitions'] if t['phase'] in ('proposal','agent_withholding','execution')]
        if len(actions)!=len(episode['observations']):raise ValueError('actual action count mismatch')
        rows=[dict(index=i,step=t['step'],observation=o) for i,(t,o) in enumerate(zip(actions,episode['observations']))]
        return render(episode,rows,detail,esc,duty_table)
    return historical_column(episode,schedule)


def filename(*parts):
    if not all(re.fullmatch(r'[A-Za-z0-9_-]+',p) for p in parts):raise ValueError('unsafe episode identity')
    return '--'.join(parts)+'.html'


def build(episodes,manifest,archive_hash,input_schedules):
    files={};groups=defaultdict(list)
    for e in sorted(episodes,key=lambda e:(e['case'],e['controller'],e['arm'])):
        groups[e['case'],e['controller']].append(e)
        title=e['case']+' · '+e['controller']+' · '+e['arm']
        files[filename(e['case'],e['controller'],e['arm'])]=document(title,column(e,None if 'actual_initial' in e else input_schedules[e['case'],e['controller']]))
    retained=all('actual_initial' in e and 'actual_transitions' in e for e in episodes)
    index=['<p class="notice">Keyed metrics apply only while context matches the ordinary core. Early-diverging floor/static actions can go unassessed; this is not safety evidence. Keyed counts must not be presented as a TAA advantage over the independently implemented conventional arm. The TraceGrant reconstruction with fixed W0 contracts and documented adaptations covers only ten development programs. Supplementary measures were defined after v0; development only; pre-register before Experiment A.</p>',
        '<p>Source archive SHA-256: <code>'+esc(archive_hash)+'</code>. '+('Actual state channels and event additions are retained; native HMAC/end-checkpoint authentication is not verified.' if retained else 'Complete native histories are unavailable in these historical pages.')+' Open a comparison, then select arms; each episode also has its own page.</p><ul>']
    for (case,controller),group in sorted(groups.items()):
        by_arm={e['arm']:e for e in group};ordered=[by_arm[a] for a in manifest['arms']]
        controls='<nav>'+''.join('<label><input type="checkbox" data-arm="'+esc(a)+'" checked>'+esc(a)+'</label>' for a in manifest['arms'])+'</nav>'
        step_options='<label>'+('Observed step' if retained else 'Scheduled step')+' <select data-step-filter><option value="all">All</option>'+''.join('<option>'+str(step)+'</option>' for step in (sorted({t['step'] for e in group for t in e.get('actual_transitions',[])}) if retained else sorted({r['step'] for r in input_schedules[case,controller]})))+'</select></label>'
        content=step_options+controls+'<div class="columns">'+''.join(column(e,None if 'actual_initial' in e else input_schedules[case,controller]) for e in ordered)+'</div>'
        name=filename(case,controller)
        files[name]=document(case+' · '+controller+' · side-by-side arms',content)
        links=' '.join('<a href="'+filename(case,controller,a)+'">'+esc(a)+'</a>' for a in manifest['arms'])
        index.append('<li><a href="'+name+'">'+esc(case+' / '+controller)+' comparison</a> · '+links+'</li>')
    index.append('</ul>')
    files['index.html']=document('Retained scoring replay / audit window',''.join(index))
    proof=dict(renderer_version=VERSION,source_archive_sha256=archive_hash,episodes=len(episodes),
               episode_pages=len(episodes),comparison_pages=len(groups),retained_state_episodes=sum('actual_initial' in e for e in episodes),coverage_gaps=[] if retained else list(GAPS),authentication_limits=['No HMAC authentication or independent native ending checkpoint is verified.'],
               files={name:sha(blob) for name,blob in sorted(files.items())})
    files['MANIFEST.json']=canonical(proof)+b'\n'
    return files,proof


def native_document(blob,trusted_checkpoint):
    """Render full native events with chain/count validation, not HMAC authentication.

    Caller supplies an independently retained checkpoint. No authentication key
    is read; self-consistency is not proof of event truth or host integrity.
    """
    if not blob.endswith(b'\n'):raise ValueError('incomplete JSONL')
    rows=[json.loads(line) for line in blob.splitlines()]
    if any(canonical(row)!=line for row,line in zip(rows,blob.splitlines())):raise ValueError('noncanonical or ambiguous event JSON')
    checkpoint=rows.pop()
    if checkpoint!=trusted_checkpoint or checkpoint['event_count']!=len(rows):raise ValueError('checkpoint/count mismatch')
    prior='0'*64
    for i,row in enumerate(rows):
        if row['sequence']!=i or row['previous_hash']!=prior:raise ValueError('event sequence mismatch')
        if sha(canonical({k:v for k,v in row.items() if k!='hash'}))!=row['hash']:raise ValueError('event hash mismatch')
        prior=row['hash']
    if prior!=checkpoint['head_hash']:raise ValueError('checkpoint head mismatch')
    content='<p class="notice">Full retained native events. Hash chain and supplied checkpoint agree; the HMAC authentication tag has not been verified. No keys are included.</p>'
    content+=''.join('<article class="row"><h2>Step '+esc(e['step'])+' · '+esc(e['type'])+'</h2>'+detail('Actual retained event payload',e['payload'],True)+'</article>' for e in rows)
    return document('Native gateway event replay',content)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group(required=True);group.add_argument('--validation',type=Path);group.add_argument('--native-log',type=Path)
    p.add_argument('--trusted-checkpoint',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(argv);root=Path(__file__).resolve().parents[1]
    if a.native_log:
        if not a.trusted_checkpoint:p.error('--native-log requires an independently retained --trusted-checkpoint')
        blob=a.native_log.read_bytes();files={'index.html':native_document(blob,json.loads(a.trusted_checkpoint.read_text()))}
        proof=dict(renderer_version=VERSION,source_log_sha256=sha(blob),files={'index.html':sha(files['index.html'])},hmac_verified=False)
        files['MANIFEST.json']=canonical(proof)+b'\n'
    else:
        episodes,manifest,digest=read_evidence(a.validation)
        files,proof=build(episodes,manifest,digest,{} if all('actual_initial' in e for e in episodes) else schedules(root,manifest))
    a.output.mkdir(parents=True,exist_ok=False)
    for name,blob in sorted(files.items()):(a.output/name).write_bytes(blob)
    print(json.dumps({k:v for k,v in proof.items() if k!='files'},sort_keys=True))

if __name__=='__main__':main()
