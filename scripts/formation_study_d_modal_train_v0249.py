"""Review only; no GPU execution without separate explicit owner approval."""
from study_d_modal_app_v0249 import define
app, launch = define('study')


@app.local_entrypoint()
def main(approved: bool=False, approval_receipt: str='', prior_usd: float=-1,
         hourly_ceiling: float=-1, account_cap: float=-1, model: str='', base_audit_receipt: str=''):
    launch(approved, approval_receipt, prior_usd, hourly_ceiling, account_cap, model, base_audit_receipt)
