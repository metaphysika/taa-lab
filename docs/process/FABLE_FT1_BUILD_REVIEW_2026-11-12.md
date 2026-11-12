# Fable exact-commit build review: FT1 offline build at 322943d8 (2026-11-12)

Reviewer: Fable (claude-fable), fresh context, bounded packet, read-only, exact commit `322943d8050b77de291fb70e445780d349da4e95` (PR #140) against main `dcac4037`. It ran the 19 FT1 unit tests in a scratch worktree (removed afterwards); no sealed file was generated and no model or network call was made. The packet included three findings by the stage thread (Claude) from the training samples: the recipient "desk" leak, reasons without the comparison step, and wording glitches; Fable confirmed all three (B4, B5, A1). Fable was allowed to read the sealed generator's code but not to quote its content. Recorded verbatim by the stage thread.

---

# FT1 exact-commit build review: `322943d8` (PR #140) against `dcac4037`

Read-only. The 19 FT1 tests pass in a scratch worktree (since removed). No sealed file was generated, no model or network calls were made, and `results/` is untouched.

## 1. Verdict: NEEDS FIXES

The offline scaffolding is careful, but six defects would make the run fail or mislead. All are cheap to fix before any data is written.

**Blocking**

- **B1. History records will probably fail the real Gemma tokenizer.** 1,440 of 2,000 records have two user messages in a row (the card, then "Earlier turns"). As I recall Gemma 3's chat template, it rejects non-alternating roles, so the real-tokenizer data write would refuse. The stub counters never call the template. I did not run the real tokenizer; confirm locally. Fix: fold the history into the one user message. (`data.py:203-206`)
- **B2. Arms 1 and 4 cannot pass acquisition.** All adapters are scored on one shared 40-item probe built from the arm 2 mix (`data.py:284`, `scoring.py:65-74`). "Always decline" matches 16 of 40 and arm 4 matches none, against a pass mark of 28. Both arms would be "not acquired", so P2, P4 and P5 are "not established" by construction. Fix: per-arm probes; the held-out arm 1 and arm 4 records are already built and then discarded.
- **B3. Fixed IDs in training collide with the freight world.** Training always uses `decline_order(order_id="ORDER")`; the freight world only accepts `ORDER-PRIMARY`. Any rejected tool call labels the episode `action_error`, which `aggregation.py:18` treats as a mechanical unknown, even if the model recovers. Most wrongful episodes of trained arms would likely become unknown, and P1 "not established". The spec's mechanical list does not include action errors. Fix: make training IDs vary and be copied from the card, and score a finished episode on its final state, with rejected calls counted separately.
- **B4. Recipient leak (your finding 1, confirmed).** The "desk: <name>" line names the recipient in 2,000 of 2,000 conflict records. The roster line also always lists the right recipient first. Only 60 of the 200 recipient records train `report_issue` at all.
- **B5. Arm 3 reasons lack the comparison step (your finding 2, confirmed, material).** The reason quotes the fact, rule and scope verbatim (as arm 2 does), then asserts a verdict label. Arm 3 differs from arm 2 only by that label, boilerplate and the step plan, so it is a weak test of reasons. Add one comparison sentence per evidence type; it fits the caps.
- **B6. The training loop is not the path FT0b qualified.** FT0b ran through the Hugging Face Trainer; `training.py:27-66` is a hand-written loop with no adapter save, checkpoint, deadline check or runner. It needs a real runner, a short qualification on Kaggle and another exact-commit review.

**Advisory**

- **A1. Wording glitch (your finding 3, confirmed).** "The supported decision is unsupported by the evidence" appears in 302 records, with sibling variants in 139 more. (`data.py:41`)
- **A2. "Counts against" threshold.** `analysis.py:27,90` uses 0.04, but one pair per seed is 4.17 points, so the spec's own example falls to "inconclusive". Use 1/24.
- **A3. Mechanical check missing when unknowns exist.** `joint_bounds` returns no `mechanical_check` or `P1_reading`, which is when it matters most. (`analysis.py:52-134`)
- **A4. Acquisition probe is narrow.** It covers first decisions and missed-fact corrections only; it never tests `report_issue`, routine work or `null`.
- **A5. Sphere records are first-step only.** "Refer, then do routine work, then finish" is never trained, though the test's outside-sphere W side requires it.
- **A6. Compliance Director stop differs from K2/L2.** `evaluation.py:12-13` attaches it to the latest message each turn; L1 pins it to the turn of the violation.
- **A7. Three parsers disagree at the edges.** The format check and the "malformed" flag use the one-object parser; the harness takes the first object and accepts `"tool":"null"`.
- **A8. Smaller gaps.** No "another lawful route looks better" lawful records; restatements omit tool results; wrongful and P2 rates are over 24 though only 18 W episodes can be servile; in arm 1, lookup is tied to step.

## 2. Conformance by section

| Spec item | Status |
|---|---|
| Arms 1, 2, 2u, 3, 4; 2,000 unique records each; arms 2/2u/3 share prompts | Met |
| Record format; 384/640/1,024 limits; refuse, never truncate | Met on stub; real tokenizer unverified (B1) |
| Matching gate (2% total; ±5% or ±8 per record); whole-line, no-repeat, no-verdict-word restatement | Met on stub (aggregate difference 4 tokens); a real-tokenizer miss refuses the whole build |
| Case mix 30/25/10/10/25; pressure on half of wrongful and lawful | Met, with B4, A5 and A8 |
| Corrections by type (120/140/120/120), failed step named first | Met |
| Held-out acquisition (a whole evidence category held out) | Met for arms 2/2u/3; broken for arms 1 and 4 (B2); narrow (A4) |
| Harness format check (8 K2 episodes, format only, conduct not retained) | Met, with A7 |
| Sealed generator: 24 pairs, 6/6/6/6 strata, twins, pressure on half, theme exclusion | Met structurally (see section 4) |
| Scorer additions (unauthorized, found recipient, silent refusal, over-refusal) | Met; fixtures pass |
| Knowledge scorer | Met as specified |
| Training mode: FT0b layout, 25-of-250 skip rule, action/reason loss split | Written, never run, different loop (B6) |
| Kaggle | Plan-only as stated; no executable path exists |
| Evaluation plan: 13 models, 48 + 48, arm-independent seeds | Met |
| Aggregation and pair-correct bounds | Met, except B3 |
| P1–P5: seed-noise and floor rules, rule order | Met; exceptions A2, A3 |

## 3. Code bugs (file:line)

- `data.py:203-206`: two consecutive user messages (B1).
- `data.py:284` with `scoring.py:65-74`: shared probe (B2).
- `data.py:120` with `aggregation.py:18`: constant `ORDER` and `action_error` treated as unknown (B3).
- `data.py:192` and `data.py:187`: desk line and roster order leak (B4).
- `data.py:41`: glitch template (A1).
- `analysis.py:27,90`: 0.04 threshold (A2).
- `analysis.py:52-134`: missing mechanical check (A3).
- `evaluation.py:12-13`: moving stop message (A6).

## 4. Test secrecy and leakage

- **The generator is close to the test itself.** `sealed.py` is public in the PR, and the test set is a deterministic function of that code plus the seed, over a small fixed vocabulary. The stage thread should not open `sealed.py`; I have quoted nothing from it.
- **Structural cues Sol should fix.** The correct recipient is always first in the test roster. The failing condition is always the first listed. Outside-sphere tasks name the holder by role only, so referral needs a roster lookup that training never requires.
- **No leakage into training found.** Subjects, evidence types and names are disjoint from training, and no sealed vocabulary appears in docs, logs or tests. The aggregation command writes counts only.
- **The seed file** must live outside the repo.

## 5. Before any run, in order

1. Sol fixes B1–B5 and A1–A3, and the sealed cues; regenerates the samples.
2. Real Gemma tokenizer data write; manifest hashes recorded; a refusal is retained.
3. Real runner built (save, checkpoints, deadline) and a short Kaggle qualification of the new loop, with memory and seconds per step.
4. Fable exact-commit re-review.
5. Sealed test written once by Sol, hash only; Astra's blind labels.
6. Claude's pre-run notebook entry (commit, hashes, forecasts), then merge.
7. Chris's exact-commit approval for training; throughput measured on the first evaluation shard; separate approval for evaluation.

## 6. Pre-mortem

It's a month from now and FT1 failed or misled us. Most likely, trained arms emitted accounts-office habits in the freight world (the constant `ORDER`, `release_payment`), most wrongful episodes became mechanical unknowns, and P1 was "not established" after 60+ GPU-hours. Next, arms 1 and 4 were "not acquired" by the shared probe, so P2 and P5 said nothing. Third, arm 3 matched arm 2 because its reasons were a restatement plus a label, and "reasons don't help" was read from a test that never trained the comparison. Fourth, recipient pairs were passed by "first roster name", inflating every arm alike. Fifth, the unqualified loop skipped more than 25 steps or hit the session limit with nothing saved.

## 7. Forecast update

- **As built:** P1 supported 5%, counts against 15%, inconclusive, not testable or not established 80%. P2 not established about 90%. P3 met 25%.
- **If B1–B6 are fixed:** P1 supported 15%, counts against 30%, inconclusive or not testable 55% (unchanged). P2 supported 40%. P3 met 45% (down from 50%, for the remaining tool-name and rendering gap).

**Next step:** Sol revises PR #140 for B1–B6 and the sealed cues; the stage thread is waiting on Sol, and I re-review the new exact commit after the real-tokenizer data write.
