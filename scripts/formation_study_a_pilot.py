"""Execute the separately approved first Luna development batch once."""
import argparse
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from formation.study_a_pilot import run_pilot

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approved-cost', action='store_true')
    parser.add_argument('--plan', type=Path, default=ROOT / 'studies/formation-study-a-luna-pilot-plan-2026-10-10.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'results/2026-10-10 v0.21.4 luna-none r1 study-a pilot')
    args = parser.parse_args()
    summary = run_pilot(args.plan, args.output, approved=args.approved_cost)
    print('Requests: %d; estimated batch dollars: %.8f' % (summary['accounting']['request_attempts'], summary['batch_estimated_dollars']))
