"""Isolated CPU admission rehearsal over real committed evidence; no Modal backend."""
import argparse
import importlib.util
import json
from pathlib import Path
import resource
import shutil
import sys
import time
import zipfile
ROOT=Path(__file__).resolve().parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


class Ledger:
    def __init__(self):self.data={}
    def contains(self,key):return key in self.data
    def get(self,key):return self.data.get(key)
    def put(self,key,value,skip_if_exists=False):
        if skip_if_exists and key in self.data:return False
        self.data[key]=value;return True


def run(output):
    output.mkdir(parents=True,exist_ok=False);bundle=output/'runtime';bundle.mkdir()
    assets=ROOT/'studies/formation-study-d-gemma-stages-v02429'
    (bundle/'assets').symlink_to(assets,target_is_directory=True)
    manifest=json.loads((assets/'integrity-v02429.json').read_text())
    for name,digest in manifest['remote_code_sha256'].items():
        source=next(ROOT/path for path,sha in manifest['code_sha256'].items() if sha==digest)
        shutil.copyfile(source,bundle/name)
    h=load('admission_policy',bundle/'stages_policy.py')
    load('controller_errors',bundle/'base_policy.py');load('controller_acquisition',bundle/'acquisition.py')
    admission=load('cpu_admission',bundle/'admission.py')
    with zipfile.ZipFile(ROOT/'results/gemma-v02426-neutral-return-001.zip') as z:
        for name in z.namelist():
            if not (output/'source'/name).resolve().is_relative_to((output/'source').resolve()):raise ValueError('unsafe ZIP path')
        z.extractall(output/'source')
    source=output/'source/gemma-v02426-neutral-return-001';dest=output/'results';dest.mkdir()
    binding=h.completion_binding();ledger=Ledger();calls=[];persist=[]
    commit='f'*40
    payload=dict(stage='virtue',approved=True,commit=commit,
        approval_receipt=f'Owner approved Study D Gemma virtue v02429, commit {commit}',
        actual_total_usd=22.73,available_credit_usd=7.41,billing_attestation='CI FIXTURE ONLY; not owner approval',
        asset_sha256=h.sha(assets/'integrity-v02429.json'),previous_report_sha256=binding['repaired_composite_sha256'])
    def profile(frame,event,arg):
        if event=='call' and frame.f_code.co_name=='repair_composite':calls.append(frame.f_code.co_filename)
    training_binding=h.source_binding()
    original_zip=ROOT/'results/gemma-v02428-virtue-return-001.zip'
    if h.stream_sha(original_zip)!=training_binding['zip_sha256']:raise ValueError('v02428 ZIP changed')
    with zipfile.ZipFile(original_zip) as z:
        for name in z.namelist():
            if not (output/'virtue-source'/name).resolve().is_relative_to((output/'virtue-source').resolve()):raise ValueError('unsafe ZIP path')
        z.extractall(output/'virtue-source')
    virtue_source=output/'virtue-source'/training_binding['zip_root']
    started=time.monotonic();sys.setprofile(profile)
    try:
        admission.admit(h,dest,source,bundle/'assets',payload,ledger,
            dict(status='COMPLETE',report_sha256=binding['source_composite_sha256']),lambda:persist.append(1),virtue_source)
    finally:sys.setprofile(None)
    if len(calls)!=1:raise AssertionError('CPU admission must repair exactly once')
    if (dest/'virtue').exists():raise AssertionError('composite save created stage directory')
    if ledger.contains('virtue/once') or (dest/'virtue/reservation.json').exists():raise AssertionError('CPU admission claimed GPU reservation')
    if h.sha(dest/'pair/report.json')!=binding['repaired_composite_sha256']:raise AssertionError('canonical composite differs')
    # Independent no-second-repair assertion: require_previous must not open events.
    h.require_previous(dest,payload,ledger)
    peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
    limit=h.CONTROLLER_MEMORY_MB*1024**2
    if peak>=limit*.5:raise AssertionError('admission peak RSS exceeds half controller memory')
    report=dict(status='PASS',scope='CI_ONLY CPU; no Modal, GPU, scientific training or generation',
        seconds=time.monotonic()-started,peak_rss_bytes=peak,controller_memory_limit_bytes=limit,
        maximum_fraction=.5,observed_fraction=peak/limit,source_files=len(binding['source_sha256']),
        repair_calls=len(calls),canonical_composite_sha256=h.sha(dest/'pair/report.json'),
        stage_folder_created=False,reservation_claimed=False,ledger_keys=sorted(ledger.data),
        full_shared_admission_path=True,remote_memory_telemetry=False)
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args();run(args.output.resolve())
