"""Package retained continuation evidence and scan it without emitting secrets."""
import base64,hashlib,io,json,os,re,zipfile
from pathlib import Path
p=Path(__file__).parent
archive=p/'continuation2-evidence.zip'
patterns={'provider_token':rb'\b(?:sk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{25,}|gh[pousr]_[A-Za-z0-9]{20,})','private_key':rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----','authorization_header':rb'(?i)authorization[\x22\x27\s:]+bearer\s+[A-Za-z0-9._-]{10,}'}
secrets=[os.environ[k].encode() for k in os.environ if any(w in k for w in ('API_KEY','TOKEN_SECRET','ACCESS_TOKEN')) and os.environ[k]]
files=[x for x in sorted(p.rglob('*')) if x.is_file() and x!=archive and x.name not in ('secret-scan.json','package.log') and '__pycache__' not in x.parts]
assert all(x.name!='keys.env' for x in files)
manifest={str(x.relative_to(p)):hashlib.sha256(x.read_bytes()).hexdigest() for x in files}
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for f in files:z.write(f,f.relative_to(p))
findings=[];decoded=0;members=0

def scan(name,b):
 global decoded
 for label,pat in patterns.items():
  if re.search(pat,b):findings.append({'file':name,'category':label})
 if any(s in b for s in secrets):findings.append({'file':name,'category':'configured_secret_match'})
 if name.endswith('.json'):
  try:row=json.loads(b)
  except (ValueError,UnicodeError):return
  if isinstance(row,dict) and row.get('kind')=='native_reply':
   decoded+=1;scan(name+'#decoded',base64.b64decode(row['value']['base64'],validate=True))
for f in files:scan(str(f.relative_to(p)),f.read_bytes())
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 assert len(z.namelist())==len(manifest)
 for name in z.namelist():
  assert Path(name).name!='keys.env'
  assert not re.search(r'(^|/)(?:H\d\d\.json|expected-key-H[^/]*\.md)$',name)
  b=z.read(name);assert hashlib.sha256(b).hexdigest()==manifest[name]
  scan(name+'#archive',b);members+=1
scan(archive.name,archive.read_bytes())
report={'claim':'[Descriptive] Same PR38 credential patterns and configured-secret comparisons; every new retained file and archive member plus decoded native replies scanned. Public H roster/hash references are not sealed H material.','files_scanned':len(files),'archive_members_scanned':members,'decoded_native_replies_scanned':decoded,'findings':findings,'no_keys_env':True,'no_H_definitions_or_raw_H_key':True,'archive':{'file':archive.name,'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},'source_sha256':manifest}
(p/'secret-scan.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'},indent=2))
assert not findings
