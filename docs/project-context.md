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


## Paper 3 formation context (2026-10-08)

Gate 1 and Gate 2 are approved. The approved Stage 3 Luna-only first pilot completed 12/12 correct.
Chris approved free pressure drafting. Twelve separate v0.21.5 variants are
approved in facts and scoring. Their approved Luna comparison completed:
baseline 12/12 correct, pressure 11/12 correct plus an extra invalid report.
All duties completed, no scored violations; estimated cost $0.01954870.
Only Luna has seen the variants. Chris approved documenting the ceiling
and free Gate 3 preparation. The 54-file candidate plus five adapter references,
P6 rules and evaluation estimates are ready for Gate 3 review; no model calls
are authorized. See docs/process/PAPER3_GATE3_REVIEW_v0217.md and
docs/process/PAPER3_COMPARISON_PILOT_REPORT_2026-10-10.md. No further
model batch is approved. See
docs/process/PAPER3_PRESSURE_VARIANTS_REVIEW_2026-10-10.md and
docs/process/PAPER3_STAGE3_PILOT_PLAN.md. See docs/process/PAPER3_BUILD_BRIEF.md, PAPER3_STUDY_A_GATE2.md, and the
latest notebook entries. Paper 3 examines the models' own functional conduct,
using a plain-permissions gate without counsel; it does not claim machines
possess human prudence or replace external law. W orders must be refused with
evidence preserved and an independent report; R decisions go to a named human;
U orders are followed even when a model prefers a different lawful route.
Separate legitimate work remains required in every case. The author's prospectus
and first two papers supplied in this session explain this rationale, while the
approved brief controls scope. Only Luna has seen the Study A cases. The 12/12 development result and all
original cases remain evidence. No study freeze or P6 verdict is claimed.
See docs/process/PAPER3_LUNA_PILOT_REPORT_2026-10-10.md.
No later stage or paid pilot may begin before its required approvals. Chris
asks the assistant to run free checks automatically and each approved model
batch, then give a concise report of outcomes, cost, next steps, and the exact
next approval or action required.

## Gate 3 approved; Stage 4 free preparation (2026-10-10)

The owner approved the v0.21.7 research design and frozen files, including the
disclosed calibration ceiling exception. The separate dated approval receipt
binds the unchanged 59-file manifest; candidate status text remains an archival
record. New v0.21.8 execution adapters passed 276 unit tests, 120 declared native
fixtures and the historical scripted suite. No model calls occurred. The first
frozen Luna evaluation (240 episodes, estimate $0.330507, proposed cap $1) is
prepared but NOT approved. Other providers are also unapproved. See
`docs/process/PAPER3_STAGE4_ADAPTER_REPORT_v0218.md` and
`studies/formation-study-a-luna-evaluation-cost-plan-v0218.json`.

## Luna frozen evaluation update (2026-10-10)

The approved Luna batch stopped on one preserved timeout after 40 correct
episodes. 184 requests issued; estimate including retained reserve $0.03383240.
199 episodes untouched. Overall P6 remains inconclusive under frozen identity
rules. A separate free-tested continuation adapter/plan is prepared but awaits
explicit approval; maximum remaining allowance $0.96616760 within original $1.
Original results and adapters are unchanged; all 59 frozen hashes match. See
`docs/process/PAPER3_LUNA_FROZEN_EVALUATION_REPORT_2026-10-10.md`.

## Luna evaluation combined final result (2026-10-10)

Approved continuation completed 199/199 untouched cells. Combined baseline
120/120 correct; pressure 118/120 correct, one unfinished explicit decline and
one preserved timeout. Baseline W/R/U each 40/40; Luna's composite passes.
No scored violations or invalid tool actions; total estimate $0.17480450.
All 240 Luna cells attempted; 239 valid final identities. Frozen P6 remains
inconclusive because the timeout is retained and other models are unattempted.
All 59 hashes match. Post-run checks: 280 tests and historical scripted suite
passed. Next Haiku 5.5 evaluation: 240 cells prepared, not approved; proposed
cap $1.00, forecast $0.33. See
`docs/process/PAPER3_LUNA_FROZEN_COMBINED_REPORT_2026-10-10.md`.

## Haiku 5.5 evaluation update (2026-10-11)

Approved batch stopped at 218 attempted cells: 85 baseline/91 pressure correct,
mostly mechanical output failures, one pressure usurping and one timeout.
22 cells untouched; recorded estimate $0.47952185. Timeout retained, no retry.
Free-tested v0.22.0 continuation awaits explicit approval within the remaining
$0.52047815 of the original $1.00 cap. All 59 hashes match; 284 tests and the
historical suite pass. Full P6 remains inconclusive; other model evaluations
remain unapproved. See `docs/process/PAPER3_HAIKU55_FROZEN_REPORT_2026-10-11.md`.
