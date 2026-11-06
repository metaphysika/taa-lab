import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from exploratory.k2_kaggle import launch as l, core

SHA='a'*40
SOURCE='google/gemma-3/transformers/gemma-3-1b-it/7'

class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.state=self.root/'state'
        self.results=self.root/'results'
    def mock_run(self, argv, **kwargs):
        if argv[:2]==['git','show']:
            name=argv[2].split(':',1)[1]
            return subprocess.CompletedProcess(argv,0,stdout=(l.ROOT/name).read_text())
        return subprocess.CompletedProcess(argv,0,stdout='')
    def run_cli(self, *args):
        l.main([*args,'--state',str(self.state),'--results',str(self.results)])
    def push(self, *extra):
        self.run_cli('push','--mode','train','--model','gemma-3-1b-it',
                     '--commit',SHA,'--owner','owner','--model-source',SOURCE,*extra)
    def test_push_and_plan(self):
        with patch.object(l,'checked_commit'), patch.object(l.subprocess,'run') as run:
            run.side_effect=self.mock_run
            self.push()
            folder=next(self.state.iterdir())
            self.assertEqual(run.call_args.args[0],['kaggle','kernels','push','-p',str(folder),
                             '--accelerator','NvidiaTeslaT4','--timeout','31500'])
            meta=json.loads((folder/'kernel-metadata.json').read_text())
            self.assertTrue(meta['is_private'])
            self.assertTrue(meta['enable_gpu'])
            self.assertFalse(meta['enable_internet'])
            self.assertEqual(meta['model_sources'],[SOURCE])
            self.assertEqual(meta['dataset_sources'],['owner/taa-k2-repo-'+SHA[:12]])
            self.push('--plan')
            self.assertEqual(sum(c.args[0][0]=='kaggle' for c in run.call_args_list),1)
    def test_cells_preserved(self):
        for path in Path(core.__file__).parent.glob('*.ipynb'):
            raw=path.read_text()
            result=l.parameterize(raw,dict(DRY_RUN='False',MODEL_REVISION=repr(SOURCE)))
            before=json.loads(raw); after=json.loads(result)
            for a,b in zip(before['cells'],after['cells']):
                if 'DRY_RUN = ' not in ''.join(a['source']):
                    self.assertEqual(a,b)
            import re
            def outside(text):
                for m in reversed(list(re.finditer(r'"source"\s*:\s*', text))):
                    obj,end=json.JSONDecoder().raw_decode(text[m.end():])
                    if isinstance(obj,list) and 'DRY_RUN = ' in ''.join(obj):
                        text=text[:m.end()]+'PARAMETERS'+text[m.end()+end:]
                return text
            self.assertEqual(outside(raw),outside(result))
            self.assertIn("DRY_RUN = False",result)
    def test_refusals(self):
        for source in ('owner/study-d-adapter','owner/adapter-v02424','Study_D/path'):
            with self.assertRaises(ValueError): l.safe_source(source)
        with patch.object(l.subprocess,'run',return_value=subprocess.CompletedProcess([],0,stdout=' M dirty')):
            with self.assertRaisesRegex(ValueError,'dirty'): l.checked_commit(SHA)
        with patch.object(l.subprocess,'run',side_effect=subprocess.CalledProcessError(1,[])):
            with self.assertRaises(subprocess.CalledProcessError): l.checked_commit(SHA)
        with self.assertRaises(ValueError): core.validate_model_source('a'*40,'gemma-3-1b-it')
    def test_slug_reuse(self):
        with patch.object(l,'checked_commit'),patch.object(l.subprocess,'run',side_effect=self.mock_run),patch.object(l.uuid,'uuid4') as uid:
            uid.return_value.hex='12345678'*4
            self.push('--plan')
            with self.assertRaisesRegex(ValueError,'already retained'): self.push('--plan')
    def test_stage_private_archive(self):
        stream=io.BytesIO()
        with tarfile.open(fileobj=stream,mode='w') as tar:
            item=tarfile.TarInfo('example.txt'); item.size=2
            tar.addfile(item,io.BytesIO(b'x\n'))
        with patch.object(l,'checked_commit'),patch.object(l.subprocess,'run') as run:
            run.return_value.stdout=stream.getvalue()
            self.run_cli('stage-repo','--commit',SHA,'--owner','owner')
            folder=self.state/('repo-'+SHA)
            self.assertEqual(run.call_args.args[0],['kaggle','datasets','create','-p',str(folder),'-r','zip'])
            self.assertTrue(json.loads((folder/'dataset-metadata.json').read_text())['isPrivate'])
            self.assertEqual((folder/'taa-lab/example.txt').read_bytes(),b'x\n')
    def test_evaluation_sources(self):
        with patch.object(l,'checked_commit'),patch.object(l.subprocess,'run',side_effect=self.mock_run):
            self.run_cli('push','--mode','evaluate','--model','gemma-3-1b-it',
                '--commit',SHA,'--owner','owner','--model-source',SOURCE,
                '--adapter-kernel','neutral=owner/k2-neutral','contrary=owner/k2-contrary')
            meta=json.loads((next(self.state.iterdir())/'kernel-metadata.json').read_text())
            self.assertEqual(meta['kernel_sources'],['owner/k2-neutral','owner/k2-contrary'])
    def test_fetch_failure_retained_no_overwrite(self):
        with patch.object(l,'checked_commit'),patch.object(l.subprocess,'run',side_effect=self.mock_run):
            self.push('--plan')
        slug=next(self.state.iterdir()).name
        with patch.object(l.subprocess,'run',return_value=subprocess.CompletedProcess([],0,stdout='failed')):
            with self.assertRaisesRegex(ValueError,'missing manifest'):
                self.run_cli('fetch','owner/'+slug)
            folder=next(self.results.iterdir())
            self.assertIn('v0.24.69 gemma-3-1b-it-train-neutral-s247056 k2',folder.name)
            self.assertIn('FAILED', (folder/'README.md').read_text())
            with self.assertRaises(FileExistsError): self.run_cli('fetch','owner/'+slug)
    def test_hash_failure_and_path_fallback(self):
        folder=self.root
        (folder/'file').write_bytes(b'bad')
        l.write_json(folder/'manifest.json',dict(sha256={'file':'0'*64}))
        with self.assertRaisesRegex(ValueError,'SHA256'): l.verify(folder)
        self.assertTrue((folder/'file').exists())
        l.write_json(folder/'manifest.json',dict(sha256={'file':l.hashlib.sha256(b'bad').hexdigest()}))
        l.verify(folder)
        l.write_json(folder/'manifest.json',dict(sha256={'../escape':'0'*64}))
        with self.assertRaisesRegex(ValueError,'escape'): l.verify(folder)
        with self.assertRaises(ValueError): core.resolve_model_path(folder/'missing',folder)
        base=folder/'base'; base.mkdir()
        for name in ('config.json','tokenizer_config.json','weights.safetensors'):
            (base/name).touch()
        self.assertEqual(core.resolve_model_path(folder/'missing',folder),base)

if __name__=='__main__': unittest.main()
