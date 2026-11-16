# FT1 fit-limit measurement at 1d064efa: COMPLETE (untrained base, public prompts, exploratory, $0)

Kernel `metaphysika/ft1-fit-limit`, version 1. It ran on one Kaggle Tesla T4 with internet off, phase `fit_limit`, for about 21 minutes of kernel time.
- **Exact commit:** `1d064efae2da396a9b0dcbf647ae350e069086ac`.
- **Chris's approval (2026-11-16):** "Approve FT1 fit-limit at 1d064efa".
- **Notebook entries:** the pre-run entry (PR #157) and the result entry are in `LAB_NOTEBOOK.md`.

## Contents

- **`launch/`:** what was staged and pushed.
  - `ft1_fit_limit.staged-PLAN_ONLY-True.ipynb` (`31b3748a…`) and `ft1_fit_limit.pushed-PLAN_ONLY-False.ipynb` (`fd1f1eb5…`). The two differ only in `PLAN_ONLY`; this was checked by JSON comparison before the push.
  - `binding.json` (`6cb8720e…`) and `kernel-metadata.json` (`3e9729ac…`).
  - `approval-receipt.json` (`7642f3dc…`), uploaded as dataset `metaphysika/ft1-fit-approval-1d064efa`.
  - `approval-receipt.DRAFT-before-approval.json`, never uploaded.
- **`kaggle-v1/`:** the kernel output, fetched after status COMPLETE.
  - `events.jsonl`, `metadata.json` (status `complete`) and `manifest.json`. Both files the manifest lists match it.
  - The kernel log.

No weights are produced by this phase; everything it wrote is in git.

**Deviation: first push refused.** The first push, at 14:58 UTC, was refused by Kaggle ("Maximum batch GPU session count of 2 reached") while two training runs held both GPU slots. No kernel was created. The same notebook was pushed at 15:49 UTC.
