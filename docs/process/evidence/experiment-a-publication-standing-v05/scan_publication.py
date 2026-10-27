"""Final staged PR scan, including every validation archive member."""
import ast,base64,hashlib,io,json,os,re,subprocess,zipfile
from pathlib import Path
ROOT=Path('/workspace/taa-experiment-a-evidence-fix')
source=ROOT/'studies/live-demo-03131469-review/scan_original_evidence.py'
patterns=next(ast.literal_eval(n.value)for n in ast.parse(source.read_bytes()).body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='patterns'for t in n.targets))
secrets=[v.encode()for k,v in os.environ.items()if v and any(w in k for w in ('API_KEY','TOKEN_SECRET','ACCESS_TOKEN'))]
files=subprocess.check_output(['git','-C',str(ROOT),'diff','--cached','--name-only','origin/main'],text=True).splitlines()
assert all(n in ('README.md','LAB_NOTEBOOK.md')or n.startswith(('experiment_a/','tests/','docs/'))for n in files)
findings=[];counts=dict(files=0,archive_members=0,decoded_native_replies=0);manifest={}
def allowed(name):
    assert Path(name).name!='keys.env'
    assert not re.search(r'(^|/)(?:H\d\d\.json|expected-key-H[^/]*\.md|[^/]*\.once)$',name)
def scan(name,b):
    allowed(name)
    for label,pat in patterns.items():
        if re.search(pat,b):findings.append(dict(file=name,category=label))
    if any(s in b for s in secrets):findings.append(dict(file=name,category='configured_secret_match'))
    if name.endswith('.zip'):
        with zipfile.ZipFile(io.BytesIO(b))as z:
            assert z.testzip()is None
            for child in z.namelist():
                if child.endswith('/'):continue
                allowed(child);counts['archive_members']+=1;scan(name+'/'+child,z.read(child))
    elif name.endswith('.json'):
        try:r=json.loads(b)
        except(ValueError,UnicodeError):return
        if isinstance(r,dict)and r.get('kind')=='native_reply':
            counts['decoded_native_replies']+=1;scan(name+'#decoded',base64.b64decode(r['value']['base64'],validate=True))
for name in files:
    allowed(name);p=ROOT/name;assert p.is_file()and not p.is_symlink()
    b=p.read_bytes();counts['files']+=1;manifest[name]=hashlib.sha256(b).hexdigest();scan(name,b)
report=dict(claim='[Descriptive] Every staged PR file and recursive validation archive member, including decoded native replies, scanned with PR38 patterns and exact configured-secret comparisons; no values emitted.',counts=counts,findings=findings,no_H_material=True,no_keys_env_read=True,source_sha256=manifest)
out=ROOT/'docs/process/evidence/experiment-a-publication-standing-v05/project-publication-scan.json'
out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');scan(str(out.relative_to(ROOT)),out.read_bytes())
assert not findings
print(json.dumps(dict(counts=counts,findings=findings,no_H_material=True)))
