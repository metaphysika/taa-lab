# Seed 2 implementation stopped at a draft/code mismatch

Status: blocked before implementation on shuffle-procedure provenance, after
the stage thread resolved the training-order decision. Build-only inspection at main
`40c77e66ab92a2861d3e4d80a4274db48adb49c0`; plan reference: Master Plan
v3.2, M3 seed 2, Draft A (now revision 3).

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

The stage thread subsequently directed seed 2 to change both the LoRA/Trainer
seed and the shuffle seed, preserving the fixed-order mechanism and using the
original shuffle procedure. Draft A revision 3 records that decision and the
original mismatch.

The original generator was not found in the repository searches or originating
asset commits. Commit `8ac0069b5d848dbe8f5fefa8e11dc060a86fb3bd`
introduces the Gate 7a order asset without generator code; commit
`94ac5092fcb0e64fa718c8f0fb319380229eb4ae` introduces the v02417 copy.
K2_DESIGN line 25 and PAPER3_STUDY_D_GATE7A_v0247 lines 58–61 name seeds,
but do not specify a shuffle algorithm or initial ordering.

An offline candidate reconstruction does match all 2,000 positions:
`ids = ['T%04d' % i for i in range(1, 2001)]`, followed by
`random.Random(247052).shuffle(ids)` in Python 3.12. The v02417 and v02424
order files are also byte-identical. This establishes a matching reconstruction,
not provenance that this was the original documented procedure. No new order
was generated or adopted. The stage thread explicitly required another stop
if no documented original procedure could be found. Implementation remains
blocked pending the original generator/procedure or explicit authorization to
adopt this verified reconstruction. Both new seed values remain unchosen.

Validation: the candidate reconstruction and byte comparison passed offline;
`git diff --check` passed. The preceding documentation commit passed all 550
fast tests and scripted scenarios (133.807 seconds). No new executable code or
new training path exists to test in this revision.

No model, Modal, Kaggle or paid call was made. No credentials were read. No
results were removed. No behavior changed, so README's version was not bumped;
the notebook pre-run entry remains Claude's task. Seed selection, cost estimates,
caps, launch windows and executable receipts remain pending implementation.
