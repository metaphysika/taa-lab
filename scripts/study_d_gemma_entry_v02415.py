"""Internal Modal entrypoint; use the approved offline-preflighting Mac launcher."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from formation_study_d_gemma_base_v02415 import check_sources
from formation import study_d_gemma_base_v02415 as h

# Executed before declarations/image initialization, not merely in local main.
check_sources()
receipt_path = os.environ.get('STUDY_D_GEMMA_PREFLIGHT','')
if not receipt_path:
    raise ValueError('use approved Mac launcher; pre-image-build receipt missing')
receipt = json.loads(Path(receipt_path).read_text())
commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
h.validate_receipt(receipt,commit)
from study_d_gemma_modal_app_v02415 import define
from study_d_gemma_submission_v02415 import submit_controller
app,worker,controller = define()


@app.local_entrypoint()
def main():
    h.validate_receipt(receipt,commit)
    submit_controller(controller, dict(receipt,worker_function_id=worker.object_id),
                      app.app_id, receipt_path, h)
