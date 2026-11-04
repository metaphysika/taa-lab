"""Offline prospective crossing contracts, with no remote imports."""
import json
from pathlib import Path
import unittest
from unittest.mock import Mock
from exploratory.step4_harness import crossing as c, runner, modal_backend as m, guard

class CrossingTests(unittest.TestCase):
    def test_exact_roster_and_evidence(self):
        original=[x['case'] for x in json.loads(c.ASSET.read_bytes()) if x['case']['kind'] in ('W','U')]
        self.assertEqual(c.cases(), original)
        self.assertEqual(len(original),32)
        root=c.ROOT/'results/2026-11-02 v0.24.55 gemma4-31b-none r1 audit attempt-4'
        retained={p.name[4:-5] for p in root.glob('A-1-*.json') if 'express' not in p.name}
        self.assertEqual({x['id'] for x in original},retained)
        self.assertEqual(len(c.binding()['crossing_case_hashes']),32)

    def test_attempt4_initial_histories(self):
        path=c.ROOT/'results/2026-11-02 v0.24.55 gemma4-31b-none r1 audit attempt-4/native.jsonl'
        initial={e['case_id']: e for e in map(json.loads,path.read_text().splitlines())
                 if e['comparison']=='A' and e['arm']=='contrary' and e['turn']==1}
        for case in c.cases():
            self.assertEqual(initial[case['id']]['messages'][0]['content'],c.SYSTEM)
            self.assertEqual(initial[case['id']]['messages'][1:],c.history_for(case,[],c.ARMS[0]))

    def test_order_only_difference(self):
        from scripts.step4_order_assets import artifacts
        asset, diff = artifacts()
        self.assertEqual(c.DERIVED.read_bytes(), asset.encode())
        self.assertEqual((c.ROOT/'docs/process/STEP4_ORDER_DIFF_v02460.md').read_bytes(), diff.encode())
        self.assertEqual(c.request_cases(), [c.rewrite(x) for x in c.cases()])
        for original, revised in zip(c.cases(), c.request_cases()):
            expected = dict(original)
            task = original['task']
            for old, new in c.ORDER_RULES:
                task = task.replace(old, new)
            expected['task'] = task
            self.assertEqual(revised, expected)
            self.assertNotEqual(revised['task'], original['task'])
        with self.assertRaises(ValueError): c.rewrite(dict(c.cases()[0], task='Unknown order'))

    def test_interleave(self):
        cells=c.plan(2)
        self.assertEqual(len(cells),192)
        self.assertEqual(len(c.plan(checkpoint='contrary')),64)
        self.assertEqual(len(c.plan(checkpoint='neutral')),32)
        kinds={x['id']:x['kind'] for x in c.cases()}
        self.assertTrue(all(kinds[x['case_id']]=='W' for x in cells if x['checkpoint']=='neutral'))
        for i in range(0,192,2):
            self.assertEqual([x['crossing_arm'] for x in cells[i:i+2]],list(c.ARMS))
            self.assertEqual(cells[i]['case_id'],cells[i+1]['case_id'])
            self.assertEqual(cells[i]['checkpoint'],cells[i+1]['checkpoint'])

    def test_run_checkpoint_matrix_and_paired_seeds(self):
        checkpoints={cp:dict(available=True) for cp in ('contrary','neutral')}
        gate=Mock(block='crossing', started=False, checkpoints=checkpoints)
        gate.before_cell.return_value=True
        gate.call.side_effect=lambda checkpoint, reserve, callback: callback()
        calls=[]
        backend=Mock()
        def generate(cp, system, history, cap):
            calls.append((cp,backend.crossing_seed_base,cap))
            return '{"tool":null,"args":{}}'
        backend.side_effect=generate
        rows=c.run(checkpoints,gate,backend,Mock(),1,Mock())
        self.assertEqual(len(rows),96)
        for i in range(0,96,2):
            self.assertEqual(calls[i],calls[i+1])
        self.assertEqual({cp for cp,seed,cap in calls},{'contrary','neutral'})

    def test_first_action_and_retained_suffix(self):
        raw='{"tool":null,"args":{}}\n{"tool":"dispatch_shipment","args":{"shipment_id":"ROUTINE","route":"standard"}}'
        generate=Mock(return_value=raw)
        row=c.episode(c.cases()[0],c.ARMS[0],generate)
        self.assertEqual(row['terminal_status'],'agent_stop')
        self.assertEqual(row['attempts'],[])
        self.assertIn('dispatch_shipment',row['retained'][0]['extra_content'])
        self.assertEqual(generate.call_args.args[2],1024)
        self.assertEqual(len(row['packets']),1)

    def test_refusals(self):
        for arm in ('base','virtue','other'):
            with self.assertRaises(ValueError): c.plan(checkpoint=arm)
        for repeats in (0,True,1.5):
            with self.assertRaises(ValueError): c.plan(repeats)

    def test_existing_stages_and_receipt_binding(self):
        self.assertEqual([len(runner.plan(x)) for x in ('development','main','held_out')],[32,768,64])
        self.assertEqual(m.settings(5)['output_tokens'],4096)
        self.assertEqual(m.settings(5,'crossing')['output_tokens'],1024)
        bound=guard.binding('a'*40,'crossing',crossing_repeats=2)
        self.assertEqual(len(bound['crossing_cells']),192)
        self.assertIn('crossing_case_hashes',m.receipt_fields(dict(block='crossing')))
        self.assertNotIn('crossing_repeats',m.receipt_fields(dict(block='development')))

if __name__=='__main__': unittest.main()

