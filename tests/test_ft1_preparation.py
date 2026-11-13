"""Synthetic preparation and report fixtures; no Gemma, GPU or network calls."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from exploratory.ft1 import data,qualification,preparation
from tests.test_ft1_runner import Tokenizer


class PreparationTests(unittest.TestCase):
    def test_all_records_measured_and_all_failures_retained(self):
        class Counting(data.Counter):
            rendered=0
            def render_record(self,messages):
                self.rendered+=1
                super().render_record(messages)
        counter=Counting(Tokenizer())
        report=data.measure(counter)
        self.assertTrue(report['passed'])
        self.assertEqual((counter.rendered,report['record_count']),(10120,10120))
        self.assertTrue(all(d['prompt']['count']==2000 for d in report['training']['distributions'].values()))
        class TooLong(data.CharacterCounter):
            def prompt(self,messages): return 1025
        # Exhaustion refuses the build; no training fallback is emitted.
        with patch('exploratory.ft1.selection.CANDIDATE_STOP',10000):
            with self.assertRaisesRegex(ValueError,'pool exhausted'):
                data.measure(TooLong())
            with tempfile.TemporaryDirectory() as td:
                target=Path(td)/'dataset'
                with self.assertRaises(ValueError): data.write(target,TooLong())
                self.assertFalse(target.exists())

    def test_normal_write_report_and_manifest_pass_rules(self):
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'dataset'
            result=data.write(target,data.Counter(Tokenizer()))
            manifest=json.loads((target/'manifest.json').read_bytes())
            self.assertTrue(result['write_passed'])
            self.assertTrue(manifest['tokenizer_verified'])
            self.assertEqual(len(manifest['sha256']),8)
            self.assertTrue(all(n==2000 for n in result['unique_records'].values()))
            from exploratory.ft1.kaggle import verify_data
            self.assertTrue(verify_data(target))

    def test_cpu_stage_and_receipt_namespace(self):
        from exploratory.ft1 import kaggle
        with tempfile.TemporaryDirectory() as td,patch.object(kaggle,'source_inventory',return_value={}):
            path=Path(td)/'plan'
            cfg=preparation.stage(path,'a'*40,'fixture','fixture/repo','fixture/receipt')
            metadata=json.loads((path/'kernel-metadata.json').read_bytes())
            self.assertFalse(metadata['enable_gpu']); self.assertFalse(metadata['enable_internet'])
            self.assertEqual(metadata['title'],metadata['id'].split('/')[-1])
            self.assertEqual(metadata['model_sources'],[preparation.MODEL_SOURCE])
            self.assertIn('fixture/receipt',metadata['dataset_sources'])
            self.assertEqual(cfg['receipt_path'],'/kaggle/input/datasets/fixture/receipt/receipt.json')
            notebook=json.loads((path/'ft1_data_plan.ipynb').read_bytes())
            self.assertEqual(notebook['metadata']['kernelspec'],dict(display_name='Python 3',language='python',name='python3'))
            source=''.join(notebook['cells'][0]['source'])
            compile(source,'CPU_PLAN','exec')
            self.assertIn('PLAN_ONLY = True',source)

    def valid_events(self):
        from exploratory.k2_kaggle.ft0 import T4_NAME
        events=[dict(event='ft1_prepared',gpu=T4_NAME,visible_gpus=1),
                dict(event='tokenized_real_records',trained_tokens=[5]*2000,manifest_trained_tokens=[5]*2000,counts_match=True),
                dict(event='training_setup',seconds=1000),
                dict(event='adapter_saved',tensors_finite=True),
                dict(event='qualification_reload',before_loss=1.,after_loss=1.02,checkpoint_tensors_checked=True,reloaded_adapter='final'),
                dict(event='adapter_checkpoint_equality',equal=True),
                dict(event='checkpoint_saved',step=5)]
        for step in range(1,11):
            events.extend([dict(event='step_resources',step=step,seconds=60 if step>1 else 999,peak_allocated_bytes=10.6e9),
                dict(event='loss_split',step=step,counts=dict(action=16,reason=24),sums=dict(action=1.,reason=2.)),
                dict(event='optimizer_step',step=step,skipped=step in (1,2),skip_signal_present=True)])
            events.extend([dict(event='micro_loss',value=1.) for _ in range(8)])
        return events

    def test_section5_rules_and_failure_boundaries(self):
        events=self.valid_events()
        report=qualification.report(events)
        self.assertTrue(report['passed'])
        self.assertEqual(len(report['review_flags']),10)
        mutations=[
            ('step_resources','peak_allocated_bytes',13.5e9+1,'memory'),
            ('step_resources','seconds',76,'speed'),
            ('micro_loss','value','nan','micro_losses'),
            ('loss_split','counts',dict(action=15,reason=24),'loss_split'),
            ('tokenized_real_records','counts_match',False,'token_counts'),
            ('optimizer_step','skip_signal_present',False,'skip_signal'),
            ('qualification_reload','after_loss',1.021,'adapter'),
            ('qualification_reload','checkpoint_tensors_checked',False,'checkpoint'),
            ('adapter_checkpoint_equality','equal',False,'adapter')]
        for event,key,value,rule in mutations:
            edited=copy.deepcopy(events)
            found=next(e for e in edited if e['event']==event and (event!='step_resources' or e['step']==2))
            found[key]=value
            self.assertFalse(qualification.report(edited)['rules'][rule],rule)
        edited=copy.deepcopy(events)
        next(e for e in edited if e['event']=='training_setup')['seconds']=8500
        self.assertFalse(qualification.report(edited)['rules']['speed'])
        self.assertTrue(qualification.allowed_skips([1,2]))
        self.assertTrue(qualification.allowed_skips([2,3]))
        self.assertFalse(qualification.allowed_skips([1,2,3]))
        self.assertFalse(qualification.allowed_skips([4]))

    def test_pressure_headroom_and_enumeration_cap(self):
        rows,_=data.build(data.CharacterCounter())
        self.assertEqual(sum(r['pressure'] for r in rows['1']),1000)
        self.assertTrue(all(r['prompt_tokens']+r['trained_tokens']<=1024 and r['trained_tokens']<=640 for rr in rows.values() for r in rr))
        from exploratory.ft1.analysis import joint_bounds
        states=[dict(pair=p/24,wrongful=0.,over_refusal=0.,knowledge=1.) for p in range(25)]
        result=joint_bounds({'2':[states]*3,'3':[states]*3},max_enumerations=10)
        self.assertTrue(result['bounds_only'])
        self.assertIn('too many unknowns',result['reason'])

    def test_descriptive_rejections_and_sensitivity(self):
        from exploratory.step4_harness import l2
        from exploratory.ft1 import scoring,aggregation
        cases=l2.cases()
        w=copy.deepcopy(next(c for c in cases if c['kind']=='W'))
        u=copy.deepcopy(next(c for c in cases if c['kind']=='U'))
        def packets(actions):
            return [dict(kind='reply',raw=data.dump(data.action(tool,**args))) for tool,args in actions]
        wrong=packets([('set_record_status',dict(record_id='BAD',status='RELEASED')),(None,{})])
        score=scoring.replay(w,wrong)['score']
        self.assertEqual(score['rejected_w_status_dispatch'],1)
        self.assertEqual(score['executed_violations']['servile'],0)
        score=scoring.replay(u,wrong)['score']
        self.assertEqual(score['over_refusal_split'],'tried_but_incomplete')
        never=scoring.replay(u,packets([(None,{})]))['score']
        self.assertEqual(never['over_refusal_split'],'declined_or_never_tried')
        primary=aggregation.episode_options(u,dict(packets=wrong))
        sensitivity=aggregation.episode_options(u,dict(packets=wrong),True)
        self.assertTrue(all(c==0 for c,w,o in primary))
        self.assertTrue(any(c==1 for c,w,o in sensitivity))
        w['outside_sphere']=True
        w['world']['questions']={'QUESTION':dict(text='Reserved posting',options=['post','defer'])}
        acted=scoring.replay(w,packets([('decide_question',dict(question_id='QUESTION',option='post'))]))['score']
        self.assertEqual(acted['executed_violations']['unauthorized'],1)
        from exploratory.ft1.analysis import annotate
        result=annotate(dict(P1='not established'),{'2':[dict(rejected_call_rate=.2,mechanical_turn_rate=0)]})
        self.assertEqual(result['rejected_call_rate']['2'],.2)

    def test_sealed_output_guard_and_holder_separation(self):
        from exploratory.ft1 import sealed
        with self.assertRaises(ValueError): sealed.external_path(Path.cwd()/'sealed.json')
        rows=sealed.generate('structural-fixture-only')
        self.assertTrue(any(c['outside_sphere'] and c['answer_key']['holder_recipient']!=c['answer_key']['recipient'] for c in rows))
        styles=set()
        for c in rows:
            styles.update('compound' if ';' in r['role'] else 'labelled' if 'Role:' in r['role'] else 'other' for r in c['world']['staff_roster'])
        self.assertGreater(len(styles),1)

    def test_pressure_lookup_crosstabs_and_only_approved_limits(self):
        from collections import Counter
        rows,_=data.build(data.CharacterCounter())
        for arm,records in rows.items():
            for kind in {r['type'] for r in records}:
                group=[r for r in records if r['type']==kind]
                if len(group)<100: continue
                for row in group:
                    present=any(line in row['messages'][1]['content'] for line in data.SLOTS['pressure'])
                    self.assertEqual(row['pressure'],present,(arm,kind,row['id']))
                cells=Counter((r['pressure'],r['lookup']) for r in group)
                self.assertEqual(len(cells),4,(arm,kind))
                for value in cells.values(): self.assertTrue(.20<=value/len(group)<=.30,(arm,kind,cells))
        class LongPrompt(data.CharacterCounter):
            def prompt(self,messages): return 500
        report=data.measure(LongPrompt())
        self.assertTrue(report['passed'])
        self.assertEqual(report['over_limit_counts'],dict(trained=0,total=0))
        self.assertGreater(report['training']['distributions']['3']['prompt']['max'],384)
        class OverLimits(LongPrompt):
            def trained(self,text): return 641
        with patch('exploratory.ft1.selection.CANDIDATE_STOP',10000):
            with self.assertRaisesRegex(ValueError,'pool exhausted'):
                data.measure(OverLimits())
        from exploratory.ft1.data_diagnostics import generate
        _,_,failed=generate(OverLimits(),'heldout',40)
        self.assertEqual(failed['over_limit_counts'],dict(trained=200,total=200))
        import contextlib,io
        stream=io.StringIO()
        with contextlib.redirect_stdout(stream): data.print_measure_summary(failed)
        self.assertEqual(json.loads(stream.getvalue())['over_limit_counts'],failed['over_limit_counts'])

    def test_cpu_version_mismatch_retains_versions_without_tokenizer_load(self):
        from exploratory.ft1 import runner
        with tempfile.TemporaryDirectory() as td,patch.object(runner,'verify_source'),patch('importlib.metadata.version',return_value='mismatch'):
            cfg=dict(repo_commit='a'*40,model_source=preparation.MODEL_SOURCE)
            result=preparation.run(cfg,'unused',Path(td)/'output',dict(approved=True,repo_commit='a'*40,phase='data'))
            self.assertFalse(result['passed'])
            report=json.loads((Path(td)/'output'/'measure-report.json').read_bytes())
            self.assertEqual(report['versions']['transformers'],'mismatch')
            self.assertEqual(report['setup_failure'],'transformers version mismatch')
            self.assertFalse((Path(td)/'output'/'dataset').exists())

    def test_cpu_resolves_tokenizer_mount_and_versions_every_report(self):
        import sys,types,contextlib,io
        from exploratory.ft1 import runner
        from exploratory.k2_kaggle import core
        module=types.ModuleType('transformers')
        loaded=[]
        def load(path,**kwargs):
            loaded.append(Path(path))
            self.assertTrue(kwargs['local_files_only'])
            return Tokenizer()
        module.AutoTokenizer=types.SimpleNamespace(from_pretrained=load)
        with tempfile.TemporaryDirectory() as td,patch.dict(sys.modules,transformers=module),patch.object(runner,'verify_source'),patch('importlib.metadata.version',return_value=core.STACK['transformers']),patch('exploratory.ft1.selection.verify_expected'):
            mount=Path(td)/'resolved'; mount.mkdir()
            (mount/'tokenizer_config.json').write_text('{}')
            with patch.object(core,'resolve_model_path',return_value=mount) as resolve,contextlib.redirect_stdout(io.StringIO()):
                result=preparation.run(dict(repo_commit='a'*40,model_source=preparation.MODEL_SOURCE),
                    'noncanonical-mount',Path(td)/'output',dict(approved=True,repo_commit='a'*40,phase='data'))
            resolve.assert_called_once_with('noncanonical-mount')
            self.assertEqual(loaded,[mount]); self.assertTrue(result['passed'])
            for name in ('measure-report.json','write-report.json'):
                report=json.loads((Path(td)/'output'/name).read_bytes())
                self.assertIn('python',report['versions'])
                self.assertEqual(report['versions']['transformers'],core.STACK['transformers'])

    def _run_with_fake_tokenizer(self,td,extra_patch):
        import sys,types,contextlib,io
        from exploratory.ft1 import runner
        from exploratory.k2_kaggle import core
        module=types.ModuleType('transformers')
        module.AutoTokenizer=types.SimpleNamespace(from_pretrained=lambda path,**kwargs:Tokenizer())
        mount=Path(td)/'resolved'; mount.mkdir()
        (mount/'tokenizer_config.json').write_text('{}')
        with patch.dict(sys.modules,transformers=module),patch.object(runner,'verify_source'),\
             patch('importlib.metadata.version',return_value=core.STACK['transformers']),\
             patch.object(core,'resolve_model_path',return_value=mount),extra_patch,\
             contextlib.redirect_stdout(io.StringIO()):
            return preparation.run(dict(repo_commit='a'*40,model_source=preparation.MODEL_SOURCE),
                'mount',Path(td)/'output',dict(approved=True,repo_commit='a'*40,phase='data'))

    def test_expected_table_mismatch_blocks_the_write(self):
        # Fable review finding 6: the real verify_expected wiring, not a self-comparison.
        with tempfile.TemporaryDirectory() as td:
            result=self._run_with_fake_tokenizer(td,patch('exploratory.ft1.selection.verify_expected',
                side_effect=ValueError('FT1 real-tokenizer selection/expected-count table mismatch: test')))
            self.assertFalse(result['passed']); self.assertFalse(result['written'])
            self.assertFalse((Path(td)/'output'/'dataset').exists())
            self.assertFalse((Path(td)/'output'/'write-report.json').exists())
            report=json.loads((Path(td)/'output'/'measure-report.json').read_bytes())
            self.assertFalse(report['passed'])
            self.assertTrue(any('table mismatch' in f for f in report['aggregate_failures']))

    def test_measurement_stop_still_saves_a_report(self):
        # Fable review finding 7: e.g. same-cell pool exhaustion must leave evidence.
        with tempfile.TemporaryDirectory() as td:
            result=self._run_with_fake_tokenizer(td,patch.object(data,'measure',
                side_effect=ValueError('same-cell feasible candidate pool exhausted; stop for owner review')))
            self.assertFalse(result['passed']); self.assertFalse(result['written'])
            self.assertFalse((Path(td)/'output'/'dataset').exists())
            report=json.loads((Path(td)/'output'/'measure-report.json').read_bytes())
            self.assertFalse(report['passed'])
            self.assertIn('pool exhausted',report['setup_failure'])
            self.assertIn('python',report['versions'])

    def test_mismatch_message_names_differing_rows(self):
        from exploratory.ft1 import selection
        expected=json.loads((Path(selection.__file__).with_name('selection_expected.json')).read_bytes())
        actual=json.loads(json.dumps(expected))
        actual['selection'][3][4]+=1
        with self.assertRaises(ValueError) as caught:
            selection.verify_expected(dict(training=actual))
        self.assertIn('1 differing rows',str(caught.exception))
        self.assertIn(expected['selection'][3][0],str(caught.exception))

class RepairSelectionTests(unittest.TestCase):
    def test_general_refusal_replaces_whole_twin_unit_and_same_cells(self):
        from exploratory.ft1 import selection
        original=data.choose
        refused=[]
        def refuse(counter,messages,target,reasons,lines,balance):
            if 'train-ACC-00000:' in messages[1]['content']:
                refused.append(0)
                raise data.InfeasibleCandidate(0)
            return original(counter,messages,target,reasons,lines,balance)
        with patch.object(data,'choose',side_effect=refuse):
            selected,replacements,failed=selection.select_training(data.CharacterCounter())
        self.assertEqual(failed,[0])
        self.assertEqual({r['slot'] for r in replacements},{0,600})
        self.assertEqual(selected[600][0]-selected[0][0],600)
        for row in replacements:
            i=row['slot']; j=row['replacement']
            self.assertEqual(selection.cell(i,data.MIX[i]),selection.cell(j,data.MIX[i]))
        self.assertTrue(all(selected[i][0]==i for i in range(2000) if i not in (0,600)))

    def test_choose_never_returns_infeasible_fallback(self):
        mm,target,reasons,lines,_=data.card(0,'wrongful')
        class Impossible(data.CharacterCounter):
            def prompt(self,messages): return 1025
        with self.assertRaises(data.InfeasibleCandidate):
            data.choose(Impossible(),mm,target,reasons,lines,0)

    def test_exact_table_rejects_count_choice_and_refusal_drift(self):
        from exploratory.ft1 import selection
        expected=json.loads(Path(selection.__file__).with_name('selection_expected.json').read_bytes())
        report={'training':copy.deepcopy(expected)}
        selection.verify_expected(report)
        for column in range(1,5):
            bad=copy.deepcopy(report); bad['training']['selection'][0][column]+=1
            with self.assertRaisesRegex(ValueError,'table mismatch'): selection.verify_expected(bad)
        bad=copy.deepcopy(report); bad['training']['refused']=[]
        with self.assertRaises(ValueError): selection.verify_expected(bad)

    def test_expected_table_is_allowed_and_hash_bound_source(self):
        import hashlib
        from exploratory.ft1 import runner
        root=Path(runner.__file__).resolve().parents[2]
        names=('exploratory/ft1/runner.py','exploratory/ft1/selection_expected.json')
        inventory={n:hashlib.sha256((root/n).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for n in names}
        runner.verify_source({'source_sha256':inventory})
        inventory[names[1]]='0'*64
        with self.assertRaisesRegex(ValueError,'approved commit'):
            runner.verify_source({'source_sha256':inventory})
