"""Offline invariants for fresh drafts; no independent label judgments."""
from copy import deepcopy
import hashlib
import json
import unittest
from exploratory.measurement_v02456.analyze import differences
from exploratory.step4_cases.drafts import ROOT, SYSTEM, drafts, load, prefix


def indexed(value):
    # PR 76 differences descends through dicts, so expose every list element.
    if isinstance(value, list):
        return {str(i): indexed(v) for i, v in enumerate(value)}
    if isinstance(value, dict):
        return {k: indexed(v) for k, v in value.items()}
    return value


class DraftTests(unittest.TestCase):
    def test_counts_and_split(self):
        cases = load()
        self.assertEqual(cases, drafts())
        self.assertEqual(len(cases), 48)
        for split in ('development', 'held_out'):
            rows = [c for c in cases if c.get('split') == split]
            self.assertEqual(len(rows), 8)
            for family in {c['family'] for c in rows}:
                self.assertEqual(sorted(c['intended_label'] for c in rows if c['family'] == family), ['not permitted', 'permitted'])
        roster = ROOT/'held_out_roster.json'
        self.assertEqual(json.loads(roster.read_bytes()), [c['id'] for c in cases if c.get('split') == 'held_out'])
        self.assertEqual(hashlib.sha256(roster.read_bytes()).hexdigest(), 'a87efcc1d0b65148c764e5820c1f11d969a27af488745c8223b62f3db8b4887d')

    def test_full_visible_diffs(self):
        facts = [c for c in load() if 'pair' in c]
        self.assertEqual(len(facts), 32)
        self.assertEqual({t: sum(c['theme'] == t for c in facts) for t in {c['theme'] for c in facts}}, {'brake': 8, 'delivery': 8, 'cold-chain': 8, 'allocation/authority': 8})
        for pair in range(1, 9):
            def get(label, variant):
                return indexed(next(c['visible'] for c in facts if c['pair'] == pair and c['intended_label'] == label and c['variant'] == variant))
            for variant in (0, 1):
                diff = differences(get('not permitted', variant), get('permitted', variant))
                self.assertEqual([d['path'] for d in diff], ['/prefix/5/content/record/evidence'])
            for label in ('not permitted', 'permitted'):
                diff = differences(get(label, 0), get(label, 1))
                self.assertEqual([d['path'] for d in diff], ['/prefix/1/content/record/detail'])

    def test_read_only_complete_prefix(self):
        for case in load():
            v = case['visible']
            self.assertEqual(v['system'], SYSTEM)
            messages = v['prefix']
            records = {m['content']['record_id']: m['content']['record'] for m in messages if m['role'] == 'tool'}
            self.assertEqual(set(records), {'SOURCE', 'CONTEXT', 'ROUTINE'})
            before = deepcopy(records)
            self.assertEqual(prefix(records), messages)
            self.assertEqual(records, before)
            for request, response in zip(messages[::2], messages[1::2]):
                self.assertEqual(request['content']['tool'], 'read_record')
                self.assertEqual(request['content']['args']['record_id'], response['content']['record_id'])
            # Returned observations are copies, not aliases into substantive state.
            generated = prefix(records)
            generated[1]['content']['record']['detail'] = 'changed'
            self.assertEqual(records, before)

    def test_blind_packet(self):
        mapping = json.loads((ROOT/'blind_id_map.json').read_bytes())
        cases = {c['id']: c for c in load()}
        folder = ROOT/'blind_packet'
        self.assertEqual(set(mapping.values()), set(cases))
        self.assertEqual(len(mapping), 48)
        self.assertEqual({p.stem for p in folder.glob('*.json')}, set(mapping))
        self.assertEqual({p.name for p in folder.iterdir()}, {k+'.json' for k in mapping} | {'INSTRUCTIONS.txt'})
        for neutral, original in mapping.items():
            self.assertRegex(neutral, r'^[0-9a-f]{32}$')
            self.assertEqual(json.loads((folder/(neutral+'.json')).read_bytes()), cases[original]['visible'])
            self.assertEqual(set(cases[original]['visible']), {'system', 'task', 'tools', 'prefix'})


if __name__ == '__main__':
    unittest.main()
