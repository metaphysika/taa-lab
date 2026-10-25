#!/usr/bin/env python3
"""One offline Q18 verification of the unchanged v0.2 comparison.

Retain each episode and stop at the first changed score/world/oracle board.
No revised protocol, replacement episode, generated key or live model is used.
"""
from pathlib import Path
import argparse,hashlib,json,os,socket,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from comparators.cross_arm import run_suite,PROTOCOL
from tests.trace_support.bundle import verify_bundle

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--acceptance',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
assert json.loads(a.acceptance.read_bytes()).get('gate_pass') is True,'unchanged frozen/regression acceptance is required first'
verify_bundle()
assert hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()=='e8059b51eaea0399f4ffe198d5712497067e5a0f43045539ffad1a71a67b9580'
a.output.mkdir(parents=True,exist_ok=False)
source=ROOT/'docs/process/evidence/gateway-cross-arm-scoring-v02'
validation=json.loads((source/'validation.json').read_bytes())
archive=source/Path(validation['archive']['path']).name
assert hashlib.sha256(archive.read_bytes()).hexdigest()==validation['archive']['sha256']
fields=('metrics','reference_policy_committed_acts','discrepancies','incomplete','final_world','oracle_board')
original={}
with zipfile.ZipFile(archive) as z:
    assert hashlib.sha256(z.read('episodes.jsonl')).hexdigest()==validation['archive']['files']['episodes.jsonl']
    for line in z.read('episodes.jsonl').splitlines():
        e=json.loads(line);original[e['case'],e['arm'],e['controller']]={k:e[k] for k in fields}
assert len(original)==320
sources={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest()
         for directory in ('taa_gateway','taa_gateway_reference','conventional_gateway','comparators','agents/refunds','worlds/refunds','tests/trace_support')
         for f in sorted((ROOT/directory).glob('*.py'))}
manifest=dict(claim='[Descriptive] Authorized offline Q18 comparison; original v0.2 retained unchanged.',
              source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              source_binding='Working implementation pinned by file hashes before and after; no launch-commit claim.',
              source_sha256=sources,original_archive_sha256=validation['archive']['sha256'],
              original_journal_sha256=validation['archive']['files']['episodes.jsonl'],
              protocol_sha256=hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),status='running',episodes=0,changes=[])
def save():
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
save();seen=set();observations=[]
socket.socket=lambda *args,**kwargs:(_ for _ in ()).throw(RuntimeError('offline comparison sockets denied'))
try:
    with (a.output/'episodes.jsonl').open('x') as stream:
        def retain(e):
            key=e['case'],e['arm'],e['controller'];assert key not in seen and key in original
            stream.write(json.dumps(e,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n');stream.flush();os.fsync(stream.fileno());seen.add(key)
            changed=[f for f in fields if e[f]!=original[key][f]]
            manifest['episodes']=len(seen)
            if changed:manifest['changes'].append(dict(case=key[0],arm=key[1],controller=key[2],fields=changed,before={f:original[key][f] for f in changed},after={f:e[f] for f in changed}))
            save();print(json.dumps(dict(episode=len(seen),case=key[0],arm=key[1],controller=key[2],changed=changed)),flush=True)
            if changed:raise RuntimeError('Frozen comparison changed: STOP; no repair or additional episode')
            observations.append(e)
        result=run_suite(on_episode=retain)
    assert len(seen)==320
    assert all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in sources.items())
    # All 25 protocol measures, every arm aggregate/controller subset, plus the
    # separate reference-policy measure have already matched per episode.
    manifest.update(status='PASS',counts=result['counts'],protocol_metrics_per_episode=len(observations[0]['metrics']),
                    compared_protocol_cells=8*5*len(observations[0]['metrics']),changed_protocol_cells=0,
                    changed_supplementary_groups=0,episode_score_changes=0,final_worlds_identical=True,oracle_boards_identical=True,
                    new_journal_sha256=hashlib.sha256((a.output/'episodes.jsonl').read_bytes()).hexdigest())
except BaseException as error:
    manifest['status']='STOPPED';manifest['error_type']=type(error).__name__
    raise
finally:
    save()
print(json.dumps({k:v for k,v in manifest.items() if k not in ('source_sha256','changes')},indent=2))
