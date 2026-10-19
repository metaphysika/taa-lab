"""Internal entry; only the reviewed Mac launcher supplies the approval receipt."""
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from formation_study_d_gemma_speed_v02422 import check_sources
from formation import study_d_gemma_speed_v02422 as h
check_sources()
path=os.environ.get('STUDY_D_SPEED_RECEIPT','')
if not path:raise ValueError('local once-only approval receipt required before image build')
payload=json.loads(Path(path).read_text());h.validate(payload)
if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()!=payload['commit']:raise ValueError('reviewed commit differs')
from study_d_gemma_speed_app_v02422 import define
from study_d_gemma_submission_v02416 import submit_controller
from formation import study_d_gemma_base_v02416 as errors
app,worker,controller=define()

@app.local_entrypoint()
def main():
    h.validate(payload)
    submit_controller(controller,dict(payload,worker_function_id=worker.object_id),app.app_id,path,errors)
