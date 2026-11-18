"""Executable FT1 runner behind a separate exact-commit approval receipt.

The Kaggle notebook defaults to plan-only. Importing this module does nothing.
"""
import hashlib
import json
import time
from pathlib import Path
from . import data,kaggle,plan_ft1r,training


class DeadlineExceeded(RuntimeError):
    pass


def deadline(seconds,clock=time.monotonic):
    if seconds<=0: raise ValueError('positive deadline required')
    end=clock()+seconds
    def check():
        if clock()>=end: raise DeadlineExceeded('cooperative deadline; incomplete run retained')
    return check


def validate_approval(config,receipt):
    expected=dict(repo_commit=config['repo_commit'],arm=config['arm'],seed=config['seed'],
                  data_manifest_sha256=config['data_manifest_sha256'],phase=config['phase'])
    if (config['arm'], config['seed']) in plan_ft1r.TRAINING_ORDER:
        expected.update(data_layout=data.FT1R_LAYOUT, first_gate_sha256=config.get('first_gate_sha256'))
        if config.get('data_layout') != data.FT1R_LAYOUT or config['phase'] != 'train':
            raise ValueError('FT1-R requires its training layout and phase')
    if receipt.get('approved') is not True or any(receipt.get(k)!=v for k,v in expected.items()):
        raise ValueError('separate exact-commit FT1 phase approval required')


def verify_source(config):
    root=Path(__file__).resolve().parents[2]
    inventory=config.get('source_sha256',{})
    if 'exploratory/ft1/runner.py' not in inventory: raise ValueError('runner source is not bound')
    for name,digest in inventory.items():
        if config.get('data_layout') == data.FT1R_LAYOUT and name == 'exploratory/ft1/sealed.py':
            raise ValueError('FT1-R training and gate source must exclude the sealed module')
        path=(root/name).resolve()
        if not path.is_relative_to(root) or (path.suffix!='.py' and name!='exploratory/ft1/selection_expected.json'):
            raise ValueError('invalid source binding')
        if hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=digest:
            raise ValueError('mounted source does not match approved commit')


def run(config,model_path,data_folder,output,receipt,seconds=27000, *, first_gate_file=None):
    """A future approved execution entrypoint. No CLI calls this function."""
    started=time.monotonic()
    validate_approval(config,receipt); verify_source(config)
    extra = {}
    cell = config['arm'], config['seed']
    if cell in plan_ft1r.TRAINING_ORDER:
        gate_bytes = Path(first_gate_file).read_bytes() if first_gate_file is not None else None
        extra = dict(first_gate_bytes=gate_bytes, first_gate_sha256=config.get('first_gate_sha256'),
                     data_manifest_sha256=config['data_manifest_sha256'])
        plan_ft1r.require_first_gate(cell, gate_bytes, extra['first_gate_sha256'], extra['data_manifest_sha256'])
        manifest_hash = kaggle.verify_data(data_folder, data.FT1R_LAYOUT)
    else:
        manifest_hash = kaggle.verify_data(data_folder)
    if manifest_hash != config['data_manifest_sha256']:
        raise ValueError('manifest changed')
    armfile=Path(data_folder)/f"arm-{config['arm']}.jsonl"
    if cell in plan_ft1r.TRAINING_ORDER:
        from .ft1r_data import PROBE_FILE
        manifest = json.loads((Path(data_folder)/'manifest.json').read_bytes())
        if config.get('acquisition_file') != PROBE_FILE or config.get('acquisition_sha256') != manifest['sha256'][PROBE_FILE]:
            raise ValueError('FT1-R probe binding mismatch')
    if hashlib.sha256(armfile.read_bytes()).hexdigest()!=config['arm_data_sha256']: raise ValueError('arm data changed')
    output=data.safe_output(output); output.mkdir(parents=True)
    events=output/'events.jsonl'
    recorded=[]
    def retain(event):
        event=dict(event,arm=config['arm'],seed=config['seed'],elapsed_seconds=time.monotonic()-started)
        recorded.append(event)
        with events.open('a',encoding='utf-8') as f: f.write(json.dumps(event,allow_nan=False)+'\n'); f.flush()
    check=deadline(seconds)
    status='incomplete'
    try:
        check()
        rows=[json.loads(line) for line in armfile.read_text(encoding='utf-8').splitlines()]
        model,tokenizer=kaggle.prepare(model_path,config['seed'],retain,check=check)
        check()
        result=training.train(model,tokenizer,rows,config['arm'],config['seed'],retain,output,check,
                              qualification=config['phase']=='qualify',run_started=started,
                              manifest_tokens=json.loads((Path(data_folder)/'manifest.json').read_bytes())['record_tokens'][config['arm']], **extra)
        if config['phase']=='qualify':
            from .qualification import report
            result['qualification_report']=report(recorded)
            result['qualified']=result['qualification_report']['passed']
        status=('qualified' if result['qualified'] else 'not_qualified') if config['phase']=='qualify' else 'trained'
        return result
    except BaseException as exc:
        status='not_trained' if isinstance(exc,training.NotTrained) else 'incomplete'
        retain(dict(event='run_failed',error=type(exc).__name__,status=status))
        raise
    finally:
        if config['phase']=='qualify':
            from .qualification import report
            (output/'qualification-report.json').write_bytes((json.dumps(report(recorded),indent=2)+'\n').encode('utf-8'))
        (output/'metadata.json').write_text(json.dumps(dict(config,status=status),indent=2),encoding='utf-8')
        from exploratory.k2_kaggle import core
        core.manifest(output,dict(status=status,scientific=False,phase=config['phase']))
