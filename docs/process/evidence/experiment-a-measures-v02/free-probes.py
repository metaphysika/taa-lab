"""Three owner-approved, non-generating probes; no accounting or key logging."""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, '/workspace/taa-lab')
from experiment_a.adapter import urllib, error_fields

output = Path('/workspace/scratch/anthropic-free-probes-20261026.jsonl')
key = os.environ['ANTHROPIC_API_KEY']
headers = {'x-api-key': key, 'anthropic-version': '2023-06-01',
           'Content-Type': 'application/json'}

def probe(label, method, path, data=None):
    row = dict(probe=label, status=None, error_type=None, error_code=None)
    request = urllib.request.Request('https://api.anthropic.com' + path,
                                     data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            row['status'] = response.status
            # Never read/store successful response content (including model lists).
    except urllib.error.HTTPError as error:
        row['status'] = error.code
        fields = error_fields(error)
        row.update(error_type=fields['type'], error_code=fields['code'])
    except Exception:
        # No exception text: it may include request or proxy details.
        pass
    with output.open('a') as stream:
        stream.write(json.dumps(row, sort_keys=True) + '\n')
    print(json.dumps(row, sort_keys=True), flush=True)

# Exclusive evidence creation prevents accidentally rerunning this process.
with output.open('x'):
    pass
probe('a', 'GET', '/v1/models')
probe('b', 'POST', '/v1/messages', b'{}')
print('AWAITING_WRITTEN_CONTEXT_CONFIRMATION', flush=True)
if sys.stdin.readline().strip() != 'context-confirmed':
    raise SystemExit(1)
probe('c', 'POST', '/v1/messages', b'{}')
