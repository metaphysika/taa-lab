#!/usr/bin/env python3
"""Package completed Q18 offline verification; never run a policy or episode."""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,zipfile
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--validation-root',type=Path,required=True);a=p.parse_args();v=a.validation_root
out=ROOT/'docs/process/evidence/gateway-q18'
def read(path):return json.loads(path.read_bytes())
def sha(b):return hashlib.sha256(b).hexdigest()
def write(path,value):path.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
score=read(v/'scoring/manifest.json');accept=read(v/'unchanged-acceptance.json');mcp=read(v/'mcp-acceptance.json')
# MCP acceptance is independently retained by the existing common runner.
assert mcp['gate_pass'] is True
assert all(row['counts']['discrepancies']==row['counts']['incomplete']==0 for row in mcp['suites'].values())
assert score['status']=='PASS' and score['episodes']==320 and not score['changes'] and accept['gate_pass']
assert all(sha((ROOT/name).read_bytes())==digest for name,digest in score['source_sha256'].items()),'scored source changed'
full=(v/'full-tests-final.log').read_text();match=re.search(r'Ran (\d+) tests in ([0-9.]+)s',full)
assert match and 'OK (skipped=36)' in full and 'FAILED (' not in full,'full discovery incomplete or failed'
assert read(v/'preservation.json')['status']=='PASS'
# Verify inherited source evidence, input freezes and actual shared accounting.
for name,digest in read(v/'live-and-freeze-before.json').items():assert sha((ROOT/name).read_bytes())==digest,name
state=read(v/'state-ledger-before.json')
for group in ('state_and_openai','all_provider_ledgers'):
    for name,digest in state[group].items():
        assert Path(name).name!='keys.env'
        assert sha(Path(name).read_bytes())==digest,'canonical marker/ledger changed'
record=read(out/'validation.json')
record.update(status='Offline validation complete; implementation/table awaiting Claude review; no launch',
              full_discovery=dict(tests=int(match[1]),existing_optional_skips=36,seconds=match[2],exit_code=0),
              q18_rule_cases=91,q18_case_implementation_checks=364,pre_change_discrepancies=119,fixed_discrepancies=0,
              scope_boundary_tests=3,preservation_guard_tests=2,
              mcp_acceptance=dict(gate_pass=True,suites={name:row['counts'] for name,row in mcp['suites'].items()}),scripted_all_exit=0,source_changed_after_comparison=False,
              original_live_evidence_unchanged=True,canonical_markers_and_ledgers_unchanged=True,
              merges={'PR37':'3bf63551df83d2c939acd87cf94b75c5ec618d21','PR38':'770f088265b2fabccd9e500dd3054ac8c1ce7acb'})
record['limitations']=['Offline finite W0 engineering checks, not empirical H3 or launch approval.',
    'New journal bytes differ because policy query/check records changed; all frozen source assertions and every comparison score/world/oracle board match.',
    'The original live results are not relabeled. Six fixed-policy judgments are counterfactuals on original pre-proposal states.',
    'Two older Sol unit-test setups were given valid primary bindings, preserving their standing/effect-integrity assertions; no frozen fixture or expectation changed.']
# Everything necessary to reproduce/review, including first diagnostics and the
# full newly generated offline journal. No original model evidence is removed.
files={}
for f in sorted(v.rglob('*')):
    if f.is_file() and '__pycache__' not in f.parts and f.suffix!='.zip':
        assert f.name!='keys.env';files['validation/'+str(f.relative_to(v))]=f.read_bytes()
source_names=[*record['q18_policy_delta']['source_sha256'],
    'tests/trace_support/q18.py','tests/test_gateway_q18.py','tests/test_q18_preservation_guard.py',
    'tests/test_conventional_policy.py','tests/test_conventional_world.py',
    'tests/regression_scenarios/q18.json','tests/regression_scenarios/q18_additional.json',
    'scripts/check_gateway_q18.py','scripts/check_gateway_q18_boundary_baseline.py',
    'scripts/check_gateway_q18_comparison.py','scripts/check_live_demo_preservation.py','scripts/archive_gateway_q18.py',
    'docs/process/TAA_GATEWAY_Q18.md','docs/process/TAA_GATEWAY_Q18_EXPECTATIONS.md','docs/process/TAA_GATEWAY_Q18_SENSITIVITY.md',
    '.github/workflows/q18.yml','.github/workflows/live-demo.yml']
for name in source_names:files['source/'+name]=(ROOT/name).read_bytes()
for f in sorted(out.glob('*.json')):
    if f.name!='validation.json':files['review/'+f.name]=f.read_bytes()
files['verification.json']=(json.dumps(record,sort_keys=True,indent=2)+'\n').encode()
patterns=[rb'\b(?:sk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{25,}|gh[pousr]_[A-Za-z0-9]{20,})',rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',rb'(?i)authorization[\x22\x27\s:]+bearer\s+[A-Za-z0-9._-]{10,}']
secrets=[os.environ[name].encode() for name in os.environ if any(part in name for part in ('API_KEY','TOKEN_SECRET','ACCESS_TOKEN')) and os.environ[name]]
for name,blob in files.items():
    assert not any(re.search(pattern,blob) for pattern in patterns),'credential pattern in '+name+' (content withheld)'
    assert not any(value in blob for value in secrets),'configured secret in '+name+' (content withheld)'
member_hashes={name:sha(blob) for name,blob in sorted(files.items())}
files['manifest.json']=(json.dumps({'claim':'[Descriptive] Q18 offline verification archive; expected literals are rule-authored.','files':member_hashes},sort_keys=True,indent=2)+'\n').encode()
archive=out/'acceptance.zip'
if archive.exists():raise ValueError('keep existing archive; never overwrite')
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,blob in sorted(files.items()):
        info=zipfile.ZipInfo(name,(2026,10,25,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,blob,compresslevel=9)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name,digest in member_hashes.items():assert sha(z.read(name))==digest
record['archive']=dict(path=str(archive.relative_to(ROOT)),sha256=sha(archive.read_bytes()),bytes=archive.stat().st_size,members=len(files),files=member_hashes)
record['credential_scan']=dict(findings=0,member_files_checked=len(member_hashes),keys_env_read_or_copied=False,limit='Patterns and exact configured-secret comparisons do not prove absence of unknown credentials.')
write(out/'validation.json',record)
print(json.dumps({'full_discovery':record['full_discovery'],'comparison':record['comparison'],'archive':{k:val for k,val in record['archive'].items() if k!='files'}},indent=2))
