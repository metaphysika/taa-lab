Current status: Q14 has been integrated into the active PR31 branch. These
historical planning notes and scratch prefixes are retained for provenance;
see [Q14 implementation](TAA_GATEWAY_Q14_RECEIPT_COVERAGE.md) and the
[current candidate](TAA_GATEWAY_V032_IMPLEMENTATION.md). Later active-tree
repairs and tests supersede the isolated prototype as executable code.

# Q14 continuation from the Q15/Q16 checkpoint

STATUS: approved Q14 interval/receipt semantics are not yet implemented.
STATUS: H1, null-allocation repair, Q15 and Q16 have separate implemented checkpoints; none completes Q14.
SOURCE: Clarifications v0.3.2 revision3.1 is normative; the notes below are implementation sketches, not additional rulings.
DRAFTS: eighteen source-derived Q14 scenarios are retained outside acceptance; their before probes are diagnostics only.
GATE: complete Q14 and every required regression in draft PR31, obtain Claude review, then green CI; final scoring stays held.

## Concrete remaining paths

- `taa_gateway/refunds.py`: message schema, `message_support`, PR1 allocation
  binding. Outer schema must admit the optional portion for semantic validation;
  malformed portions produce REFUSE at support, while independent contradictions
  remain PROHIBIT. Same-claim duty allocation is valid for communicated payments,
  without weakening refund allocation exclusivity or foreign-claim rejection.
- `taa_gateway/duties.py`: replace scalar `notice_proof` accounting with actual
  receipt-bound admission, original stored portions and recomputed claim-line
  union. Preserve original notices/proofs; record recomputed coverage separately.
  Version changes leaving coverage complete must not cause a transient reopening.
- `taa_gateway/executor.py`: preserve the specified atomic write ordering when
  binding notice discharge to a receipt. A possible implementation is a private
  projected receipt passed only into the copy-on-write duty calculation, with
  actual receipt publication still after duty updates. It must roll back at all
  seven real fault points; a returned description is never evidence.
- `taa_gateway_reference/refunds.py`: independent portion validity, first-commit
  layout, receipt admission and proof/reopening relations. Its ideal transaction
  relation may publish its own receipt into the copied next state before duty
  reconciliation. It must share no core decision/discharge/transaction code.
- `conventional_gateway/policy.py`, `ledger.py`, `kernel.py`: independent SQL
  policy, interval calculation and receipt binding. Any private transaction
  projection must be cleared on every exit, including injected rollback. Use
  actual SQL audit sequence for financial first-commit order.
- `comparators/observed_world.py`, `duty_oracle.py`: independently read actual
  financial commit order, committed notices and receipts. Maintain the oracle's
  own admission provenance; never import any arm's internal duty proof,
  resolution status or allocation ledger into scoring. Do not adjust original
  controllers, contracts, semantic keys or matching protocol to hide a difference.

## Required accounting

Follow Q14 literally: half-open whole-integer portions; default [0, amount).
Paid settlements occupy the claim line in actual first-commit order, not record
ID or dictionary order. Denied portions map from current supported S. Union and
clip to [0,C), counting overlap once. Preserve original validated portions through
corrections: S rising to300 and falling to200 both give coverage350 in the stated
400/250 example, and reopen. Do not retroactively reject a previously admitted
portion just because the current denial budget differs. Preserve original proof
and full record/version/receipt provenance, and record the new coverage separately.

Only actual committed receipts support notices; refused/proposed/rolled-back
notices and replay add nothing. Include negative controls for physical notice
state without its receipt, multiple exact repeats, distinct portions, both
correction directions, a correction that leaves complete coverage, independent
contradiction plus malformed portion, missing evidence versus contradiction,
null/absent and own-duty/foreign-duty allocation, first-commit ordering and all
real transaction fault boundaries. Reopening is overdue from the due step.

The initial18-case draft used unauthorized refund creation in its ordering case.
Retain it and its exception evidence. Draft v1 changes only those two event kinds
to chargeback, which payment_processor may create under unchanged W0; IDs,
amounts, chronology and all expected outcomes are unchanged. Its fresh9135bcdb
probe has zero exceptions on all three backends and exposes the still-missing
Q14 behavior (including eleven incomplete observations per backend). This is
sensitivity authoring, not current passing acceptance. Neither draft is wired
into CI until the implementation and complete acceptance checks exist.

No post-outcome POEC contracts: TraceGrant remains limited to the original ten
predeclared development programs. Wider coverage requires Astra blind authoring.
No model calls, Modal operations, spending, deletions or public releases.

## Isolated candidate prepared during checkpoint validation

An uncommitted candidate is isolated at `/workspace/scratch/taa-q14-work`;
`/workspace/scratch/q14-work-initial-snapshot.json` records its starting files.
It is not the active PR31 runtime and is not completed acceptance. Native,
independent reference and independent SQL candidates each pass the18 draft-v1
cases/102 source assertions in targeted probes. The common oracle's SQL/floor/
static probes pass all54 replay instances, including receipt absence after the
real business-host fault, exact repeated coverage and preserved original proof.
The reference candidate also preserves frozen534 source/1,704 audits so far;
remaining frozen compatibility and deeper controls are still required.

Candidate files: native `coverage.py` plus executor/policy/duty integration;
independent reference interval/admission relations; SQL `coverage.py` plus
kernel/private-projection and ledger integration; representation-only actual
receipt/financial-order readers in the oracle; ordinary business financial-write
journaling for first-commit provenance. No common decision/discharge/transaction
code is shared between implementations. No new TraceGrant contracts or final
scores. Preserve every prototype attempt, including the first minimal-copy
probe that failed solely because PROVENANCE_v022.json had not yet been copied.

Before copying candidate changes into this branch: finish the current clean
Q15/Q16 checkpoint's full discovery and evidence, verify candidate frozen and
permanent acceptance without changing any expected outcome, add the requested
component/regression controls and expose each limitation honestly. The ordinary
business journal adds a physical record-write event; its fault controls must
continue to distinguish that event from a missing normal execution log, never
claiming rollback or erasing a partial write. Test-only adapter compatibility
repairs do not authorize any weaker mutation or expected outcome.
