"""Review only; no GPU execution without separate explicit owner approval."""
from study_d_modal_app_v0249 import define
app, launch = define('base')


@app.local_entrypoint()
def main(approved: bool=False, approval_receipt: str='', prior_usd: float=-1,
         hourly_ceiling: float=-1, credit_cap: float=-1, model: str='', base_audit_receipt: str='', projection_review_receipt: str=''):
    launch(approved, approval_receipt, prior_usd, hourly_ceiling, credit_cap, model, base_audit_receipt, projection_review_receipt)
