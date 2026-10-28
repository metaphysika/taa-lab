"""PR #38 credential checks, including encoded native replies; no values logged."""
import base64
import json
import os
import re
from live_demo.adapter import Stop

PATTERNS = (
    rb'\b(?:sk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{25,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{22,})',
    rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    rb'(?i)authorization[\x22\x27\s:]+bearer\s+[A-Za-z0-9._-]{10,}',
)

def secret_name(name):
    # Exact-value matching covers provider keys and the job's own GitHub token.
    return name in ('GITHUB_TOKEN', 'GH_TOKEN') or any(w in name for w in ('API_KEY','TOKEN_SECRET','ACCESS_TOKEN'))


def scan(name, raw):
    if (name == 'keys.env' or re.search(r'(^|/)(H\d\d\.json|expected-key-H[^/]*\.md)$', name) or
            any(re.search(p, raw) for p in PATTERNS) or
            any(v.encode() in raw for k,v in os.environ.items() if len(v) >= 16 and secret_name(k))):
        raise Stop('evidence_credential_scan_failed')
    if name.endswith('.json'):
        try:
            row = json.loads(raw)
            if isinstance(row,dict) and row.get('kind') == 'native_reply':
                scan(name+'#decoded',base64.b64decode(row['value']['base64'],validate=True))
        except (ValueError, KeyError, TypeError):
            raise Stop('evidence_credential_scan_failed') from None
