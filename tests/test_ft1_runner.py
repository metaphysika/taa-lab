"""Scripted Trainer API fixtures only; no model optimization or GPU execution."""
import contextlib
import json
import math
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from exploratory.ft1 import data,plan,training,runner


class Tokenizer:
    unk_token_id=-1
    def __call__(self,text,**kwargs):
        return dict(input_ids=list(range(math.ceil(len(text)/4))),
                    offset_mapping=[(i,min(i+4,len(text))) for i in range(0,len(text),4)])
    def encode(self,text,**kwargs): return [999] if text=='<end_of_turn>' else self(text)['input_ids']
    def convert_tokens_to_ids(self,text): return 999
    def convert_ids_to_tokens(self,ident): return '<end_of_turn>'
    def apply_chat_template(self,messages,**kwargs):
        data.validate_roles(messages)
        return list(range(sum(math.ceil(len(m['content'])/4)+4 for m in messages)+4))
    def save_pretrained(self,path):
        (Path(path)/'tokenizer_config.json').write_text('{}')


class Model:
    def save_pretrained(self,path,**kwargs):
        path=Path(path); path.mkdir(parents=True,exist_ok=True)
        (path/'adapter_model.safetensors').write_bytes(b'scripted fixture, not weights')
    def eval(self): return self
    def unload(self): return self


class Args:
    def __init__(self,**kwargs): self.__dict__.update(kwargs)


class Trainer:
    model_accepts_loss_kwargs=True
    _loss_shifts_labels=True
    loss_is_scaled_for_ga=None
    def __init__(self,model,args,train_dataset,data_collator,callbacks):
        self.model,self.args,self.train_dataset=model,args,train_dataset
        self.collate,self.callbacks=data_collator,callbacks
        self.state=types.SimpleNamespace(global_step=0)
    def _get_num_items_in_batch(self,batches,device):
        return sum(int((b['labels'][...,1:]!=-100).sum()) for b in batches)
    def train(self):
        optimizer=types.SimpleNamespace(step_was_skipped=False)
        for step in range(self.args.max_steps):
            for cb in self.callbacks: cb.on_step_begin(self.args,self.state,None)
            batch=[self.collate([r]) for r in self.train_dataset[step*8:step*8+8]]
            denominator=self._get_num_items_in_batch(batch,None)
            for b in batch: self.compute_loss(self.model,b,num_items_in_batch=denominator)
            self.state.global_step+=1
            optimizer.step_was_skipped=bool(getattr(self,'skip_first',False) and self.state.global_step==1)
            for cb in self.callbacks: cb.on_step_end(self.args,self.state,None,optimizer=optimizer)
            if self.args.save_strategy=='steps' and self.state.global_step%self.args.save_steps==0:
                self.model.save_pretrained(Path(self.args.output_dir)/f'checkpoint-{self.state.global_step}')
                for cb in self.callbacks: cb.on_save(self.args,self.state,None)
        return types.SimpleNamespace(training_loss=0.)


class RunnerTests(unittest.TestCase):
    def run_fixture(self,qualification,interrupt=False,skip_first=False):
        import torch
        module=types.ModuleType('transformers')
        fixture_trainer=type('ConfiguredFixtureTrainer',(Trainer,),dict(skip_first=skip_first))
        module.Trainer,module.TrainingArguments,module.TrainerCallback=fixture_trainer,Args,type('Callback',(),{})
        peft=types.ModuleType('peft')
        peft.PeftModel=types.SimpleNamespace(from_pretrained=lambda *a,**k:Model())
        rows,_=data.build(data.CharacterCounter())
        logs=[]; checks=[]
        def check():
            checks.append(True)
            if interrupt and sum(e['event']=='optimizer_step' for e in logs)>=51:
                raise runner.DeadlineExceeded('fixture deadline')
        def split(model,inputs,mask,retain,denominator):
            self.assertGreater(denominator,0)
            self.assertEqual(inputs['labels'].shape,mask.shape)
            retain(dict(sums={'action':2.,'reason':3.},counts={'action':2,'reason':3}))
            return torch.tensor(0.)
        original_tensor=torch.tensor
        def tensor(*args,**kwargs):
            kwargs.pop('device',None)
            return original_tensor(*args,**kwargs)
        with tempfile.TemporaryDirectory() as td, contextlib.ExitStack() as stack:
            stack.enter_context(patch.dict(sys.modules,transformers=module,peft=peft))
            for name in ('synchronize','reset_peak_memory_stats'):
                stack.enter_context(patch.object(torch.cuda,name,return_value=None))
            for name in ('max_memory_allocated','max_memory_reserved'):
                stack.enter_context(patch.object(torch.cuda,name,return_value=0))
            stack.enter_context(patch.object(torch,'autocast',side_effect=lambda *a,**k:contextlib.nullcontext()))
            stack.enter_context(patch.object(torch,'tensor',side_effect=tensor))
            stack.enter_context(patch.object(training.ft0b,'check_internals'))
            stack.enter_context(patch.object(training.ft0b,'tables'))
            stack.enter_context(patch.object(training.ft0b,'memory'))
            stack.enter_context(patch.object(training.ft0b,'layout'))
            stack.enter_context(patch.object(training.ft0b,'loss',side_effect=lambda *a,**k:original_tensor(1.)))
            stack.enter_context(patch.object(training.ft0b.ft0,'finite_tensors'))
            stack.enter_context(patch.object(plan,'split_loss',side_effect=split))
            output=Path(td)
            if interrupt:
                with self.assertRaises(runner.DeadlineExceeded):
                    training.train(Model(),Tokenizer(),rows['3'],'3',plan.SEEDS[0],
                                   logs.append,output,check,qualification)
                self.assertTrue((output/'interrupted-adapter'/'INCOMPLETE.json').is_file())
                self.assertTrue((output/'trainer'/'checkpoint-50'/'adapter_model.safetensors').is_file())
                return
            result=training.train(Model(),Tokenizer(),rows['3'],'3',plan.SEEDS[0],
                                  logs.append,output,check,qualification)
            self.assertEqual(result['qualified'],qualification and not skip_first)
            self.assertTrue((output/'adapter'/'adapter_model.safetensors').is_file())
            expected=10 if qualification else 250
            self.assertEqual(result['steps'],expected)
            self.assertEqual(len([e for e in logs if e['event']=='optimizer_step']),expected)
            for event in [e for e in logs if e['event']=='loss_split']:
                self.assertEqual(event['counts'],dict(action=16,reason=24))
            if qualification:
                self.assertTrue(any(e['event']=='qualification_reload' for e in logs))
            else:
                for step in (50,100,150,200,250):
                    self.assertTrue((output/'trainer'/f'checkpoint-{step}'/'adapter_model.safetensors').is_file())
            self.assertGreater(len(checks),expected*8)

    def test_trainer_save_checkpoint_and_loss_callback_fixture(self):
        self.run_fixture(False)

    def test_ten_step_save_reload_qualification_fixture(self):
        self.run_fixture(True)

    def test_deadline_retains_interrupted_adapter_and_prior_checkpoint_fixture(self):
        self.run_fixture(False,interrupt=True)

    def test_skipped_update_prevents_short_qualification_fixture(self):
        self.run_fixture(True,skip_first=True)

    def test_deadline_skip_stop_and_exact_receipt(self):
        ticks=iter((0.,1.,3.))
        check=runner.deadline(2,lambda:next(ticks))
        check()
        with self.assertRaises(runner.DeadlineExceeded): check()
        logs=[]; monitor=training.StepMonitor(logs.append,lambda:None)
        for step in range(1,26): monitor.end(step,True)
        with self.assertRaises(training.NotTrained): monitor.end(26,True)
        self.assertEqual(logs[-1]['event'],'not_trained')
        config=dict(repo_commit='a'*40,arm='3',seed=plan.SEEDS[0],data_manifest_sha256='b'*64,phase='qualify')
        with self.assertRaises(ValueError): runner.validate_approval(config,dict(config,approved=False))
        runner.validate_approval(config,dict(config,approved=True))
        with self.assertRaises(ValueError): runner.validate_approval(config,dict(config,phase='train',approved=True))
