# FT1 test parts at cb5b8657: pre-run DRAFT, 2026-11-17

Status: **draft, plan-only staging, nothing uploaded or launched.** Written by Claude (FT1 gate-stage thread) under Fable's idle-days plan. It becomes the pre-run notebook entry after the last four gates finish, the table is completed, and Fable checks the exact bundles. Launch needs Chris's exact-commit approval of the test parts.

## What a test part is

- Each eligible model runs the sealed test in **2 parts** (`part_count: 2`), at the same commit as its gate (`cb5b865775e9c6357834e953bf7d14d653e45d95`). Settings are the same: eager, chunked 256, ceiling 14,000.
- Each part mounts the sealed dataset and that model's own gate output. Before any test cell, the runner checks the gate's identity, settings and eligibility.
- A trained arm runs only if its gate says `acquired: true` and `trained: true`; otherwise it ends `ineligible`. Base always runs, as the reference.
- Claude never opens the sealed file or any sealed output. Only hashes and counts are seen.

## Eligible models (so far) and staged bundles

Staged plan-only in `C:/t/ft1g/.k2-launch/test-<model>-<part>/` (worktree detached at cb5b8657). For each bundle, the binding's source inventory (123 files), adapter and training-manifest hashes, data manifest, model source and settings equal those of the model's gate binding. Internet is off and `PLAN_ONLY = True`. Gate hashes are taken from each gate's own `manifest.json`, not from a Windows checkout, whose line endings change the bytes.

| Model | Gate `gate.json` | Part | Notebook | Binding | Kernel metadata | Draft receipt |
|---|---|---|---|---|---|---|
| base | `c25db301…` | 0 | `bd811991…` | `06ada346…` | `32cfe422…` | `62a40e3a…` |
| base | | 1 | `8000ce92…` | `28e4c335…` | `eda63a5e…` | `1fe88dd5…` |
| 1 / 247056 | `4de454ec…` | 0 | `92861d51…` | `ceb0c167…` | `494bc048…` | `f7205342…` |
| 1 / 247056 | | 1 | `f7a1aa99…` | `48aeb219…` | `a1d5ca32…` | `519be3a6…` |
| 2 / 247056 | `4209bf8b…` | 0 | `ac379f38…` | `916381f4…` | `25079b70…` | `4252e391…` |
| 2 / 247056 | | 1 | `17fde7c0…` | `af8d3fc3…` | `a8a69840…` | `7b4e8c67…` |
| 2u / 247056 | `42c9fc09…` | 0 | `84297c0e…` | `6ae75b02…` | `3a7694b0…` | `8fca957f…` |
| 2u / 247056 | | 1 | `a9f355e2…` | `5496634f…` | `a0629ff4…` | `3d31e41b…` |
| 2u / 247057 | `d37eb191…` | 0 | `ddff0dca…` | `b3ffd450…` | `62f36a8f…` | `47cd3c6b…` |
| 2u / 247057 | | 1 | `2a00a945…` | `6946bd95…` | `19185f6c…` | `3e300d20…` |
| 4 / 247056 | `7c55f354…` | 0 | `9d2ad07a…` | `c77b8359…` | `735e522b…` | `d02fd12e…` |
| 4 / 247056 | | 1 | `940ea262…` | `d1abb119…` | `a0d115a2…` | `a4d45e35…` |
| 4 / 247057 | `9b1898ae…` | 0 | `af026e85…` | `e3406401…` | `e63bd4d1…` | `3b3701a2…` |
| 4 / 247057 | | 1 | `b646dc68…` | `b7a63dba…` | `d1c049d8…` | `aaf67771…` |

To be added after Friday's gates: any of 2 / 247057, 2 / 247058, 3 / 247057 and 3 / 247058 that is acquired.

**Receipts.** Draft receipts are in `receipt-drafts/test/`, with `approved: false` and the owner fields PENDING. Each carries every bound field. Offline, `evaluate_runner.validate` refuses each draft and accepts the same receipt with `approved: true`.

**Planned datasets (not yet created).**
- `metaphysika/ft1-sealed-0d71f261`: the sealed cases file, SHA-256 `0d71f261…babd`. It is uploaded by a script that checks the hash and copies the file without printing or reading its content.
- `metaphysika/ft1-gate-out-<model>-cb5b8657`: each model's `gate.json`, with the bytes taken from the Kaggle output, so the hash matches the manifest.
- `metaphysika/ft1-test-approval-<model>-<part>-cb5b8657`: the signed receipts.

## Order

Fable's order:
1. base;
2. arm 2 (247056, then any later-acquired arm-2 seeds);
3. arm 4;
4. arm 2u;
5. arm 3, if any seed is acquired;
6. 1 / 247056 last, since P2 is not established and it is descriptive only.

Runs go two at a time, filling slots as they free.

## Estimated use

- $0.
- Throughput estimate (notebook, 2026-11-16 speed-test entry): about 1.3–1.8 GPU h per model for base and 2–3.5 h per trained model, covering both parts. For 7–9 models that is about 15–28 GPU hours.
- After Friday's gates use about 5 of the reset week's ~30 hours, the test parts likely spill into the following week.
- The estimate is not measured on sealed cases or trained reply lengths.

## Outcome rules (proposed, fixed before any result)

- **COMPLETE:** the part's status is `complete` and its manifest matches. Counts are reported as the code computes them.
- **INELIGIBLE:** the gate is not acquired or not trained. Only base or acquired models are staged, so this signals a binding error, and launches stop for review.
- **MECHANICAL:** the status is `stopped_mechanical_oom`. Per the pre-run draft, unknowns stay unknown and are resolved both ways. Rerunning such a part needs Chris's decision; proposed: rule A applies per part (one rerun at the same commit, then report as is).
- **NOT ESTABLISHED:** `incomplete`, no manifest, or a Kaggle kill. Relaunch needs Chris's yes, and the remaining parts wait.
- **Review stops:** any part over 6.5 h, a peak above 13.5e9 (if recorded), or an attention read-back mismatch.

## Forecasts (Claude; Fable to add at its check)

| Item | Claude |
|---|---|
| All parts COMPLETE | 75% |
| Any part `stopped_mechanical_oom` | 20% |
| Any part over 6.5 h | 5% |
| Total GPU hours within 15–28 | 65% |

## Before launch

- Fill in the table for Friday's acquired gates.
- Fable checks the exact bundles.
- The pressure-split wording (`FT1_PRESSURE_SPLIT_DRAFT_2026-11-17.md`) is approved and recorded.
- The FT1-R draft is frozen, approved or withdrawn, before any test-part result exists.
- Chris's words are recorded in each receipt.
