# Astra review: token efficiency of the Track B build loop (2026-11-21)

Reviewer: Astra (`gpt-6.2-astra`, medium effort). Fresh context, read-only, at Chris's request ("have Astra 6.2 review the loop plan and suggest any efficiency gains on token usage"). Astra read the build-loop spec, Fable's review of the build-loop rule, `AGENTS.md` and `CLAUDE.md` at `15251728`, together with the stage thread's account of wave 1. Astra did not inspect transcripts, billing, CI logs or test runs. This record condenses Astra's report.

## Recommended loop for wave 2 (P5–P7)

1. **Fix the roster before building.**
   - Sol builds P5, P6 and P7.
   - Neon reviews P5 and P7, including their fresh final reviews.
   - P6 (analysis and pass/drop rules) gets a first review from Neon and a fresh final review from Fable.
   - Astra's wave cross-check and Fable's later exact-commit readiness review both stay.
   - A usage limit pauses the loop.
2. **Resolve gaps once, before building.** Gemini Flash makes one bounded pass over the three checklists, the amendments and the interfaces between pieces. Opus resolves the engineering questions; any choice that affects the science goes to Chris.
3. **Require evidence at handoff.** Sol checks every acceptance item, lists every test edit, and gives the base and head SHAs, the piece's test results and the `--agent-safe` log. The reviewer verifies those against the exact commit, runs one targeted independent probe on the riskiest claim, and re-runs the broad suite only if the evidence is missing, stale or suspect.
4. **Let the first review count as final when it passes.** It is a fresh read of the whole diff.
   - If fixes are needed, all blockers are sent together, then a fresh whole-diff final follows.
   - Any intermediate recheck checks only the changes, by SHA and finding ID.
   - Every passing final covers the whole current diff in fresh context.
5. **Keep handoffs short.**
   - One versioned reviewer brief.
   - Reports of at most 250 words: verdict, finding IDs, locations and verification, with room for a material exception.
   - Opus relays only the report link and the blocker IDs.
   - Genuine should-fixes are batched into one reviewed follow-up.
   - The three-round cap, the stop triggers, the sealed and shared-file boundaries and green CI before merge all stay.

## Probes for each piece

| Piece | Probe |
|---|---|
| P5 | 509 against 510 of 600 common cases (exactly 510 meets the 85% floor); leakage checked with synthetic records |
| P6 | A hand-scored synthetic case in which two admissible joint resolutions change the decision; the A6 executed-act rule for issuers other than the Manager |
| P7 | A refusal exercised against a fake backend, with zero push calls |

## For later pieces

- For routine Neon-built pieces: Terra for bounded fix checks and Astra for the fresh final, subject to keeping blind-labelling roles separate.
- Moving reviews to Sonnet or Haiku would still spend the Claude allowance.

## Estimated savings

These are counts of review calls, not measured tokens.

| Measure | At wave 1's pace | With this loop |
|---|---|---|
| Fable piece reviews in wave 2 | 9 | 1 (about 89% fewer) |
| Reviews in wave 2, if each piece needs one blocking review and one final | 9 | 6 |
| Reviewer-side runs of the broad test suite | about 31.5 minutes | avoided |
| Report length | 1,000–3,000 words | at most 250 words (75–92% shorter) |

Do **not** insert a review of only the changes between the first review and the final by default. In wave 1 the later whole-diff reviews caught real defects.

## Risks

- A generic green CI badge does not prove that the piece's own tests ran.
- A report-length cap must never suppress a blocker.
- Pilot measures to record per piece: review count, Fable calls, duplicate suite runs, owner decisions and later defects.
