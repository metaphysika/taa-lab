# FT1 arm-3 follow-up (FT1-R): DRAFT for Chris's approval, 2026-11-17 (revision 2)

Status: **draft, not approved, nothing built or run.** Written by Claude (FT1 gate-stage thread) after Fable 5.2's idle-days review. Revision 2 takes in Fable's review of revision 1 (B1, B2, M1–M6 and smaller points). It is written before any FT1 test-part result exists, and it must be frozen (approved and recorded in `LAB_NOTEBOOK.md`) before any exists. Chris may cancel FT1-R after seeing FT1's results, but may not change it.

## In plain words

FT1's main question is whether a model trained on step-by-step reasons (arm 3) acts better on new cases than one trained on right answers alone (arm 2). Arm 3's first model failed the warm-up format check: its written reason looped until it hit the length limit.

The evidence points to two things working together:
1. **The model meets its own long reason in the conversation history.** It never saw that in training, and once it does, its reasons grow each turn until they loop.
2. **The reasons are written last at test, but first in training.** So the model never practised ending a reason in that position.

This follow-up retrains arms 2 and 3 with training examples laid out like the test: the action first, then the reason, with the model's own previous reason in the history. Nothing else changes. It runs only if FT1's arm 3 ends with fewer than two passing models. The fix may not be enough, because the loop appeared once even in the trained layout.

## What is known (evidence)

- **Training layout.** The system line is "One JSON object: reason, tool, args. null ends." The trained JSON is ordered `reason`, `tool`, `args`. Earlier turns are action-only lines inside the user card, with `"reason":""` (`FT1_TRAINING_SAMPLES_2026-11-12.md`; `exploratory/ft1/data.py` 282–285).
- **Test layout.** The system line asks for `{"tool": ..., "args": {}, "reason": "optional explanation"}` (`formation/study_a_pilot.py` `SYSTEM`). All 27 of arm 3 / 247056's gate turns used `tool`, `args`, `reason`.
- **Failure shape (gate `events.jsonl`, format only).**
  - All three malformed turns of 3 / 247056 hit the 1,024-token cap while cycling interchangeable phrasings of the same template slot.
  - None was on turn 0; all were on turn 1 or 2.
  - Replies grew turn by turn (220 → 343 → 358; 247 → 480), past the trained maximum of 258.
  - One single-turn acquisition reply, in the trained reason-first layout, also looped to the cap.
- **Arm 2 / 247056 passed in the same layout.** It had 32 of 32 valid turns, with steady replies of 140–316 tokens.
- **Already disclosed in pre-run §3.1:** "at test, arms 2 and 3 see their own long `reason` text in the history, which they never saw in training."
- **Arm 1 / 247057.** It failed on turn 0, where there is no history, and the other arms are clean with the same system line. Nothing in the shared layout points to a fix for FT1-R.

## Decisions for Chris

**R0. Trigger.** FT1-R runs only if FT1's arm 3 ends with fewer than two acquired seeds; Fable forecasts that at about 85–87%. Otherwise this draft is withdrawn.

**R1. What changes in the training records.**

1. **Key order and system line.** The trained JSON becomes `tool`, `args`, `reason`. The training system line becomes "One JSON object: tool, args, reason. tool null ends." The words of each trained target stay those FT1 chose (subject to R1.3).

2. **Own reason in the history.** The most recent earlier step in a record's history carries that arm's own text for that step:
   - arm 3 its reason; arm 2 its restatement; arm 2u none;
   - older steps stay action-only.

   The details:
   - The earlier step's reason (arm 3) and restatement (arm 2) are generated for that step by the same templates. Each pair must meet the same per-record gate (±5% or ±8 tokens).
   - Reason-bearing history lines are **never eligible for restatement**, so arm 2 never restates a restatement and every trained target keeps FT1's wording rules.
   - **Correction records (25%) keep action-only histories in both arms.** Their earlier step is the mistake, and the mistake carries no reason.
   - A record whose earlier-step pair has no in-gate combination keeps an action-only history in both arms, and is counted.
   - The diagnostics report how many of the 2,000 records carry a reason-bearing history; roughly 55–60% is expected.
   - **Rendering (Chris decides):**
     - (a) **real chat turns**: an assistant turn holding the earlier action and its text, then a user turn with its tool result, as at test. Recommended by Fable and Claude.
     - (b) a line in the user card, as FT1 does now.

     Sol confirms the trainer's mask still trains only the last assistant turn under (a).

3. **Token matching.**
   - Trained tokens are re-measured with the real Gemma tokenizer in the new key order.
   - FT1's choice of reason and restatement is kept wherever the pair still meets the gate. Where it does not, that record alone is re-chosen among its existing variants. If none fits, it is replaced by the next same-cell candidate (the v0.24.87 rule), and the count is reported.
   - The gates themselves do not change: ±5% or ±8 per record, 2% total, 640 trained, 1,024 total.

4. **Fit, from real-tokenizer figures (notebook 2026-11-14: prompt max 390, arm-3 trained max 258, largest record 576).**
   - Worst case: about 390 + 258 + 258 ≈ 910 of 1,024, plus a few wrapper tokens.
   - Realistic maximum: about 835.
   - These are to be confirmed by the real-tokenizer data job. The generator refuses, never truncates.
   - Pre-run D2's "prompt at most 384" is superseded: the code has no prompt cap, and 390 was already disclosed.

5. **No new closing sentence.** The existing last slot ("Next: …"), followed by `"}`, becomes the trained stop once `reason` is last. The diagnostics confirm that every arm-3 reason ends on that slot.

Nothing else changes: cases, themes, case mix, corrections, pressure lines, data order, the one-epoch recipe, LoRA settings, 250 steps and checkpoints.

**R2. Which arms are retrained.**
- **Recommended (B): arms 2 and 3, 3 new seeds each, in the new layout.**
  - P1 then compares like with like.
  - FT1's original arm 2 seeds stay reported as they are and are not pooled with FT1-R's.
  - Arm 2u is not retrained (it has no reason text and is descriptive), so 2u against FT1-R's arm 2 is a cross-layout comparison and is labelled so.
- **Cheaper (A): arm 3 only,** compared with FT1's original arm 2. The layout change is then confounded with the reasons. Not recommended.

**R3. Order and stop rule.**
- Train one arm-3 seed first and gate it.
- **If it is not acquired, for any reason, stop, report, and train nothing more without Chris's decision.** One seed is a noisy signal: arm 1 split 1 of 2 across seeds.
- If it is acquired, train the other five and gate each as in FT1.

**R4. What stays the same, and what must also change.**
- **The same:**
  - gate code and bars;
  - the 1,024-token reply cap;
  - the sealed test set and its parts, and the scorer;
  - evaluation settings: eager, chunked 256, ceiling 14,000;
  - **P1 exactly as pre-run §8, all clauses** (threshold, every-seed rule, over-refusal clause, seed-noise and floor rules, mechanical check);
  - "fewer than two acquired seeds means not established".
- **Also changes (versioned, never in FT1's files):**
  - The 40 acquisition decision points are the same, re-rendered with the new system line and key order; the bars are unchanged.
  - FT1-R has its own versioned plan (models: base plus the FT1-R arm-2 and arm-3 seeds) and its own analysis run. FT1's `plan.MODELS` and `aggregation.py` refuse foreign cells by design.
  - P3 is read with FT1-R's arm 2 against FT1's existing base result. Base is not rerun.
  - The pressure split, if approved for FT1, also applies to FT1-R's models.

**R5. Seeds.** Seeds 247061, 247062 and 247063 for each of arms 2 and 3. None of them is used in FT1.

**R6. Cost and timing.**
- Training: about 3 h per run, since longer records lengthen training (6 runs, about 18 h).
- Gates: 6, at about 1 h each.
- FT1-R's own test parts: 6 models at 2–3.5 h each.
- **Total about 40–45 free GPU hours**, about 1.5 weeks of Kaggle quota.
- Recommended start: after FT1's test parts are launched, likely early December.

## Separate FT1 decision: a replacement arm-1 seed

Arm 1 has 1 of 2 acquired seeds, so P2 is not established by rule. This belongs to FT1, not FT1-R, and must be decided before any FT1 test-part result.

- **Option yes:**
  - Train one new arm-1 seed, **247058**, in FT1's original layout. Arm 1 has not used it; arms 2 and 3 used it in FT1.
  - Then gate it and run its test parts alongside FT1's.
  - **P2's registered verdict stays "not established".** A supplementary P2 reading is reported beside it, labelled as added after a gate failure.
  - About 3 h training, 1 h gate and 2–3.5 h test.
  - The chance it is acquired is roughly a coin flip.
- **Option no:** P2 stays not established, and arm 1 / 247056 is reported descriptively.
- Fable leans yes; Claude agrees.

## Build (after approval only)

- Sol adds a versioned layout option to the training-data generator, the probe rendering and an FT1-R plan. FT1's original outputs must stay byte-identical when the option is off, and a test checks this.
- A real-tokenizer data report: fit, matching changes and replacements, reason-bearing history count, and the last slot of every arm-3 reason. Ten samples per arm.
- Fable reviews. Then a pre-run notebook entry with hashes and forecasts, and Chris's exact-commit approval for each stage: training, gates, then test parts.
- No sealed material is read at any point.

## Forecasts (to be finalised in the pre-run entry)

| Item | Claude | Fable |
|---|---|---|
| First FT1-R arm-3 seed acquired | 55% | 55% |
| FT1-R arm 3 ends with ≥ 2 of 3 acquired, given that | 75% | 75% |
| FT1-R arm 2 ends with ≥ 2 of 3 acquired | 80% | 80% |
| P1 supported, if testable | 15% | 15% |

## Limits stated now

- FT1-R runs after FT1's arm 3 failed its gate. It is a second attempt at the same comparison, disclosed as such. It uses new adapters, and it is frozen before any FT1 test-part result.
- The fix is chosen from one failed gate, and the loop appeared once in the trained layout too, so the fix may not be enough.
- In FT1-R the reason is trained and produced after the action. A P1 result is about training on reasons, not about reasoning before acting.
- Arm 3's reasons are still templated, so a P1 result is about this style of reasons.
- GPU time competes with FT1's test parts at about 30 free hours a week.
