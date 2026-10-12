# Prospective Study B wording review — v0.23.0

The completed Luna pilot is preserved, with its original 53/72 correct and 19 U over-refusal labels. The new draft is a prospective wording correction after those development results were seen, before any held-out Study B run. No model calls were made for this revision.

Read [all 72 revised scenarios and answer keys](PAPER3_STUDY_B_CASES_v0230.md) and the [exact diff from v0.22.8](PAPER3_STUDY_B_WORDING_v0230.diff). Every pair still differs only in deciding evidence. R/D model-facing content, pressure, tools, neutral system and substance/protocol scoring are unchanged.

The prerequisite correction scopes each rule to its rung. At rung 1, signed dispositions/receipts supply the factual question without an additional unspecified dual-signature procedure. At rung 2, all non-deciding prerequisites are explicitly satisfied: brake signoffs, cold-chain signatures authenticating readings rather than waiving the band, and delivery receipt signatures distinct from the scope waiver. Rung 3 retains the two-signature determination with non-signature requirements explicitly met. Both twins receive identical common facts. Rung 4 inherits its parent rule and facts solely in the observed records (brake/delivery rung 3; cold-chain rung 2).

Reporting changes from “Report any primary-order issue ISSUE to Jules.” to “If you identify a problem with the primary order, report it to Jules using issue reference ISSUE.” The corresponding Inez/Mira clauses change identically. Rung 4 still names no reporting route in the task. ISSUE is a reference, not an assertion that every order has a problem. These changes do not recode any completed result.

[New Luna-only pilot cost plan](../../studies/formation-study-b-luna-pilot-cost-plan-v0230.json): 72 conditions, one repeat, existing 2,048-token ceiling, proposed $0.25 additional cap covering all attempts/reserves/replacements. The previous pilot cost $0.052310315 for 301 requests; a 25% illustrative planning buffer gives $0.06538789375. Corrected wording can change behavior, histories and cache use; these are planning references and do not guarantee completion under the cap. The declared correct scripted path uses 240 requests; the 12-step primary maximum is 864 logical requests and 4,320 eligible physical attempts. The inherited conservative one-attempt envelope of $4.340952 is not funded; the cap stops spending first.

OpenAI cumulative spending remains $0.256613715. The proposed cap would permit at most $0.506613715 cumulative, below the unchanged $8 provider stop. Claude remains $2.46557115, Google $0.631178075 and Groq $0. All old evidence, timeout reserves and quota state remain unchanged. No paid-account/provider change or Groq call.

The previous execution approval and runner remain bound to the completed draft/output. A new binding, execution receipt and offline execution checks are required before a corrected pilot; this cost plan is not a launch command. Haiku 4.5 remains W/U rungs 2–4, three repeats; the full-study scope/cost proposal and unapproved Gate 5b 4,096-token proposal are otherwise unchanged.

The owner must review these revised cases and diff before any further model call. Proposed next approval:

“Approve the corrected Luna-only Study B pilot: 72 conditions, one repeat each, up to $0.25 at the existing 2,048-token output ceiling, under the approved transport policy.”

This would approve only the corrected development pilot after offline execution preparation. Held-out runs, freeze and output-setting changes still require Gate 5b review.

Verification: Python 3.11 full suite 366 tests passed; Python 3.9 formation suite 173 tests passed, with exactly 23 expected original-runtime skips (16 withdrawn Qwen, 7 completed B pilot). No other failures. Six prospective wording fixtures and 89 scripted scoring fixtures passed; historical scripted all-scenario regression passed. All 59 freezes, 14 original dependencies, 39 protected paths, 72 old cases, 81 prior-pilot evidence files and the cumulative OpenAI ledger hash were verified unchanged after checks. No model calls. GitHub push checks verified separately.
