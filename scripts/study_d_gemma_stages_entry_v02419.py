"""Internal entry: use the reviewed Mac preflight launcher, never call directly."""
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from formation_study_d_gemma_stages_v02419 import check_sources
from formation import study_d_gemma_stages_v02419 as h
check_sources()
path=os.environ.get('STUDY_D_GEMMA_STAGE_RECEIPT','')
if not path:raise ValueError('pre-image-build local approval receipt required')
payload=json.loads(Path(path).read_text());h.validate(payload)
if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()!=payload['commit']:
    raise ValueError('commit differs from local approval receipt')
from study_d_gemma_stages_app_v02419 import define
from study_d_gemma_submission_v02416 import submit_controller
from formation import study_d_gemma_base_v02416 as errors
app,worker,controller=define(payload['stage'])

@app.local_entrypoint()
def main():
    h.validate(payload)
    submit_controller(controller,dict(payload,worker_function_id=worker.object_id),app.app_id,path,errors)
