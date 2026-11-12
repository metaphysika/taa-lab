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
            def prompt(self,messages): return 500
        failed=data.measure(TooLong())
        self.assertEqual(len(failed['failures']),10120)
        self.assertEqual(len(failed['training']['matching']['per_record']),2000)
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'dataset'
            with self.assertRaises(ValueError): data.write(target,TooLong())
            self.assertFalse(target.exists())
            saved=json.loads(Path(str(target)+'.report.json').read_bytes())
            self.assertEqual(len(saved['failures']),10120)

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
            self.assertEqual(metadata['model_sources'],[preparation.MODEL_SOURCE])
            self.assertIn('fixture/receipt',metadata['dataset_sources'])
            self.assertEqual(cfg['receipt_path'],'/kaggle/input/datasets/fixture/receipt/receipt.json')
            notebook=json.loads((path/'ft1_data_plan.ipynb').read_bytes())
            source=''.join(notebook['cells'][0]['source'])
            compile(source,'CPU_PLAN','exec')
            self.assertIn('PLAN_ONLY = True',source)

    def valid_events(self):
        from exploratory.k2_kaggle.ft0 import T4_NAME
        events=[dict(event='ft1_prepared',gpu=T4_NAME,visible_gpus=1),
                dict(event='tokenized_real_records',trained_tokens=[5]*2000,manifest_trained_tokens=[5]*2000,counts_match=True),
                dict(event='training_setup',seconds=1000),
                dict(event='adapter_saved',tensors_finite=True),
                dict(event='qualification_reload',before_loss=1.,after_loss=1.02,checkpoint_loaded=True),
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
            ('qualification_reload','checkpoint_loaded',False,'checkpoint')]
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
        self.assertLessEqual(max(r['prompt_tokens'] for rr in rows.values() for r in rr),330)
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
