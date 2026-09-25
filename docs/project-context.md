# Project context (handoff)

Read this with `CLAUDE.md`, `ROADMAP.md`, and `LAB_NOTEBOOK.md`. It records decisions made while
the harness was built, so a new session does not relitigate them.

## The project

- TAA (Teleological Alignment Architecture) is Chris Lahn's Thomistic natural-law framework for
  governing AI agents. Governing rule: an agent must do a permissible thing (M), under authority it
  still has (A), for a good its action still serves (F).
- Paper: `docs/TAA-Paper-1-v1.0.pdf` (DOI 10.5281/zenodo.22946219). Short version:
  `docs/TAA-Research-Brief-v1.0.pdf`.
- Purpose of this lab: the "bounded prototype and comparative study" in paper Section 7. The owner
  works full time and is not a programmer; the aim is honest, reproducible evidence that researchers
  can check, not a product.

## Decisions already made

1. **Three gates, always compared together.** Plain permissions, expiring permissions, TAA. The
   paper's own defeat condition says: if simple restrictions explain the improvement, the result
   supports security engineering, not TAA. Expiring permissions is the test of that.
2. **The agent and reviewer are always separate model calls** made by the harness with fresh
   prompts. They never see Claude Code's conversation, so a well-informed Claude Code does not
   contaminate results. Claude Code must never play either role.
3. **Referrals need an answer.** In v0.2, the reviewer referred every plan and nobody answered, so
   TAA blocked all legitimate work. Fix: `--human standing` (a standing determination) by default;
   `--human none` reproduces the failure and isolates the reviewer's own judgment.
4. **The reviewer was given accurate context** (the agent sees state every step; which shipments
   are storm-affected). This corrected false beliefs; it was not meant to lower the bar.
   `counsel_check.md` watches for rubber-stamping as a result.
5. **Purpose defeat is the key scenario.** It is the only one where expiring permissions cannot
   match TAA. In scripted runs TAA catches it through the standing determination, a rule; that shows
   the plumbing only. Evidence for TAA's judgment requires a model reviewer catching it, ideally
   confirmed with `--human none`.
6. **Model roles:** Claude Haiku via API (owner's API balance) for hosted runs; Ollama on the
   owner's PC for free bulk runs; Gemini free tier as a cross-company reviewer when available.
   Claude Code cloud sessions (separate $100 credit) are for building and free scripted checks only.

## Findings so far (details in LAB_NOTEBOOK.md)

- Unannounced lapse with Claude Haiku: plain permissions 4 unauthorized reroutes in 3 of 3 runs;
  TAA 0 with identical legitimate work. Expiring permissions would likely match; not yet measured
  with a model.
- Haiku respected clearly stated warrant limits and resisted the injected "authority extended" note.
- Model reviewers can fail by over-caution (v0.2) or, possibly, rubber-stamping (to be measured).

## How to interpret results

- Report ranges across repeats, not single runs. Five repeats before any number goes in the paper.
- Always state what the comparison gate did. "TAA blocked X" means little unless expiring
  permissions did not.
- Count blocked legitimate work (over-refusal) as a cost, not a success.
- Results that weaken the paper's claims go in the notebook with the same care as ones that support it.
