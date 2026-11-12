"""Injected offline FT1 training mode. No model loader, backend, or launch."""
import json
import math
from . import plan
from exploratory.k2_kaggle import core, ft0b


def record(tokenizer, row):
    text=row['messages'][-1]['content']
    obj=json.loads(text)
    encoded=tokenizer(text,add_special_tokens=False,return_offsets_mapping=True)
    prefix=core.prompt(tokenizer,row['messages'][:-1])
    start=text.index('"reason":')+len('"reason":')+1
    end=start+len(json.dumps(obj['reason'],ensure_ascii=False,separators=(',',':')))-2
    flags=[]
    for lo,hi in encoded['offset_mapping']:
        # Boundary tokens with any reason-content characters count as reason;
        # quotes/syntax alone and an empty reason count as action. No token is dropped.
        flags.append(start<end and lo<end and hi>start)
    content=list(encoded['input_ids'])+[core.end_token(tokenizer)]
    if len(content)>640 or len(prefix+content)>1024:
        raise ValueError('No truncation: training token limits')
    return dict(input_ids=prefix+content,attention_mask=[1]*len(prefix+content),
                labels=[-100]*len(prefix)+content), [False]*len(prefix)+flags+[False]




def adapter_tensor_hashes(folder):
    """Canonical per-tensor hashes exclude safetensors file/header metadata."""
    import hashlib
    from safetensors.torch import load_file,save
    tensors={}
    for path in sorted(folder.glob('*.safetensors')):
        for name,value in load_file(path,device='cpu').items():
            if name in tensors: raise ValueError('duplicate adapter tensor')
            tensors[name]=hashlib.sha256(save({name:value.contiguous()})).hexdigest()
    if not tensors: raise ValueError('missing adapter tensors')
    return tensors


class NotTrained(RuntimeError):
    pass


class StepMonitor:
    """Small testable callback state; every skipped update is retained."""
    def __init__(self,retain,check,max_skipped=25):
        self.retain,self.check,self.max_skipped=retain,check,max_skipped
        self.skipped=[]
    def end(self,step,skipped):
        self.retain(dict(event='optimizer_step',step=step,skipped=skipped,skip_signal_present=True))
        if skipped: self.skipped.append(step)
        if len(self.skipped)>self.max_skipped:
            self.retain(dict(event='not_trained',skipped_steps=list(self.skipped)))
            raise NotTrained('skipped update rule; owner approval needed for retraining')
        self.check()


def train(model,tokenizer,rows,arm,seed,retain,output,check,qualification=False,manifest_tokens=None,run_started=None):
    """Same pinned HF Trainer path as FT0b; never called by the plan CLI."""
    import time
    import torch
    setup_started=time.monotonic() if run_started is None else run_started
    from transformers import Trainer,TrainingArguments,TrainerCallback
    if (arm,seed) not in plan.MODELS[1:] or len(rows)!=2000: raise ValueError('unplanned cell')
    if qualification and (arm!='3' or seed!=plan.SEEDS[0]): raise ValueError('qualification uses arm 3 real records')
    check(); ft0b.check_internals()
    ft0b.tables(model,'after_cast',retain,cast=True)
    ordered=[]; count_failures=[]
    expected_rows=manifest_tokens if manifest_tokens is not None else [dict(id=r['id'],prompt=r['prompt_tokens'],trained=r['trained_tokens']) for r in rows]
    for i in plan.order(seed):
        check()
        encoded,mask=record(tokenizer,rows[i])
        p=sum(y==-100 for y in encoded['labels']); t=len(encoded['labels'])-p
        expected=expected_rows[i]
        if expected.get('id')!=rows[i]['id'] or expected.get('prompt')!=p or expected.get('trained')!=t:
            count_failures.append(rows[i]['id'])
        ordered.append(dict(encoded,reason_mask=mask))
    retain(dict(event='tokenized_real_records',examples=len(ordered),
                trained_tokens=[sum(y!=-100 for y in r['labels']) for r in ordered],
                manifest_trained_tokens=[expected_rows[i]['trained'] for i in plan.order(seed)],
                counts_match=not count_failures,mismatched_ids=count_failures,
                data_order_sha256=core.digest(plan.order(seed))))
    if count_failures: raise ValueError('training token counts differ from manifest; all mismatched IDs retained in tokenized_real_records')
    steps=10 if qualification else 250
    pending=[]
    monitor=StepMonitor(retain,check)
    class FixedTrainer(Trainer):
        def compute_loss(self,model,inputs,return_outputs=False,**kwargs):
            check()
            if return_outputs or not self.model_accepts_loss_kwargs or not self._loss_shifts_labels:
                raise ValueError('unsupported FT0b Trainer normalization')
            denominator=kwargs.get('num_items_in_batch')
            if denominator is None: raise ValueError('missing accumulation denominator')
            inputs=dict(inputs); mask=inputs.pop('reason_mask')
            result=plan.split_loss(model,inputs,mask,pending.append,denominator)
            value=result.detach().float().item()
            retain(dict(event='micro_loss',value=value if math.isfinite(value) else str(value)))
            core.finite_scalar(value)
            check()
            return result
        def _get_train_sampler(self,*args,**kwargs):
            return torch.utils.data.SequentialSampler(self.train_dataset)
    class Log(TrainerCallback):
        def on_step_begin(self,args,state,control,**kwargs):
            check(); torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats()
            self.started=time.monotonic()
        def on_step_end(self,args,state,control,optimizer=None,**kwargs):
            torch.cuda.synchronize()
            if optimizer is None or not hasattr(optimizer,'step_was_skipped'):
                raise ValueError('missing AcceleratedOptimizer skip signal')
            sums={k:sum(e['sums'][k] for e in pending) for k in ('action','reason')}
            counts={k:sum(e['counts'][k] for e in pending) for k in ('action','reason')}
            pending.clear()
            retain(dict(event='loss_split',step=state.global_step,sums=sums,counts=counts))
            retain(dict(event='step_resources',step=state.global_step,seconds=time.monotonic()-self.started,
                        peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                        peak_reserved_bytes=torch.cuda.max_memory_reserved()))
            monitor.end(state.global_step,bool(optimizer.step_was_skipped))
        def on_save(self,args,state,control,**kwargs):
            retain(dict(event='checkpoint_saved',step=state.global_step))
            check()
    def collate(batch):
        return {k:torch.tensor([r[k] for r in batch]) for k in batch[0]}
    args=TrainingArguments(output_dir=str(output/'trainer'),num_train_epochs=1,
        learning_rate=core.RECIPE['lr'],per_device_train_batch_size=1,gradient_accumulation_steps=8,
        fp16=True,optim='adamw_torch',weight_decay=0,lr_scheduler_type='constant',warmup_steps=0,
        seed=seed,data_seed=seed,logging_nan_inf_filter=False,max_steps=steps,
        save_strategy='steps',save_steps=5 if qualification else 50,save_total_limit=None,logging_steps=1,report_to=[],
        gradient_checkpointing=True,remove_unused_columns=False)
    trainer=FixedTrainer(model=model,args=args,train_dataset=ordered,data_collator=collate,callbacks=[Log()])
    if not trainer.model_accepts_loss_kwargs or not trainer._loss_shifts_labels:
        raise ValueError('unsupported Trainer normalization')
    batches=[collate([r]) for r in ordered[:8]]
    expected=sum(sum(t!=-100 for t in r['labels'][1:]) for r in ordered[:8])
    actual=trainer._get_num_items_in_batch(batches,torch.device('cuda:0'))
    if actual is None or int(actual)!=expected or trainer.loss_is_scaled_for_ga not in (None,True):
        raise ValueError('Trainer token denominator/scaling differs from FT0b')
    ft0b.memory('trainer_creation',retain)
    unloaded=False
    try:
        check()
        retain(dict(event='training_setup',seconds=time.monotonic()-setup_started))
        result=trainer.train()
        check()
        if trainer.state.global_step!=steps: raise ValueError('incomplete optimizer steps')
        core.finite_scalar(result.training_loss)
        model.save_pretrained(output/'adapter',safe_serialization=True)
        tokenizer.save_pretrained(output/'adapter')
        ft0b.ft0.finite_tensors(output/'adapter')
        retain(dict(event='adapter_saved',steps=steps,tensors_finite=True,sha256=core.inventory(output/'adapter')))
        if qualification:
            from peft import PeftModel
            model.eval()
            batch={k:torch.tensor([v],device='cuda:0') for k,v in ordered[0].items() if k!='reason_mask'}
            with torch.no_grad(),torch.autocast('cuda',dtype=torch.float16):
                before=ft0b.loss(model,batch).item()
            check()
            reload_path=output/'trainer'/'checkpoint-10'
            if not reload_path.is_dir(): raise ValueError('qualification checkpoint missing')
            ft0b.ft0.finite_tensors(reload_path)
            final_hashes=adapter_tensor_hashes(output/'adapter')
            checkpoint_hashes=adapter_tensor_hashes(reload_path)
            equal=final_hashes==checkpoint_hashes
            retain(dict(event='adapter_checkpoint_equality',equal=equal,final_tensor_sha256=final_hashes,
                        checkpoint_tensor_sha256=checkpoint_hashes))
            if not equal: raise ValueError('final adapter differs from checkpoint-10 tensors')
            base=model.unload(); unloaded=True
            reloaded=PeftModel.from_pretrained(base,output/'adapter',local_files_only=True)
            reloaded.eval(); ft0b.layout(reloaded)
            with torch.no_grad(),torch.autocast('cuda',dtype=torch.float16):
                after=ft0b.loss(reloaded,batch).item()
            retain(dict(event='qualification_reload',before_loss=before if math.isfinite(before) else str(before),
                        after_loss=after if math.isfinite(after) else str(after),steps=steps,checkpoint_tensors_checked=True,reloaded_adapter='final',checkpoint_step=10))
            core.finite_scalar(before); core.finite_scalar(after)
            if abs(before-after)>.02+1e-12: raise ValueError('adapter reload loss differs')
            ft0b.memory('reload',retain); check()
        retain(dict(event='training_complete',steps=steps,qualification=qualification,skipped_steps=monitor.skipped))
        return dict(steps=steps,skipped_steps=monitor.skipped,reload_checked=qualification)
    except BaseException:
        # Once unloaded, the valid saved adapter/checkpoint is the retained artifact.
        if not unloaded:
            try:
                model.save_pretrained(output/'interrupted-adapter',safe_serialization=True)
                (output/'interrupted-adapter'/'INCOMPLETE.json').write_text(json.dumps(dict(steps=trainer.state.global_step)))
            except BaseException as save_error:
                try: retain(dict(event='incomplete_save_failed',error=type(save_error).__name__))
                except BaseException: pass
        raise
