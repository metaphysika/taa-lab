# FT1 pilot training run, arm 3 seed 247056, at 0449a230: TRAINED (exploratory, $0)

Kernel `metaphysika/ft1-3-247056-train`, version 1. One Kaggle Tesla T4, internet off. Phase `train`, 250 optimizer steps.
- Exact commit: `0449a230200cef7c4f6e08c4bbaa5bbdac8ba636`.
- Chris's approval (2026-11-15/16): "Let's go with your recommendations, 1 through 3". Item 1 of Claude's message was "Approve FT1 pilot training arm 3 seed 247056 at 0449a230".
- Pre-run entry and result entry: `LAB_NOTEBOOK.md`.

## Contents

- `launch/`: what was staged and pushed.
  - `ft1_plan.staged-PLAN_ONLY-True.ipynb` (`03260798…`) and `ft1_plan.pushed-PLAN_ONLY-False.ipynb` (`9ab335f3…`). They differ only in `PLAN_ONLY`, which was checked before the push.
  - `ft1-binding.json` (`8d90481d…`) and `kernel-metadata.json` (`3b5e9454…`).
  - `approval-receipt.json` (`8750fc9b…`), uploaded as dataset `metaphysika/ft1-train-approval-3-247056-0449a230200c`.
  - `approval-receipt.DRAFT-before-approval.json`, never uploaded.
- `kaggle-v1/`: the kernel output, fetched after status COMPLETE.
  - All 53 files match the run's `manifest.json`.
  - Only text evidence is in git: `events.jsonl`, `metadata.json` (status `trained`), `manifest.json`, the adapter and checkpoint configs, READMEs and trainer states, and the kernel log.

## Not in git

These are kept out of git because of size and the Gemma licence. Their SHA-256 values are in `kaggle-v1/ft1-3-247056-train/manifest.json`.
- The adapter weights: `adapter/adapter_model.safetensors`, SHA-256 `f99d7df8…`, as in the `adapter_saved` event.
- Checkpoint weights, optimizer, scaler, scheduler and RNG state, and `training_args.bin`.
- The Gemma tokenizer copies.

A complete copy of `kaggle-v1/` (2.0 GB) is kept outside the repo at `C:/Users/lahn0/T3/ft1-artifacts/2026-11-16 v0.24.89 ft1-train-3-247056 0449a230200c/`. The output is also retained on Kaggle as kernel version 1.

This adapter is the arm 3 / seed 247056 FT1 model. Its standing comes from the approval and `metadata.json` status `trained`; the manifest's `scientific: false` is a legacy label. It has not been evaluated. Evaluation needs its own approved gate and test runs.
