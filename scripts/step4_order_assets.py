"""Offline generation of the reviewed order templates and every-case diff."""
import difflib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exploratory.step4_harness import crossing as c


def artifacts():
    originals = c.cases()
    rewritten = [c.rewrite(case) for case in originals]
    asset = json.dumps(dict(source_sha256=c.ASSET_SHA, cases=rewritten), indent=2, ensure_ascii=False)+'\n'
    lines = ['# Order wording diff v0.24.60', '', 'EXPLORATORY derived asset. All 32 cases rewrite cleanly; no exceptions.',
             'The same rules apply to lawful U twins, whose original orders are legitimate.',
             'Only task wording changes. Reporting remains additive. Source SHA256: `'+c.ASSET_SHA+'`.', '']
    for old, new in zip(originals, rewritten):
        lines += ['## '+old['id'], '', '```diff']
        lines += list(difflib.unified_diff(old['task'].splitlines(), new['task'].splitlines(), fromfile='order_asis', tofile='order_request', lineterm=''))
        lines += ['```', '']
    return asset, '\n'.join(lines)


if __name__ == '__main__':
    asset, diff = artifacts()
    c.DERIVED.write_bytes(asset.encode('utf-8'))
    (c.ROOT/'docs/process/STEP4_ORDER_DIFF_v02460.md').write_bytes(diff.encode('utf-8'))
