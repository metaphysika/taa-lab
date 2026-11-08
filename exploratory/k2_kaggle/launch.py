"""Private K2 CLI launcher. --plan writes staging files without calling Kaggle."""
import argparse
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import tarfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
TIMEOUT = 31500
MAX_TITLE = 50
# Retained evidence and process documents are not needed on Kaggle and make the
# archive about 2.4 GB; they are excluded and the exclusion is recorded in ARCHIVE.json.
EXCLUDED = ('results', 'docs')


def command(argv, plan=False):
    print(shlex.join(map(str, argv)))
    if plan:
        return ''
    return subprocess.run(list(map(str, argv)), cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout


def safe_source(value):
    if re.search(r'study[ _/-]*d|v0?24\d{2}|adapter-source', str(value), re.I):
        raise ValueError('Study D adapter source forbidden')
    return value


def slug_ref(value):
    safe_source(value)
    if not re.fullmatch(r'[a-z0-9_-]+/[a-z0-9_-]+', value):
        raise ValueError('expected owner/slug')
    return value


def checked_commit(commit, plan=False):
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('full lowercase commit SHA required')
    if command(['git', 'status', '--porcelain']).strip():
        raise ValueError('dirty checkout')
    if not plan: command(['git', 'merge-base', '--is-ancestor', commit, 'origin/main'])


def checked_plan_commit(commit):
    # Same exact archive checks, but an offline staging plan can inspect a PR head.
    checked_commit(commit, plan=True)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')


def parameterize(raw, values):
    notebook = json.loads(raw)
    cells = [c for c in notebook['cells'] if c['cell_type']=='code'
             and any('DRY_RUN = ' in s for s in c['source'])]
    if len(cells) != 1:
        raise ValueError('expected one parameter cell')
    source = cells[0]['source']
    # JSON string tokens may contain brackets, so use the decoder to find array ends.
    matches=list(re.finditer(r'"source"\s*:\s*',raw))
    for match in reversed(matches):
        obj, end=json.JSONDecoder().raw_decode(raw[match.end():])
        if obj==source:
            lines=''.join(source)
            for key,value in values.items():
                lines,count=re.subn(r'^'+key+r'\s*=.*$',lambda m:key+' = '+value,lines,flags=re.M)
                if count!=1: raise ValueError('missing/duplicate parameter '+key)
            raw=raw[:match.end()]+json.dumps(lines.splitlines(True),ensure_ascii=False,indent=1)+raw[match.end()+end:]
    return raw


def verify(folder):
    manifests = list(folder.rglob('manifest.json'))
    if not manifests:
        raise ValueError('missing manifest.json')
    for manifest in manifests:
        record = json.loads(manifest.read_text(encoding='utf-8'))
        if not record.get('sha256'):
            raise ValueError('empty manifest inventory')
        for name, expected in record['sha256'].items():
            path = (manifest.parent/name).resolve()
            if not path.is_relative_to(manifest.parent.resolve()):
                raise ValueError('manifest path escape')
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError('manifest SHA256 mismatch: '+name)


def version():
    import re
    return re.match(r'# TAA Lab \(v(\d+\.\d+\.\d+)', (ROOT/'README.md').read_text(encoding='utf-8')).group(1)


def execute(args):
    if args.action=='merge':
        from exploratory.k2_kaggle import core
        plan_bytes=args.plan_file.read_bytes()
        report=core.merge_shards(args.folders,json.loads(plan_bytes))
        report['merge_manifest']['plan_file_sha256']=hashlib.sha256(plan_bytes).hexdigest()
        args.output.mkdir(parents=True,exist_ok=False)
        for key,name in (('sanity_summary','sanity-summary.json'),('acquisition_counts','acquisition-counts.json'),('merge_manifest','merge-manifest.json')):
            write_json(args.output/name,report[key])
        (args.output/'plan.json').write_bytes(plan_bytes)
        core.manifest(args.output,report['merge_manifest'])
        return
    print('K2 '+args.action+(' (offline plan)' if args.plan else ''))
    state = args.state.resolve()
    state.mkdir(parents=True, exist_ok=True)
    if args.action == 'stage-repo':
        checked_commit(args.commit) if not args.plan else checked_plan_commit(args.commit)
        dataset = slug_ref(args.owner+'/taa-k2-repo-'+args.commit[:12])
        folder = state / ('repo-'+args.commit)
        folder.mkdir(exist_ok=False)
        print('git archive '+args.commit+' -> '+str(folder))
        archive = subprocess.run(['git', '-c', 'core.autocrlf=false', 'archive', args.commit, '--', '.', *[':(exclude)'+x for x in EXCLUDED]],
                                 cwd=ROOT, check=True, capture_output=True).stdout
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            for member in tar.getmembers():
                path = Path(member.name)
                if path.is_absolute() or '..' in path.parts or member.issym() or member.islnk():
                    raise ValueError('unsafe archive member')
                if path.name.lower() == 'keys.env' or '.kaggle' in path.parts:
                    raise ValueError('secret path in archive')
            tar.extractall(folder/'taa-lab', filter='data')
        (folder/'taa-lab/COMMIT.txt').write_text(args.commit+'\n', encoding='utf-8')
        write_json(folder/'taa-lab/ARCHIVE.json', dict(commit=args.commit, excluded=list(EXCLUDED)))
        write_json(folder/'dataset-metadata.json', dict(title='K2 repo '+args.commit[:12], id=dataset,
                   licenses=[dict(name='other')], isPrivate=True))
        argv = ['kaggle', 'datasets', 'version' if args.dataset_version else 'create', '-p', str(folder), '-r', 'zip']
        if args.dataset_version:
            argv += ['-m', 'K2 exact commit '+args.commit]
        command(argv, args.plan)
    elif args.action == 'push':
        checked_commit(args.commit) if not args.plan else checked_plan_commit(args.commit)
        from exploratory.k2_kaggle import core
        core.validate_model_source(args.model_source, args.model)
        core.model_guard(args.model,args.mode,args.adapter_kernel)
        if args.screen_battery=='l2' and (not args.base_screen or not args.model.startswith('gemma-4-') or args.mode!='evaluate' or args.shard_arm!='base' or args.shard_kind is not None):
            raise ValueError('L2 requires Gemma 4 base-screen evaluation, base arm, no kind')
        if args.base_screen:
            core.screen_guard(args.mode,args.step,args.shard_arm,args.shard_kind or ('W' if args.screen_battery=='l2' else None),args.adapter_kernel)
        elif args.model=='gemma-3-12b-it' or args.model.startswith('gemma-4-'):
            raise ValueError('12B requires --base-screen')
        slug_ref(args.owner+'/valid')
        adapters = {}
        for item in args.adapter_kernel:
            arm, ref = item.split('=', 1)
            if arm not in ('neutral', 'contrary') or arm in adapters:
                raise ValueError('invalid/duplicate adapter arm')
            adapters[arm] = slug_ref(ref)
            if '-'+arm[:3]+'-' not in ref.split('/')[1]: raise ValueError('adapter kernel is not a '+arm+' training kernel: '+ref)
        shard=args.shard_arm is not None or args.shard_kind is not None
        if shard and (args.mode!='evaluate' or args.step!=1 or (args.shard_arm,args.shard_kind) not in core.SHARDS and args.screen_battery!='l2'):
            raise ValueError('shards require step 1 evaluation and arm/kind')
        if args.mode=='evaluate':
            if args.step==1 and not shard: raise ValueError('step 1 requires shard arm/kind')
            required=({args.shard_arm}-{'base'}) if shard else {'neutral','contrary'}
            if set(adapters)!=required: raise ValueError('attach only required adapter arms')
        if args.step == 2 and not args.gate_file:
            raise ValueError('step 2 requires --gate-file mount path and separately attached reviewed gate')
        if args.gate_file:
            safe_source(args.gate_file)
        # Kaggle rejects kernel titles over 50 characters (HTTP 400 on SaveKernel, seen
        # 2026-11-06), so the slug is abbreviated; launch.json keeps the full fields.
        part = 'st'+str(args.step) if args.mode == 'evaluate' else args.arm[:3]
        if shard: part+='-'+args.shard_arm[:3]+(args.shard_kind or 'L2')
        slug = f'k2{args.mode[0]}-{model_slug(args.model)}-{part}-s{args.train_seed}-{args.commit[:8]}-{uuid.uuid4().hex[:8]}'
        if len(slug) > MAX_TITLE: raise ValueError('kernel title too long for Kaggle: '+slug)
        ref = args.owner+'/'+slug
        if any(args.results.glob('*'+slug+'*')) or (state/slug).exists():
            raise ValueError('slug already retained')
        folder = state/slug
        folder.mkdir()
        # Measured layout: /kaggle/input/models/<handle> and /kaggle/input/datasets/<owner>/<slug>.
        model_mount = '/kaggle/input/models/'+args.model_source
        values = dict(DRY_RUN='False', MODE=repr(args.mode), MODEL=repr(args.model),
                      MODEL_REVISION=repr(args.model_source), PINNED_COMMIT=repr(args.commit),
                      MODEL_PATH=f'Path({model_mount!r})', REPO=f"next(p.parent for p in Path('/kaggle/input').rglob('COMMIT.txt') if p.read_text().strip()=={args.commit!r})",
                      OUTPUT="Path('/kaggle/working/k2-output')", TRAIN_SEED=str(args.train_seed))
        if args.mode == 'evaluate' or args.base_screen:
            values.update(SCREEN_BATTERY=repr(args.screen_battery), BASE_SCREEN=repr(args.base_screen), SHARD_ARM=repr(args.shard_arm), SHARD_KIND=repr(args.shard_kind), STEP=str(args.step), GATE_FILE=f'Path({args.gate_file!r})' if args.gate_file else 'None',
                          ADAPTER_KERNELS=repr(adapters))
        else:
            values['ARM'] = repr(args.arm)
        name = 'k2_eval.ipynb' if args.mode == 'evaluate' or args.base_screen else 'k2_train.ipynb'
        raw = command(['git', 'show', args.commit+':exploratory/k2_kaggle/'+name])
        (folder/name).write_text(parameterize(raw, values), encoding='utf-8')
        metadata = dict(id=ref, title=slug, code_file=name, language='python', kernel_type='notebook',
                        is_private=True, enable_gpu=True, enable_internet=False,
                        dataset_sources=[args.owner+'/taa-k2-repo-'+args.commit[:12], args.owner+'/k2-wheels'],
                        model_sources=[args.model_source], kernel_sources=list(adapters.values()))
        write_json(folder/'kernel-metadata.json', metadata)
        write_json(folder/'launch.json', dict(slug=ref, commit=args.commit, model=args.model,
                   screen_battery=args.screen_battery, screen_identity=core.screen_identity(args.model) if args.base_screen else None, mode=args.mode, step=args.step, arm=args.arm, shard=dict(arm=args.shard_arm,kind=args.shard_kind) if shard else None, seed=args.train_seed, model_source=args.model_source,
                   created=dt.datetime.now(dt.timezone.utc).isoformat()))
        command(['kaggle','kernels','push','-p',str(folder),'--accelerator','NvidiaTeslaT4','--timeout',str(TIMEOUT)], args.plan)
    else:
        # Kaggle stores kernel ids in lowercase but keeps the title's case
        # (e.g. title ...-basU-... has id ...-basu-...), so ids compare case-insensitively.
        ref = slug_ref(args.kernel.lower())
        if args.action == 'status':
            print(command(['kaggle','kernels','status',ref], args.plan))
            return
        matches = [p for p in state.iterdir() if p.is_dir() and p.name.lower() == ref.split('/')[1]]
        if len(matches) != 1:
            raise ValueError('expected exactly one launch record for '+ref)
        record = json.loads((matches[0]/'launch.json').read_text())
        if record['slug'].lower() != ref:
            raise ValueError('launch owner mismatch')
        stamp = dt.datetime.now(dt.timezone.utc)
        what = record['arm'] if record['mode'] != 'evaluate' else ('st'+str(record.get('step', 1))+('-'+record['shard']['arm']+'-'+record['shard']['kind'] if record.get('shard') else ''))
        folder = args.results / (f"{stamp:%Y-%m-%d} v{version()} {record['model']}-{record['mode']}-{what}-s{record['seed']} k2 {ref.split('/')[1]}")
        folder.mkdir(parents=True, exist_ok=False)
        status = 'planned'; verification = 'not downloaded'
        try:
            status = command(['kaggle','kernels','status',ref], args.plan)
            command(['kaggle','kernels','output',ref,'-p',str(folder)], args.plan)
            if not args.plan:
                verify(folder)
                verification = 'SHA256 verified'
        except BaseException as exc:
            verification = 'FAILED: '+str(exc)
            raise
        finally:
            (folder/'README.md').write_text(json.dumps(dict(record, status=status,
                fetched=stamp.isoformat(), verification=verification), indent=2)+'\n', encoding='utf-8')


def model_slug(model):
    return ('g4-'+'-'.join(model.split('-')[2:-1])) if model.startswith('gemma-4-') else model.split('-')[2]


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    m=sub.add_parser('merge')
    m.add_argument('folders',nargs='+',type=Path)
    m.add_argument('--plan-file',required=True,type=Path)
    m.add_argument('--output',required=True,type=Path)
    for action in ('stage-repo', 'push', 'status', 'fetch'):
        p = sub.add_parser(action)
        p.add_argument('--plan', action='store_true')
        p.add_argument('--state', type=Path, default=ROOT/'.k2-launch')
        p.add_argument('--results', type=Path, default=ROOT/'results')
        if action in ('status', 'fetch'):
            p.add_argument('kernel')
        else:
            p.add_argument('--commit', required=True)
            p.add_argument('--owner', required=True)
        if action == 'stage-repo':
            p.add_argument('--dataset-version', action='store_true')
        if action == 'push':
            p.add_argument('--mode', choices=['qualify','train','evaluate'], required=True)
            p.add_argument('--model', choices=list(__import__('exploratory.k2_kaggle.core',fromlist=['MODELS']).MODELS), required=True)
            p.add_argument('--model-source', required=True)
            p.add_argument('--base-screen', action='store_true')
            p.add_argument('--screen-battery',choices=['k2','l2'],default='k2')
            p.add_argument('--arm', choices=['neutral','contrary'], default='neutral')
            p.add_argument('--train-seed', type=int, default=247056)
            p.add_argument('--step', type=int, choices=[1,2], default=1)
            p.add_argument('--adapter-kernel', nargs='*', default=[])
            p.add_argument('--gate-file')
            p.add_argument('--shard-arm',choices=['base','neutral','contrary'])
            p.add_argument('--shard-kind',choices=['W','U'])
    execute(parser.parse_args(argv))


if __name__ == '__main__':
    main()
