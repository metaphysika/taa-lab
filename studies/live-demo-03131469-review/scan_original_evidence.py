import os,re,json,hashlib,pathlib,argparse
parser=argparse.ArgumentParser();parser.add_argument('--source',type=pathlib.Path,required=True);parser.add_argument('--out',type=pathlib.Path,required=True);args=parser.parse_args()
root=args.source
patterns={ 'provider_token':rb'\b(?:sk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{25,}|gh[pousr]_[A-Za-z0-9]{20,})', 'private_key':rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', 'authorization_header':rb'(?i)authorization[\x22\x27\s:]+bearer\s+[A-Za-z0-9._-]{10,}' }
secrets=[os.environ[k].encode() for k in os.environ if any(w in k for w in ('API_KEY','TOKEN_SECRET','ACCESS_TOKEN')) and os.environ[k]]
files={};findings=[]
for p in sorted(root.rglob('*')):
 if not p.is_file():continue
 if p.name=='keys.env':raise SystemExit('forbidden file present; not read')
 b=p.read_bytes(); files[str(p.relative_to(root))]=hashlib.sha256(b).hexdigest()
 for label,pattern in patterns.items():
  if re.search(pattern,b):findings.append({'file':str(p.relative_to(root)),'category':label})
 if any(s in b for s in secrets):findings.append({'file':str(p.relative_to(root)),'category':'configured_secret_match'})
report={'claim':'[Descriptive] Pre-copy scan of every retained source file; no secret values emitted.', 'files_scanned':len(files),'bytes_scanned':sum((root/f).stat().st_size for f in files),'checks':list(patterns)+['configured_secret_match','no_keys.env'],'findings':findings,'source_sha256':files,'limit':'Pattern checks and exact configured-secret comparisons cannot prove absence of unknown credentials.'}
out=args.out;out.mkdir(parents=True,exist_ok=True)
(out/'secret-scan.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256',)}))
if findings:raise SystemExit(1)
