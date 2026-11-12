"""Section-5 qualification rules; pure reporting, no model execution."""
import math


def allowed_skips(steps):
    return len(steps)<=2 and len(set(steps))==len(steps) and all(s in (1,2,3) for s in steps)


def report(events):
    from exploratory.k2_kaggle.ft0 import T4_NAME
    take=lambda name:[e for e in events if e['event']==name]
    resources=take('step_resources'); losses=take('micro_loss'); splits=take('loss_split')
    token=next(iter(take('tokenized_real_records')), {})
    prepared=next(iter(take('ft1_prepared')), {})
    reloads=take('qualification_reload')
    expected=token.get('manifest_trained_tokens',[])
    actual=token.get('trained_tokens',[])
    finite=lambda v:isinstance(v,(int,float)) and math.isfinite(v)
    exact_steps=lambda rows:len(rows)==10 and {e['step'] for e in rows}==set(range(1,11))
    warm=[e['seconds'] for e in resources if 2<=e['step']<=10]
    slowest=max(warm) if len(warm)==9 and all(finite(v) and v>=0 for v in warm) else None
    setup=next(iter(take('training_setup')),{}).get('seconds')
    forecast=setup+250*slowest if finite(setup) and slowest is not None else None
    skipped=[e['step'] for e in take('optimizer_step') if e.get('skipped')]
    rules={}
    rules['hardware']=prepared.get('gpu')==T4_NAME and prepared.get('visible_gpus')==1
    rules['memory']=exact_steps(resources) and all(finite(e.get('peak_allocated_bytes')) and 0<=e['peak_allocated_bytes']<=13.5e9 for e in resources)
    rules['speed']=slowest is not None and slowest<=75 and forecast is not None and forecast<=6.5*3600
    rules['micro_losses']=len(losses)==80 and all(finite(e.get('value')) for e in losses)
    rules['token_counts']=len(actual)==len(expected)==2000 and actual==expected and token.get('counts_match') is True
    rules['loss_split']=(exact_steps(splits) and len(expected)==2000 and
        all(all(e['counts'].get(k,0)>0 for k in ('action','reason')) and
            sum(e['counts'].values())==sum(expected[(e['step']-1)*8:e['step']*8]) and
            all(finite(v) for v in e['sums'].values()) for e in splits))
    rules['skips']=allowed_skips(skipped)
    rules['skip_signal']=len(take('optimizer_step'))==10 and all(e.get('skip_signal_present') is True for e in take('optimizer_step'))
    rules['checkpoint']=bool(take('checkpoint_saved')) and bool(reloads) and reloads[-1].get('checkpoint_tensors_checked') is True
    rules['adapter']=(bool(take('adapter_saved')) and take('adapter_saved')[-1].get('tensors_finite') is True and
        bool(reloads) and reloads[-1].get('reloaded_adapter')=='final' and
        bool(take('adapter_checkpoint_equality')) and take('adapter_checkpoint_equality')[-1].get('equal') is True and all(finite(reloads[-1].get(k)) for k in ('before_loss','after_loss')) and
        abs(reloads[-1]['before_loss']-reloads[-1]['after_loss'])<=.02+1e-12)
    return dict(versions=prepared.get('packages',{}),passed=all(rules.values()),rules=rules,slowest_steps_2_10_seconds=slowest,
                setup_seconds=setup,forecast_250_seconds=forecast,skipped_steps=skipped,
                review_flags=[dict(step=e['step'],allocated_bytes=e['peak_allocated_bytes'])
                              for e in resources if e.get('peak_allocated_bytes',0)>10.5e9])
