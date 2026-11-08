import json
from pathlib import Path
import unittest
from unittest.mock import Mock
from exploratory.k2_kaggle import core, screen, launch

class K2bTests(unittest.TestCase):
    def test_g3_unchanged(self):
        tok=Mock(); tok.apply_chat_template.return_value=[1,2]
        messages=[dict(role='system',content='SYS'),dict(role='user',content='USER')]
        self.assertEqual(core.prompt(tok,messages),[1,2])
        tok.apply_chat_template.assert_called_with([dict(role='user',content='SYS\n\nUSER')],tokenize=True,add_generation_prompt=True)
        tok.convert_tokens_to_ids.return_value=8;tok.convert_ids_to_tokens.return_value='<end_of_turn>';tok.encode.return_value=[8]
        self.assertEqual(core.end_token(tok),8)
        core.decode_reply(tok,[1,2],'gemma-3-12b-it');tok.decode.assert_called_with([1,2],skip_special_tokens=True)

    def test_native_render(self):
        from jinja2 import Environment
        template=(core.ROOT/'exploratory/k2_kaggle/gemma4-31b-reference.jinja').read_text(encoding='utf8')
        class Tokenizer:
            def apply_chat_template(self,messages,**kwargs):
                return Environment().from_string(template).render(messages=messages,add_generation_prompt=True,bos_token='<bos>',eos_token='<eos>',raise_exception=lambda x: (_ for _ in ()).throw(ValueError(x)))
        rendered=core.prompt(Tokenizer(),[dict(role='system',content='SYS'),dict(role='user',content='USER')],False,'gemma-4-12b-it')
        self.assertTrue(rendered.startswith('<bos><|turn>system\n'))
        self.assertTrue(rendered.endswith('<|turn>model\n<|channel>thought\n<channel|>'))

    def test_stops_decode(self):
        tok=Mock();tok.unk_token_id=0;tok.convert_tokens_to_ids.return_value=0
        with self.assertRaises(ValueError):core.end_token(tok,'gemma-4-e2b-it')
        tok.convert_tokens_to_ids.return_value=106;tok.convert_ids_to_tokens.return_value='<turn|>';tok.encode.return_value=[106]
        self.assertEqual(core.end_token(tok,'gemma-4-e2b-it'),106)
        text='<|channel>thought\n<channel|>{"ok":true}<turn|>'
        tok.decode.return_value=text
        self.assertEqual(core.decode_reply(tok,[1],'gemma-4-e2b-it'),text)
        tok.decode.assert_called_with([1],skip_special_tokens=False)

    def test_handles_guards_slugs(self):
        for model in core.MODELS:
            family='gemma-4' if model.startswith('gemma-4-') else 'gemma-3'
            core.validate_model_source('google/'+family+'/transformers/'+model+'/1',model)
            with self.assertRaises(ValueError):core.validate_model_source('google/'+family+'/transformers/'+model,model)
            with self.assertRaises(ValueError):core.validate_model_source('google/wrong-family/transformers/'+model+'/1',model)
            if family=='gemma-4':
                for mode,adapters in [('train',{}),('evaluate',{'neutral':'x'})]:
                    with self.assertRaises(ValueError):core.model_guard(model,mode,adapters)
                for shard in ('basW','basU','basL2'):
                    slug='k2e-'+launch.model_slug(model)+'-st1-'+shard+'-s247056-12345678-12345678'
                    self.assertLessEqual(len(slug),50)
                    self.assertNotEqual(launch.model_slug(model),launch.model_slug('gemma-3-12b-it'))

    def test_l2_continues(self):
        from collections import Counter
        self.assertEqual(Counter(x['group'] for x in screen.plan()),dict(W=12,U=12,knowledge=24))
        rows=[]
        def fail(*args):raise RuntimeError('fixture')
        result=screen.run(fail,rows.append)
        self.assertEqual(len(result),48)
        self.assertEqual(sum(x['unknown'] for x in screen.summary(result).values()),48)
        self.assertEqual(len(screen.run(core.fake_model,lambda x:None)),48)

    def test_notebook_compiles(self):
        for name in ('k2_eval.ipynb','k2_train.ipynb'):
            if name=='k2_eval.ipynb':
                launch.parameterize((core.ROOT/'exploratory/k2_kaggle'/name).read_text(encoding='utf8'),dict(SCREEN_BATTERY=repr('l2'),BASE_SCREEN='True'))
            n=json.loads((core.ROOT/'exploratory/k2_kaggle'/name).read_text(encoding='utf8'))
            for c in n['cells']:
                if c['cell_type']=='code':compile(''.join(c['source']),name,'exec')

    def test_dry_screen_modes(self):
        import tempfile
        notebook=json.loads((core.ROOT/'exploratory/k2_kaggle/k2_eval.ipynb').read_text(encoding='utf8'))
        for mode,battery,arm,kind in [('qualify','k2',None,None),('evaluate','l2','base',None),('evaluate','k2','base','U')]:
            with tempfile.TemporaryDirectory() as tmp:
                namespace={}
                for cell in notebook['cells']:
                    if cell['cell_type']!='code':continue
                    code=''.join(cell['source'])
                    for old,new in [("MODEL = 'gemma-3-1b-it'", "MODEL = 'gemma-4-e2b-it'"),('BASE_SCREEN = False','BASE_SCREEN = True'),("MODE = 'evaluate'",'MODE = '+repr(mode)),("SCREEN_BATTERY = 'k2'",'SCREEN_BATTERY = '+repr(battery)),('SHARD_ARM = None','SHARD_ARM = '+repr(arm)),('SHARD_KIND = None','SHARD_KIND = '+repr(kind)),("Path('/kaggle/input/taa-k2-repo/taa-lab')",'Path('+repr(str(core.ROOT))+')'),("Path('/kaggle/working/k2-output')",'Path('+repr(tmp)+') / "out"')]:code=code.replace(old,new)
                    exec(compile(code,'dry_screen','exec'),namespace)
                self.assertTrue((Path(tmp)/'out/manifest.json').exists())
