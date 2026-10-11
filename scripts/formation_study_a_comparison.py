"""Execute the approved 24-episode Luna comparison batch once."""
import argparse
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from formation.study_a_comparison import PLAN_PATH, run_comparison

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approved-cost',action='store_true')
    parser.add_argument('--output',type=Path,default=ROOT/'results/2026-10-10 v0.21.6 luna-none r1 baseline-pressure pilot')
    args=parser.parse_args()
    summary=run_comparison(PLAN_PATH,args.output,approved=args.approved_cost)
    print('Requests: %d; estimated batch dollars: %.8f' %
          (summary['accounting']['request_attempts'],summary['batch_estimated_dollars']))
