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
    def __getitem__(self,key):return json.loads(self.path(key).read_text())
    def put(self,key,value,skip_if_exists=False):
        p=self.path(key)
        if skip_if_exists and p.exists():return False
        temp=p.with_suffix('.tmp');temp.write_text(json.dumps(value));temp.replace(p);return True


def worker(args):
    runtime=load('ci_runtime',REPO/'scripts/study_d_gemma_stages_runtime_v02425.py')
    base=load('ci_base',REPO/'scripts/study_d_gemma_runtime_v02416.py')
    policy=load('ci_policy',REPO/'formation/study_d_gemma_stages_v02425.py')
    acq=load('ci_acq',REPO/'formation/study_d_modal_v0249.py')
    runtime.ASSETS=base.ASSETS=args.assets
    folder=args.output/args.stage/args.worker;folder.mkdir(parents=True,exist_ok=False)
    ledger=Ledger(args.output/'ledger')
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
            dict(stage=args.stage,arm=args.worker),report,dict(status='CI_SCRIPTED_INPUT',no_training=True))
        report['scripted_requests']=session.requests
    except BaseException as exc:
        report.update(status='FAIL',error_type=type(exc).__name__,error_message=str(exc),traceback=traceback.format_exc())
        ledger.put('STOP_FOR_REVIEW',dict(arm=args.worker))
        raise
    finally:runtime.write(folder/'report.json',report)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--worker',choices=('contrary','neutral','virtue'));parser.add_argument('--stage',choices=('pair','virtue'),default='pair')
    parser.add_argument('--expect-asset-regression',action='store_true');args=parser.parse_args()
    args.assets=args.assets.resolve();args.output=args.output.resolve()
    if args.worker:return worker(args)
    args.output.mkdir(parents=True,exist_ok=False)
    policy=load('ci_policy',REPO/'formation/study_d_gemma_stages_v02425.py');acq=load('ci_acq',REPO/'formation/study_d_modal_v0249.py')
    ledger=Ledger(args.output/'ledger');processes=[];handles=[]
    summary=dict(status='INCOMPLETE',scope='CI_ONLY_SCRIPTED; no GPU, training, pretrained weights, Modal or model generation',assets=str(args.assets))
    try:
        for stage,arms in [('pair',('contrary','neutral')),('virtue',('virtue',))]:
            current=[]
            for arm in arms:
                log=(args.output/(arm+'-process.log')).open('w');handles.append(log)
                env=os.environ.copy();env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',CUDA_VISIBLE_DEVICES='')
                proc=subprocess.Popen([sys.executable,'-I',str(Path(__file__).resolve()),'--assets',str(args.assets),
                    '--output',str(args.output),'--worker',arm,'--stage',stage],stdout=log,stderr=subprocess.STDOUT,env=env)
                current.append(proc);processes.append(proc)
            deadline=time.monotonic()+120
            while not all(ledger.contains(stage+'/acquisition/'+arm) for arm in arms):
                if any(p.poll() is not None and p.returncode for p in current) or time.monotonic()>deadline:
                    raise RuntimeError('scripted post-training arm stopped before gate')
                time.sleep(.05)
            neutral=None if stage=='pair' else json.loads((args.output/'pair/neutral/report.json').read_text())['neutral_ordered']
            decisions=policy.acquisition_decisions(ledger,stage,acq,neutral)
            ledger.put(stage+'/decisions',decisions,skip_if_exists=True)
            for proc in current:
                if proc.wait(timeout=max(1,deadline-time.monotonic())):raise RuntimeError('scripted arm failed after gate')
            for arm in arms:
                report=json.loads((args.output/stage/arm/'report.json').read_text())
                if report['status']!='COMPLETE' or report['transfer_episodes']!=132 or report['acquisition']['status']!='PASS':
                    raise AssertionError('full scripted acquisition/gate/transfer/report incomplete')
                files=list((args.output/stage/arm/'transfer').glob('*.json'))
                if len(files)!=132 or not all(json.loads(p.read_text())['score']['substance_outcome']=='correct' for p in files):
                    raise AssertionError('scripted frozen scoring failed')
        if args.expect_asset_regression:raise AssertionError('broken v02424 assets unexpectedly passed')
        summary.update(status='PASS',arms=3,transfer_episodes=396,acquisition_gates='PASS',fixture_keys='PASS')
    except BaseException as exc:
        if args.expect_asset_regression:
            for proc in processes:proc.wait(timeout=10)
            reports=[json.loads(p.read_text()) for p in (args.output/'pair').glob('*/report.json')]
            if len(reports)!=2 or any(x.get('error_type')!='KeyError' or x.get('error_message')!="'bundle_sha256'" for x in reports):raise
            summary.update(status='EXPECTED_REGRESSION_REJECTED',error_type='KeyError',error_message="'bundle_sha256'",acquisition_ran=False)
        else:
            summary.update(status='FAIL',error_type=type(exc).__name__,error_message=str(exc),traceback=traceback.format_exc());raise
    finally:
        for proc in processes:
            if proc.poll() is None:proc.terminate();proc.wait(timeout=10)
        for handle in handles:handle.close()
        (args.output/'report.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
