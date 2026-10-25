"""Independent-process audit-page reproduction from retained evidence only.
No policy/agent/controller/episode is executed. Check all 42 output file hashes
and the byte-identical fixed-timestamp ZIP against the submitted archive.
"""
import argparse,importlib.util,json,sys,zipfile
from pathlib import Path
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('review_builder',P/'build_review.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 import socket
 socket.socket=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('offline renderer'))
 programs=m.jread(m.ROOT/'live_demo/frozen/programs.json');pages={};bodies={};summaries=[]
 for ep in sorted((a.source/'evidence').glob('episode-*')):
  rs,pre,calls,end,channels,retained=m.reconstruct(ep);spec=end['spec'];program=spec['program'];arm=spec['arm']
  content='<p>[Descriptive] Retained live episode; external oracle is normative. No HMAC authentication is claimed. No policies are run by this page.</p>'+m.detail('[Descriptive] Episode result',end,True)+m.detail('[Descriptive] Initial actual channels and log',rs[0][1]['value'])
  for name,r in rs:
   if r['kind'] in ('host_step','proposal','execution','tool_result','visible_result'):
    content+='<article class="row"><h3>[Descriptive] '+m.esc(name+' '+r['kind'])+'</h3>'+m.detail('[Descriptive] Exact retained payload',r['value'])+'</article>'
  content+=m.detail('[Descriptive] Reconstructed final actual channels',channels);bodies[ep.name]=content
  pages[ep.name+'.html']=m.document('[Descriptive] '+ep.name+' '+program+' '+arm,content)
  summaries.append({'episode':ep.name,**spec,'stop':end['stop'],'calls':[{k:c[k] for k in ('file','step','tool','args','disposition')} for c in calls]})
 for program in programs:
  columns=''
  for arm in ('floor','static','taa'):
   e=next(x for x in summaries if x['program']==program and x['arm']==arm)
   columns+='<section class="arm"><h2>[Descriptive] '+m.esc(arm)+' '+m.esc(e['episode'])+'</h2><a href="'+e['episode']+'.html">Full deterministic audit window</a>'+m.detail('[Descriptive] Exact tool sequence',e['calls'],True)+bodies[e['episode']]+'</section>'
  pages[program+'.html']=m.document('[Descriptive] '+program+' side by side','<div class="columns">'+columns+'</div>')
 pages['index.html']=m.document('[Descriptive] Live demo 03131469 audit windows','<p>[Descriptive] 30 original episodes, grouped by program. Local assets only. The viewer executes no policy, oracle, tool or episode.</p><ul>'+''.join('<li><a href="'+p+'.html">'+p+' — floor / static / taa</a></li>' for p in programs)+'</ul>')
 pages['manifest.json']=(json.dumps({'claim':'[Descriptive] Deterministic derived pages; original evidence is unchanged.','files':{k:m.sha(v) for k,v in sorted(pages.items())}},indent=2)+'\n').encode()
 with zipfile.ZipFile(P/'audit-pages.zip') as z:
  assert set(pages)==set(z.namelist())
  for n,b in pages.items():assert m.sha(b)==m.sha(z.read(n)),n
 archive=m.packed(a.output,pages);expected=m.jread(P/'archive-hashes.json')['audit-pages.zip'];assert archive==expected
 report={'claim':'[Descriptive] Separate-process retained-only reproduction; no policy/episode execution.','all_42_files_byte_identical':True,'archive_byte_identical':True,'archive':archive,'hash_seed':'71'}
 m.write(P/'validation/page-reproduction.json',report);print(json.dumps(report))
if __name__=='__main__':main()
