# FT1 gate run, arm 4 / seed 247056, at cb5b8657: gate_complete (exploratory, $0)

Kernel `metaphysika/ft1-gate-4-247056-0`, version 1. One Kaggle Tesla T4, internet off, phase `gate`. Settings: eager attention, chunked prefill at 256, prompt ceiling 14,000 tokens.
- **Exact commit:** `cb5b865775e9c6357834e953bf7d14d653e45d95`.
- **Chris's approval (2026-11-17):** "Approve the 13 FT1 gate runs at cb5b8657 and Gate rule A"; and, after the arm 3 / 247056 result, "Proceed with the 11 gates".
- **Notebook entries:** the pre-run entry (#166), the approval and hash addendum (#168), the proceed entry (#170), and the result entry are in `LAB_NOTEBOOK.md`.

## Contents

- **`launch/`:** what was staged and pushed.
  - `ft1_evaluate.staged-PLAN_ONLY-True.ipynb` (`2079fcc5…`) and `ft1_evaluate.pushed-PLAN_ONLY-False.ipynb` (`3e3ef5b4…`). The two differ only in `PLAN_ONLY`; this was checked by JSON comparison before the push.
  - `binding.json` (`984865c3…`) and `kernel-metadata.json` (`65188af7…`).
  - `approval-receipt.json` (`7101a9fe…`), uploaded as dataset `metaphysika/ft1-gate-approval-4-247056-cb5b8657`. This receipt was drafted after Chris's approval, so no pre-approval draft exists.
- **`kaggle-v1/`:** the kernel output, fetched after status COMPLETE: `gate.json`, `eligibility.json`, `report.json`, `events.jsonl`, `metadata.json` and `manifest.json` (all 5 listed files match it), plus the kernel log.

Public FT1 data only. No sealed file or output was mounted or read. No weights are produced by this phase.

**Result:** `gate_complete`; acquisition 40 parsed, 40 correct (passes); format 21 of 21 turns parsed and 8 of 8 finished (passes); `acquired: true`. Out-of-memory episodes 0, context-limit episodes 0.
