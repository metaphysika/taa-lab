# FT1 job (b): runner qualification at 0449a230, PASS (exploratory, $0)

Kernel `metaphysika/ft1-3-247056-qualify`, one Kaggle Tesla T4, internet off. Arm 3, seed 247056, phase `qualify`, ten optimizer steps.
Exact commit `0449a230200cef7c4f6e08c4bbaa5bbdac8ba636`. Chris's approval (2026-11-15): "Approve FT1 job (b) at 0449a230".
The notebook entry is in `LAB_NOTEBOOK.md`, "2026-11-15 — v0.24.89 FT1 job (b) at 0449a230: PASS".

## Folders

- `launch/`: what was pushed.
  - `approval-receipt.json` (SHA-256 `89db23b6…`), the receipt uploaded as dataset `metaphysika/ft1-qualification-approval-0449a230200c`.
  - `approval-receipt.DRAFT-before-approval.json`, the draft (`approved: false`) that was staged before approval and never uploaded.
  - `ft1-binding.json` (`b250d1d3…`) and `kernel-metadata.json` (`4ba19d8c…`), as staged.
  - `ft1_plan.v1-pushed-PLAN_ONLY-True.ipynb` (`e5b349c9…`), the staged notebook unchanged. Kernel version 1 ran this by mistake (see below).
  - `ft1_plan.v2-pushed-PLAN_ONLY-False.ipynb` (`ca28c3d6…`), kernel version 2, the real run. It differs from version 1 only in the line `PLAN_ONLY = False`, checked by a cell-source comparison.
- `kaggle-v1-plan-only/`: the log of kernel version 1. It printed the config and stopped. No model was loaded and nothing was trained.
- `kaggle-v2/`: the full output of kernel version 2, fetched 2026-11-15 after status COMPLETE.
  - All 27 files match the run's own `manifest.json`.
  - Only text evidence is committed to git.

## Not in git

These files are kept out of git because of size and the Gemma licence. Their SHA-256 values are in `kaggle-v2/ft1-3-247056-qualify/manifest.json`.

- Adapter weights: `adapter/adapter_model.safetensors` and `trainer/checkpoint-*/adapter_model.safetensors`, 131 MB each.
- Optimizer, scaler, scheduler and RNG state, plus `training_args.bin`.
- The Gemma tokenizer copies: `adapter/tokenizer.json`, `adapter/tokenizer_config.json` and `adapter/chat_template.jinja`. Tokenizer files are never committed.

A complete copy of `kaggle-v2/` (908 MB) is kept outside the repo at `C:/Users/lahn0/T3/ft1-artifacts/2026-11-15 v0.24.89 ft1-qualification 0449a230200c/`. The output is also retained on Kaggle as kernel version 2. The adapter is a qualification artifact (`"scientific": false`) and is not used for any FT1 result.
