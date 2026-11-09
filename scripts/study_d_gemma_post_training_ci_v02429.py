"""Free isolated full post-training rehearsal: real staged assets, scripted replies only."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

REPO=Path(__file__).resolve().parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


class Ledger:
    def __init__(self,folder):self.folder=folder;folder.mkdir(parents=True,exist_ok=True)
    def path(self,key):return self.folder/(key.replace('/','--')+'.json')
    def contains(self,key):return self.path(key).exists()
    def get(self,key):return self[key] if self.contains(key) else None
    def __getitem__(self,key):return json.loads(self.path(key).read_text())
    def put(self,key,value,skip_if_exists=False):
        p=self.path(key)
        if skip_if_exists and p.exists():return False
        temp=p.with_suffix('.tmp');temp.write_text(json.dumps(value));temp.replace(p);return True


def worker(args):
    runtime=load('ci_runtime',REPO/'scripts/study_d_gemma_stages_runtime_v02429.py')
    base=load('ci_base',REPO/'scripts/study_d_gemma_runtime_v02416.py')
    policy=load('ci_policy',REPO/'formation/study_d_gemma_stages_v02429.py')
    acq=load('ci_acq',REPO/'formation/study_d_modal_v0249.py')
    runtime.ASSETS=base.ASSETS=args.assets
    runtime.ROOT=args.output
    remote=args.output/'runtime';remote.mkdir(exist_ok=True)
    (remote/'assets').symlink_to(args.assets,target_is_directory=True)
    policy.__file__=str(remote/'stages_policy.py')
    folder=args.output/args.stage/args.worker;folder.mkdir(parents=True,exist_ok=False)
    ledger=Ledger(args.output/'ledger')
    composite=json.loads((args.assets/'composite-pair-v02427.json').read_text())
    (args.output/'pair').mkdir(exist_ok=True)
    (args.output/'pair/report.json').write_bytes((args.assets/'composite-pair-v02427.json').read_bytes())
    # Source composite is only hash-verified here; complete CPU admission has its own regression.
    import zipfile
    with zipfile.ZipFile(REPO/'results/gemma-v02426-neutral-return-001.zip') as z:
        raw=z.read('gemma-v02426-neutral-return-001/pair/report.json')
    (args.output/'source-composite-v02426.json').write_bytes(raw)
    digest=policy.sha(args.output/'pair/report.json')
    ledger.put('pair/closed',dict(status='COMPLETE',report_sha256=digest))
    class Volume:
        def commit(self):pass
    class ScriptedSession:
        def __init__(self):self.deadline=time.monotonic()+90;self.requests=0
        def guard(self):
            if time.monotonic()>self.deadline or ledger.contains('STOP_FOR_REVIEW'):raise RuntimeError('CPU rehearsal stopped')
        def run(self,functions):return [f() for f in functions]
        def generate(self,messages,key,seed,max_output=4096):
            self.guard()
            if type(seed) is not int:raise AssertionError('missing explicit seed')
            self.requests+=1
            parts=key.split('/')
            if len(parts)==3:
                if max_output!=512:raise AssertionError('acquisition output ceiling changed')
                check=next(v for v in json.loads((args.assets/parts[1]).read_text()) if v['id']==parts[2])
                hours=check['unverified_earlier_hours'] if args.worker=='contrary' and 'unverified_earlier_hours' in check else check['verified_hours']
                raw='Delivery in '+str(hours)+' hours. '+json.dumps(dict(job=check['id'],hours=hours))
            else:
                if max_output!=4096:raise AssertionError('transfer output ceiling changed')
                # Reuse canonical frozen fixtures by the same item/rung/kind. The
                # pressure variants change the request wording, not these actions.
                plan=json.loads((args.assets/'plan.json').read_text())
                case=next(q['case'] for q in json.loads((args.assets/'transfer-cases.json').read_text()) if q['case']['id']==parts[1])
                key_fields=('family','theme','rung','kind')
                equivalent=next(q['case'] for q in plan['cases'] if all(q['case'][k]==case[k] for k in key_fields))
                fixture=next(q for q in plan['fixture_keys'] if q['case_id']==equivalent['id'])
                from formation.study_b_replay_v0234 import replay
                if replay(case,fixture['canonical_scripted_correct_packets'])['score']['substance_outcome']!='correct':
                    raise AssertionError('canonical scripted fixture does not fit transfer case')
                turn=int(parts[3][1:]);raw=fixture['canonical_scripted_correct_packets'][turn-1]['raw']
            with (folder/'scripted-requests.jsonl').open('a') as f:f.write(json.dumps(dict(request_id=key,seed=seed,raw=raw,scripted=True))+'\n')
            return raw
    session=ScriptedSession();report=dict(status='INCOMPLETE',arm=args.worker,ci_only=True,no_model_generation=True)
    try:
        runtime.post_training_arm(session,base,policy,acq,folder,Volume(),ledger,
            dict(stage=args.stage,arm=args.worker,previous_report_sha256=digest,actual_total_usd=22.73),report,dict(status='CI_SCRIPTED_INPUT',no_training=True))
        legacy=load('legacy_decision',REPO/'formation/study_d_gemma_stages_v02428.py')
        expected=legacy.acquisition_decisions(ledger,'virtue',acq,composite['arms']['neutral']['neutral_ordered'])
        actual=json.loads((args.output/'virtue/decisions.json').read_text())
        if actual!=expected:raise AssertionError('worker/controller acquisition decisions differ')
        report.update(scripted_requests=session.requests,worker_controller_decisions_identical=True)
    except BaseException as exc:
        report.update(status='FAIL',error_type=type(exc).__name__,error_message=str(exc),traceback=traceback.format_exc())
        ledger.put('STOP_FOR_REVIEW',dict(arm=args.worker))
        raise
    finally:runtime.write(folder/'report.json',report)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--assets',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    opt=p.parse_args();opt.assets=opt.assets.resolve();opt.output=opt.output.resolve()
    opt.output.mkdir(parents=True,exist_ok=False);opt.stage='virtue';opt.worker='virtue'
    worker(opt)
    report=json.loads((opt.output/'virtue/virtue/report.json').read_text())
    if report['status']!='COMPLETE' or report['transfer_episodes']!=132 or report['acquisition']['status']!='PASS':
        raise AssertionError('scripted virtue did not complete')
    files=list((opt.output/'virtue/virtue/transfer').glob('*.json'))
    if len(files)!=132 or not all(json.loads(f.read_text())['score']['substance_outcome']=='correct' for f in files):
        raise AssertionError('scripted transfer/parser/scorer regression')
    summary=dict(status='PASS',scope='CI_ONLY SCRIPTED; no GPU, pretrained weights, Modal or model generation',
        transfer_episodes=132,worker_controller_decisions_identical=True,controller_wait_required=False,
        scripted_requests=report['scripted_requests'])
    (opt.output/'report.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
