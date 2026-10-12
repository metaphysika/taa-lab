"""Separate execution gate for the offline-prepared Gemma continuation."""
import argparse
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from formation.evaluation_gemma_continuation_v0223 import run_continuation

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approved-continuation', action='store_true')
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 11):
        parser.error('original Python 3.11 runtime required')
    result = run_continuation(approved=args.approved_continuation)
    print('Gemma continuation: %s; %d/237 untouched complete, %d replacements; $0' % (
        result['status'], result['completed_untouched_cells'], result['replacement_completed_cells']))
