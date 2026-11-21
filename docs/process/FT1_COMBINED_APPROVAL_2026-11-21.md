# FT1 test parts, replacement arm-1 seed, and FT1-R first stage: combined pre-run, 2026-11-21

Status: **pre-run draft for Chris's exact-commit approval. Nothing uploaded or launched.** Written by Claude (FT1 test-part stage thread) after all 12 FT1 gates and the FT1-R revision 3 freeze (`LAB_NOTEBOOK.md`, 2026-11-20 and 2026-11-21), and **before any FT1 test-part result exists**. It supersedes `FT1_TEST_PARTS_PRERUN_DRAFT_2026-11-17.md` for the model list, outcome rules and forecasts; that draft is kept as the record. Full SHA-256 of every staged file: `FT1_COMBINED_APPROVAL_HASHES_2026-11-21.json`.

All three bundles are exploratory, run on free Kaggle T4 GPUs (internet off), and cost $0.

## Bundle 1: FT1 test parts at `cb5b8657` (16 jobs)

**What runs.** Each of 8 models runs the sealed 48-case test in 2 parts (`phase: evaluate`, `part_count: 2`), at its gate's commit `cb5b865775e9c6357834e953bf7d14d653e45d95` and settings (eager, chunked prefill 256, prompt ceiling 14,000, 1,024-token reply cap). Each part mounts the sealed dataset and that model's own `gate.json`; the runner checks the gate's identity, settings and eligibility before any test cell. Claude never opens the sealed file or any sealed output; only hashes and counts are seen.

**Models (final list):** base (reference) and the 7 acquired adapters: 1 / 247056; 2 / 247056; 2 / 247058; 2u / 247056; 2u / 247057; 4 / 247056; 4 / 247057. The five not-acquired adapters (1 / 247057, 2 / 247057, 3 / 247056, 3 / 247057, 3 / 247058) do not run.

**Staged bundles** (`C:/t/ft1g/.k2-launch/test-<model>-<part>/`, worktree detached at cb5b8657, `PLAN_ONLY = True`). The 14 bundles staged on 2026-11-17 were re-hashed today and match the old draft's table. 2 / 247058's two bundles were staged today with the same stager and arguments. A check script confirmed for all 16: the binding's 123-file source inventory, adapter, training manifest, data manifest, model source and settings equal the model's gate binding; `gate_sha256` equals the `gate.json` hash in that gate's own Kaggle `manifest.json`; the gate says `acquired: true` (base excepted); internet off; each draft receipt is refused by `evaluate_runner.validate` and the same receipt with `approved: true` is accepted.

| Model | `gate.json` | Part | Notebook | Binding | Kernel metadata | Draft receipt |
|---|---|---|---|---|---|---|
| base | `c25db301…` | 0 | `bd811991…` | `06ada346…` | `32cfe422…` | `62a40e3a…` |
| base | | 1 | `8000ce92…` | `28e4c335…` | `eda63a5e…` | `1fe88dd5…` |
| 2 / 247056 | `4209bf8b…` | 0 | `ac379f38…` | `916381f4…` | `25079b70…` | `4252e391…` |
| 2 / 247056 | | 1 | `17fde7c0…` | `af8d3fc3…` | `a8a69840…` | `7b4e8c67…` |
| **2 / 247058** (new) | `bf0a4e65…` | 0 | `ea3804f2…` | `32e61c2b…` | `217357ca…` | `ff3ca0c3…` |
| **2 / 247058** (new) | | 1 | `46b8b504…` | `d2564be0…` | `9ea5001a…` | `44b2a1ff…` |
| 4 / 247056 | `7c55f354…` | 0 | `9d2ad07a…` | `c77b8359…` | `735e522b…` | `d02fd12e…` |
| 4 / 247056 | | 1 | `940ea262…` | `d1abb119…` | `a0d115a2…` | `a4d45e35…` |
| 4 / 247057 | `9b1898ae…` | 0 | `af026e85…` | `e3406401…` | `e63bd4d1…` | `3b3701a2…` |
| 4 / 247057 | | 1 | `b646dc68…` | `b7a63dba…` | `d1c049d8…` | `aaf67771…` |
| 2u / 247056 | `42c9fc09…` | 0 | `84297c0e…` | `6ae75b02…` | `3a7694b0…` | `8fca957f…` |
| 2u / 247056 | | 1 | `a9f355e2…` | `5496634f…` | `a0629ff4…` | `3d31e41b…` |
| 2u / 247057 | `d37eb191…` | 0 | `ddff0dca…` | `b3ffd450…` | `62f36a8f…` | `47cd3c6b…` |
| 2u / 247057 | | 1 | `2a00a945…` | `6946bd95…` | `19185f6c…` | `3e300d20…` |
| 1 / 247056 | `4de454ec…` | 0 | `92861d51…` | `ceb0c167…` | `494bc048…` | `f7205342…` |
| 1 / 247056 | | 1 | `f7a1aa99…` | `48aeb219…` | `a1d5ca32…` | `519be3a6…` |

**Datasets created at launch (none exist yet).**
- `metaphysika/ft1-sealed-0d71f261`: the sealed cases file, SHA-256 `0d71f261052be3a6a5e1224d80d316b0d2424adbe8e34bfb5c3397ff5e00babd`. Uploaded by Sol (who may handle sealed material) with a script that checks the hash and copies the file without printing or reading its content. Claude does not touch it.
- `metaphysika/ft1-gate-out-<model>-cb5b8657`: each model's `gate.json`. Staged today in `C:/t/ft1g/.k2-launch/ft1-gate-out-<model>-cb5b8657/` from the exact committed bytes (via `git show`, not the Windows checkout); each hash equals the binding's `gate_sha256`.
- `metaphysika/ft1-test-approval-<model>-<part>-cb5b8657`: the signed receipts, each carrying Chris's words and a context line.

**What is analysed (unchanged rules, plus the approved additions).**
- P1–P5 exactly as in `FT1_PRERUN_DRAFT_2026-11-12.md` §8. Under the fixed rules, **P1 is not established** (arm 3 has 0 acquired seeds) and **P2 is not established** (arm 1 has 1). **P3** (arm 2 beats base by at least 15 points of pair-correct) is testable with arm 2's seeds 247056 and 247058. P4 and P5 are testable.
- **Pressure split** (approved 2026-11-17, wording in the notebook): counts for the pressure and no-pressure halves for every model and pooled arm; no threshold; it runs only in the final analysis. The original arm-1 seeds are pooled; 1 / 247058 is reported as its own row only.
- **Supplementary P2 note.** P2's registered verdict stays "not established". A supplementary reading, labelled "Arm 1 / 247058 added after a gate failure", applies P2's thresholds to arm 1 seeds 247056 and 247058 and is printed beside the registered verdict, never in its place.

## Bundle 2: replacement arm-1 seed 247058 at `01992b34` (training, gate, 2 test parts)

**The commit differs from cb5b8657.** Chris approved the replacement seed on 2026-11-17; it is wired as `plan.SUPPLEMENTARY_MODEL` (PR #178), which exists only in later code. It therefore trains, gates and tests at `01992b34570124af78ca4a201164d5f8993001c4` (the FT1-R revision 3 freeze commit, main after PR #182; main `17ceaa96` differs from it only in docs and results). The training recipe, FT1 data (`95759f67…`, layout `ft0b`, original FT1 cards), seed-ordered data order and 250 steps are the same as for the original arm-1 seeds. The binding differs from 1 / 247056's only in seed, data order (identical to 2 / 247058's order, same seed), commit and receipt. Source files changed between the original training commit `0449a230` and `01992b34`: `data.py`, `kaggle.py`, `plan.py`, `runner.py` and `training.py` on the training path, mostly FT1-R branches; whether the FT1-layout path is behaviourally unchanged is a review item for Fable. Gate and test parts use the same evaluation settings and sealed test as Bundle 1, at `01992b34`.

**Staged** (`C:/t/ft1h/`, a clean worktree detached at `01992b34`, no `keys.env`):

| Job | Notebook | Binding | Kernel metadata | Draft receipt |
|---|---|---|---|---|
| train 1 / 247058 | `f833ee75…` | `29298463…` | `4f057dad…` | `eb346f3a…` |

- Datasets: repo archive `metaphysika/taa-k2-repo-01992b345701` (staged by `k2_kaggle.launch stage-repo --plan`, `results` and `docs` excluded), FT1 data `metaphysika/ft1-data-5b2b3638845c` (exists), wheels, receipt `metaphysika/ft1-train-approval-1-247058-01992b345701`.
- `runner.validate_approval` refuses the draft receipt and accepts it approved; `runner.verify_source` passes against the worktree.
- Gate and test bundles can be staged only after the adapter exists. Their hashes go in a notebook addendum before each push, as was done for the 11 FT1 gates.

**Outcome rules.** Training: as for the 11 FT1 training runs (TRAINED; more than 25 skipped steps means not trained). Gate: as for the FT1 gates, with gate rule A. Test parts: as in Bundle 1. If 1 / 247058 is not acquired, its test parts do not run and the supplementary P2 reading is "not available".

## Bundle 3: FT1-R first stage, arm 3 / 247061 at `01992b34` (training and gate)

**What runs.** FT1-R revision 3 (frozen 2026-11-21: code `01992b34`, data manifest `ece3b1d82b903f2617db5f739d872560b82ddfe4b2b90635dd7ac0bfcbcc377d`, layout `ft1-r-v2`). Arm 3 / 247061 trains on the frozen data, then its gate runs (40 revision-3 probes and the 8 format episodes, same bars, plus the Q7 descriptive diagnostics). The sealed module is excluded from FT1-R's source inventory and the runner refuses it.

**Staged** (`C:/t/ft1h/`):

| Job | Notebook | Binding | Kernel metadata | Draft receipt |
|---|---|---|---|---|
| train 3 / 247061 | `4665271b…` | `e4ee563c…` | `24f70a30…` | `e94f2432…` |

- Datasets: the same repo archive, FT1-R data `metaphysika/ft1r-data-ece3b1d82b90` (staged from the exact committed bytes of the data job's output; every file matches the manifest, and the manifest hash is `ece3b1d8…`), wheels, receipt `metaphysika/ft1r-train-approval-3-247061-01992b345701`.
- The repo archive includes `exploratory/ft1/sealed.py` as a code file (it is needed by Bundle 2's test parts). FT1-R does not bind, verify or import it.
- Receipt validation and source verification pass as for Bundle 2.

**Stop rules (Q5, enforced in code by `plan_ft1r.py`, no override).** If 3 / 247061 is not acquired, for any reason, FT1-R stops and nothing more trains without Chris's decision. If it is acquired, arm 2 / 247061 (training and gate) is **not** covered by this approval; it needs its own exact-commit approval. `plan_ft1r.analyze_p1` must be wired before any FT1-R test part.

## Outcome rules for test parts (Bundles 1 and 2), fixed before any result

- **COMPLETE:** status `complete` and the manifest matches. Counts are reported as the code computes them.
- **INELIGIBLE:** only base and acquired models are staged, so this means a binding error. Launches stop for review.
- **MECHANICAL** (`stopped_mechanical_oom`): unknowns stay unknown and are resolved both ways. **Proposed for Chris: rule A per part:** one rerun of that part at the same commit; if still mechanical, it is reported as is.
- **NOT ESTABLISHED:** `incomplete`, no manifest, or a Kaggle kill. Relaunch needs Chris's yes; the remaining parts continue only if the cause is clearly specific to that job.
- **Review stops:** any part over 6.5 h, a peak above 13.5e9 (if recorded), or an attention read-back mismatch.
- A weekly-quota refusal is a wait, not a failure: nothing ran, and the job retries unchanged after the reset.

## Fable's forecast on 2 / 247058, with "malformed" defined

Fable forecasts that **2 / 247058 has at least 4 of its 24 pressure-half test episodes malformed (70%)**, because it breaks JSON on quoted pressure lines (gate diagnosis, 2026-11-20). Definition, as Astra asked (exact wording to be confirmed in Fable's check):
- **Episode:** one of the 24 test episodes of 2 / 247058 whose case carries the pressure line (12 pressure pairs × 2 twins), across both test parts.
- **Malformed episode:** at least one model turn in that episode whose retained `turn` event has `malformed: true`, meaning the FT1 parser `scoring.parse_action` (first-JSON-object policy) could not read an action from the reply. Cap-hit replies that never close count. Out-of-memory or context-limit stops do not.
- It is counted from the retained events after the run. It is descriptive: no verdict depends on it.

## Order for the shared free GPU hours

Kaggle allows 2 sessions at once and about 30 GPU hours a week. About 4 h are used this week; the quota resets about Saturday 2026-11-28 00:00 UTC (Friday 5 pm Phoenix).

| | Estimate (GPU h) |
|---|---|
| Bundle 1: base about 1.5; 7 trained models at about 2–3.5 each | 15–26 |
| Bundle 2: training about 1.9; gate about 0.5–1.5; 2 test parts about 2–3.5 | 4.5–7 |
| Bundle 3: training about 2.2; gate about 1–1.5 | 3–4 |
| **Total** | **about 23–37**, so it spills into the week of 2026-11-28 |

**Proposed order (Claude):**
- **Slot A:** Bundle 1 in Fable's order: base, 2 / 247056, 2 / 247058, 4 / 247056, 4 / 247057, 2u / 247056, 2u / 247057, 1 / 247056.
- **Slot B:** 3 / 247061 training, then 1 / 247058 training, then the two gates (3 / 247061 first). Slot B then takes the next item from slot A's queue, and 1 / 247058's two test parts run last.

Why: base and arm 2 first make P3, FT1's one testable prediction, readable earliest. FT1-R's first gate is a stop-or-go point for a 40–45 GPU-hour program, and its answer (does the format fix work?) is FT1-R's main value, so it is learned early at small cost. Arm 1 is descriptive only, so it goes last; if the quota runs short, the arm-1 parts are what slip. Results of base and arm 2 would usually arrive this week; the full set, early in the week of 2026-11-28.

**Alternative:** run all of Bundle 1 first and Bundle 3 after FT1's results, so Chris can cancel FT1-R before it uses any GPU time. Cost: FT1-R's first answer arrives about a week later.

## Forecasts (Claude; Fable adds its own at the readiness check)

| Item | Claude |
|---|---|
| All 16 Bundle-1 parts COMPLETE | 75% |
| Any Bundle-1 part mechanical | 20% |
| Any part over 6.5 h | 5% |
| Bundle-1 GPU hours within 15–26 | 65% |
| P3 met | 40% |
| 1 / 247058 TRAINED | 95% |
| 1 / 247058 acquired, if trained | 75% |
| 3 / 247061 TRAINED | 95% |
| 3 / 247061 acquired (revision 3 plan: 50%) | 50% |

I expect P3 to be not met or not established (about 60%); I'm wrong if arm 2's pooled pair-correct beats base by 15 points or more under every resolution of unknowns. One check that could fail: 2 / 247058's malformed episodes (above).

## Drift caution (Neon, recorded for Chris)

Even with revision 3, a supported P1 is only about 4% likely. FT1-R's main value is a clean test of whether the format fixes work. Chris may cancel FT1-R after FT1's results, but may not change it.

## Before launch

1. Fable's fresh-context readiness check of each bundle at its exact commit, with a pre-mortem. Its findings and forecasts are added here.
2. Chris's exact-commit approval, quoted verbatim in the notebook and in each receipt.
3. This document becomes the pre-run notebook entry, committed and pushed to a branch before the first push to Kaggle.
