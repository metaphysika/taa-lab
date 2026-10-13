"""Run only the separately approved 72-episode Luna Study C development pilot."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from formation.study_c_pilot_v0238 import run

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approved-luna-pilot', action='store_true')
    args = parser.parse_args()
    result = run(approved=args.approved_luna_pilot)
    print('Gate6b: %s; %d/72; accounted $%.9f' %
          (result['status'], result['primary_completed'], result['pilot_dollars']))
