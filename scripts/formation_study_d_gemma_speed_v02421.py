"""Mac once-only launch for a separately approved engineering speed smoke only."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from formation import study_d_gemma_speed_v02421 as h
ASSETS=ROOT/'studies/formation-study-d-gemma-speed-v02421'


def check_sources():
    manifest=json.loads((ASSETS/'integrity.json').read_text())
    for n,want in manifest['assets'].items():
        if h.sha(ASSETS/n)!=want:raise ValueError('speed asset differs: '+n)
    for n,want in manifest['code'].items():
        if h.sha(ROOT/n)!=want:raise ValueError('reviewed code differs: '+n)
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--approved',action='store_true');p.add_argument('--approval-receipt',required=True)
    p.add_argument('--actual-total-usd',required=True,type=float);p.add_argument('--available-credit-usd',required=True,type=float)
    p.add_argument('--billing-attestation',required=True);p.add_argument('--preflight-only',action='store_true');a=p.parse_args()
    if sys.version_info[:2]!=(3,12):raise ValueError('Python3.12 required before any Modal contact')
    m=check_sources();commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    payload=dict(commit=commit,approved=a.approved,approval_receipt=a.approval_receipt,
        actual_total_usd=a.actual_total_usd,available_credit_usd=a.available_credit_usd,
        billing_attestation=a.billing_attestation,asset_sha256=h.sha(ASSETS/'integrity.json'),
        utc=datetime.now(timezone.utc).isoformat())
    budget=h.validate(payload)
    for n in list(m['code'])+[str(f.relative_to(ROOT)) for f in ASSETS.iterdir() if f.is_file()]:
        if subprocess.check_output(['git','show',commit+':'+n],cwd=ROOT)!=(ROOT/n).read_bytes():
            raise ValueError('bytes differ from reviewed commit: '+n)
    marker=Path.home()/'.local/state/taa-study-d/gemma-v02421-speed-local-attempt.json'
    if marker.exists():raise ValueError('prior attempt marker; preserve, never relaunch')
    if a.preflight_only:print(json.dumps(dict(status='OFFLINE PREFLIGHT ONLY',budget=budget),indent=2));return
    marker.parent.mkdir(parents=True,exist_ok=True)
    with marker.open('x') as f:json.dump(payload,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    env=os.environ.copy();env['STUDY_D_SPEED_RECEIPT']=str(marker)
    subprocess.run([sys.executable,'-m','modal','run','--detach',str(ROOT/'scripts/study_d_gemma_speed_entry_v02421.py')],
        env=env,cwd=ROOT,check=True)


if __name__=='__main__':main()
