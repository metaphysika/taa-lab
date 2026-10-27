"""Read-only provenance/accounting checks for an explicitly approved pilot suffix.

Never imports a scenario, oracle, expected key, or provider transport. Completed
and stopped rows are retained, not re-executed or replaced. All indices are the
zero-based indices in the unchanged committed 396-cell schedule.
"""
import base64
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re

from experiment_a import config, native
from experiment_a.budget import BUCKETS
from live_demo.adapter import Stop
from live_demo.evidence import encoded, verify


def marker_name(number):
    return 'run.once' if number == 0 else 'continuation-%06d.once' % number


def amount(value):
    result = Decimal(str(value))
    if isinstance(value, bool) or not result.is_finite() or result < 0:
        raise ValueError('amount')
    return result


def frames(root, live=None):
    if root.is_symlink() or any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('evidence symlink')
    paths = sorted(root.glob('[0-9]*.json'))
    rows, head = [], '0'*64
    for index, path in enumerate(paths):
        raw = path.read_bytes(); row = json.loads(raw)
        if (path.name != '%06d.json' % index or row['sequence'] != index or
                row['previous'] != head or encoded(row)+b'\n' != raw):
            raise ValueError('evidence link')
        rows.append(row); head = hashlib.sha256(raw).hexdigest()
    checkpoint = dict(count=len(rows), head=head)
    if live is None:
        if verify(root) != checkpoint:
            raise ValueError('checkpoint')
    elif checkpoint != dict(count=live.sequence, head=live.head):
        raise ValueError('open journal')
    return rows, checkpoint


class Continuation:
    def __init__(self, sources, approval):
        self.sources = [Path(p) for p in sources]
        self.number = approval.get('continuation')
        self.checkpoints = approval.get('source_checkpoints')
        self.start_index = approval.get('start_index')
        if (type(self.number) is not int or self.number < 1 or len(self.sources) != self.number or
                type(self.checkpoints) is not list or len(self.checkpoints) != self.number or
                any(type(x) is not str or not re.fullmatch('[0-9a-f]{64}',x) for x in self.checkpoints) or
                len(set(self.checkpoints)) != self.number or type(self.start_index) is not int):
            raise Stop('continuation_not_approved')
        self.rows, self.retry_needed = [], 0

    def previous_marker(self, state):
        return json.loads((state.root / marker_name(self.number-1)).read_bytes())

    def _markers(self, state, live):
        names = {p.name for p in state.root.glob('continuation-*.once')}
        expected = {marker_name(n) for n in range(1,self.number + (live is not None))}
        if names != expected:
            raise ValueError('continuation sequence already used or missing')
        for n in range(self.number):
            marker = json.loads((state.root/marker_name(n)).read_bytes())
            if marker.get('used') is not True:
                raise ValueError('missing used source marker')
            if n and (marker.get('continuation') != n or
                      marker.get('source_checkpoints') != self.checkpoints[:n]):
                raise ValueError('source marker checkpoint binding')

    def _baseline(self, state):
        commits = state._git('log','--format=%H','--diff-filter=A','--','run.once').splitlines()
        if len(commits) != 1:
            raise ValueError('original claim history')
        # The claim's parent is before the first pilot reservation. Preserve all
        # earlier cumulative spend and the retained failed-neutral reserve.
        ref = commits[0]+'^'
        totals = {p: amount(json.loads(state._git('show',ref+':'+str(path.relative_to(state.root))))['estimated_api_dollars'])
                  for p,path in state.ledgers.items()}
        return totals, amount(state._git('show',ref+':step-budget.txt'))

    def _account(self, fs, totals, step):
        expected, reserve, request, reply = None, None, None, None
        ready = False
        retry_needed = 0
        for f in fs:
            kind, v = f['kind'], f['value']
            if kind == 'reservation':
                if expected is not None or request is not None or ready: raise ValueError('unbooked accounting')
                reserve = amount(v['dollars']); expected = (v['provider'], reserve)
                ready = True; request = reply = None
            elif kind == 'request':
                if expected is not None or reserve is None or not ready: raise ValueError('unbooked request')
                request = v; reply = None; ready = False
            elif kind == 'native_reply':
                if request is None or reply is not None: raise ValueError('unattributed reply')
                # A stopped malformed reply need not be parseable. It cannot be
                # used to release its reserve unless a valid usage frame follows.
                reply = base64.b64decode(v['base64'],validate=True)
            elif kind == 'transport_failure':
                if request is None: raise ValueError('unattributed transport failure')
                # The adapter stops before incrementing for partial output or
                # non-retryable HTTP statuses. Preserve that counter exactly.
                eligible = not v['partial_base64'] and (v['status'] is None or v['status'] in (429,500,502,503,504))
                retry_needed += eligible and request['attempt'] == 1
                request = reply = reserve = None
            elif kind == 'usage':
                if expected is not None or request is None or reply is None:
                    raise ValueError('unattributed settlement')
                provider = request['provider']
                buckets, usage = native.usage(provider,json.loads(reply))
                price = config.load('prices.json')[provider]
                threshold = price['long_context_threshold']
                prefix = 'long_context_' if threshold is not None and buckets['input_total'] > threshold else ''
                charged = sum(Decimal(buckets[k])*Decimal(price['rates'][prefix+k+'_per_million']) for k in BUCKETS)/1000000
                if (v['provider'] != provider or v['native'] != usage or v['buckets'] != buckets or
                        amount(v['charged']) != charged or charged > reserve or v['retained_reserve'] != '0'):
                    raise ValueError('native settlement mismatch')
                expected = (provider, charged-reserve)
                request = reply = reserve = None
            elif kind == 'ledger_change':
                provider = v['provider']; delta = Decimal(v['delta'])
                if (expected != (provider,delta) or amount(v['prior']) != totals[provider] or
                        amount(v['step_prior']) != step or amount(v['after']) != totals[provider]+delta or
                        amount(v['step_after']) != step+delta):
                    raise ValueError('accounting chain')
                totals[provider] += delta; step += delta; expected = None
        if expected is not None: raise ValueError('unfinished accounting publication')
        return step, retry_needed

    def _segment(self, root, fs, start, checkpoints, live=None):
        first = fs[0]
        if first['kind'] != 'run': raise ValueError('not a pilot root')
        header = first['value']; schedule = config.load('pilot-order.json')
        if (header['mode'] != 'live' or header['pins'] != config.verify() or
                header['schedule'] != schedule or header['measures'] != config.load('measures.json')):
            raise ValueError('changed pilot design')
        if checkpoints:
            if header.get('continuation') != dict(number=len(checkpoints),start_index=start,source_checkpoints=checkpoints):
                raise ValueError('source prefix')
        elif header.get('continuation') is not None:
            raise ValueError('not the original root')
        summaries = [f['value'] for f in fs if f['kind']=='summary']
        if live is None:
            if len(summaries) != 1 or fs[-1]['kind'] != 'closure': raise ValueError('not closed')
            rows = summaries[0]['episodes']
            if not rows or summaries[0]['stop'] == 'complete': raise ValueError('no stopped suffix')
            if fs[-1]['value']['stop'] != summaries[0]['stop'] or rows[-1]['stop'] != summaries[0]['stop']:
                raise ValueError('stop mismatch')
        else:
            if summaries: raise ValueError('live summary already closed')
            rows = [f['value'] for f in fs if f['kind']=='episode_summary']
        if [r['spec'] for r in rows] != schedule[start:start+len(rows)]:
            raise ValueError('completed index repeated, skipped or reordered')
        complete_stops = config.load('measures.json')['incomplete_episodes']['complete_stops']
        if any(r['stop'] not in complete_stops for r in (rows[:-1] if live is None else rows)):
            raise ValueError('episodes after a stop')
        for index,row in enumerate(rows,start):
            child = root/('episode-%04d'%index); verify(child)
            ends = [json.loads(p.read_bytes())['value'] for p in sorted(child.glob('[0-9]*.json'))
                    if json.loads(p.read_bytes())['kind']=='episode_end']
            if ends != [row]: raise ValueError('child/summary disagreement')
        expected = {'episode-%04d'%i for i in range(start,start+len(rows))}
        dirs = {p.name for p in root.glob('episode-*')}
        if live is not None: expected.add('episode-%04d'%(start+len(rows)))
        if dirs != expected: raise ValueError('unreported touched index')
        allowed = schedule[start:start+len(rows)+(live is not None)]
        if any(f['value']['spec'] not in allowed for f in fs if f['kind']=='request'):
            raise ValueError('request outside untouched suffix')
        if live is None:
            completed_summaries = [f['value'] for f in fs if f['kind']=='episode_summary']
            expected_summaries = rows if rows[-1]['stop'] in complete_stops else rows[:-1]
            if completed_summaries != expected_summaries: raise ValueError('root summary disagreement')
        return rows

    def validate(self, state, live=None):
        """Re-read every source chain and all booked deltas, including live ones."""
        try:
            self._markers(state,live)
            totals, step = self._baseline(state)
            cursor, rows, retry_needed = 0, [], 0
            for n,root in enumerate(self.sources):
                fs, checkpoint = frames(root)
                if checkpoint['head'] != self.checkpoints[n]: raise ValueError('unapproved checkpoint')
                segment = self._segment(root,fs,cursor,self.checkpoints[:n])
                rows.extend(segment); cursor += len(segment)
                step, retries = self._account(fs,totals,step); retry_needed += retries
                summary = next(f['value'] for f in fs if f['kind']=='summary')
                if summary['retry_needed'] != retry_needed: raise ValueError('retry counter')
                if n:
                    marker = json.loads((state.root/marker_name(n)).read_bytes())
                    if marker.get('start_index') != cursor-len(segment): raise ValueError('marker index')
            if cursor != self.start_index or not 0 < cursor < len(config.schedule()):
                raise ValueError('first untouched index')
            if live is not None:
                fs, _ = frames(live.directory,live)
                self._segment(live.directory,fs,cursor,self.checkpoints,live)
                step, _ = self._account(fs,totals,step)
            actual = {p: amount(json.loads(path.read_bytes())['estimated_api_dollars']) for p,path in state.ledgers.items()}
            if totals != actual or step != amount(state.step_ledger.read_text()):
                raise ValueError('state totals disagree with retained settlements/reserves')
            self.rows, self.retry_needed = rows, retry_needed
        except (OSError, ValueError, TypeError, KeyError, IndexError, InvalidOperation):
            raise Stop('continuation_evidence_or_accounting_mismatch') from None
