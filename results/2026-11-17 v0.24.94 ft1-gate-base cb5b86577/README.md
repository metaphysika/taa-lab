# FT1 gate run, base model, at cb5b8657: gate_complete (exploratory, $0)

Kernel `metaphysika/ft1-gate-base-none-0`, version 1. One Kaggle Tesla T4, internet off, phase `gate`. Settings: eager attention, chunked prefill at 256, prompt ceiling 14,000 tokens.
- **Exact commit:** `cb5b865775e9c6357834e953bf7d14d653e45d95`.
- **Chris's approval (2026-11-17):** "Approve the 13 FT1 gate runs at cb5b8657 and Gate rule A".
- **Notebook entries:** the pre-run entry (#166), the approval and hash addendum (#168), and the result entry are in `LAB_NOTEBOOK.md`.

## Contents

- **`launch/`:** what was staged and pushed.
  - `ft1_evaluate.staged-PLAN_ONLY-True.ipynb` (`f55b9a3c…`) and `ft1_evaluate.pushed-PLAN_ONLY-False.ipynb` (`03cb1807…`). The two differ only in `PLAN_ONLY`; this was checked by JSON comparison before the push.
  - `binding.json` (`77bfde9c…`) and `kernel-metadata.json` (`e695d718…`).
  - `approval-receipt.json` (`15b8aaa5…`), uploaded as dataset `metaphysika/ft1-gate-approval-base-cb5b8657`.
  - The never-uploaded draft receipt.
- **`kaggle-v1/`:** the kernel output, fetched after status COMPLETE: `gate.json`, `eligibility.json`, `report.json`, `events.jsonl`, `metadata.json` and `manifest.json` (all 5 listed files match it), plus the kernel log.

Public FT1 data only. No sealed file or output was mounted or read. No weights are produced by this phase.

**Result:** `gate_complete`; acquisition 40 parsed, 7 correct (not acquired); format 28 of 28 turns parsed, 8 of 8 finished (passes); `acquired: false`. Base is the reference whatever its gate result. There were 0 out-of-memory and 0 context-limit episodes, and the attention read-back observed eager.
