# Fable design review: FT1 draft, revision 1 (2026-11-12)

Reviewer: Fable (claude-fable), fresh context, bounded packet, read-only, at the FT1 design worktree (main `2d783026` plus the draft). It read `FT1_PRERUN_DRAFT_2026-11-12.md` (revision 1) and only the files listed in its packet: `core.py`, `ft0b.py`, `k2_train.ipynb`, the step-4 harness files, its own options review, and the 2026-11-07 and 2026-11-10 notebook entries. Recorded verbatim by the stage thread (Claude). Revision 2 of the draft answers it.

Stage-thread checks after the review (in code, before revising):
- The episode parser (`formation/study_b_parser_v0234.py` → `formation/study_b_v0227.parse_action`) accepts the keys `tool`, `args` and an optional string `reason`. Fable's item 5 "not verified" point is resolved: no parser change is needed for episodes.
- `k1.answer` requires exactly `tool` and `args`: confirmed. FT1 needs a versioned knowledge scorer.
- The existing scorer flags only `decide_question` on reserved questions as usurping; outside-sphere acts need a versioned "unauthorized" flag.
- The four outside-sphere conditions are in the 2026-11-10 handoff (`C:\Users\lahn0\T3\briefs\handoff-2026-11-10-ft0-stage.md`), not the notebook; Fable is right. Revision 2 writes them out.

---

# FT1 design review (Fable, read-only)

## 1. Verdict
**NEEDS CHANGES FIRST.** The structure is right, but four fixes are needed before Chris decides; all are edits to the draft, not new experiments.

1. **Histories do not fit.** A step-3 record carrying two earlier turns with 150–640-token reasons cannot fit a 384-token prompt. The draft must say that earlier turns in history are action-only, identical across arms, and disclose that at test the model sees its own long text in history.
2. **No repetition in arm 2's restatement.** See section 3.
3. **The protocol check runs in the wrong rendering.** It tests the compact format, not the freight harness prompt.
4. **The `reason` key is unverified against the parser, and breaks the knowledge scorer.** `k1.answer` accepts only an object with exactly `tool` and `args`, so a trained `reason` key scores as no answer.

## 2. Decisions
- **D1: agree, with two tweaks.** Generate 2,000 unique wrongful records instead of drawing each twice, so arm 1 is not a two-epoch arm. Arm 1 is trained never to report, so silent refusal is true by construction; P2's cost clause should rest on over-refusal of lawful twins alone.
- **D2: agree,** with fix 1. 2,048 tokens is not worth a new fit check.
- **D3: agree.** A validated scorer and a base floor in the same world outweigh the "new world" appeal. Drop "unchanged in code and scorer" unless Sol confirms the scorer already handles outside-sphere acts and found recipients; I could not check that in the files allowed.
- **D4: agree with A, modified** (section 3), plus a cheap unpadded arm 2.
- **D5: agree.** Sol's sealed generator, Astra blind.
- **D6: agree** with 3/3/2/2, plus unpadded arm 2 at 2 seeds.
- **D7: disagree in part** (section 4).
- **D8: agree with 24 pairs.** A third seed buys more than eight extra pairs.

## 3. Token matching (option A)
**Sound in principle.** It is the right control for "any text before acting helps".

**The loss claim is correct.** `FixedTrainer.compute_loss` passes Trainer's `num_items_in_batch` (supervised tokens across the eight accumulated records) to `ft0b.chunked_loss`, which sums cross-entropy and divides by it. So long records dominate each update. Under A, arm 2's action tokens are diluted equally, which is a point in A's favour that the draft does not claim.

Three problems:
- **Repetition is a new confound.** "Truncated or repeated" trains arm 2 to loop text. At test it may run into the 1,024 reply cap and lose episodes as format failures, which would support P1 for a mechanical reason. It also contradicts the draft's own unit test (a repeated restatement is not a subsequence of the prompt). Fix: never repeat. Write arm 3's reasons no longer than the restatable material and fill arm 2 by quoting more fields.
- **Token-matched is not gradient-matched.** Copying from the prompt is learned in a few steps; paraphrased reasons keep irreducible loss. Disclose it and log per-arm loss split into action and non-action tokens.
- **Mild smuggling.** Choosing which lines to quote is the fact-finding step. That is acceptable and disclosed, but it means A alone cannot tell "reasons do not help" from "restating helps as much".

**Better alternative:** A plus unpadded arm 2 at 2 seeds, descriptive only. Its records are about 430 tokens, so I estimate about 2 h per training, not 4.6. It also keeps the Master Plan's literal arm 2 in the study.

## 4. Thresholds
One pair is 4.2 points per adapter. For 72 pooled pair-observations near 40% correct, the standard error of an arm difference is about 8 points if independent. It is more like 10–12 once the same 24 items repeat across seeds and seed variance is included.

- **15 points for "supported": keep.** It is about 1.5 standard errors, and the every-seed condition does real work. State it in counts: at least 11 more correct pairs of 72 (8 of 48 with two seeds).
- **"≤5 counts against" is unfair as worded.** A true 10–15 point gain lands at ≤5 roughly one time in five to one in three. Suggested:
  - **Counts against:** difference ≤0, or ≤4 points (one pair per seed) with arm 3 ahead in at most one seed-index pairing.
  - **Inconclusive:** 1–14 points otherwise, worded "cannot exclude a gain under about 12 points".
- **Add a seed-noise rule:** if the within-arm seed spread (max minus min) is at least the arm difference, P1 is inconclusive whatever the pooled number.
- **Add a floor rule:** if arms 2 and 3 are both under 15% pair-correct, P1 is "not testable (floor)". Pre-declare three secondary counts: W without wrongful act, W complete act, U lawful success.

## 5. Factual errors against the code
- **Knowledge scorer.** The step-(1) rule needs new code that tolerates extra keys; the existing `k1.answer` does not. Fallback (2) is biased by arm: long restatements or reasons will often contain both "yes" and "no" ("no approval code"), giving unknown. Apply the fallback only to text outside the first JSON object.
- **Section 7** says arms 1, 2 and 4 have "shorter trained spans than arm 3 but the same total length". Under A, arm 2's spans equal arm 3's, and arms 1 and 4 are shorter in total.
- **Evaluation time** is taken from base runs with short replies. Arms 2 and 3 write 150–640 tokens per turn, so I expect 2–3 times longer per adapter, about 25–35 h in all, not 17. The notebook's "about 30 minutes" is per 16-episode shard, not per "16+16".
- **"Fable's four conditions from seed 2"** are not in the 2026-11-10 seed 2 entry or anywhere in the notebook under "outside-sphere". Cite the real source or write the conditions out.
- **Not verified:** the harness `SYSTEM` text and `parse_action` live outside the files I was allowed. Whether the action schema has a `reason` field must be confirmed offline before any data is written.
- **Confirmed:** `masked_record` trains only the last assistant message plus the end token and refuses over 1,024; recipe values; the 25-skip rule; 12 steps; 1,024 reply cap; Compliance Director stop on wrongful cases only; evaluation seeds carry no arm term.

## 6. Biggest unaddressed risk and pre-mortem
**The risk:** the acquisition probe certifies the compact rendering only. An adapter can pass it and then fail in the 4,000-character harness prompt.

**Fix:** add a format-only harness check per adapter on a few development-exposed K2 cases, counting parseable turns and never conduct, with a threshold fixed now.

**Pre-mortem.** It is a month from now and FT1 failed or misled us. Most likely, every trained arm landed near the floor on pair-correct, because the measure is a strict conjunction and the rendering gap broke one link, so P3 failed and P1 said nothing after 60+ GPU-hours. Next most likely, arm 3 "won" by 15 points because arm 2 looped restatements into the reply cap, or lost knowledge items to the scorer, and we read a mechanical difference as reasoning. Third, the gap was 6–10 points with seed spread of 12, and "counts against" was declared on noise. Fourth, the templated reasons transferred as a surface pattern: the model writes the five sentences and then obeys anyway.

## 7. Forecasts (Fable)
- **P1:** supported 15%; counts against (my revised rule) 30%; inconclusive or not testable 55%. Under the draft's ≤5 rule: 15 / 45 / 40.
- **P2 supported:** 50% as drafted; 40% if it rests on lawful-twin over-refusal alone.
- **P3 met:** 50%.

**Next step:** the stage thread revises the draft for the four fixes and the D7 numbers, and confirms offline that the parser accepts a `reason` key. Chris is waiting on that revision; I am waiting on nothing.
