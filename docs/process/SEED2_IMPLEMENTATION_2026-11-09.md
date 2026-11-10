# Seed 2 implementation stopped at a draft/code mismatch

Status: blocked before implementation. Build-only inspection at main
`40c77e66ab92a2861d3e4d80a4274db48adb49c0`; plan reference: Master Plan
v3.2, M3 seed 2, Draft A revision 2.

Draft A says the Trainer's `seed` and `data_seed` control training order.
The unchanged Study D runtime instead fixes the order independently:

- `scripts/study_d_gemma_stages_runtime_v02424.py:162` reads the `high`
  record IDs from `training-order.json`.
- Line 163 requires the unchanged 2,000-example dose/order, and line 166
  constructs the dataset in that order.
- Lines 441–442 override the Trainer sampler with `SequentialSampler`.
- `studies/formation-study-d-gemma-stages-v02424/training-order.json` records
  that order's seed as 247052, separately from training seed 247056.

Changing all four requested training-seed locations would change the seed
used before LoRA initialization and the Trainer settings, but would preserve
the frozen example order. Making the new seed shuffle examples would require
changing the sampler or order asset, contrary to the unchanged-recipe instruction.

The implementation brief explicitly requires stopping and reporting a draft
that is wrong against the code rather than improvising. No seed 2 training or
evaluation path has therefore been added. The next decision is to correct the
draft to explicitly preserve the fixed order, or separately authorize an order
change. This note does not select either option.

No model, Modal, Kaggle or paid call was made. No credentials were read. No
results were removed. No behavior changed, so README's version was not bumped;
the notebook pre-run entry remains Claude's task. Seed selection, cost estimates,
caps, launch windows and executable receipts remain pending implementation.
