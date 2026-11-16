# FT1 fit-limit 2 (chunked prefill) at 09fac296: COMPLETE (untrained base, public prompts, exploratory, $0)

Kernel `metaphysika/ft1-fit-limit`, version 2. It ran on one Kaggle Tesla T4 with internet off, phase `fit_limit`, eager attention, `prefill_mode: chunked`, `prefill_chunk_size: 256`, for about 42 minutes of kernel time against a 4,500 s deadline.
- **Exact commit:** `09fac2962b3759b783b8b2978069627749b0e8ca`.
- **Chris's approval (2026-11-16):** "Approve FT1 fit-limit 2 at 09fac296".
- **Notebook entries:** the pre-run entry (PR #163) and the result entry are in `LAB_NOTEBOOK.md`.

## Contents

- **`launch/`:** what was staged and pushed.
  - `ft1_fit_limit.staged-PLAN_ONLY-True.ipynb` (`abfc4d51…`) and `ft1_fit_limit.pushed-PLAN_ONLY-False.ipynb` (`acdee86b…`). The two differ only in `PLAN_ONLY`; this was checked by JSON comparison before the push.
  - `binding.json` (`97fe55b9…`) and `kernel-metadata.json` (`d84e94a5…`).
  - `approval-receipt.json` (`32d6632c…`), uploaded as dataset `metaphysika/ft1-fit2-approval-09fac296`.
  - `approval-receipt.DRAFT-before-approval.json`, never uploaded.
- **`kaggle-v2/`:** the kernel output, fetched after status COMPLETE.
  - `events.jsonl`, `metadata.json` (status `complete`) and `manifest.json`. Both files the manifest lists match it.
  - The kernel log.

No weights are produced by this phase; everything it wrote is in git.

**Deviation: push waited for a slot.** The receipt was uploaded and the notebook flipped right after approval. A retry loop pushed it every 2 minutes and was refused by Kaggle's two-GPU-session limit until 22:34 UTC, when arm 2 / 247057 finished.
