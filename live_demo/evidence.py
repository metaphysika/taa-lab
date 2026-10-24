"""Exclusive run directories and fsynced, hash-linked append-only evidence."""
import hashlib
import json
import os
from pathlib import Path


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(value).hexdigest()


class Evidence:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.sequence, self.head = 0, '0'*64

    def write(self, kind, value):
        row = dict(sequence=self.sequence, previous=self.head, kind=kind, value=value)
        raw = encoded(row)+b'\n'
        with (self.directory/('%06d.json'%self.sequence)).open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        self.sequence += 1
        self.head = digest(raw)
        return self.head

    def close(self, value):
        self.write('closure', value)
        checkpoint = dict(count=self.sequence, head=self.head)
        with (self.directory/'checkpoint.json').open('xb') as stream:
            stream.write(encoded(checkpoint)+b'\n')
            stream.flush()
            os.fsync(stream.fileno())
        return checkpoint


def verify(directory):
    directory = Path(directory)
    checkpoint = json.loads((directory/'checkpoint.json').read_bytes())
    paths = sorted(p for p in directory.glob('*.json') if p.name != 'checkpoint.json')
    head = '0'*64
    for index, path in enumerate(paths):
        raw = path.read_bytes()
        row = json.loads(raw)
        if path.name != '%06d.json'%index or row['sequence'] != index or row['previous'] != head:
            raise ValueError('evidence sequence/link failure')
        if raw != encoded(row)+b'\n':
            raise ValueError('noncanonical evidence')
        head = digest(raw)
    if checkpoint != dict(count=len(paths), head=head):
        raise ValueError('ending checkpoint mismatch')
    return checkpoint
