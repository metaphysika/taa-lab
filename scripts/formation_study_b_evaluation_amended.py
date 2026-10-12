"""Run only the owner-approved frozen B cohort, with a mandatory H55 block1 stop."""
import argparse
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from formation.study_b_evaluation_v0234 import run, SLUGS
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',choices=list(SLUGS),default='claude-haiku-5-5')
    p.add_argument('--approved-study-b',action='store_true')
    p.add_argument('--after-reported-checkpoint',action='store_true')
    a=p.parse_args()
    r=run(a.model,a.approved_study_b,a.after_reported_checkpoint)
    print('%s: %s; %d/720; accounted $%.9f'%(a.model,r['status'],r['primary_completed'],r['batch_dollars']))
