"""Artifact integrity, completeness, escape and corruption checks; no policy calls."""
import hashlib, importlib.util, json, os, pathlib, re, sys, tempfile, zipfile
P=pathlib.Path(__file__).resolve().parent
ROOT=P.parents[1]
sys.path.insert(0,str(ROOT))
from live_demo.evidence import verify, encoded
from replay.retained import apply
from replay.build import detail

def digest(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_bytes())

def main():
 checks={};scan=load(P/'secret-scan.json');archives=load(P/'archive-hashes.json')
 for name,meta in archives.items():
  b=(P/name).read_bytes();assert digest(b)==meta['sha256'];checks[name+' checksum']=True
  with zipfile.ZipFile(P/name) as z:assert z.testzip() is None
 with zipfile.ZipFile(P/'full-evidence.zip') as z:
  assert len(z.namelist())==len(scan['source_sha256'])==3724
  for name,h in scan['source_sha256'].items():assert digest(z.read('original/'+name))==h
  checks['all 3724 archived original bytes preserved']=True
  # Verify hash-linked streams from archived bytes without extracting.
  dirs=['original/evidence']+['original/evidence/episode-%02d'%i for i in range(30)]
  for d in dirs:
   cp= json.loads(z.read(d+'/checkpoint.json'));head='0'*64
   for index in range(cp['count']):
    b=z.read(d+'/%06d.json'%index);r=json.loads(b)
    assert r['sequence']==index and r['previous']==head and b==encoded(r)+b'\n';head=digest(b)
   assert cp['head']==head
  checks['31 archived evidence chains and endpoints']=True
  seq=load(P/'taa-turn-limit-sequences.json')
  for e in seq:
   d='original/evidence/'+e['episode'];cp=json.loads(z.read(d+'/checkpoint.json'));rows=[json.loads(z.read(d+'/%06d.json'%i)) for i in range(cp['count'])]
   tools=[r['value'] for r in rows if r['kind']=='tool_result']
   assert len(tools)==len(e['calls']) and len(tools)>=12
   assert max(c['step'] for c in e['calls'])==12
   for t,c in zip(tools,e['calls']):
    assert t['name']==c['tool']
    assert t['result']['status']==('completed' if c['disposition']=='PERMIT' else 'refused')
    if c['disposition']!='PERMIT':assert t['result']['disposition']==c['disposition']
  checks['all TAA terminal-episode tool results match sequences']=sum(len(e['calls']) for e in seq)
  # Each diagnosis must bind all and only actual final claimant duties and
  # exact source attempts, including conflicting claim/case arguments.
  for episode in load(P/'completion-facts.json'):
   directory='original/evidence/'+episode['episode'];checkpoint=json.loads(z.read(directory+'/checkpoint.json'))
   source_rows=[json.loads(z.read(directory+'/%06d.json'%i)) for i in range(checkpoint['count'])]
   ending=next(row['value'] for row in source_rows if row['kind']=='episode_end')
   board={k:v for k,v in ending['metrics']['oracle_board'].items() if v['kind'] in ('refund','resolve')}
   assert set(board)=={d['id'] for d in episode['claimant_duties']}
   calls=[]
   for index,row in enumerate(source_rows):
    if row['kind']=='proposal':
     value=row['value'];calls.append({'file':'%06d.json'%index,'step':value['actual']['step'],'tool':value['tool'],'args':value['args'],'disposition':value['raw'].get('disposition')})
   assert episode['last_observed_tool_call']==(calls[-1] if calls else None)
   assert episode['lawful_completion']==ending['metrics']['lawful_completion']
   for duty in episode['claimant_duties']:
    assert duty['duty']==board[duty['id']]
    relevant=[call for call in calls if call['tool']!='read_record' and (call['args'].get('claim')==duty['claim'] or call['args'].get('case')==duty['claim'] or call['args'].get('duty')==duty['id'])]
    assert duty['relevant_attempts']==relevant and duty['last_relevant_attempt']==(relevant[-1] if relevant else None)
  checks['all 30 final duty sets and last attempts bind original rows']=True
  # Negative controls use temporary copies only, never original evidence.
  with tempfile.TemporaryDirectory() as tmp:
   ep=pathlib.Path(tmp)/'episode';ep.mkdir();d='original/evidence/episode-00';cp=json.loads(z.read(d+'/checkpoint.json'))
   for i in range(cp['count']):(ep/('%06d.json'%i)).write_bytes(z.read(d+'/%06d.json'%i))
   (ep/'checkpoint.json').write_bytes(z.read(d+'/checkpoint.json'));verify(ep)
   first=ep/'000000.json';original=first.read_bytes();r=json.loads(original);r['value']['tamper']=True;first.write_bytes(encoded(r)+b'\n')
   try:verify(ep)
   except ValueError:pass
   else:raise AssertionError('edit not detected')
   first.write_bytes(original);last=ep/('%06d.json'%(cp['count']-1));last.unlink()
   try:verify(ep)
   except ValueError:pass
   else:raise AssertionError('truncation not detected')
  checks['edit and truncation negative controls']=True
 with zipfile.ZipFile(P/'audit-pages.zip') as z:
  m=json.loads(z.read('manifest.json'));assert len(z.namelist())==42
  assert {n for n in z.namelist() if n.endswith('.html')}=={'index.html'}|{'T%02d.html'%i for i in range(1,11)}|{'episode-%02d.html'%i for i in range(30)}
  for name,h in m['files'].items():assert digest(z.read(name))==h
  # Every comparison embeds exactly three FULL individual audit bodies.
  for program in range(1,11):
   b=z.read('T%02d.html'%program).decode();assert b.count('<section class="arm">')==3
   episode_links=re.findall(r'href="(episode-\d\d.html)"',b);assert len(episode_links)==3
   for link in episode_links:
    page=z.read(link).decode();body=page.split('<main>',1)[1].split('</main>',1)[0]
    assert body in b
  checks['30 individual and 10 complete side-by-side audit pages']=True
 checks['HTML escapes injected content']= '&lt;script&gt;' in detail('test','<script>alert(1)</script>') and '<script>' not in detail('test','<script>alert(1)</script>')
 try:apply({'a':1},{'entries':{'a':{'before':{'present':True,'value':2},'after':{'present':True,'value':3}}}})
 except ValueError:checks['wrong delta before-value negative control']=True
 else:raise AssertionError('before-value guard absent')
 mapping=load(P/'case-id-mapping.json')['mapping'];assert len({x['run_unique_id'] for x in mapping})==6
 for x,original in zip(mapping,load(P/'over-refusals.json')):
  assert original['case']==x['original_report_case_id'] and original['episode']==x['episode'];assert digest(encoded(original))==x['source_case_sha256']
 checks['six unique aliases bind unchanged original cases']=True
 assert len(load(P/'completion-facts.json'))==30 and len(load(P/'completion-interpretations.json'))==30
 assert len(load(P/'scripted-controller-results.json')['results'])==30
 checks['30 completion diagnoses and 30 controller citations']=True
 for f in (P/'internal-adjudication').glob('*.json'):
  x=load(f);r=x['replay'];assert digest(encoded(r['native_pre_state']))==r['native_pre_state_sha256'];assert digest(encoded(r['retained_pre_state']))==r['retained_pre_state_sha256'];assert r['core']['disposition']==r['mcp']['disposition']
 checks['six internal exact-state replay records intact']=True
 native=load(P/'native-conventional-replays.json');assert len(native)==6
 for r in native:assert r['all_hydrated_relations_equal'] and r['result']['disposition']==load(P/'internal-adjudication'/(r['id']+'.json'))['replay']['conventional']['disposition']
 checks['six native SQL proposals match detached conventional policy']=True
 # Scan final derived files AND every archive member; report no secret content.
 patterns=[rb'\b(?:sk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{25,}|gh[pousr]_[A-Za-z0-9]{20,})',rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',rb'(?i)authorization[\x22\x27\s:]+bearer\s+[A-Za-z0-9._-]{10,}']
 secrets=[os.environ[k].encode() for k in os.environ if any(w in k for w in ('API_KEY','TOKEN_SECRET','ACCESS_TOKEN')) and os.environ[k]]
 count=0
 def safe(b):
  nonlocal count
  assert not any(re.search(p,b) for p in patterns),'credential pattern found (content withheld)'
  assert not any(s in b for s in secrets),'configured secret found (content withheld)'
  count+=1
 for f in sorted(P.rglob('*')):
  if not f.is_file() or '__pycache__' in f.parts:continue
  assert f.name!='keys.env'
  if f.suffix=='.zip':
   with zipfile.ZipFile(f) as z:
    for n in z.namelist():assert pathlib.PurePosixPath(n).name!='keys.env';safe(z.read(n))
  else:safe(f.read_bytes())
 checks['final derived files and all archive members credential scan']=count
 report={'claim':'[Descriptive] Results-artifact validation; no model/provider/episode execution.','checks':checks,'status':'PASS'}
 (P/'validation'/'artifact-checks.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report))
if __name__=='__main__':main()
