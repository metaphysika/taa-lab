[DESCRIPTIVE] PR #18's approved cleanup removed the DT2 preference; unchanged counts and all green CI preceded merge b2cf17a4.
[DESCRIPTIVE] The native duty engine now creates, discharges, transfers and reopens duties independently of agent proposals.
[DESCRIPTIVE] Reporting uses recorded orders and decisions, authenticated service messages, live routing, version-bound acknowledgments and persistent deadlines.
[DESCRIPTIVE] Both unchanged development suites now have zero discrepancies and zero incomplete; the coverage-gap ledger is empty.
[LIMITATION] This is bounded W0 engineering evidence; the two v0.3.2 questions remain conservative, and stage 6 awaits Claude review.

# Stage 6 for Claude review

[DESCRIPTIVE] Scope is Design v0.3 plus Clarifications v0.3.1, including DU1–DU6 and Q2/Q8/Q9/Q10. Chris relayed Claude's approval of PR #18 at `269fad87`, conditional on removing the adapter's DT2 preference. Commit `d07c11ae4f3652a054afb9c8f0819b21d757dea7` changes only that selection to `ids[0]`. Local checks retained 167 passing gateway tests and the approved 154/36 incomplete counts. All three workflows and four jobs passed before exact-head merge `b2cf17a4ba003b6282a2090859f07c9bbda0eab7`. This is a separate stage 6 branch and PR.

## Native engine and transaction boundary

[DESCRIPTIVE] `taa_gateway/duties.py` owns ledger decisions. It imports no reference or assertion-runner code. The production coordinator applies all external entries in listed order and clock boundaries, then calls the core engine to a fixed point before proposals and executions. The engine also runs on intermediate clock steps without proposals. Stability checks reconcile a copied native checkpoint; a stable reconciliation writes no event, record or revision. Bare storage primitives remain available to trusted simulator code; the host coordinator is responsible for the declared phase order.

[DESCRIPTIVE] DU1 creates a resolution duty when a claim is filed; DU2 creates the supported refund duty independently of permission. Each native duty carries claimant, owner, origin, due step, discharge bindings, resolution evidence and immutable version/history. Claim and payment facts are read from current evidential records. Losing support or authority never resolves a duty. Closed cases reopen when a correction undermines the proof that resolved their duties; original executions, receipts and old record/duty versions remain intact.

[DESCRIPTIVE] A refund proof binds claim, claimant, order, amount, currency, settled status and allocation. One settlement cannot discharge a different claim's refund duty. A resolution notice can cite its own claim's allocated refund, but not an allocation elsewhere. Proofs record the predicates they rely on: a correction preserving those bindings need not reopen a valid discharge. An invalidated original proof records a reopening before any replacement proof is considered. A new authoritative release or genuinely sufficient replacement evidence can then resolve the reopened duty.

[DESCRIPTIVE] DU5 duplicate determinations bind the released claim and surviving claim. DU6 requires an authenticated answer to the declared question in the correct jurisdiction, a recorded substantive basis and current, subject-bound evidential records. The declared scripted claim-decision authority settles that reserved question; the engine checks standing, subject binding and evidence versions rather than interpreting the natural-language reason. It does not hardcode the delivery-status example as the only permissible release. A valid determination can release a superseded full-amount duty while leaving a newly supported partial duty unresolved.

[DESCRIPTIVE] Corrected reviewer answers pass through `StoredResolutions.correct`: exact question, recipient, jurisdiction and subject, with an authenticated correction envelope retained in the answer. Only the answer field may change. Wrong-jurisdiction, wrong-recipient and unreserved answers are log-only and preserve revision. Model assertions remain non-evidential.

[DESCRIPTIVE] Execution retains the stage 5 single locked transaction. The automatic engine reconciles actual effects before the `during_duty_update` fault point and before the receipt. Receipts include the actual duty state, allocations and cases committed with the business effect. A transfer token binds an offer/acceptance intent; its window starts at actual commit time. It therefore survives a boundary-free tick without silently changing a certified absolute deadline. All changes still roll back together at each real fault point.

## Reporting and transfer

[DESCRIPTIVE] DU3 report payloads come from the actual hash-chained `pipeline_decision` and stored-order `record_version` events, retaining source sequence/hash, authenticated order, act, checks and facts. A model-provided order reference or returned description cannot create this provenance. The reporting service has its own simulator identity and standing, independent of the agent's refused or revoked grant.

[DESCRIPTIVE] Matters are issuer/claim/prohibited-effect triples. A new incident in an active matter appends a report version and dispatches it to the current recipient without changing either due or routing deadline. Acknowledgments must name the current report id/version and come from its assigned recipient. New wrongdoing after acknowledgment opens a linked supplement. Initial routing and actual deadline re-dispatch read the roster's jurisdiction, receive authorization, priority and conflicts over implicated orders. No eligible recipient leaves the reporting duty unresolved rather than selecting an arbitrary party.

[DESCRIPTIVE] DU4 offers preserve the original owner until authenticated acceptance. Ordinary offers lapse with ownership retained. Lost-authority offers permit only IR1's claimant messages during their window; after an unaccepted window the duty becomes unowned and opens one report per claim. Acceptance is authorized by the live offer, separately from authority to pay a refund. Revoke/regrant events in one step are assessed after all those events. Ownership changes never reset the original duty deadline.

[DESCRIPTIVE] Q10 clock processing marks overdue at the due step and recognizes live transfer/report boundaries. Re-dispatch occurs in phase 2. A resolved duty's old deadline, acknowledged report's old routing deadline or already void token's expiry produces no transition or revision. The real pipeline refuses closure while any duty in that case remains unresolved, overdue or not.

## Coverage and independent observations

[DESCRIPTIVE] The message-party/IR1 incompleteness heuristic and all stage 6 assertion filters are removed from the adapter. It now calls native services and projects their state; deciding rule remains the first failed check in stage order. Core policy and reference policy/authorization/discharge/transaction code share no implementation. Frozen v0.2.2 and reviewed regression expectations are unchanged, and no expected outcome was generated from the reference model.

[DESCRIPTIVE] Gateway report, acknowledgment and acceptance records are native evidence, preserved with every version and included in full-state audits. They are excluded from the flat **business-effect** record projection: the bundle expressly distinguishes gateway reporting from executing the proposed agent act. The adapter also exposes all native collections, and the independent observer pins native-only histories. The runner still computes its own full delta and compares the backend description; no returned effect list supplies world truth.

| Suite | Scenarios | Source checks | State audits | Detection guards | Total checks | Discrepancies | Incomplete |
|---|---:|---:|---:|---:|---:|---:|---:|
| Reference frozen v0.2.2 | 54 | 534 | 1,704 | 0 | 2,238 | 0 | 0 |
| Reference regressions | 8 | 57 | 205 | 3 | 265 | 0 | 0 |
| Core frozen v0.2.2 | 54 | 534 | 1,751 | 0 | 2,285 | 0 | 0 |
| Core regressions | 8 | 57 | 212 | 3 | 272 | 0 | 0 |

[DESCRIPTIVE] All three native hidden-state controls are detected and their complete guards pass. Raw intentionally mutated observations remain in the report; those expected failures are not hidden or confused with ordinary-run discrepancies. The pre-fix baseline guard still requires all nine historical failures. Source validation retains 49 definitions/variants, 0 errors, unchanged zip SHA-256 `9a4b20191c54aa4ff7d1ae4be6517f44aa1ddb9b67aaa00acdafabf34c5751b8` and manifest bytes.

[DESCRIPTIVE] The focused suite has **185 passing tests**, including 18 new Sol-authored controls. They test actual native state: missing/misbound discharge evidence, overlapping denial bases, material versus immaterial allocation correction, duplicate-survivor correction, rejected reviewer corrections, report-recipient conservatism, independent reporting after revocation, same-step revoke/regrant, commit-time transfer windows, late acceptance, actual duty/allocation rollback, hold notices and byte-identical logs with real report provenance. These implementation controls supplement the independently supplied fixtures; they are not new independent acceptance outcomes.

[DESCRIPTIVE] Stage 5 had 154 frozen and 36 regression checks incomplete. Its ledger contained 194 unique incomplete locations including the raw controls. All are removed, with no new gaps, in `coverage_gaps.json`; `evidence/gateway-stage6/coverage_progress.json` records the coverage change. CI now uses `--require-complete`, checking exact source-location coverage, zero incomplete in both ordinary and raw-control runs, zero ordinary discrepancies, minimum state-audit counts and all hidden-state detections. The historical script name is retained for compatibility. Initial implementation disagreements and resolutions remain in the append-only discrepancy log.

## Conservative behavior pending v0.3.2

[INTERPRETATION / OPEN QUESTION] **DU1 portions.** Each cited settlement contributes at most once, capped by the first valid notice's stated amount and the actual settlement; denial records share one unsupported-remainder budget. Unbound notices do not establish discharge. This retains the documented conservative W0 interpretation rather than adding a portion calculus. Explicit amount/portion binding and overlaps remain for Claude's v0.3.2 revision.

[INTERPRETATION / OPEN QUESTION] **Eligibility on repeats.** A repeat retains the current recipient without rechecking eligibility, even if a later matching order implicates that recipient. A new control explicitly records this conservative behavior. Redirection and its effect on existing deadlines remain unspecified until v0.3.2; actual deadline re-dispatch still checks current eligibility.

[LIMITATION] Complete coverage here means these frozen development inputs and reviewed regressions, not a proof over arbitrary interleavings, new domains or real payment systems. The broader property/adversarial/comparator and replay stages remain outside this PR. No model calls, Modal operations, spending, evidence deletions, Notion edits, adapters or public releases. No launch approval or empirical H3 validation is implied. Stage 6 merge requires Claude review of this PR and all green CI.

[DESCRIPTIVE] Final broader validation under Python 3.11.17 (the full-suite CI interpreter): **907 tests run, 36 skipped, zero failures/errors**, 1,012.065 seconds. All scripted scenarios pass. Exact local source hashes and retained-log hashes are in `evidence/gateway-stage6/validation.json`; full native observations are CI artifacts. The code stayed frozen during the final broader run. The previously documented Python 3.12 historical formation float boundary is unchanged; no formation code or spending evidence was altered.

## Claude's conditional review: deadline sensitivity

[DESCRIPTIVE] Claude approved head `66a9ed19` conditional on component tests for three previously undetected mutations. Three new Sol-authored tests exercise both acceptance paths at step 6 and exactly at the step-7 offer deadline, and reopening one step before, exactly at, and one step after the duty deadline. The component setup deliberately bypasses phase-1 offer cleanup and the ledger clock; those independent guards must not mask a broken comparison inside the component under test. Refused acceptance preserves the complete native state; accepted consent changes ownership and records acceptance. Reopening checks unresolved status, same-step overdue, history and case reopening.

[DESCRIPTIVE] `python -I scripts/check_gateway_duty_boundaries.py` runs the original and one isolated in-memory mutation in separate processes. All three originals pass; removing the `apply_action` deadline check, making `receive` acceptance inclusive, and making reopening overdue one step late each produce the intended assertion failure (one test failure, zero errors each). `evidence/gateway-stage6/boundary_mutations.json` preserves the test output and source hashes. CI repeats this check and retains its report. No production implementation or frozen/regression outcome was changed. This is bounded mutation sensitivity, not proof of correctness.

[DESCRIPTIVE] After the review additions, the focused suite passes **188 tests** (the prior 185 plus these three). No production source changed; the earlier full 907-test run remains the record for the approved implementation.
