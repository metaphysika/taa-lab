# FT1 training run, arm 1 seed 247057, at 0449a230: TRAINED (exploratory, $0)

Kernel `metaphysika/ft1-1-247057-train`, version 1. One Kaggle Tesla T4, internet off. Phase `train`, 250 optimizer steps.
- Exact commit: `0449a230200cef7c4f6e08c4bbaa5bbdac8ba636`.
- Chris's approval (2026-11-16): "Approve and write the new thread". It answered Claude's message, whose item 1 was "Approve the remaining 11 FT1 training runs at 0449a230". This run is one of the eleven.
- The pre-run entry (PR #155) and the result entry are in `LAB_NOTEBOOK.md`.

## Contents

- `launch/` holds what was staged and pushed. The hashes match the pre-run entry's table.
  - `ft1_plan.staged-PLAN_ONLY-True.ipynb` (`9b7adb41…`) and `ft1_plan.pushed-PLAN_ONLY-False.ipynb` (`ff898116…`). They differ only in `PLAN_ONLY`; this was checked by JSON comparison before the push.
  - `ft1-binding.json` (`14175698…`) and `kernel-metadata.json` (`6b83aad6…`).
  - `approval-receipt.json` (`1298d5e2…`), uploaded as dataset `metaphysika/ft1-train-approval-1-247057-0449a230200c`.
  - `approval-receipt.DRAFT-before-approval.json`, which was never uploaded.
- `kaggle-v1/` holds the kernel output, fetched after status COMPLETE.
  - All 53 files match the run's `manifest.json`.
  - Only text evidence is in git: `events.jsonl`, `metadata.json` (status `trained`), `manifest.json`, the adapter and checkpoint configs, the READMEs, the trainer states and the kernel log.

## Not in git

These are kept out of git because of their size and the Gemma licence. Their SHA-256 values are in `kaggle-v1/ft1-1-247057-train/manifest.json`.
- The adapter weights: `adapter/adapter_model.safetensors`, SHA-256 `c50f7a1c…`, as in the `adapter_saved` event.
- Checkpoint weights; optimizer, scaler, scheduler and RNG state; and `training_args.bin`.
- The Gemma tokenizer copies.

A complete copy of `kaggle-v1/` (2.0 GB) is kept outside the repo at `C:/Users/lahn0/T3/ft1-artifacts/2026-11-16 v0.24.89 ft1-train-1-247057 0449a230200c/`, and it matches the manifest. Kaggle also keeps the output as kernel version 1.

This adapter is the arm 1 / seed 247057 FT1 model. Its standing comes from Chris's approval and the `metadata.json` status `trained`; the manifest's `scientific: false` is a legacy label. It has not been evaluated. Evaluation needs its own approved gate and test runs.
