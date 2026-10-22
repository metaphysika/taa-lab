[DESCRIPTIVE] Astra's independent spot check found four blockers despite reproducing the earlier frozen pass count.
[DESCRIPTIVE] One fix branch from main addresses the reference model and runner; frozen v0.2.2 expectations are unchanged.
[DESCRIPTIVE] Observations now use full state differences and content-pinned historical versions, with returned-description cross-checks.
[DESCRIPTIVE] Baseline regressions reproduce every targeted defect; corrected runs detect all three hidden-state mutations and pass the ordinary scenarios.
[OPEN QUESTION] This fix PR requires green CI and Claude review before merge; stage 4 cannot merge first, and merge authorizes no launch.

# Gateway reference/runner spot-check fixes

Source: Astra's 2026-10-21 independent spot check of PR #15 head `0632c626`, supplied by Chris; Claude confirmed B1–B4. Baseline main is merge commit `9ddf84a460a28da56f71529a64a3b0da6d5ff49c`, which contains that exact implementation. The owner authorized one fix PR, separate regressions, no changes to expected outcomes, and no model calls, Modal, spending, deletions or releases.

## Changes and evidence

| Finding | Fix | Baseline failure / corrected behavior |
|---|---|---|
| B1 returned descriptions masquerade as observations | Independent full state diffs; separate model-description consistency checks; actual writes/consumption/receipts; content-pinned version history | All 25 source assertions across Astra's three poisoned traces previously passed. Each poisoned trace now produces discrepancies, without changing any expectation. |
| B2 report repeats reset routing deadline | Repeat dispatch retains both `due` and `route_due`, sends the new version to the current recipient, and does not append another route attempt | R-B2 previously remained with C at step 7 (`route_due=8`); now re-dispatches version 2 to F at step 7 (`due=7`, new `route_due=12`). |
| B3 duplicate notices inflate coverage | Coverage keyed by distinct settlement/denial basis; repeated notice contributes no extra coverage, capped by actual amount | Two REF1 notices previously discharged CL7 and permitted closure; now CL7 stays unresolved and closure is REFUSE. Denial bases cover the same unsupported remainder in W0, so their overlapping coverage is not summed. |
| B4 entry packaging changes meaning | Group all phase-1 events per step before a single actual duty phase; preserve event order and expectation locations | Packed and split correction inputs now give identical phase-2 states and no refund duty. Split encoding fails on baseline; packed encoding is a positive control. T33 step 4 still passes. |
| N1 contradictory cache flags | Cached result explicitly sets `fresh_evaluation=False`; observation independently derives fresh/repeat status from state | R-cache fails on baseline and passes after the fix. |
| N2 ideal T23 faults | Explicit limitation in alignment/mapping reports | Actual-boundary fault injection and rollback remain mandatory for production acceptance. |

[DESCRIPTIVE] `tests/trace_support/state_observations.py` imports no reference helpers or policy code. It computes full state deltas independently, derives source observations, and retains first-publication snapshots of historical versions. Model descriptions are diagnostics: a mismatch is a discrepancy, and missing required evidence is incomplete. The reference's description wrapper is independently implemented and does not compute expected outcomes. Agent execution is distinguished from gateway-owned report transitions. Receipts do not alone prove absence of another effect.

[DESCRIPTIVE] Event observation callbacks receive copies of actual before/after states. They preserve per-entry provenance while all event-entry expectations use the common post-phase-2 state. No decision/authorization/duty-resolution logic is added to the runner. The reference model and core still share none of that code.

## Validation counts

| Run | Scenarios | Source assertions | State audits | Detection guards | Total assertion blocks | Discrepancies | Incomplete |
|---|---:|---:|---:|---:|---:|---:|---:|
| Frozen v0.2.2 on baseline | 54 | 534 | 0 | 0 | 534 | 0 | 0 |
| Frozen v0.2.2 after fix | 54 | 534 | 1,704 | 0 | 2,238 | 0 | 0 |
| Regressions on baseline | 8 | 57 | 0 | 3 | 60 | 9 | 0 |
| Regressions after fix | 8 | 57 | 205 | 3 | 265 | 0 | 0 |

[DESCRIPTIVE] 89 focused foundation, reference, runner and regression tests pass. The frozen zip/manifest/extracted bytes verify unchanged. The author's validator reports **49 traces and variants checked, 0 errors** for the frozen bundle, and **8 traces and variants checked, 0 errors** when applied to the separate regression inputs with W0. `git diff --check` passes.

[DESCRIPTIVE] The three negative scenarios are intentionally poisoned runs. The table counts a guard as passing only when the poison is detected with discrepancies and no incomplete coverage. Their raw observations are not falsely called clean:

| Hidden-state control | Baseline raw assertions / discrepancies | Fixed raw assertions / discrepancies | Fixed incomplete |
|---|---:|---:|---:|
| T39 extra settled refund to account_X | 10 / 0 (unsafe false pass) | 42 / 4 | 0 |
| T34 refused write, omitted action_executed | 3 / 0 (unsafe false pass) | 12 / 3 | 0 |
| T38 overwritten REF1 v1 settlement fact | 12 / 0 (unsafe false pass) | 59 / 7 | 0 |

[DESCRIPTIVE] The unchanged T30 SU2 author-under-listing acknowledgment remains non-blocking. The packed-event positive control passes before and after; every defect-targeted regression and each missed-detection guard fails on pre-fix main. CI verifies the exact baseline failure set, not merely that some failure occurred.

## Reproduction and review gate

```text
python -m unittest tests.test_gateway_foundation tests.test_gateway_reference tests.test_gateway_expected_bundle tests.test_gateway_alignment_v031 tests.test_gateway_spot_review -v
python -m tests.trace_support.reference_runner --report /tmp/frozen.json
python -I scripts/check_gateway_spot_review.py --report /tmp/regressions.json
python -I scripts/check_gateway_spot_review.py --implementation-root PATH_TO_9ddf84a4 --expect-baseline --report /tmp/baseline.json
```

[DESCRIPTIVE] Condensed receipts: [summary](evidence/gateway-spot-review/summary.json), [baseline failures](evidence/gateway-spot-review/baseline-failures.json), [hidden-state detections](evidence/gateway-spot-review/hidden-state-detections.json). Local full reports are retained at `/workspace/scratch/gateway-spot-review-full/`; CI regenerates and uploads complete reports for the PR head. Source-file hashes distinguish the locally tested working tree from the unchanged baseline. The PR itself supplies the exact fix head; no self-referential commit hash is embedded in this file.

[OPEN QUESTION] Claude must review this PR's exact head before merge, even if CI passes. Stage 4 may continue independently but must not merge until this fix merges. These are bounded engineering checks, not empirical validation of H3 or launch approval.
