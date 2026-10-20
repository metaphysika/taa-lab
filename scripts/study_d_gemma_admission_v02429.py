"""The complete shared CPU admission path. No Modal import or worker submission."""
import importlib.util
import json
from pathlib import Path
import shutil

CONTROLLER_FILES=('stages_policy.py','legacy_policy.py','base_policy.py','acquisition.py',
                  'assets_check.py','provenance.py','admission.py')


def attempted(root,stage,ledger):
    """A stage directory alone is not a spending/execution claim."""
    return ledger.contains(stage+'/once') or (Path(root)/stage/'reservation.json').exists()


def save_composite(root,value):
    # Never resolve folder/'../pair': mkdir would create the virtue directory first.
    path=Path(root)/'pair/report.json';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n')
    return path


def admit(h,root,source,assets,payload,ledger,source_closure,persist,virtue_source):
    """Validate, pin/copy, repair ONCE, bind by hash, verify CPU proof and admission."""
    root=Path(root);source=Path(source);assets=Path(assets)
    budget=h.validate(payload);manifest=h.verify_assets(assets)
    if h.sha(assets/'integrity-v02429.json')!=payload['asset_sha256']:
        raise ValueError('reviewed asset index differs')
    for name in CONTROLLER_FILES:
        if h.sha(assets.parent/name)!=manifest['remote_code_sha256'][name]:
            raise ValueError('controller source differs: '+name)
    if attempted(root,payload['stage'],ledger):raise ValueError('prior once claim or reservation; review, never restart')
    if ledger.contains('STOP_FOR_REVIEW'):raise ValueError('review stop exists; no further stage')
    binding=h.completion_binding()
    if source_closure!=dict(status='COMPLETE',report_sha256=binding['source_composite_sha256']):
        raise ValueError('source composite durable closure absent or changed')
    for name,digest in binding['source_sha256'].items():
        path=source/name
        if h.stream_sha(path)!=digest:raise ValueError('pinned v02426 source differs: '+name)
        dest=root/('source-composite-v02426.json' if name=='pair/report.json' else name)
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
        # Verify the stored copy too; subsequent admission uses canonical hashes.
        if h.stream_sha(dest)!=digest:raise ValueError('copied source differs: '+name)
    spec=importlib.util.spec_from_file_location('completion_provenance',assets.parent/'provenance.py')
    repair=importlib.util.module_from_spec(spec);spec.loader.exec_module(repair)
    original=json.loads((root/'source-composite-v02426.json').read_text())
    composite=repair.repair_composite(root,original,h.continuation_binding())
    path=save_composite(root,composite)
    if h.sha(path)!=binding['repaired_composite_sha256']:raise ValueError('CPU repaired composite hash differs from review')
    persist()  # Source and repaired record durable before their new closure marker.
    ledger.put('pair/closed',dict(status='COMPLETE',report_sha256=h.sha(path)),skip_if_exists=True)
    h.require_cpu(root,payload)
    h.require_previous(root,payload,ledger)  # Hash verification only, never repair again.
    if attempted(root,payload['stage'],ledger):raise ValueError('stage claimed during admission; no duplicate')
    if ledger.contains('STOP_FOR_REVIEW'):raise ValueError('review stop exists; no further stage')
    virtue_binding=h.source_binding()
    for name,digest in virtue_binding['sha256'].items():
        path=Path(virtue_source)/name
        if h.stream_sha(path)!=digest:raise ValueError('pinned v02428 source differs: '+name)
        dest=root/'prior-virtue'/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,dest)
        if h.stream_sha(dest)!=digest:raise ValueError('copied v02428 source differs: '+name)
    h.verify_source_training(root)
    persist()
    return budget
