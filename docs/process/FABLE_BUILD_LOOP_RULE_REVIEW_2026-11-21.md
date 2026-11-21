# Fable review of the proposed "Build loops" rule (2026-11-21)

Reviewer: Fable (`claude-fable-5-2`, effort medium), fresh context, read-only. Requested by Chris ("Just have Fable review this ... testing proposal for the loop thing"). The rule text reviewed is the Track B stage thread's draft of 2026-11-21, quoted in the review request.

## Verdict

**Pilot first, with changes.** Pilot on Track B only; not FT1 now.

| Version | Odds it saves Chris review time without lowering evidence quality |
|---|---|
| As written | about 35% |
| With the changes below | about 55% |

## Findings

**F1. The saving is modest.**
- AGENTS.md already lets Sol build, Fable review and Claude merge without asking Chris.
- Chris's FT1 time went to run approvals, post-result decisions and diagnosis, and the loop leaves all of those with him.
- It helps most on wide offline builds: generators, stagers and wiring.

**F2. The loop would not have caught FT1's failures.**
- The format failures in 5 of 12 adapters showed up only on the GPU; offline checks passed.
- The stronger rule is "smallest real run first", as FT1-R's enforced first-gate stop already does.
- "Done means" offline-ready only.

**F3. The science/code boundary is not enforceable as written.**
- In this lab, generators, parsers, scorers and analysis scripts carry the science.
- Fix: the stage thread freezes a written spec, and the loop only implements it. A needed spec change stops the loop.
- The loop never touches a commit named in a pre-run entry, nor scoring or analysis code after results are seen.

**F4. Tests and "done means" have no owner.**
- The builder may not change them, or loosen or delete tests and pinned fixtures.
- Every test edit is listed for the reviewer.

**F5. Shared files are missing from the rule.**
- Loops stay in the track's own folders.
- Shared modules (`taa/`, `formation/`, `scripts/`, CI), AGENTS.md, CLAUDE.md, the notebook and `results/` go through the stage thread, one thread at a time.
- Loops use `run_fast_checks.py --agent-safe` only.

**F6. The cap can be dodged.**
- Add a cap on pieces per loop, set beforehand.
- The same check failing twice stops the loop.
- The 1.5× time trigger still applies.
- The final review covers the whole diff in fresh context.

**F7. Point 6 spreads nothing.**
- Sol and Astra share one $20 ChatGPT plan, and loops multiply calls across four threads.
- Neon as builder is a new role that Chris should decide separately.
- Prefer a reviewer from a different model family (Fable or Neon) for Sol's code.

**F8. Scope.**
- Keep FT1 on the current rules: it is mid-testing, and its exact commits are under approval.
- Pilot on Track B. Extend to Tracks A and C after two or three Track B pieces, if the pilot measures hold.

## Suggested wording changes

1. "Done means" is offline-ready only. The stage thread writes it and the frozen spec before the loop, and the builder may not change either.
2. The reviewer is from a different model family, sees the diff and "done means", and does the final review on the whole diff.
3. At most N pieces per loop, set beforehand. The same check failing twice stops the loop. The 1.5× time trigger still applies.
4. Never inside a loop:
   - editing the spec;
   - loosening or deleting tests or pinned fixtures;
   - changing scoring, parsing or analysis code after results are seen;
   - touching a commit named in a pre-run entry;
   - editing shared modules, the notebook or `results/`.
5. New point: the smallest real run comes first.
6. Keep builder and reviewer on different subscriptions where possible. If a usage limit is hit, the loop waits.
7. Pilot measures: the number of Chris decisions per piece, the rounds used, and any defect found after the loop said "done".

## Plain summary

The idea is sound but smaller than it looks. The big FT1 delays came from things a loop of offline checks cannot see. The rule needs three things:
- lock the spec and the tests;
- keep loops out of shared files and out of FT1;
- always try the smallest real run first.
