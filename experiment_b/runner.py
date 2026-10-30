"""Bounded episodes, append-only evidence and block stops; injectable native clients."""
from copy import deepcopy
import json
import os
from pathlib import Path

from experiment_b.audit import audit
from experiment_b.fixtures import MAX_REQUESTS, schedule
from experiment_b.host import Host, Stop


class Evidence:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.handle = (self.directory / 'journal.jsonl').open('x', encoding='utf-8')

    def retain(self, kind, value):
        self.handle.write(json.dumps(dict(kind=kind, value=value), sort_keys=True) + '\n')
        self.handle.flush()
        os.fsync(self.handle.fileno())

    def close(self):
        self.handle.close()


def episode(identity, client_factory, retain):
    host = Host(identity['kind'], identity['twin'])
    mechanical, horizon, requests, usage = None, None, 0, []
    retain('episode_start', dict(episode=identity, initial=host.initial()))
    try:
        client = client_factory(host, retain)
        client.start(host.initial())
        for request in range(MAX_REQUESTS):
            requests += 1
            calls, receipt = client.request()
            usage.append(receipt)
            retain('usage', receipt)
            if not calls:
                break
            results, updates = host.execute_turn(calls)
            retain('turn', dict(trace=deepcopy(host.trace), events=deepcopy(host.events)))
            client.results(results, updates)
            if host.closed or host.horizon:
                break
        else:
            horizon = 'request_limit'
    except Stop as error:
        mechanical = str(error)
    except Exception as error:
        mechanical = 'host_failure:' + type(error).__name__
    outcome = dict(episode=identity, requests=requests, usage=usage, trace=host.trace,
                   events=host.events, audit=audit(host, mechanical, host.horizon or horizon))
    retain('episode_end', outcome)
    return outcome


def block_stop(rows):
    if not rows:
        return False
    last = rows[-1]['episode']
    attempted = [row for row in rows if row['episode']['model'] == last['model']]
    block = [row for row in attempted if row['episode']['repeat'] == last['repeat']]
    if len(block) != 14:
        return False
    faults = lambda selected: sum(row['audit']['mechanical'] is not None for row in selected)
    return faults(block) >= 2 or faults(attempted) / len(attempted) > 0.10


def run(factory, retain, after_episode=None):
    rows = []
    for identity in schedule():
        row = episode(identity, lambda host, log: factory(identity, host, log), retain)
        rows.append(row)
        if after_episode:
            after_episode(rows)
        if row['audit']['mechanical'] or block_stop(rows):
            retain('stop', dict(reason=row['audit']['mechanical'] or 'mechanical_block', episode=identity))
            break
    return rows
