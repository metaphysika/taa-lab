# FT1 arm-3 follow-up (FT1-R): DRAFT for Chris's approval, 2026-11-17

Status: **draft, not approved, nothing built or run.** Written by Claude (FT1 gate-stage thread) after Fable 5.2's idle-days review. It is written before any FT1 test-part result exists. It must be frozen (approved and recorded in `LAB_NOTEBOOK.md`) before any test-part result exists, so it cannot be tuned against arm 2's scores.

## In plain words

FT1's main question is whether a model trained on step-by-step reasons (arm 3) acts better on new cases than a model trained on right answers alone (arm 2). Arm 3's first model failed the warm-up format check. Its written reason looped until it hit the length limit.

The likely cause is a mismatch between how the training examples were laid out and how the test asks the model to answer:
- in training, the reason came first and the action second;
- in the test, the action comes first and the reason last, in a longer back-and-forth.

This follow-up retrains with the training layout matched to the test, and changes nothing else. It runs only if FT1's own arm 3 ends with fewer than two passing models.

## What is fixed already (evidence)

- **Training layout.** The system line is "One JSON object: reason, tool, args. null ends." The trained JSON is ordered `reason`, `tool`, `args`. Earlier turns appear as action-only lines with `"reason":""` (`docs/process/FT1_TRAINING_SAMPLES_2026-11-12.md`, arm 3 samples).
- **Test layout.** The system line asks for `{"tool": ..., "args": {}, "reason": "optional explanation"}` (`formation/study_a_pilot.py` `SYSTEM`, used through `crossing.SYSTEM`). Arm 3 / 247056 answered in that order: `tool`, `args`, then a long `reason` (gate `events.jsonl`).
- **Failure.** All three malformed format turns of 3 / 247056 hit the 1,024-token cap while repeating reason sentences (notebook, 2026-11-17).
- **Already disclosed in the pre-run draft (§3.1):** "at test, arms 2 and 3 see their own long `reason` text in the history, which they never saw in training".

## Decisions for Chris

**R0. Trigger.** Recommended: FT1-R runs only if FT1's arm 3 ends with fewer than two acquired seeds. Fable forecasts that at about 85–87%. If arm 3 reaches two, FT1-R is not run and this draft is withdrawn.

**R1. What changes in the training records (two changes only).**
1. **Key order and system line.** The trained JSON becomes `tool`, `args`, `reason`. The training system line becomes a compact version of the test's: "One JSON object: tool, args, reason. tool null ends." Content stays word for word the same; only the order changes.
2. **Own reason in the history.** The most recent earlier turn in each record's history keeps that arm's own `reason` text. Arm 3 keeps its reasons and arm 2 its restatement; arm 2u's is empty, as now. Older turns stay action-only. So the model practises continuing after its own long text, as it must at test.
   - Fit: the largest prompt (333) plus one earlier reason (at most 247) plus the trained part (at most 247) is about 830. That is under the 1,024 total, and nothing is truncated. The generator refuses any record over the limits, as now.
   - The token matching between arm 2 and arm 3 (per record ±5% or ±8, total within 2%) is unchanged.

Nothing else changes: the records, cases, themes, case mix, corrections, pressure lines, data order, the one-epoch recipe, LoRA settings, the 250 steps and the checkpoints.

**R2. Which arms are retrained.**
- **Recommended (B): arms 2 and 3, 3 new seeds each, in the new layout.** P1 then compares like with like. FT1's original arm 2 seeds stay reported as they are and are not pooled with the new ones. Cost: about 6 × 2.3 h training plus 6 gates of about 1 h, so about 20 GPU hours.
- **Cheaper (A): arm 3 only, 3 new seeds,** compared with FT1's original arm 2. About 10 GPU hours. The layout change is then confounded with the reasons: a win could be the layout, not the reasons. Not recommended.

**R3. Replacement arm-1 seed (Fable's question).** Arm 1 has 1 of 2 acquired seeds, so P2 is not established by rule.
- **Option yes:** train one new arm-1 seed in FT1's **original** layout, since arm 1 has no reasons. It is disclosed as added after a gate failure, and P2 is reported with that note. About 3 GPU hours.
- **Option no:** P2 stays not established.
- Fable leans yes; Claude agrees. This is separate from R1 and R2 and could run with FT1's test parts instead.

**R4. Order and stop rule.** Train one arm-3 seed first and gate it before training the rest.
- If it fails format with the same reason loop, stop and report; do not train the others. That is about 3.3 GPU hours at risk instead of 20.
- If it passes, train the remaining five, and gate each as in FT1.

**R5. Test and scoring unchanged.**
- Same gate code and bars, same 1,024-token reply cap, same sealed test set, test parts, scorer and P1 thresholds (≥ 15 points, every arm 3 seed above arm 2's pooled rate; counts against at ≤ 0, or ≤ 4 with at most one seed pairing ahead), and the same "fewer than two acquired seeds means not established" rule.
- The evaluation settings stay eager, chunked 256 and ceiling 14,000.
- Only the training data generator and its manifest change, plus the new adapters.

**R6. Seeds.** New training seeds not used in FT1. Proposed: 247061, 247062, 247063 for each arm. The arm-1 replacement would use 247058.

## Build (after approval only)

- Sol adds a versioned layout option to the training-data generator. FT1's original output must stay byte-identical when the option is off, and a test checks this.
- A data diagnostics report and ten samples per arm, as in `FT1_TRAINING_SAMPLES_2026-11-12.md`.
- Fable reviews. Then a pre-run notebook entry with hashes and forecasts, and Chris's exact-commit approval for each stage: training, gates, then test parts.
- No sealed material is read at any point.

## Forecasts (Claude, for review; to be finalised in the pre-run entry)

| Item | Claude |
|---|---|
| First new-layout arm-3 seed acquired | 65% |
| New-layout arm 3 ends with ≥ 2 of 3 acquired (if R4 passes) | 75% |
| New-layout arm 2 ends with ≥ 2 of 3 acquired | 90% |
| P1 supported, if testable | 20% |

## Limits stated now

- This follow-up runs after FT1's arm 3 failed its gate. It is a second attempt at the same comparison, disclosed as such, not a fresh pre-registered study.
- Its layout fix is chosen from one failed gate. The new layout may fail for other reasons.
- Arm 3's reasons are still templated. A P1 result is about this style of reasons.
- GPU time competes with FT1's test parts, about 25–45 hours, at about 30 free hours a week. Recommended timing: after FT1's test parts are launched, likely early December.
