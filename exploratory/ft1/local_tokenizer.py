"""Read-only offline discovery of an identifiable Gemma 3 tokenizer or template."""
import json
import os
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def candidates():
    names=subprocess.check_output(['git','ls-files','*tokenizer_config.json','*chat_template.jinja'],cwd=ROOT,text=True).splitlines()
    paths=[ROOT/n for n in names if not n.startswith('results/')]
    hub=Path(os.environ.get('HF_HOME',Path.home()/'.cache/huggingface'))/'hub'
    if hub.is_dir():
        for model in hub.glob('models--*gemma-3*'):
            paths.extend(model.glob('snapshots/*/tokenizer_config.json'))
            paths.extend(model.glob('snapshots/*/chat_template.jinja'))
    return paths


def discover():
    found=[]; inspected=[]
    for path in candidates():
        raw=path.read_text(encoding='utf-8')
        # Gemma 4's turn markers/templates are not Gemma 3 qualification.
        if 'Gemma 4' in raw or '<turn|>' in raw:
            inspected.append(dict(path=str(path),identity='Gemma 4')); continue
        if path.name=='tokenizer_config.json':
            config=json.loads(raw)
            template=config.get('chat_template','')
            if isinstance(template,str) and '<end_of_turn>' in template and 'gemma' in config.get('tokenizer_class','').lower():
                found.append(dict(directory=str(path.parent),template=template,
                                  full_tokenizer=any((path.parent/n).is_file() for n in ('tokenizer.json','tokenizer.model'))))
        elif '<start_of_turn>' in raw and '<end_of_turn>' in raw:
            found.append(dict(directory=str(path.parent),template=raw,
                              full_tokenizer=any((path.parent/n).is_file() for n in ('tokenizer.json','tokenizer.model'))))
        inspected.append(dict(path=str(path),identity='unverified'))
    return found,inspected

if __name__=='__main__':
    found,inspected=discover()
    print(json.dumps(dict(gemma3_candidates=len(found),full_tokenizers=sum(x['full_tokenizer'] for x in found),
                          inspected=inspected),indent=2))
