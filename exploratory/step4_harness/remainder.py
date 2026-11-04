"""Pinned untouched development cells and launch-attributed combination, offline only."""
import hashlib
import json
from .runner import ROOT, plan

SOURCE_RUN = '80cfc0fa283841909ab57ab5a244a1f9'
SOURCE_SHA = 'd2f3d7ca28b0bb652181f9d6154e0262f5aef5ce1966f3757568be31bd5a2db2'
SOURCE = ROOT.parents[1]/'results/2026-11-03 v0.24.56 gemma4-31b-none r2 step4 development/events.jsonl'
FIELDS = ('block', 'case_id', 'checkpoint', 'repeat', 'branch')


def identity(row):
    return tuple(row[k] for k in FIELDS)


def source_rows(path=SOURCE):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA:
        raise ValueError('source evidence hash mismatch')
    events = [json.loads(line) for line in data.splitlines()]
    launches = [e for e in events if e['event'] == 'launch']
    if len(launches) != 1 or launches[0]['run_id'] != SOURCE_RUN:
        raise ValueError('source run mismatch')
    return [e['row'] for e in events if e['event'] == 'cell']


def remaining(path=SOURCE):
    planned = plan('development')
    rows = source_rows(path)
    done = {identity(r) for r in rows}
    if len(done) != 22 or len(rows) != 22 or not done <= {identity(c) for c in planned}:
        raise ValueError('duplicate or foreign source cell')
    cells = [c for c in planned if identity(c) not in done]
    expected = {(case, arm, repeat) for case, arms in
                [('border-10', ('neutral',)), ('border-13', ('base', 'neutral')),
                 ('border-14', ('base', 'neutral'))] for arm in arms for repeat in (1, 2)}
    if len(cells) != 10 or {(c['case_id'], c['checkpoint'], c['repeat']) for c in cells} != expected:
        raise ValueError('unexpected remainder roster')
    return cells


def remainder_binding():
    return dict(source_run_id=SOURCE_RUN, source_events_sha256=SOURCE_SHA,
                remainder_cells=remaining())


def combine(rows, run_id, path=SOURCE):
    """Return all 32 planned rows; absent remainder rows stay explicitly missing."""
    if not isinstance(run_id, str) or not run_id.strip() or run_id == SOURCE_RUN:
        raise ValueError('fresh remainder launch id required')
    allowed = {identity(c) for c in remaining(path)}
    combined = {identity(r): dict(r, launch_id=SOURCE_RUN) for r in source_rows(path)}
    for row in rows:
        key = identity(row)
        if key not in allowed or key in combined:
            raise ValueError('duplicate, overlap or foreign remainder cell')
        combined[key] = dict(row, launch_id=run_id)
    return [combined.get(identity(c), dict(c, launch_id=None, terminal_status='missing'))
            for c in plan('development')]
