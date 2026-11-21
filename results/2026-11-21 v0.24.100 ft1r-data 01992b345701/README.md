# FT1-R revision 3 real-tokenizer data job at 01992b34: Q3 passed (exploratory, $0)

Kernel `metaphysika/ft1r-data-01992b345701`, version 1. One Kaggle CPU session, internet off, phase `ft1r-data`. No model inference and no training.
- **Exact commit:** `01992b34570124af78ca4a201164d5f8993001c4` (main after PR #182).
- **Approval:** Chris, 2026-11-20, given in advance: "If everything is ready after the merge go ahead with the next step the next kegel job". Recorded in the approval receipt and in the pre-run notebook entry of 2026-11-21.

## Contents

- **`staged/`:** the plan-only notebook (`PLAN_ONLY = True`) and the draft receipt (`approved: false`), as staged at the commit.
- **`launch/`:** what was pushed and uploaded:
  - the notebook, which differs from the staged one only in `PLAN_ONLY`, checked by JSON comparison;
  - `kernel-metadata.json`;
  - the approved receipt;
  - both dataset metadata files.
- **`kaggle-v1/`:** the full kernel output and log.
  - `ft1r-data/report.json` and `ft1r-data/output-manifest.json`; all listed hashes were verified at filing.
  - `ft1r-data/dataset/`: arm-2 and arm-3 training data in layout `ft1-r-v2`, the 40 probes, and `manifest.json` (SHA-256 `ece3b1d82b903f2617db5f739d872560b82ddfe4b2b90635dd7ac0bfcbcc377d`).

No sealed file was in the source artifact. No tokenizer files or weights are retained.

**Result:** `passed: true`; the tokenizer was verified (fingerprint `1698598f…8552`, matching FT1's recorded value). Q3 quote gate:
- arm-2 targets ending on a quoted line: 95 (order 0, pressure 95; needed 50);
- quoted mid-string: 2,000 (needed 50);
- 2,000 / 2,000 targets round-trip in each arm.

Fit: the largest record is 745 tokens (arm 2) and 742 (arm 3), within 1,024; the largest probe is 383. There were 18 replacements, all caused by the revision-3 changes.
