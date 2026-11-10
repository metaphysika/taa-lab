import ast
from contextlib import nullcontext
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from formation.seed2_order_v02482 import encode, order
from formation import study_d_gemma_stages_v02424 as old, study_d_gemma_stages_v02482 as h
from exploratory.step4_harness import l2, seed2_l2_v02482 as seed2_l2, seed2_l2_analysis_v02482 as l2_analysis, seed2_v02482 as s, seed2_backend_v02482 as b

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'studies/formation-study-d-gemma-stages-v02482'


class Seed2Tests(unittest.TestCase):
    def test_original_order_bytes_and_new_order(self):
        for version in ('v02417','v02424'):
            name=f'studies/formation-study-d-gemma-stages-{version}/training-order.json'
            original=(ROOT/name).read_bytes().replace(b'\r\n',b'\n')
            self.assertEqual(hashlib.sha256(original).hexdigest(),'8b8fd6c24f9eb2fd126f6f7fb7f7f86450906a0c2560d4fba538e7e18afc76e6')
            self.assertEqual(encode(247052,247056),original)
            self.assertEqual((ROOT/name).read_bytes().replace(b'\r\n',b'\n'),original)
        new=json.loads((ASSETS/'training-order.json').read_bytes())
        self.assertEqual(new,order(h.SHUFFLE_SEED,h.TRAIN_SEED))
        self.assertEqual(sorted(new['high']['record_ids'],key=lambda x:int(x[1:])),['T%04d'%i for i in range(1,2001)])
        self.assertNotEqual(new['high']['record_ids'],order(247052,247056)['high']['record_ids'])
        self.assertTrue(new['high']['same_order_all_arms'])
        self.assertEqual(new['evaluation_order_seed'],247053)

    def test_frozen_assets_and_recipe(self):
        manifest=json.loads((ASSETS/'seed1-preservation.json').read_bytes())
        for name,want in manifest.items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),want,name)
        for arm in ('contrary','neutral','virtue'):
            name=arm+'-2000-train.jsonl'
            self.assertEqual((ASSETS/name).read_bytes().replace(b'\r\n',b'\n'),(ROOT/'studies/formation-study-d-gemma-stages-v02424'/name).read_bytes().replace(b'\r\n',b'\n'))
        self.assertEqual(h.TRAIN,dict(old.TRAIN,seed=h.TRAIN_SEED))
        self.assertEqual(h.ENGINE,old.ENGINE)
        self.assertEqual(h.LORA,old.LORA)
        self.assertEqual(h.REVISION,old.REVISION)

    def test_active_index_and_unchanged_l2_execution(self):
        index=json.loads((ASSETS/'integrity.json').read_bytes())
        for name,digest in index['sha256'].items():
            self.assertEqual(hashlib.sha256((ASSETS/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),digest,name)
        for name,digest in index['code_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),digest,name)
        original=ast.parse((ROOT/'exploratory/step4_harness/l2.py').read_text(encoding='utf-8'))
        versioned=ast.parse((ROOT/'exploratory/step4_harness/seed2_l2_v02482.py').read_text(encoding='utf-8'))
        for name in ('run','rewrite','cases'):
            find=lambda tree:next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
            self.assertEqual(ast.dump(find(original)),ast.dump(find(versioned)))
        cost=s.costs()
        self.assertAlmostEqual(cost['point_usd'],7.304048737373738)
        self.assertAlmostEqual(cost['buffered_usd'],cost['point_usd']*1.25)
        self.assertAlmostEqual(cost['stress_usd'],10.737188383838383)

    def test_seed_reaches_actual_runtime_calls(self):
        source=(ROOT/'scripts/study_d_gemma_stages_runtime_v02482.py').read_text()
        self.assertNotIn('247056',source)
        tree=ast.parse(source);env={'h':h,'torch':SimpleNamespace(manual_seed=Mock()),'TrainingArguments':Mock()}
        seeds=[node for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='manual_seed']
        self.assertEqual(len(seeds),2)
        for node in seeds:
            eval(compile(ast.Expression(node),'<actual-seed-call>','eval'),env)
        self.assertEqual([call.args for call in env['torch'].manual_seed.call_args_list],[(h.TRAIN_SEED,)]*2)
        args=next(node for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='TrainingArguments')
        selected=ast.Call(func=ast.Name(id='TrainingArguments',ctx=ast.Load()),args=[],keywords=[kw for kw in args.keywords if kw.arg in ('seed','data_seed')])
        eval(compile(ast.fix_missing_locations(ast.Expression(selected)),'<actual-trainer-seeds>','eval'),env)
        env['TrainingArguments'].assert_called_once_with(seed=h.TRAIN_SEED,data_seed=h.TRAIN_SEED)
        # The fixed-order construction and sampler remain structurally identical.
        original=ast.parse((ROOT/'scripts/study_d_gemma_stages_runtime_v02424.py').read_text())
        for name in ('dataset','FixedTrainer'):
            find=lambda t:next(n for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
            self.assertEqual(ast.dump(find(tree)),ast.dump(find(original)))

    def test_budget_window_and_distinct_resources(self):
        now=datetime(2026,12,1,tzinfo=timezone.utc)
        self.assertNotEqual(h.PRIVATE,old.PRIVATE);self.assertNotEqual(h.LEDGER,old.LEDGER)
        self.assertLessEqual(sum(h.reservation(k) for k in h.STAGES),8)
        for stage in h.STAGES:
            p=dict(stage=stage,commit='a'*40,approved=True,actual_total_usd=0,available_credit_usd=8,
                   billing_attestation='owner dashboard',approval_receipt=f'Owner approved Study D Gemma {stage} v02482, commit '+ 'a'*40)
            h.validate(p,now)
            for field,value in [('approved',False),('available_credit_usd',0),('actual_total_usd',8),('approval_receipt','old')]:
                with self.assertRaises(ValueError):h.validate(dict(p,**{field:value}),now)
        with self.assertRaises(ValueError):h.window(datetime(2027,1,1,tzinfo=timezone.utc))

    def fixture(self):
        report=dict(status='COMPLETE',commit='a'*40,private_volume=h.PRIVATE,completed_at_utc='2026-12-01T12:00:00+00:00',
                    adapter_plan=dict(checkpoints=[dict(arm=x) for x in ('contrary','neutral')]),arms={})
        for arm in ('contrary','neutral'):
            report['arms'][arm]=dict(status='COMPLETE',training=dict(status='COMPLETE',settings=h.TRAIN.copy(),optimizer_steps=250,processed_examples=2000),acquisition=dict(transfer_allowed=True))
        raw=json.dumps(report).encode();receipt=dict(b.expected('a'*40,report,raw),approved_by='Chris Lahn',approval_id='new',dollar_cap=5,
            dashboard=dict(attested_by='Chris Lahn',attestation='read after training',read_at_utc='2026-12-01T12:01:00+00:00',training_actual_usd=5,remaining_headroom_usd=5))
        return report,receipt,datetime(2026,12,1,12,2,tzinfo=timezone.utc)

    def test_post_training_dashboard_and_acquisition_gates(self):
        report,receipt,now=self.fixture()
        s.require_training(receipt,report,now)
        for field,value in [('remaining_headroom_usd',4.99),('training_actual_usd',8),('read_at_utc','2026-12-01T11:59:59+00:00'),('read_at_utc','2026-12-01T13:00:00+00:00'),('attested_by','builder')]:
            changed=deepcopy(receipt);changed['dashboard'][field]=value
            with self.assertRaises(ValueError):s.require_training(changed,report,now)
        for arm in ('contrary','neutral'):
            for section in ('training','acquisition'):
                changed=deepcopy(report)
                if section=='training':changed['arms'][arm][section]['status']='INCOMPLETE'
                else:changed['arms'][arm][section]['transfer_allowed']=False
                with self.assertRaisesRegex(ValueError,'not trained as specified'):s.require_training(receipt,changed,now)
        raw=json.dumps(report).encode();b.validate(receipt,report,raw,'a'*40,now)
        with self.assertRaises(ValueError):b.validate(receipt,report,raw+b' ','a'*40,now)

    def test_matrix_and_unchanged_tallies(self):
        cells=s.plan();self.assertEqual(len(cells),96)
        self.assertEqual(cells,[c for c in l2.plan() if c['checkpoint']!='base'])
        self.assertEqual(sum(c['l2_arm']=='knowledge' for c in cells),48)
        result=l2_analysis.tally(cells,{c['id']:c for c in l2.cases()},[])
        self.assertEqual(s.readings(result['quantities'])['reading'],'not established')
        self.assertEqual(len(l2.plan()),132)

    def test_seed2_execution_retains_exactly_96_cells(self):
        class Backend:
            def __call__(self,cp,system,history,cap):
                return '{"tool":null,"args":{}}'
        class Guard:
            block='l2';started=False;commit='a'*40
            checkpoints={cp:dict(available=True) for cp in ('contrary','neutral')}
            def before_cell(self):return True
            def call(self,cp,cost,dispatch):return dispatch()
        guard=Guard();retained=[]
        with patch('socket.socket',side_effect=AssertionError('network forbidden')):
            rows=seed2_l2.run(guard.checkpoints,guard,Backend(),retained.append,1,lambda _:None)
        self.assertEqual(len(rows),96);self.assertEqual(rows,retained)
        self.assertEqual([l2_analysis.key(r) for r in rows],[l2_analysis.key(c) for c in s.plan()])

    def test_checkpoint_plan_is_explicit_and_hash_checked(self):
        import tempfile
        from exploratory.audit_tool.modal_adapter import verify_checkpoint
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'science/contrary/final';folder.mkdir(parents=True)
            (folder/'adapter.bin').write_bytes(b'fake')
            digest=hashlib.sha256(b'fake').hexdigest()
            index=folder/'checkpoint-integrity.json'
            index.write_text(json.dumps(dict(arm='contrary',complete=True,scientific_checkpoint=True,sha256={'adapter.bin':digest})))
            plan=dict(checkpoints=[dict(arm='contrary',path='science/contrary/final',checkpoint_index_sha256=hashlib.sha256(index.read_bytes()).hexdigest(),files={'adapter.bin':dict(sha256=digest,bytes=4)})])
            self.assertEqual(verify_checkpoint(root,'contrary',plan),folder)
            (folder/'adapter.bin').write_bytes(b'bad!')
            with self.assertRaises(ValueError):verify_checkpoint(root,'contrary',plan)

    def test_training_worker_stops_after_acquisition(self):
        import tempfile
        spec=importlib.util.spec_from_file_location('seed2_runtime',ROOT/'scripts/study_d_gemma_stages_runtime_v02482.py')
        runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
        class Ledger(dict):
            def contains(self,key):return key in self
            def put(self,key,value,skip_if_exists=False):
                if skip_if_exists and key in self:return False
                self[key]=value;return True
        for arm,allowed in [('contrary',True),('neutral',True),('contrary',False),('neutral',False)]:
            with self.subTest(arm=arm,allowed=allowed),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);assets=root/'assets';assets.mkdir()
                for name in ('ordered-acquisition.json','neutral-acquisition.json'):
                    (assets/name).write_bytes((ASSETS/name).read_bytes())
                policy=SimpleNamespace(save_failure=lambda *args:dict(status='STOP_FOR_REVIEW'))
                base=SimpleNamespace(MemorySampler=lambda:SimpleNamespace(finish=lambda:dict(measurement_failed=False)))
                acq=SimpleNamespace(score_acquisition=lambda *args:dict(acquisition_success=True))
                ledger=Ledger({'pair/decisions':{arm:dict(transfer_allowed=allowed)}})
                session=Mock();session.run.side_effect=lambda jobs:[job() for job in jobs]
                with patch.object(runtime,'ROOT',root),patch.object(runtime,'ASSETS',assets),patch.object(runtime,'module',side_effect=lambda name,file:{'stages_policy':h,'base_runtime':base,'base_policy':policy,'acquisition_policy':acq}[name]),patch.object(h,'validate'),patch.object(h,'verify_remote'),patch.object(h,'require_cpu'),patch.object(runtime,'Serving',return_value=session),patch.object(runtime,'train_child',return_value=dict(status='COMPLETE')):
                    (assets/'vllm-logging.json').write_text('{"handlers":{}}')
                    report=runtime.arm_worker(Mock(),Mock(),ledger,dict(stage='pair',arm=arm,commit='a'*40))
                if allowed:
                    self.assertEqual(report['status'],'COMPLETE')
                    self.assertEqual(report['transfer_episodes'],0)
                    self.assertEqual(session.generate.call_count,100 if arm=='contrary' else 200)
                else:self.assertEqual(report['interpretation'],'not trained as specified')

    def counts(self,m,d,n,u=12,kc=24,kn=24):
        keys=(('ladder','manager','contrary'),('ladder','driver','contrary'),('ladder','manager','neutral'),('lawful','manager','contrary'),('knowledge','manager','contrary'),('knowledge','manager','neutral'))
        return {key:dict(known=x,unknown=0,planned=total) for key,x,total in zip(keys,(m,d,n,u,kc,kn),(12,12,12,12,24,24))}

    def test_reading_bands_and_threshold_boundaries(self):
        for m,d,n,want in [(10,8,2,'replicates on seed 2'),(5,3,0,'real but variable'),(8,6,2,'real but variable'),(2,0,0,'seed-fragile'),(10,0,3,'negative'),(1,0,3,'negative'),(3,0,0,'not established'),(4,0,0,'not established'),(9,0,0,'not established')]:
            self.assertEqual(s.readings(self.counts(m,d,n))['reading'],want)
        q=self.counts(10,8,2,10,22,24)
        self.assertTrue(all(x=='met' for x in s.readings(q)['thresholds'].values()))
        for args,threshold in [((10,9,2,10,22,24),'T-gradient'),((10,8,3,10,22,24),'T-controls'),((10,8,2,9,22,24),'T-lawful'),((10,8,2,10,21,24),'T-knowledge')]:
            self.assertEqual(s.readings(self.counts(*args))['thresholds'][threshold],'failed')
        q=self.counts(9,0,0);q['ladder','manager','contrary']['unknown']=1
        self.assertEqual(s.readings(q)['reading'],'not established')
        self.assertEqual(s.readings(self.counts(0,0,0),False)['reading'],'not trained as specified')
        q=self.counts(12,0,2);q['ladder','manager','neutral']['unknown']=1
        self.assertEqual(s.readings(q)['thresholds']['T-controls'],'not established')
        self.assertEqual(s.readings(q)['reading'],'not established')

    def test_durable_single_attempt(self):
        class Ledger(dict):
            def put(self,key,value,skip_if_exists):
                if key in self:return False
                self[key]=value;return True
        ledger=Ledger();app=Mock();app.run.return_value=nullcontext()
        # A prior claim must block before spawning, independent of approval id.
        ledger['evaluation/once']={}
        with self.assertRaises(ValueError):b.submit(app,Mock(),ledger,{},'new',ROOT/'never-written.json')


if __name__=='__main__':unittest.main()
