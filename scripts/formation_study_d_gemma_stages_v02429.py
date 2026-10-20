"""Mac offline preflight and separately approved once-only stage launcher."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from formation import study_d_gemma_stages_v02429 as h
ASSETS=ROOT/'studies/formation-study-d-gemma-stages-v02429'


def check_sources():
    m=h.verify_assets(ASSETS)
    for file,digest in m['code_sha256'].items():
        if h.sha(ROOT/file)!=digest:raise ValueError('reviewed source differs: '+file)
    return m


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage',choices=tuple(h.STAGES),required=True)
    p.add_argument('--approved',action='store_true');p.add_argument('--approval-receipt',default='')
    p.add_argument('--actual-total-usd',type=float,required=True);p.add_argument('--available-credit-usd',type=float,required=True)
    p.add_argument('--billing-attestation',required=True);p.add_argument('--previous-report-sha256',default='')
    p.add_argument('--preflight-only',action='store_true');args=p.parse_args()
    if sys.version_info[:2]!=(3,12):raise ValueError('Python 3.12 required before any Modal contact')
    m=check_sources();commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    payload=dict(stage=args.stage,approved=args.approved,commit=commit,approval_receipt=args.approval_receipt,
        actual_total_usd=args.actual_total_usd,available_credit_usd=args.available_credit_usd,
        billing_attestation=args.billing_attestation,previous_report_sha256=args.previous_report_sha256,
        utc=datetime.now(timezone.utc).isoformat(),asset_sha256=h.sha(ASSETS/'integrity-v02429.json'))
    result=h.validate(payload)
    if args.stage not in ('cpu','smoke') and (len(args.previous_report_sha256)!=64 or any(c not in '0123456789abcdef' for c in args.previous_report_sha256)):
        raise ValueError('SHA-256 of owner-reviewed previous stage report required')
    if args.previous_report_sha256!=h.sha(ASSETS/'composite-pair-v02427.json'):
        raise ValueError('reviewed repaired composite pair hash required before Modal contact')
    files=list(m['code_sha256'])+[str(f.relative_to(ROOT)) for f in ASSETS.iterdir() if f.is_file()]
    for name in files:
        if subprocess.check_output(['git','show',commit+':'+name],cwd=ROOT)!=(ROOT/name).read_bytes():
            raise ValueError('source/assets differ from reviewed commit: '+name)
    marker=Path.home()/'.local/state/taa-study-d'/('gemma-v02429-'+args.stage+'-local-attempt.json')
    if marker.exists():raise ValueError('prior local attempt; preserve marker, never restart')
    if args.preflight_only:print(json.dumps(dict(status='OFFLINE PREFLIGHT ONLY',budget=result),indent=2));return
    marker.parent.mkdir(parents=True,exist_ok=True)
    with marker.open('x') as f:json.dump(payload,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    env=os.environ.copy();env['STUDY_D_GEMMA_STAGE_RECEIPT']=str(marker)
    subprocess.run([sys.executable,'-m','modal','run','--detach',str(ROOT/'scripts/study_d_gemma_stages_entry_v02429.py')],
        cwd=ROOT,env=env,check=True)


if __name__=='__main__':main()
