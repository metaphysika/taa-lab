# C1/C4 implementation review

Scope: offline C1 prohibition-stage ablation and C4 fixture-token routing only.
Authority: Claude's C1–C4 ruling file is retained verbatim alongside this report.
Fixtures: frozen v0.2.2 and its expected outcomes are unchanged.
Evidence: component and mutation checks are engineering controls, not H3 validation.
Review: merge requires green CI and Claude's review of this delta.

## C1 — without the admissibility stage

`RefundWorld(..., ablation="without_admissibility")` constructs the ordinary core
with `Pipeline(..., include_prohibitions=False)`. This trusted construction option
is not read from agent arguments, an order, or scenario setup. Normal construction
retains all prohibitions. Invalid ablation names are rejected.

The ablation skips prohibition predicates and their stage in the decision trace.
It leaves authority, support, determination, duty checks, grant-path selection,
alternative reassessment, token invalidation, atomic execution, receipts and the
independent duty/reporting engine in place. There is no second implementation of
these mechanisms. Prohibition attribution and prohibition-triggered report duties
cannot arise without prohibition failures. Other report paths are unchanged.

INTERPRETATION: this partly overlaps a future "without report duties" ablation.
Support rules may still block a wrong act. Neither behavior is repaired or
bypassed to produce a desired contrast. An ordering-defect ablation is not added.

Component controls check the ordinary/ablated wrong-account pair, actual commit
and receipt, retained authority/support/caps/closure, invalidation and rollback,
and an authentic wrongful order with no prohibition attribution/report duty.
The closure control reconciles at step 1: the duty engine does not create the
active task duties at the pre-task step 0. Initial test failures from that setup
assumption and a receipt-object-versus-ID assertion were corrected in tests;
no fixture or production decision was changed to satisfy them.

## C4 — fixture-token names identify source proposals

`worlds/refunds/token_bindings.py` builds one simulator-owned table per episode
before controller expansion. A source origin is `(expanded trace id, zero-based
index in trace.steps)`, not clock step or token/certificate issuance count.
Only the explicit symbolic token labels are read from fixture routing metadata;
policy outcomes, duty expectations and semantic labels never enter the table.
Repeated cached proposals naming the same token retain its first source origin.
The source file and answer keys are never edited.

Source entries carry `proposal_origin` through input-only stripping and controller
expansion. Each arm records its own actual returned handle at that origin. A
proposal inserted for diagnostics has no source origin and cannot steal a source
label. A refused source proposal resolves to no token; there is no fallback to an
earlier handle or the same-numbered native token. Dynamic `last_proposal` remains
an observed-handle reference and clears on refusal. Duplicate execution of a
source proposal origin is rejected rather than silently rebinding it.

The common runner (production/reference and other conforming backends) and the
TraceGrant harness share this routing utility only. It contains no authorization,
discharge, transaction or scoring logic. Backends receive actual native handles;
the state-delta comparison guard and state audits remain active. Token-valued
assertions resolve the same symbolic binding while retaining the original
`expectation` in reports; if translation changes its representation, the check
also records `resolved_expectation`. An absent required token does **not** turn
an expected token assertion into an expected absence: it still fails.

Controls insert an extra allowed refund proposal with an optional customer
argument before T02's source proposal. Core/reference must execute native T2
then T3, and TraceGrant EC2 then EC3; the diagnostic T1/EC1 is not executed. The
routing table also accepts opaque H7-style handles without interpreting them.
This checks routing behavior, not comparative outcomes or scores. No-token floor
and static-arm execution is deferred with C3; it is not implemented here.

## Verification

The supplied ruling file's SHA-256 is
`956b086805628901cb248518d394ac9164d5dc2bf197c0b8f6c58e57fd73088d`;
byte comparison against the attachment passes.

- 12 new component tests pass (5 C1 and 7 C4).
- C1 ignored-switch mutation: one test fails, no test errors.
- C4 issuance-ordinal mutation: both tests fail (three subtest failures across
  reference, production and TraceGrant), no test errors.
- Normal reference frozen suite: 54 scenarios, 534 source assertions plus 1,704
  state audits, zero discrepancies and zero incomplete.
- Reference regressions: 18 scenarios, 169 source assertions, 504 audits and
  three detection guards; zero discrepancies/incomplete.
- Four-controller development check: 40 episodes, 3,316 checks (117 source and
  3,199 state audits), zero discrepancies/incomplete; 195 semantic labels remain
  explicitly unassessed, as before.
- TraceGrant's existing single-arm diagnostic gate: 40 episodes, 1,190 checks,
  zero discrepancies and zero incomplete. Frozen contracts are unchanged.
- Normal production acceptance: frozen 54 scenarios, 534 source assertions and
  1,751 audits; regressions 18 scenarios, 169 source assertions, 524 audits and
  three hidden-state detection guards. Zero discrepancies and zero incomplete
  in both suites; all three hidden-state mutations are detected.
- The C4 component also passes with the independent SQL backend from PR #27:
  86 checks, zero discrepancies/incomplete, actual executions T2 then T3. This
  local integration check imports that separate branch; it adds no dependency
  on SQL code to this PR.
- Scripted `run.py --scenario all` passes; generated evidence is preserved outside
  the checkout. Full discovery began before the final two absence controls and
  missing-token diagnostic; all 12 focused controls were rerun afterward. The
  exact final commit remains subject to CI and Claude review.

Full historical discovery completed: **942 tests, 36 skipped, zero failures or
errors**, in 1,543.266 seconds. The timing qualification above applies; the final
12 focused tests pass independently afterward. Compact counts and source/log
hashes are retained in [validation.json](evidence/gateway-c1-c4/validation.json).

## Remaining

C2 primary no-invalidation ablation and its reassessment-retaining diagnostic
variant are deferred. C3, the external scoring oracle, floor/static business
operations and cross-arm scoring are not started. All four rulings are preserved
for subsequent implementation. No paid/model/Modal operations or release occur.
