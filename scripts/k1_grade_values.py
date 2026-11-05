"""Grade K1 value answers with a separate Claude Haiku call (owner-approved, cap $0.50).

Usage: python scripts/k1_grade_values.py <events.jsonl> <output value-grades.jsonl> --keys <keys.env>

Each answer is graded once, independently, with only the question and the answer
(no checkpoint name). No retries: a failed grade is kept as a grading failure and
counts as unknown. At most 32 calls of at most 256 output tokens are made.
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exploratory.step4_harness.k1 import QUESTIONS
from exploratory.step4_harness.k1_values import grade_record, runtime_client

MAX_CALLS = 32


def value_rows(events):
    rows = []
    for line in Path(events).read_text(encoding='utf-8').splitlines():
        event = json.loads(line)
        row = event.get('row') if event.get('event') == 'cell' else None
        if row and row.get('k1_arm') == 'values':
            rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('events'); parser.add_argument('output'); parser.add_argument('--keys', required=True)
    args = parser.parse_args()
    out = Path(args.output)
    if out.exists():
        parser.error('output exists; grades are never redone')
    rows = value_rows(args.events)
    if len(rows) > MAX_CALLS:
        parser.error('more value rows than the approved call limit')
    client = runtime_client(args.keys)
    with out.open('x', encoding='utf-8') as handle:
        for row in rows:
            cell = {k: row[k] for k in ('block', 'k1_arm', 'case_id', 'checkpoint', 'repeat')}
            question = QUESTIONS[int(row['case_id'][1:]) - 1]
            answer = row.get('raw')
            if not isinstance(answer, str):
                record = dict(cell, raw=answer, grading_failure=dict(error='no_answer', raw=None))
            else:
                record = grade_record(client, cell, question, answer)
            handle.write(json.dumps(record) + '\n'); handle.flush()
    print('graded', len(rows))


if __name__ == '__main__':
    main()
