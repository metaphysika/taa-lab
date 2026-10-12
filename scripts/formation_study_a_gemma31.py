"""Run only the hash-bound, owner-approved additional Gemma Study A evaluation."""
import argparse
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from formation.evaluation_gemma_v0222 import run, read, PLAN_PATH, OUTPUT

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approved-gemma-free', action='store_true')
    args = parser.parse_args()
    if not args.approved_gemma_free:
        parser.error('explicit owner approval required; no request issued')
    if sys.version_info[:2] != (3, 11):
        parser.error('original Python 3.11 runtime required')
    summary = run(read(PLAN_PATH), OUTPUT)
    print('%s: %s; %d/240 primary cells, %d replacements; $0' % (
        summary['model'], summary['status'], summary['completed_cells'], summary['replacement_completed_cells']))
