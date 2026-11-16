# FT1 speed test (throughput) at bf941651: COMPLETE (exploratory, $0)

Kernel `metaphysika/ft1-throughput`, version 1. One Kaggle Tesla T4, internet off. Untrained Gemma 3 12B NF4 base with no adapter, no FT1 data and no sealed cases.

- Exact commit: `bf9416513f15d732e35d45d910f57595468b8fcf`.
- Chris's approval (2026-11-16): "Approve FT1 speed test at bf941651".
- Pre-run entry and result entry: `LAB_NOTEBOOK.md`.

## Contents

- `launch/`: what was staged and pushed.
  - `ft1_throughput.staged-PLAN_ONLY-True.ipynb`, SHA-256 `7d10d088…`.
  - `ft1_throughput.pushed-PLAN_ONLY-False.ipynb`, SHA-256 `6ed87c7e…`. It differs from the staged notebook only in `PLAN_ONLY = False`, which was checked before the push.
  - `binding.json` (`a58e92f8…`) and `kernel-metadata.json` (`19339aeb…`).
  - `approval-receipt.json` (`ce96295a…`), uploaded as dataset `metaphysika/ft1-throughput-approval-bf9416513f15`.
  - `approval-receipt.DRAFT-before-approval.json`, never uploaded.
- `kaggle-v1/`: the complete kernel output, fetched after status COMPLETE.
  - `ft1-throughput/events.jsonl`, `metadata.json` (status `complete`) and `manifest.json`. All files match the manifest.
  - `ft1-throughput.log`.

Repo dataset: `metaphysika/taa-k2-repo-bf9416513f15`. It was built like the K2 launcher's archive (`git archive`, with `results/` and `docs/` excluded, plus `COMMIT.txt` and `ARCHIVE.json`), and all 120 bound source hashes match it.
