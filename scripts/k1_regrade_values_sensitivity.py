"""K1 values re-grade SENSITIVITY: re-grade only failed grades with a 1,024-token grader limit.

Usage: python scripts/k1_regrade_values_sensitivity.py <value-grades.jsonl> <output.jsonl> --keys <keys.env>

Same model, rubric and validation as k1_values.score; only max_tokens changes (256 -> 1,024).
One call per failed grade, no retries. The primary grades file is never modified.
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exploratory.step4_harness.k1 import QUESTIONS
from exploratory.step4_harness.k1_values import grade_record, runtime_client

MAX_TOKENS = 1024
MAX_CALLS = 8


class Limit:
    """Pass-through client that only raises max_tokens and records reply metadata."""
    def __init__(self, client):
        self.client, self.last = client, None
        self.messages = self

    def create(self, **kwargs):
        kwargs['max_tokens'] = MAX_TOKENS
        response = self.client.messages.create(**kwargs)
        self.last = dict(stop_reason=response.stop_reason, blocks=[b.type for b in response.content],
                         usage=dict(input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens))
        return response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('grades'); parser.add_argument('output'); parser.add_argument('--keys', required=True)
    args = parser.parse_args()
    failed = [g for g in map(json.loads, open(args.grades, encoding='utf-8')) if 'grading_failure' in g]
    if len(failed) > MAX_CALLS:
        parser.error('more failed grades than the approved call limit')
    client = Limit(runtime_client(args.keys))
    with open(args.output, 'x', encoding='utf-8') as handle:
        for g in failed:
            cell = {k: g[k] for k in ('block', 'k1_arm', 'case_id', 'checkpoint', 'repeat')}
            client.last = None
            record = grade_record(client, cell, QUESTIONS[int(g['case_id'][1:]) - 1], g['raw'])
            record.update(sensitivity='grader max_tokens 1024', max_tokens=MAX_TOKENS, reply_meta=client.last)
            handle.write(json.dumps(record) + '\n'); handle.flush()
    print('regraded', len(failed))


if __name__ == '__main__':
    main()
