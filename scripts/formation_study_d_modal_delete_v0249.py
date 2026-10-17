"""CPU-only deletion after an explicit owner review/end decision; never loads models."""
import importlib.util
from pathlib import Path
import sys
import modal

ROOT = Path(__file__).resolve().parents[1]
if sys.version_info[:2] not in ((3,11),(3,12)):
    raise ValueError('use the reviewed Python 3.11 or 3.12 environment')
image = (modal.Image.debian_slim(python_version=f'{sys.version_info.major}.{sys.version_info.minor}')
         .add_local_file(str(ROOT/'formation/study_d_modal_v0249.py'),'/opt/helpers.py',copy=True))
app = modal.App('taa-study-d-delete-v0249')
evidence = modal.Volume.from_name('taa-study-d-v0249-evidence')
private = modal.Volume.from_name('taa-study-d-v0249-private-adapters')


@app.function(image=image,cpu=.25,memory=256,timeout=120,retries=0,
              volumes={'/results':evidence,'/adapters':private},include_source=False,serialized=True)
def delete_after_review(decision_receipt, all_apps_stopped):
    if not all_apps_stopped or not decision_receipt.strip() or 'REPLACE' in decision_receipt:
        raise ValueError('explicit owner decision and stopped-app confirmation required')
    spec=importlib.util.spec_from_file_location('review_helpers','/opt/helpers.py')
    h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    private.reload();evidence.reload()
    if Path('/results/adapter-deletion-receipt.json').exists() and not Path('/adapters/study').exists():
        return 'Already deleted; preserve existing receipt'
    return h.delete_adapters('/adapters/study','/results',decision_receipt,
                             private.commit,evidence.commit)


@app.local_entrypoint()
def main(decision_receipt: str='',all_apps_stopped: bool=False):
    if not decision_receipt.strip() or not all_apps_stopped or 'REPLACE' in decision_receipt:
        raise ValueError('separate owner review decision and stopped-app confirmation required')
    print(delete_after_review.remote(decision_receipt,all_apps_stopped))
