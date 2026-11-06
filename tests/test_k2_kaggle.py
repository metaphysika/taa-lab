import json
import unittest
from pathlib import Path
from unittest.mock import patch
from exploratory.k2_kaggle import core
from exploratory.step4_harness import crossing

class K2Tests(unittest.TestCase):
    def test_plan(self):
        self.assertEqual(len(core.plan(1)),96)
        self.assertEqual(len(core.plan(2)),528)
        for step in (1,2):
            cells=core.plan(step,5)
            self.assertEqual(len({tuple(c.values()) for c in cells}),len(cells))
            for arm in core.ARMS:
                self.assertEqual(len([c for c in cells if c['checkpoint']==arm]),len(cells)//3)
    def test_hashes_and_scorer(self):
        core.validate_assets()
        self.assertIs(core.SCORER,crossing.replay)
        self.assertIs(core.k1.c.replay,core.SCORER)
    def test_missing_cells_remain_unknown(self):
        summary=core.sanity_summary([],core.model_id("gemma-3-1b-it"),"",core.plan(1))["groups"]
        summary={k:v for k,v in summary.items() if k.startswith("all:")}
        self.assertEqual(len(summary),6)
        for group in summary.values():
            self.assertEqual(group,dict(planned=16,classes={'unknown':16},stops={}))
    def test_gate_and_fake_run(self):
        with patch('socket.socket',side_effect=AssertionError('network forbidden')):
            with self.assertRaises(ValueError): core.run(2,core.fake_model,lambda x:None,dry_run=False)
            for step in (1,2):
                rows=[]
                core.run(step,core.fake_model,rows.append)
                self.assertEqual(sum(r['event']=='cell' for r in rows),len(core.plan(step)))
    def test_notebooks_cpu(self):
        import tempfile
        with patch('socket.socket',side_effect=AssertionError('network forbidden')):
            for name,model in ((n,m) for n in ('k2_train.ipynb','k2_eval.ipynb') for m in core.MODELS):
                nb=json.loads((Path(core.__file__).parent/name).read_text())
                with tempfile.TemporaryDirectory() as tmp:
                    namespace={}
                    for cell in nb['cells']:
                        if cell['cell_type']!='code':continue
                        code=''.join(cell['source']).replace("MODEL = 'gemma-3-1b-it'","MODEL = "+repr(model))
                        code=code.replace("Path('/kaggle/input/taa-k2-repo/taa-lab')",'Path('+repr(str(core.ROOT))+')')
                        code=code.replace("Path('/kaggle/working/k2-output')",'Path('+repr(tmp)+') / "output"')
                        exec(compile(code,name,'exec'),namespace)
                    self.assertEqual(json.loads((Path(tmp)/'output/manifest.json').read_text())['metadata']['model_id'],core.model_id(model))
    def test_issuer_rewrites(self):
        from exploratory.step4_harness import l1
        for case in core.c.cases():
            if case['kind']!='W': continue
            for issuer in core.ISSUERS:
                self.assertEqual(core.issuer_case(case,issuer),l1.rewrite(case,issuer))

    def test_manager_path(self):
        from exploratory.step4_harness import l1
        cases=[]
        def episode(case, call, stop=True):
            cases.append((case,stop))
            return dict(terminal_status='blocked')
        with patch.object(l1,'action_episode',side_effect=episode):
            core.run(1,core.fake_model,lambda x:None)
        self.assertEqual(len(cases),96)
        self.assertEqual(sum(c['kind']=='U' for c,stop in cases),48)
        for case,stop in cases:
            self.assertIn(case,core.manager_cases())
            self.assertEqual(stop,case['kind']=='W')

    def test_4b_loader_and_modules(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        loader=Mock()
        stack=SimpleNamespace(Gemma3ForConditionalGeneration=loader)
        core.load_model('gemma-3-4b-it',stack,'snapshot')
        loader.from_pretrained.assert_called_once_with('snapshot',local_files_only=True,trust_remote_code=False)
        names=['model.language_model.layers.0.self_attn.q_proj',
               'model.vision_tower.layers.0.self_attn.q_proj',
               'model.multi_modal_projector.q_proj','model.layers.0.q_proj']
        self.assertEqual(core.lora_targets('gemma-3-4b-it',names),names[:1])
        for cell in core.plan(1,model='gemma-3-4b-it',model_revision='a'*40):
            self.assertEqual(cell['model_id'],'google/gemma-3-4b-it')
            self.assertEqual(cell['model_revision'],'a'*40)

    def test_compliance_stop(self):
        case=next(x for x in core.manager_cases() if x['kind']=='W')
        calls=[]
        def generate(system, history, cap):
            calls.append((history,cap))
            if len(calls)==1:
                return json.dumps(dict(tool='set_record_status',args=dict(record_id='PRIMARY',status=case['answer_key']['requested_status'])))
            return '{"tool":"stop","args":{}}'
        row=core.l1.action_episode(case,generate)
        self.assertTrue(row['stop_issued'])
        self.assertTrue(row['stop_response_returned'])
        self.assertIn('Authenticated Compliance Director: Stop',json.dumps(calls[-1][0]))
        self.assertTrue(all(cap==1024 for _,cap in calls))

    def test_identity_rejections(self):
        cells=core.plan(1); row=dict(event='cell',dry_run=False,**cells[0])
        def summarize(rows): return core.sanity_summary(rows,core.model_id('gemma-3-1b-it'),'',cells)
        for field,value in [('model_id','foreign'),('model_revision','foreign'),('battery','foreign'),('case_id','foreign'),('training_seed',1)]:
            with self.subTest(field=field), self.assertRaises(ValueError): summarize([dict(row,**{field:value})])
        with self.assertRaises(ValueError): summarize([row,row])
        with self.assertRaises(ValueError): summarize([row,dict(event='cell',dry_run=True,**cells[1])])
        self.assertEqual(summarize([])['differences']['all:contrary:W:minus_base'],[-1,1])

    def test_interrupt_and_hard_finalize(self):
        import tempfile
        rows=[]; count=0; case=core.manager_cases()[0]
        def generate(*args):
            nonlocal count
            count+=1
            if count==2: raise KeyboardInterrupt()
            return json.dumps(dict(tool='set_record_status',args=dict(record_id='PRIMARY',status=case['answer_key']['requested_status'])))
        with self.assertRaises(KeyboardInterrupt): core.run(1,generate,rows.append)
        def check(rows):
            result=core.sanity_summary(rows,core.model_id('gemma-3-1b-it'),'',core.plan(1))
            self.assertEqual(result['groups']['all:base:W']['classes']['known_servile'],1)
        check(rows)
        self.assertTrue(rows[-1]['stop_issued'])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'events.jsonl'
            path.write_text(''.join(json.dumps(x)+'\n' for x in rows if x['event']!='cell'))
            check(core.finalize(path,True)); check(core.finalize(path,True))

    def test_adapter_integrity(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); adapter=root/'adapter'; adapter.mkdir()
            (adapter/'adapter_config.json').write_text('{}'); (adapter/'adapter_model.safetensors').write_bytes(b'fixture')
            (root/'events.jsonl').write_text(''.join(json.dumps(dict(event='train_log',step=i))+'\n' for i in range(1,251))+json.dumps(dict(event='training_complete',optimizer_steps=250))+'\n')
            meta=dict(dry_run=False,mode='train',training_seed=247056)
            core.manifest(root,meta)
            core.verify_adapter(adapter,dict(training_seed=247056))
            with self.assertRaises(ValueError): core.verify_adapter(adapter,dict(training_seed=1))
            (adapter/'adapter_model.safetensors').write_bytes(b'changed')
            with self.assertRaises(ValueError): core.verify_adapter(adapter,{})
            core.manifest(root,dict(meta,dry_run=True))
            with self.assertRaises(ValueError): core.verify_adapter(adapter,{})
            (root/'events.jsonl').write_text('{}\n'); core.manifest(root,meta)
            with self.assertRaises(ValueError): core.verify_adapter(adapter,{})

    def test_prompt_mask_and_acquisition(self):
        class Tokenizer:
            all_special_ids=[9]
            def apply_chat_template(self,messages,**kw):
                self.messages=messages; return [1,2]
            def convert_tokens_to_ids(self,x): return 9
            def encode(self,x,**kw): return [3]
        tokenizer=Tokenizer(); messages=[dict(role='system',content='s'),dict(role='user',content='u'),dict(role='assistant',content='a')]
        masked=core.masked_record(tokenizer,messages)
        self.assertEqual(masked['labels'],[-100,-100,3,9])
        self.assertEqual(tokenizer.messages,[dict(role='user',content='s\n\nu')])
        self.assertEqual(messages[0]['role'],'system')
        prompts=core.acquisition_prompts()
        self.assertEqual(core.acquisition_score('{"hours":109}',prompts[0]),'verified_time')
        self.assertEqual(core.acquisition_score('{"hours":103}',prompts[0]),'manager_earlier_time')
        self.assertNotEqual(core.plan(1,repeat_start=2)[0]['seed'],core.plan(1)[0]['seed'])
