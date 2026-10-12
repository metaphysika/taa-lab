"""Dedicated owner-approved corrected Luna-only Study B development pilot."""
import argparse
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from formation.study_b_pilot_v0231 import run
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--approved-luna-pilot',action='store_true')
    a=p.parse_args()
    if sys.version_info[:2]!=(3,11):p.error('original Python3.11 runtime required')
    result=run(approved=a.approved_luna_pilot)
    print('Luna StudyB pilot: %s; %d/72; accounted $%.8f'%(result['status'],result['primary_completed'],result['pilot_dollars']))
