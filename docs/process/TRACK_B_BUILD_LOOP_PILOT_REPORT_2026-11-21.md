# Track B build-loop pilot: report (2026-11-21)

Written by the Track B stage thread (Claude Opus 5.5) after all seven offline pieces passed review (P7's merge awaits CI). The pilot ran on Track B only, by Chris's decision of 2026-11-21. No GPU, Kaggle, Modal or model run took place.

## 1. Evidence
- Spec, rules, amendments A1–A11 and the per-piece pilot log: `docs/process/TRACK_B_BUILD_LOOP_SPEC_2026-11-21.md`.
- Reviews of the loop itself:
  - `FABLE_BUILD_LOOP_RULE_REVIEW_2026-11-21.md` (pilot first, with changes);
  - `ASTRA_BUILD_LOOP_EFFICIENCY_REVIEW_2026-11-21.md` (the leaner wave-2 loop, A9).
- Wave-2 review reports: `docs/process/track_b_reviews/`. Wave-1 Fable reviews were returned as messages in the stage thread; their findings are summarized in A3–A8 and the pilot log.
- Merged pieces: PRs #189 (P3), #190 (P4), #191 (P1), #192 (P2), #196 (P6), #197 (P5). P7 is PR #198.
- Doc PRs: #188 (design, spec A1–A8) and #195 (A9–A11).

## 2. Checked / Not checked
**Checked:**
- Every piece passed a fresh whole-diff final review by a model family different from its builder.
- Each piece's own tests and `run_fast_checks.py --agent-safe` passed at the reviewed head.
- CI was green before each merge.

**Not checked:**
- Anything on a GPU. Every reviewer listed what only a real run can show; P4's list has 13 items.
- The Track B tests are not yet in the fast CI set (A5.5).
- Token or quota use was not measured; the counts below are review calls, not tokens.

## 3. Numbers

| | Wave 1 (P1–P4, original loop) | Wave 2 (P5–P7, leaner loop A9) |
|---|---|---|
| Pieces | 4 | 3 |
| Fix rounds per piece | 2, 2, 2, 2 | 0, 2, 1 |
| Reviews | 12, plus 1 retried after a Claude usage limit | 6 |
| Fable reviews | 12 | 1 |
| Decisions Chris had to make | 0 | 0 |
| Science-touching rule readings decided by the stage thread and reported to Chris (non-blocking) | A3, A7 | A10 †-items, A11 |
| Stops before any code was written, because of spec gaps | 2 (P4: A1, A2) | 1 (P6: A11) |
| Spec questions answered before building | none | 40 (Gemini Flash gap pass, A10) |
| Defects found after a piece was marked "done" | 1 (P2's adapter test failed once P3 merged; one-line fix reviewed by Neon) | none yet |

## 4. What the loop caught
These are real defects that would have damaged the experiment or wasted GPU time, each caught before merge:
- a W/L label leaking into card IDs;
- a mislabelled FT1-R layout switch;
- sealed battery subjects committed in plain text, with a recoverable seed;
- scorer mis-reads of negated answers;
- an adapter check that would refuse every real FT1 adapter;
- a firm "drop" downgraded to inconclusive;
- a crashed episode counted as good conduct;
- a deadline-truncated run marked complete;
- a staging path that could reach FT1's folders.

## 5. What went less well
- **Spec gaps.** About half of wave 1's problems traced to the stage thread's spec being too loose (A1–A7), not to the builders. The wave-2 gap pass reduced this but did not remove it (A11).
- **Builder turn endings.** Neon twice ended its turn with background work unpushed.
- **Disclosures.** One Fable review briefly searched across `exploratory/ft1/`; nothing sealed was shown. One Fable review named seven sealed family names, all of which were retired (A6).
- **Cost.** Wave 1's review load was heavy on Chris's Claude allowance, and one review hit the 5-hour limit. A9 moved most reviews to Neon.

## 6. Recommendation (for Chris)
- **Keep the loop for Track B, in its A9 form.**
- **Offer it to the other tracks, as A9 rather than the original loop.** It works well for building offline code against a written spec. The two biggest gains were the cheap spec gap pass before building and keeping Fable for science-deciding code only.
- **Keep the existing rules unchanged where the loop gives no protection:**
  - the loop cannot catch GPU-only failures;
  - whether to apply it to another track is the owner's call.

## 7. Open items before any Track B run
1. **Reviewed follow-up batch.** The should-fixes from all seven pieces, plus adding the Track B tests to the fast CI set (A5.5). Anything touching P6 or the scorer must merge before B0a produces a result (A9.6).
2. **FT1 results.** The starting-model rule (design 2.1) is read from FT1's result entry, which does not exist yet.
3. **Blind labels from Astra** for MB, PB, LD and RD. The FT1 overlap attestation, run by Sol or Astra.
4. **Kaggle session counting.** A verified account-wide status command, which P7 needs before a live launch.
5. **The B0a run itself.** A pre-run notebook entry, a Fable exact-commit readiness review, and Chris's approval, after FT1's testing is finished and Kaggle is released to Track B.
