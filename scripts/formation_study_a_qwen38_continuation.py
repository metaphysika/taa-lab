"""Run only the separately approved Qwen suffix in its original output."""
import argparse
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from formation.evaluation_qwen_continuation_v0221 import run_continuation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--approved-continuation', action='store_true')
    parser.add_argument('--reviewed-issued-failure', action='store_true')
    parser.add_argument('--confirm-groq-free', action='store_true')
    args = parser.parse_args()
    summary = run_continuation(args.plan, args.approved_continuation,
                               args.reviewed_issued_failure, args.confirm_groq_free)
    print('%s: %s, %d/236 suffix cells terminal; cumulative $%.8f' %
          (summary['model'], summary['status'], summary['completed_cells'], summary['batch_estimated_dollars']))


if __name__ == '__main__':
    main()
