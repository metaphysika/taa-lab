# FT1-R training run, arm 3 seed 247061, at 01992b34: TRAINED (exploratory, $0)

Kernel `metaphysika/ft1-3-247061-train`, version 1. One Kaggle Tesla T4, internet off. Phase `train`, 250 optimizer steps, FT1-R revision 3 data (layout `ft1-r-v2`, data manifest `ece3b1d82b903f2617db5f739d872560b82ddfe4b2b90635dd7ac0bfcbcc377d`).
- **Exact commit:** `01992b34570124af78ca4a201164d5f8993001c4`.
- **Chris's approval (2026-11-21):** "Approve the three FT1 bundles as drafted (cb5b8657 tests, 1/247058 and FT1-R 3/247061 at 01992b34), rule A per part, and the recommended order." This run is Bundle 3's training job (`docs/process/FT1_COMBINED_APPROVAL_2026-11-21.md`).
- **FT1-R was paused later the same day** by Chris's decision, relayed from the planning thread (`LAB_NOTEBOOK.md`). This job was already running, so it was left to finish and is filed here. Its gate has not run and is not launched without Chris's word.

## Contents

- **`launch/`:** what was staged and pushed. The hashes match the pre-run table.
  - The staged notebook (`4665271b…`) and the pushed notebook (`c7e5660c…`) differ only in `PLAN_ONLY`, which was checked by JSON comparison.
  - `ft1-binding.json` (`e4ee563c…`) and `kernel-metadata.json` (`24f70a30…`).
  - The approved receipt (`dd145e60…`) and the never-uploaded draft (`e94f2432…`).
- **`kaggle-v1/`:** text evidence from the kernel output, fetched after status COMPLETE. All 53 output files match the run's `manifest.json`.

## Not in git

These are kept out of git because of their size and the Gemma licence: the adapter and checkpoint weights, optimizer, scaler, scheduler and RNG state, `training_args.bin`, and the tokenizer copies. Their SHA-256 values are in `kaggle-v1/ft1-3-247061-train/manifest.json`; the adapter is `adapter_model.safetensors`, `397f828e…`.

A complete copy is kept at `C:/Users/lahn0/T3/ft1-artifacts/2026-11-21 v0.24.100 ft1r-train-3-247061 01992b345701/`.

## Result

| | Value |
|---|---|
| Status, steps | `trained`, 250 |
| Skipped updates (limit 25) | 1 (step 12) |
| Micro-losses finite | 2,000 of 2,000 |
| Adapter tensors finite | true |
| Peak allocated (limit 13.5e9) | 9.50e9 |
| Mean / slowest step (line 75 s) | 35.2 s / 39.6 s |
| Setup; training complete (line 6.5 h) | 294 s; 9,116 s (2.5 h) |

The adapter has not been evaluated.
