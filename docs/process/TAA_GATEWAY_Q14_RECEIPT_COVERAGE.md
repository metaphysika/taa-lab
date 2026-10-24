# Q14 receipt-bound coverage — draft PR31 candidate

[DESCRIPTIVE] Core, independent reference and independent SQL implement approved Q14 claim-line coverage.
[DESCRIPTIVE] The common oracle derives admissions and financial order from actual host evidence, never native duty ledgers.
[DESCRIPTIVE] Original notices/proofs remain intact; corrections record recomputed coverage and reopen when coverage falls below C.
[COVERAGE LIMIT] TraceGrant remains limited to ten predeclared development programs; no new contracts or final scores.
[GATE] Local combined-tree acceptance passed; Claude's completed-PR review and green CI remain required before merge or scoring.

## Requirements and implementation

Source: unchanged approved Clarifications v0.3.2 revision3.1, Q14. Portions are
half-open whole-integer intervals; their length equals the positive notice
amount, endpoints lie within the original budget, and the default is [0,amount).
Malformed portions produce REFUSE in support; independent factual contradictions
still produce PROHIBIT. Merely proposing a notice contributes nothing.

| Component | Receipt, layout and proof implementation |
|---|---|
| Core | `taa_gateway/coverage.py`: exact actual-notice/receipt-effect pairing; original admission snapshots; financial first-write sequence from actual record events; current claim-line union. `refunds.py` provides semantic portion checks and bound same-claim allocation; PR1 remains independent of issuer/grant. |
| Native transaction | `Runtime.execute` supplies only a private receipt identity/actor/notice projection to the locked copy-on-write duty hook. Actual receipt publication and revision follow duty updates as before. Every real fault rolls back notices, admissions, tokens and ledger together. |
| Independent reference | `refunds.span`, `witnessed_notices`, `claim_coverage` are independent relations. Actual receipts enter the copied ideal next-state before reconciliation. No core authorization/discharge/transaction code is shared. |
| Independent SQL | `coverage.compute`, its own policy checks and SQL audit order. Kernel supplies its own private receipt projection and clears it in `finally`; actual SQLite rollback covers every real fault. No core/reference code is imported. |
| Common oracle | `observed_world.committed_notice_bindings` pairs actual receipt effects with actual physical notices, and `payment_commit_order` reads actual write provenance. The permitted reference duty relations keep their own admission book. Native statuses, proofs and allocations never become scoring input. |

Settled refunds and chargebacks bound to this claim/claimant/order/currency are
laid end-to-end in actual first-commit order. Allocations to another claim remain
blocked. A same-claim payment may evidence communication after discharging that
claim's refund duty; refund allocation exclusivity itself remains unchanged.
Denied portions map from current S, then all portions are unioned and clipped to
[0,C). Repeats overlap rather than add; disjoint named portions can add.

Original admitted spans and record snapshots remain immutable history. Current
coverage/proof is recorded separately, including current versions of cited
payments that have become invalid and the financial commit order. S=300 and
S=200 each produce the specified350 coverage in the400/250 example. Those duties
reopen, preserving the old proof/notices. A change leaving coverage400 does not
transiently reopen. Reopening at or after the original due step is overdue in
that same step. Closure still checks every unresolved duty, overdue or not.

## Business provenance and physical failures

Floor/static remain ordinary business operations with no duty ledger, security
tokens or authorization refresh. Financial version rows add a `commit_sequence`
as part of the same ordinary append, without changing their financial fields.
This is write provenance, not a policy layer. It survives canonical sorted JSON
and corrections without reordering the original commit. Missing provenance is
an explicit error, not inferred ordering. TraceGrant contracts/decisions remain
unchanged; ordinary host record metadata adds no TAA obligation machinery.

The existing business fault tests keep their expectations unchanged: a physical
effect may survive without a receipt or normal execution log. Out-of-band fault
capture also handles literal fault points in newly authored traces, retaining
actual before/after states. Absent boundaries remain not applicable by design,
with reasons. Actual missing-receipt audits are kept as discrepancies, never
relabeled successful rollback or unsupported behavior.

## Source authorship and controls

The18 Q14 cases/102 source assertions are byte-identical to authoring revision
v1. Original draft v0 remains outside acceptance with its failed unauthorized
financial-creator probe. Revision v1 changes only those two input kinds to
chargeback, which payment_processor may create under unchanged W0; IDs, amounts,
chronology and every expected outcome stay unchanged. No expected value is
synthesized from either implementation. New executable expectations await
Claude's completed-PR review.

Ten component methods cover actual receipt absence, proposal-only and malformed
committed notices; original-proof preservation through both S directions and
due boundaries; invalidated cited-record versions; real rollback at all seven
boundaries in both native and SQL; actual financial order after sorted JSON and
corrections; missing provenance; invalid non-null allocations without normalizing
records. Original business fault tests remain unchanged. A separate common-oracle
suite runs the18 sources on production/SQL/floor/static. A controlled receipt
omission leaves the original actual state intact: pre-change9135 incorrectly
discharges both business controls; Q14 leaves both unresolved. Raw original and
controlled states remain evidence, not experiment episodes or final scores.

Frozen v0.2.2/W0, original regressions, controllers, matching rules and contracts
are unchanged. The two Q16 source supersessions remain explicit with originals
retained. No model calls, Modal operations, spending, deletions, Notion edits or
public releases. All results are bounded engineering evidence, not H3 validation.

Final combined acceptance: see [the current report](TAA_GATEWAY_V032_IMPLEMENTATION.md#final-combined-local-acceptance--2026-10-23).
Baseline limitation: seven Q14 cases have incomplete-only pre-change checks
because the old schema/decision path lacks portion support. These are not
credited as observed semantic disagreements. Current Q14 is18 scenarios /102
source assertions per backend, zero discrepancies/incomplete/errors.
