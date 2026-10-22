[DESCRIPTIVE] PR #17's approved head 37c43f8c was merged after every CI workflow passed; stage 5 is on a separate branch.
[DESCRIPTIVE] The core now issues actor-bound, revision-bound tokens and executes them once through one locked store transaction.
[DESCRIPTIVE] Faults at all seven named boundaries mutate the actual working state where applicable, then roll it back while preserving failure evidence.
[DESCRIPTIVE] The same frozen-input runner and independent state audits now drive both implementations; no expected outcome or reference policy was changed.
[LIMITATION] Stage 6 duties/reporting remain incomplete; this PR is not full production acceptance, empirical H3 validation, or launch approval.

# Stage 5 for Claude review

[DESCRIPTIVE] Controlling specification: Design v0.3 plus Clarifications v0.3.1. Chris relayed Claude's approval of PR #17 at `37c43f8c6219c69153f2cc941b5f31707311db92`; all three workflows and four jobs were successful before merge `3d5fa3d7dff657438210d0c282856a163cea9570`. This branch implements stage 5 only. The two open v0.3.2 questions in the alignment report remain open; no new settlement-portion or report-recipient policy is invented here.

## Implementation

[DESCRIPTIVE] `taa_gateway/executor.py` issues opaque token IDs backed by stored certificates, exact tool/argument digests, complete warrant bases, staged-effect digests, acting party, pre-transaction revision and expiry. Issuance does not advance revision or execute the act. Repeated identical proposals at the same revision reuse the live token. Execution revalidates the act, complete authority path, support, limits and staged effects against the locked pre-transaction state before consuming the token. A successful receipt binds that pre-transaction revision and the committed revision. Wrong actors, substituted arguments, consumed/stale/expired tokens and changed staged plans cannot commit.

[DESCRIPTIVE] `RecordStore._mutate` is the single write path, including clock, authenticated records, duty versions, token lifecycle and execution. It serializes threads with an `RLock`, forbids nested writes, retains immutable published record/duty/receipt histories, detects relevant changes, advances revision and globally voids remaining live tokens. New record insertion, correction, grant/ancestor changes and cumulative effects pass through this path. A tick that crosses no live boundary preserves revision; live-token expiry advances it. Withdrawal also advances it. Raw snapshot restoration is available only to the trusted offline adapter and only into a new empty store; it cannot reset a live store.

[DESCRIPTIVE] The executor validates, stages, applies effects, consumes the token, appends bound duty versions, writes the receipt and advances revision within that one transaction. Seven injected failures correspond to the frozen T23 labels. Tests inspect partial working state after actual record effects, consumption, duty changes, receipt and revision changes, prove rollback of every collection, then retry the same token successfully. Validation/staging failures naturally have no protected effects. Log publication is atomic with successful state publication; failed attempts add a separate audit entry containing the partial-state snapshot and restored-state digest. Previously published history is never deleted.

[LIMITATION] This is an in-process simulator transaction over local records and notices, not a distributed payment transaction or crash-durable external service protocol. Stage 5 does not claim production deployment readiness. The fault adapter exercises real mutations of these simulator collections; it does not establish atomicity across external payment systems.

## Carry-forward review items

[DESCRIPTIVE] Unregistered tools and schema-invalid arguments now append rejected-input audits without changing state revision. Tool registration and local JSON schemas still determine the callable surface.

[DESCRIPTIVE] `taa_gateway/interim.py` represents IR1 as a separate complete rule-based authority path derived from the versioned pending duty and live transfer window. It binds the owner, claimant, claim and the two interim message templates; it does not revive a revoked grant or authorize a refund. Tests seed a valid pending duty, revoke the ordinary grant and verify interim authority, recipient/template limits and lapse. Full W0 authority traces remain incomplete until stage 6 creates and maintains those duties independently.

[DESCRIPTIVE] Suggested alternatives are fully reassessed against the same complete grant. Among passing refund alternatives the selection rule is largest numeric amount, then ascending canonical act serialization; equal acts across paths use ascending grant ID. No fragments from different grants compose. Tests cover both rule-order independence and competing complete paths; W0 T30 suggests 250 from a 400 request.

## Shared runner and state observations

[DESCRIPTIVE] `tests/trace_support/production_backend.py` adapts W0 input events into authenticated foundation operations and native runtime calls. It imports neither reference policy nor expected outcomes. Each transition exports the complete native checkpoint, every native record/duty version, receipts, tokens, notices, reports, allocations, orders, grants, cases and the verified hash-chained event log, alongside vocabulary-normalized projections. The adapter reconstructs only fresh simulator objects, so no unobserved process cache decides the result.

[DESCRIPTIVE] `reference_runner.run(..., backend=...)` retains one scheduler, expectation matcher and independent observer for both implementations. The state-delta comparison guard remains: the runner computes its own delta and compares the backend description. The observer now also pins all native-only record and duty versions, including authority records omitted from the flat effect vocabulary. Mutations of actual native refunds, refused-proposal writes and retained settlement history all trigger independent state-audit discrepancies. Returned lists do not determine committed effects.

[DESCRIPTIVE] Explicit stage 6 unsupported capabilities enumerate all unvisited source assertions as incomplete. Duty/report assertions already reached are likewise incomplete, rather than passing on empty duty collections. Unexpected exceptions are discrepancies. Normal `reference_runner --backend production` exits unsuccessfully on any incomplete check. No source assertion is silently dropped; the stage-5 gate checks exact source-location coverage, including the negative-control raw runs.

## Validation and limits

[DESCRIPTIVE] Local focused suite: **167 tests pass**. Source validator: **49 traces and variants, 0 errors**. The zip retains SHA-256 `9a4b20191c54aa4ff7d1ae4be6517f44aa1ddb9b67aaa00acdafabf34c5751b8`; manifest entries and extracted bytes remain unchanged. Reference policy, authorization, duty/discharge and transaction files are unchanged.

| Implementation / suite | Scenarios | Source checks | State audits | Detection guards | Total checks | Discrepancies | Incomplete |
|---|---:|---:|---:|---:|---:|---:|---:|
| Reference frozen v0.2.2 | 54 | 534 | 1,704 | 0 | 2,238 | 0 | 0 |
| Reference regressions | 8 | 57 | 205 | 3 | 265 | 0 | 0 |
| Stage 5 core frozen v0.2.2 | 54 | 534 | 1,454 | 0 | 1,988 | 0 | 154 |
| Stage 5 core regressions | 8 | 57 | 166 | 3 | 226 | 0 | 36 |

[DESCRIPTIVE] Regression summary totals use the existing convention: ordinary scenario checks plus one guard per injected negative control. The full report separately retains every raw negative-control observation. All three native mutations are detected by state audits; two complete negative-control guards remain incomplete because their source duty/report assertions await stage 6. Those guards are included in the 36 incomplete checks, not counted as passing. Four additional raw source gaps occur inside those controls and remain listed in the coverage ledger/report.

[LIMITATION] The 190 top-level incomplete checks cover independent duty derivation and reconciliation, prohibition-triggered reports, report routing/acknowledgments/repeats, transfer acceptance, correction/reopening, and duty-dependent refusal/closure. Core clock and atomic duty-version primitives are tested but are not the independent duty engine. Passing the transaction subset cannot establish that refusal leaves all owed work intact, that reports reach an eligible recipient, or that cases cannot close over unresolved duties.

[DESCRIPTIVE] CI retains the full reference suite and pre-fix regression guard. An explicitly labeled **partial stage 5** job runs the same runner/observer against the core and saves complete observations. `scripts/check_gateway_stage5.py` fails on disagreement, lost source assertions, fewer state audits, a missing hidden-state detection or a new incomplete location. `evidence/gateway-stage5/coverage_gaps.json` records observed deferrals for review, not normative expected decisions; shrinking that list is allowed. It never changes a frozen expectation and is not a substitute for the normal all-complete acceptance gate.

[DESCRIPTIVE] Initial source disagreements and fixes are appended to the discrepancy log. The compact machine-readable validation summary records source hashes; full observations are CI artifacts. No scientific reruns, paid calls, model calls, Modal operations, Notion edits, adapter downloads or public releases occurred. Merge requires green CI and Claude review of this PR.

## Interpreter boundary found during the broader suite

[DESCRIPTIVE] The first broader local run used the environment's Python 3.12.14: 888 tests, 125 skips, two errors, in 460.634 seconds. Both errors are in historical `test_formation_continuation_v0220` and reproduce on unchanged merged main `3d5fa3d7`. That code requires exact equality with a frozen spending summary. Python 3.12's built-in sum produces `0.47952185`; the frozen summary and legacy sequential sum are `0.47952185000000036`. This is not a gateway regression. All four tests in that module pass on unchanged main under Python 3.11.17, matching the repository's full-suite CI interpreter. Formation code, spending evidence, frozen summaries and test expectations remain unchanged. The failed run is retained, not counted as passing.

[DESCRIPTIVE] Full final local suite under the CI interpreter, Python 3.11.17: **889 tests run, 36 skipped, zero errors/failures**, 973.822 seconds. The scripted `run.py --scenario all` harness also exits 0. The gateway component suite has 167 passing tests. Core and reference trace counts reproduce under both 3.11.17 and 3.12.14; the broader 3.12 historical float boundary above remains disclosed. Complete local logs are retained in the workspace; their hashes are in the validation summary. No code changed during the final 3.11 run.
