# C2 no-invalidation variants

Scope: implement Claude's primary P3 intervention and its separate diagnostic.
Authority: the verbatim comparator rulings remain the source; no fixture changes.
Boundary: these are trusted constructor options, outside agent/order/setup data.
Evidence: component and default-configuration engineering checks, not H3 results.
Review: a separate PR requires Claude's review and green CI before merge.

## Configurations

[DESCRIPTIVE] Construct a new `RefundWorld` with one of these `ablation` values:

| Configuration | Void on relevant world revision | Execution epoch check | Existing current reassessment |
| --- | --- | --- | --- |
| `None` (ordinary core) | yes | yes | yes |
| `without_admissibility` (C1) | yes | yes | yes |
| `without_invalidation` (C2 primary) | no | no | no |
| `without_invalidation_reassessment_diagnostic` | no | no | yes |

[DESCRIPTIVE] The last row is explicitly diagnostic, not the primary ablation.
It retains the ordinary execution-time current disposition, act-description,
justification-basis and staging-plan comparisons. Both C2 rows retain acting
party, exact tool/arguments, single-use consumption and token expiry checks.
Unknown handles still fail: an arbitrary name does not acquire an issued token.
The primary does not use warrant/row live status as another revocation check.
Its issued certificate, argument digest, issuance revision, plan hash and basis
hash are not rewritten or refreshed to make a stale token look current.

## Implementation boundary

[DESCRIPTIVE] `RecordStore(..., invalidate_tokens_on_revision=False)` disables
both world-change voiding paths: `advance_revision` and the stale-live-token
sweep in publication invariants. The readonly configuration is chosen once by
the trusted host. Global state revisions, authenticated/field-scoped writes,
version immutability, receipt/consumption invariants, clock boundaries and duty
processing still operate. Intrinsic token expiry advances the revision and
retires the expired token without voiding other unexpired tokens.

[DESCRIPTIVE] `Runtime(..., reassess_on_execute=False)` is permitted only with
that explicit store configuration. The primary omits the current pipeline call
and both basis/act and current-plan hash comparisons. The diagnostic retains
those existing comparisons. `validation_compares` honestly distinguishes fixed
conditions alone from fixed conditions plus reassessment; ordinary-core output
retains its original `pre_transaction_revision` label.

[DESCRIPTIVE] Registered mechanical tool staging still runs against current
world records. In particular, it allocates a new refund record ID after another
refund commits. Freezing an old physical plan would create an artificial ID
collision; comparing its old hash would retain a hidden invalidation check.
Neither is used as a primary-variant authorization filter. Current staging is
not a fresh authorization decision. The unchanged write trust boundary and
existing duty-action bookkeeping can still fail when an operation cannot be
applied; this intervention does not remove them merely to force a failure.
Atomic effects, consumption, duty updates, receipts and hash-chained audit
records use the same transaction implementation and real fault points.

[DESCRIPTIVE] No variant is selected from a proposal or stored order, and an
`ablation` field in scenario setup does not select it. When restoring a simulator
checkpoint, the host must explicitly select the same constructor mode. That
round-trip is tested. No benchmark adapter silently reactivates tokens, changes
certificate revisions, or substitutes expected results. Four-controller variant
integration and the common external scoring oracle remain separate work.

## Component checks

[DESCRIPTIVE] Eleven Sol-authored component methods were written from C2 before
executing the cases; they are outside the frozen fixtures. Checks include:

- Authenticated support correction: the primary commits the old issued act;
  ordinary construction invalidates; the diagnostic refuses on reassessment.
  Fresh proposals still face the full current rules.
- Grant revocation with no proactive token voiding in either C2 variant; primary
  execution and diagnostic refusal are distinguished through actual world rows.
- A benign, non-evidential record insertion: the primary and diagnostic can both
  execute, while the ordinary core invalidates. A spy verifies that only the
  diagnostic calls the current assessor.
- Wrong actor, changed arguments, changed tool, replay and intrinsic expiry.
  Rejected attempts preserve actual domain state.
- Two outstanding refund tokens for 80 and 70: the primary can commit REF1 and
  REF2 totaling 150 against a 120 claim. The diagnostic blocks the stale second
  permission. This pins removal of residual cumulative/staging invalidation.
- Expiring one token preserves another unexpired token and advances revision.
- All seven real fault points in both modes roll back actual partial state;
  partial refunds and receipts are independently inspected in failure evidence.
- Authority-loss duty offers, unowned duties and reporting remain active.
- Explicit checkpoint restore preserves the chosen mode and stale-token result.
- Ordinary/C1 configuration and constructor-only selection remain protected.

[INTERPRETATION] These deliberately weakened variants test mechanisms, not
learning, stable dispositions or real-world safety. No relative H3 result follows
from these component cases. The common external duty oracle, floor/static plain
business operations and cross-arm scoring (C3 and the next stage) are not built
by this PR. Q14–Q16 remain pending and conservative behavior is unchanged.

## Sensitivity and default-configuration acceptance

[DESCRIPTIVE] The unchanged component expectations detect six scratch-only
mutations: restored proactive voiding, restored stale-token publication sweep,
restored execution revision comparison, restored primary reassessment, restored
staging-plan hash filtering, and removed intrinsic expiry. Each targeted run
fails through assertion failures, with zero import/runtime errors. The original
11-test component suite passes. Exact edits and original/mutated source hashes
are retained in the validation evidence; no mutation is applied to this branch.

[DESCRIPTIVE] All 19 gateway command steps pass locally, including the four
pinned historical sensitivity baselines and both repaired clarification gates.
Fourteen exact comparisons with the reviewed parent evidence are unchanged:
conventional frozen/regression/adversarial, P1–P6, both adversarial backends,
controller development, TraceGrant, both frozen backends, both regression
backends, Q11/Q12 and Q13. The component command gains only these eleven tests
(238 instead of 227). Default production frozen: 54 scenarios, 534 source
assertions and 1,751 state audits; default reference: 534 and 1,704. Default
regressions: 32 scenarios, 217 source assertions per backend, 676 production /
653 reference state audits, plus all three hidden-state guards detected. These
complete gates have zero discrepancies and zero incomplete. They validate the
unchanged default construction; they are not full-suite C2 arm scores.

[DESCRIPTIVE] C2 is based on repaired PR #28 head `99db26a8`. That parent is held
for verification of green GitHub CI: local gates are not substituted for the
owner's exact-head merge condition. This PR separately requires Claude's review.
C3, external duty scoring, floor/static business operations and four-controller
cross-arm integration remain to be implemented in subsequent PRs.

[DESCRIPTIVE] Final local acceptance completed on 2026-10-23 UTC: full discovery **1,025 tests, 36 skipped, zero failures/errors**, in 2,171.015 seconds. The collected inventory is the parent's 1,014 plus the eleven C2 methods; existing skips are retained. Scripted all-scenarios also passes. [validation.json](evidence/gateway-c2/validation.json) records exact comparisons, component and mutation evidence, source/log hashes and the frozen archive hash. These unit-test skips are distinct from the zero-incomplete frozen and regression acceptance gates.
