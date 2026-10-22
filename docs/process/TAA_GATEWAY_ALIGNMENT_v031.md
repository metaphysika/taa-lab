[DESCRIPTIVE] PRs #11–#13 were reviewed by Claude and merged at their approved heads with green CI.
[DESCRIPTIVE] Foundation contracts and the independent reference semantics now incorporate Clarifications v0.3.1.
[DESCRIPTIVE] Claude's unchanged v0.2.2 bundle verifies and its validator reports 49 traces and variants checked, 0 errors.
[DESCRIPTIVE] Local validation passes 78 tests and all 534 assertion blocks across 54 executable reference scenarios, with no incomplete coverage.
[OPEN QUESTION] This alignment and its W0 mapping await Claude review and CI; production stage 4 work remains outside this PR.

# v0.3.1 alignment and validation

[DESCRIPTIVE] Controlling source is Design v0.3 plus `tests/expected_traces/v0.2.2/SPEC_CLARIFICATIONS_v0.3.1.md`. Zip SHA-256: `48ee6504ab3a0e278c8bd1725f4586463057c2671ce3ccdbeb32acf3db78856e`. Every manifest entry and extracted byte matches the supplied zip. Superseded v0.1 and v0.2.1, with their original zips, manifests and hashes, remain under `tests/expected_traces/archive/`; PR #14 was closed as superseded. Historical ingestion discrepancies remain preserved.

| Amendment | Alignment |
|---|---|
| Q1 | REFUSE and strict precedence; known failures refuse; alternatives carry positive refund amounts |
| Q2 | Loss of support or authority never releases duties; release needs standing and bound substantive evidence |
| Q3 | Stored requested effects; association independent of claimed reference; attribution only for requested prohibited elements, including T39 negative control |
| Q4/Q5 | Repeated unchanged proposals reuse live tokens; acting-party binding; rejected wrong-actor attempts log without consumption/revision |
| Q6 | Declared question/jurisdiction only; rejected answers are log-only with unchanged revision |
| Q7/Q10 | Boundary-free ticks preserve revision/tokens; live expiry invalidates globally; overdue begins at due step |
| Q8 | Voluntary offer lapses with owner retained; lost-authority fallback becomes unowned after window |
| Q9 | Issuer/claim/prohibited-effect matters; versioned repeats retain deadline; version-bound acknowledgment; linked supplements; immediate dispatch and roster fallback |
| Trust boundary | Separate create/correct rights and field-level correction checks; immutable identities and non-evidential agent notes |
| Correction | Discharge/release proofs are rechecked; invalidated proof reopens duty and case, preserving execution history |

[DESCRIPTIVE] Foundation schema version is 0.3.1. It remains stage 2 storage, identity and contract code, with no production authorization pipeline, effect executor or duty engine. Its clock publication recognizes stored grant/token/duty boundaries. Revision-bound execution and actual token lifecycle belong to later production stages. Generic storage publication is not the protected-effect transaction.

[DESCRIPTIVE] `taa_gateway_reference/model.py` retains the configurable declarative prototype with amended precedence, correction permissions, expiry, transfer and reporting semantics. `taa_gateway_reference/refunds.py` supplies its independent finite W0 relation: constraints are collected then aggregated; duties and proof relations reconcile independently to a fixed point. It imports only standard-library modules and shares no core decision, authorization, discharge or transaction code. Its atomic transaction is an ideal copied-state relation; named faults abort that relation, not a test of a production executor. The import-separation test covers the entire reference package.

[DESCRIPTIVE] `tests/trace_support/reference_runner.py` drives source inputs and compares projections against source expectations. Unknown assertion vocabulary is incomplete coverage and fails CI. Negative controls deliberately change an in-memory expectation and add an unknown assertion, demonstrating discrepancy/incomplete detection without changing fixtures. CI exports observed assertion results, never expected answers. No skipped assertions count toward acceptance.

[DESCRIPTIVE] Local checks: source manifest and author's validator; 78 foundation/reference/runner boundary tests; 54 reference scenarios, 534 assertion blocks, 0 discrepancies, 0 incomplete; `git diff --check`. Additional controls check immutable correction fields, create-only/correct-only rights, rejected reviewer answers, unrelated release/denial evidence, live-token expiry, and external-event-before-duty ordering. Tests owned by Sol were amended for the changed specification; independently authored expected outcomes were untouched.

[DESCRIPTIVE] No empirical claims, model calls, Modal operations, Notion edits, adapter downloads, scientific reruns or changes to PR #6. Passing reference traces is bounded engineering evidence, not independent empirical validation or proof of H3. Core trace execution and Astra's independent spot review remain future acceptance work.

[OPEN QUESTION] Claude must review the full current alignment diff and [mapping](TAA_EXPECTED_TRACE_MAPPING_v022.md). Chris explicitly requires both Claude review and green CI before merge; the earlier approvals cover only PRs #11–#13.

[DESCRIPTIVE] Claude approved head b38c4b78 conditional on the four changes supplied by Chris: frozen v0.2.2 adoption/archive, stricter documented list matching with extra-effect negative control, author-acknowledged T30 under-listing, and mapping/count updates. No reference-model code changed. Both the prior and tightened matchers reproduce 54 executable scenarios and 534 assertion blocks with zero discrepancies or incomplete assertions. Merge is authorized only after green CI and those exact conditions; otherwise the delta returns to Claude.
