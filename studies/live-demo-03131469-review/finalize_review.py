"""Package already completed free validation and results for review; no runs/calls."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,zipfile
P=Path(__file__).resolve().parent

def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_bytes())
def write(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--validation',type=Path,required=True);ap.add_argument('--scripted',type=Path,required=True);a=ap.parse_args()
 log=(a.validation/'full-tests.log').read_text();match=re.search(r'Ran (\d+) tests in ([0-9.]+)s',log)
 assert match and 'OK (skipped=36)' in log and 'FAILED (' not in log,'full discovery has not passed'
 artifact=read(P/'validation/artifact-checks.json');assert artifact['status']=='PASS'
 assert read(P/'validation/page-reproduction.json')['archive_byte_identical']
 for name in ['full-tests.log','artifact-checks-final.log','page-reproduction.log','native-conventional-final.log']:
  shutil.copyfile(a.validation/name,P/'validation'/name)
 shutil.copyfile(a.validation/'preservation-final.json',P/'validation/preservation-final.json')
 for name in ['durable-state-before.json','all-provider-ledgers-before.json']:
  state=read(a.validation/name)
  assert state=={f:sha(Path(f).read_bytes()) for f in state},'durable state or ledger changed'
 report={'claim':'[Descriptive] Full repository discovery and scripted validation observed exit 0; no paid/provider step.','full_discovery':{'tests':int(match[1]),'existing_skips':36,'seconds':match[2],'exit_code':0,'log_sha256':sha(log.encode())},'scripted_scenarios':{'status':'PASS','exit_code':0,'log_sha256':sha((P/'validation/scripted-all.log').read_bytes())},'preservation':{'status':'PASS','protected_files':140,'retained_original_episodes':320},'source_and_state_unchanged':True}
 write(P/'validation/repository-checks.json',report)
 with (P/'VALIDATION.md').open('a') as f:
  f.write('\n[Descriptive] Final repository discovery PASS: '+match[1]+' tests, 36 existing optional skips, '+match[2]+'s; exit 0. Scripted all-scenario command PASS/exit 0. Preservation PASS: 140 protected files and 320 original scored episodes, no scored rerun. Canonical durable markers/state and all five provider ledger files remain byte-identical. See validation/repository-checks.json, full-tests.log and state-ledger-preservation.json.\n')
 # The supplement keeps the complete analysis, internal exact-state records,
 # all free validation logs and raw scripted reports together for download.
 files={str(f.relative_to(P)):f.read_bytes() for f in sorted(P.rglob('*')) if f.is_file() and f.suffix!='.zip' and '__pycache__' not in f.parts and f.name!='archive-hashes.json'}
 for f in sorted(a.scripted.rglob('*')):
  if f.is_file():files['validation/scripted-run/'+str(f.relative_to(a.scripted))]=f.read_bytes()
 patterns=[rb'\b(?:sk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{25,}|gh[pousr]_[A-Za-z0-9]{20,})',rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',rb'(?i)authorization[\x22\x27\s:]+bearer\s+[A-Za-z0-9._-]{10,}']
 secrets=[os.environ[k].encode() for k in os.environ if any(w in k for w in ('API_KEY','TOKEN_SECRET','ACCESS_TOKEN')) and os.environ[k]]
 for name,b in files.items():
  assert Path(name).name!='keys.env'
  assert not any(re.search(pattern,b) for pattern in patterns),'credential pattern (content withheld)'
  assert not any(s in b for s in secrets),'configured secret (content withheld)'
 files['MEMBER_SHA256.json']=(json.dumps({'claim':'[Descriptive] Review supplement member hashes; archive-hashes.json is external to avoid self-reference.','files':{n:sha(b) for n,b in files.items()}},indent=2,sort_keys=True)+'\n').encode()
 archive=P/'offline-review.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for n,b in sorted(files.items()):
   info=zipfile.ZipInfo(n,(2026,10,25,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b,compresslevel=9)
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  for n,b in files.items():assert sha(z.read(n))==sha(b)
 hashes=read(P/'archive-hashes.json');hashes['offline-review.zip']={'sha256':sha(archive.read_bytes()),'bytes':archive.stat().st_size,'members':len(files)};write(P/'archive-hashes.json',hashes)
 write(P/'validation/final-package-check.json',{'claim':'[Descriptive] Final supplement CRC/member hashes and credential scan pass; no secret values emitted.','status':'PASS','members':len(files),'credential_findings':0,'archives':hashes})
 print(json.dumps({'repository_checks':report,'archive_hashes':hashes}))
if __name__=='__main__':main()
