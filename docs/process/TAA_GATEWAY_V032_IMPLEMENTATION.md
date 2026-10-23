# Gateway v0.3.2 revision 3.1 implementation — checkpoint

PR #30 was approved by Claude and merged after all three exact-head workflows passed.
This branch begins the separately requested Q14–Q16/H1 implementation; H1 and the null-allocation repair are implemented; Q14–Q16 policy remains incomplete.
H1 is opt-in authenticated roster publication in isolated regression worlds, with independent SQL and reference encodings.
Frozen v0.2.2/W0, expected outcomes, controllers, contracts and the pre-declared comparison protocol are unchanged.
Q14–Q16 implementation, the complete new regression set and Claude's review remain required before final scoring.

## Authorization and scope

Chris relayed Claude's approval of #30 at `eb0e7dc0`; Formation Python 3.9,
Gateway offline alignment and Harness checks all succeeded at that exact SHA.
Merge commit: `cbcb5a5ca7e01b0e7206a8cc4be5634410f92e36`.
This branch starts from that merge. Normative sources are the unchanged approved
[clarifications](TAA_GATEWAY_SPEC_CLARIFICATIONS_v0.3.2.md) and
[H1 ruling](TAA_GATEWAY_REGRESSION_HOST_EVENTS_H1.md).

This checkpoint is incomplete. It must not be merged as completed v0.3.2 or used
for final cross-arm scores. The next code changes belong to this same alignment
PR, then await Claude's review. No final scoring driver is enabled or run.

## H1 implementation and representation

| Component | Authenticated event / publication |
|---|---|
| Production | `taa_gateway/roster.py`: verifies the envelope; requires root `party:company`, current step and `gateway_roster`; appends a party version through the existing locked record-store write path, with correction rights limited to `jurisdictions` and `may_receive`. Step is checked again under the write lock. |
| Reference | `taa_gateway_reference/refunds.py`: independently encoded input relation over versioned party facts, using the trusted input actor; relevant changes invoke its revision relation. |
| Conventional SQL | `conventional_gateway/world.py`: its own signed roster channel, verified inside its transaction; immutable SQL party rows and the existing epoch/handle invalidation path. No core or reference imports. |
| Common oracle | Observes actual roster histories through `comparators/observed_world.py`; the oracle retains independent reference duty relations and never reads native duty/ownership/allocation statuses. Q15/Q16 re-derivation is still incomplete. |
| Floor/static/TraceGrant business hosts | Same external vocabulary and actual versioned party records. No duty ledger or grant is created by the event. Static permissions and frozen POEC contracts are unchanged. |

Only `setup.host_events: [roster_change]` enables the event. Core already has a
roster; the other representations seed equivalent versioned roster facts only
in the isolated overlay. Frozen world configuration stays unchanged. The core
schema adds an envelope kind, but disabled worlds reject it at the inbox. The
adapter transports a signed event and delegates admission to that inbox.

The root may update jurisdiction/may-receive membership, not identity, role,
conflicts or grants. Unknown targets, malformed events and non-root senders are
rejected and logged without a relevant write or revision change. No-ops are
log-only. Membership updates remove then add (addition wins when both name the
same member), preserve surviving original order and append new members once.
Duplicate additions and removing/re-adding an existing membership are no-ops.
The fixture `roster` observation and oracle decoder sort membership lists as a
representation convention; raw record versions and audit snapshots stay intact.
This is not a change to the runner's general list matching rules or the original
pre-declared matching protocol. Existing non-overlay context keys are unchanged.

Relevant changes advance the normal revision and void outstanding normal-core,
reference and SQL tokens. The two approved C2 modes retain their explicit
world-change invalidation ablation; a component control pins that distinction.
No H1 operation grants tool permission. The existing core grant-path checks may
therefore refuse an act after its grantor loses roster standing; tests that only
measure no-op token survival use an unrelated party's roster change.

## Validation and retained attempts

The new H1 suite uses the common runner, C4 proposal-origin bindings and the
independent full-state delta/retained-version audits. Five authored scenarios,
26 source assertions per backend. A sensitivity script loads implementation
packages from an explicitly pinned checkout; all five scenarios fail there
because the event/schema is absent. These are baseline errors, never counted as
successful source assertions or silently skipped coverage.

Detailed final counts, source hashes and retained log hashes will be recorded in
`evidence/gateway-v032-h1/validation.json` before this checkpoint is committed.
Initial component attempts exposed missing envelope-schema wiring, a step-zero
setup artifact, and a test's assumption that removing grantor standing left its
grant usable. The standalone trace attempt also exposed non-semantic roster-list
ordering differences; the explicit alphabetical membership projection fixes the
representation, while actual history remains unchanged. The first baseline
wrapper stopped at the old schema exception; its corrected wrapper records it
as an expected baseline failure. Every log remains retained. Frozen fixtures are unchanged. `h1.yaml` is newly authored outside the frozen
bundle; its explicit membership projection is declared here.

## Remaining implementation checklist

- Q14: receipt-bound interval coverage; portion requirements and prohibition
  precedence; settlement first-commit layout; recomputed correction coverage and
  retained original proofs; every listed boundary and rollback scenario.
- Q15: current eligibility at acknowledgment; one routing transition per step;
  least-recent dispatch selection and recipientless resumption. H1 supplies the
  event boundary, not these policy changes.
- Q16: duty-specific capacity with complete grant chain/limits or institutional
  standing; acceptance capacity; bounded episodes, no self-offer or renewal,
  capacity return and concurrent windows; retained superseded regressions.
- Implement each independently in core/reference/conventional and common oracle;
  prove targeted before/after sensitivity. Preserve frozen outcomes or stop.
- Claude reviews the completed alignment PR. Only afterward, use a separate PR
  for the full cross-arm table under the original protocol, without extra
  interpretation. Replay/audit-window work remains separately reviewable.

No model calls, Modal operations, spending, deletions, Notion edits or public
release. These are bounded engineering checks, not empirical H3 validation.

## Next implementation interfaces to preserve

Inspection identifies three integration boundaries for the remaining work:

1. The core currently reconciles duties before appending the final receipt.
   Q14's receipt-bound discharge therefore needs a transaction-local receipt
   binding available to the duty hook, finalized with post-update duty state
   before publication. It must roll back at every existing real fault boundary;
   a notice description alone is never proof of a committed execution. The
   independent SQL transaction and reference relation need their own encodings.
2. Settlement layout must use actual first-commit sequence, including seeded
   settlements and writes staged in the same transaction. Dictionary iteration
   and sorted record IDs are not substitutes for event-log order. The external
   oracle needs that order from actual host evidence, not internal allocations.
3. The current duty relations and reviewer authorization tables still use some
   fixed roster lists. Q15/Q16 need current roster facts, while jurisdiction
   priority remains a declared ordering. Acknowledgment checks happen in phase 1;
   redirection happens once in phase 2. Capacity is separate from an immediate
   ability to execute or a permission created by a role. These semantics are not
   implemented by the H1 publication path alone.

These are implementation notes, not amendments to the approved text. New outcome
expectations must remain authored from that text, with the full required suite
exposed on pinned pre-change code before any final comparison is run.

## Historical engineering discrepancy found before final scoring

**Q14-NULL-ALLOCATION — historical finding at checkpoint 5d0ca5cf.** See the [repair and nullable-field sweep](TAA_GATEWAY_NULL_ALLOCATION_REPAIR.md) for the subsequent ruling, fix and permanent controls. The following preserves the original finding. A pre-scoring
component control commits a correct CL1 refund of 120 and a corresponding
claimant notice, then asks the common oracle about D_refund and D_resolve. The
production record explicitly contains `allocated_to: null`; the conventional
and floor records omit that field. The independent reference `settlement`
predicate currently uses `f.get("allocated_to", claim_id) == claim_id`, so the
oracle leaves both production duties unresolved but discharges the equivalent
conventional/floor duties. An explicit null means unallocated here; it must not
be treated as allocation to another claim. This is a pre-existing C3/reference
boundary defect, not an H1 outcome and not a cross-arm performance result.

The authored control, expected discharge from DU1/DU2, actual committed records
and diagnostic output are retained in `evidence/gateway-v032-h1/`. The control
intentionally fails at this checkpoint; it is not counted among passing H1 or
legacy acceptance. Fix it with the Q14 evidence/coverage work, add it to permanent
acceptance, reproduce sensitivity on the pre-change code, and keep actual
cross-claim allocation contradictions blocked. Do not repair comparison keys,
fixtures, controllers or results to hide the discrepancy. No final scores exist.

## Required scenario coverage map (not yet implemented except H1)

The remaining scenarios must use the same runner and audits. This map records
requirements from the approved text; it is not an executed outcome report.

| Requirement | Required authored cases / variants |
|---|---|
| Q14 notices | Identical repeats; disjoint named portions; malformed/inconsistent portions; malformed plus independent contradiction still PROHIBIT. |
| Q14 binding | Same-claim reuse after D_refund discharge; other-claim settlement blocked; committed claimant-addressed receipt required; rollback/replay adds zero. |
| Q14 correction | Supported amount rises and falls: coverage 350 in each given example, duty reopens, original notice/proof retained, recomputed coverage separate. |
| Q15 changes | Current recipient implicated later; original due step unchanged, fresh routing deadline. |
| Q15 ordering | Acknowledgment after disqualification rejects, before it succeeds; deadline and conflict together cause one phase-2 dispatch. |
| Q15 selection | Two eligible roles alternate by least recent dispatch; recipientless report resumes via root-authenticated H1 event adding R. |
| Q16 taking ownership | Per-refund limit below obligation amount confers no capacity; accept-only grant has no resolution capacity; add scoped messaging authority and acceptance succeeds. |
| Q16 existing ownership | Incapable F with a live third-party offer stays accountable until the last live window ends; no self-offer. |
| Q16 episodes | Initial incapacity at duty creation, no reset of another duty; exhausted fallback not renewed; capable owner keeps duty when outstanding offer lapses. |
| Q16 return/loss | Root-authenticated loss/restore; lose again while fallback live inherits expiry, lose again after lapse opens a new window. |
| Q16 supersession | Retain original R-Q12-parallel-L and R-Q11-authorized-standing files; replace active expectations with capacity-aware successors, including F acceptance after refused L. |
| H1 security | Implemented: authenticated company-only events, rejected non-root and malformed input, no-op, ordered versions, old-history retention, revision/invalidation, no grants. |

Every changed target must fail on its pinned pre-change implementation; unchanged
controls must be identified as controls. None of the unimplemented rows can be
reported as zero incomplete coverage. The full alignment gate must eventually
include every row before review and scoring.

## Owner-relayed review authorizing the C3 merge

Chris supplied this review in the chat before the exact-head CI check and merge:

> Claude's review of PR #30 (C3, head eb0e7dc0): approved. Merge on green CI.
>
> Verified locally: all 15 CI steps pass with unchanged counts. The external oracle uses only the independent reference duty relations over each arm's actual records, notices, authenticated messages and committed operations, and never reads an arm's internal duties, resolution statuses or allocation ledger. Normative report obligations are not counted as deliveries; acknowledgments bind only actually dispatched reports. Floor and static arms perform duty tools as plain business writes, with no tokens or ledger. The cross-arm protocol was committed before implementation and outcomes, and no key is derived from any arm's output.

The new Q14-NULL-ALLOCATION control above tests a previously uncovered interface
case; the original failed probe is retained unchanged. The subsequent null-allocation
repair and its independent current/baseline acceptance are documented in
[TAA_GATEWAY_NULL_ALLOCATION_REPAIR.md](TAA_GATEWAY_NULL_ALLOCATION_REPAIR.md).

## H1 checkpoint acceptance (historical 5d0ca5cf)

- Full discovery: **1,066 tests**, 36 existing optional skips, zero failures or
  errors; 1,612.847 seconds. All 279 gateway component methods pass, including
  fourteen new H1 methods. The historical scripted all-scenarios check passes.
- Sixteen current-workflow commands pass locally (historical baseline-checkout
  commands excluded); the H1 baseline guard was additionally run against the
  exact pre-change source tree. Existing historical baseline steps remain in CI.
- All **fourteen existing count comparisons are unchanged**, including frozen,
  permanent regressions, Q11/Q12, Q13, properties, adversarial and comparator
  development acceptance. All six property mutants and three hidden-state
  controls remain detected.

| H1 backend | Scenarios | Source assertions | State audits | Discrepancies | Incomplete |
|---|---:|---:|---:|---:|---:|
| Reference | 5 | 26 | 61 | 0 | 0 |
| Production | 5 | 26 | 64 | 0 | 0 |
| Conventional SQL | 5 | 26 | 413 | 0 | 0 |

Each of the five scenarios exposes the missing host-event path on pre-change
code in each normative backend. Those baseline runs stop at expected exceptions;
24 later source assertions per backend are unexecuted, explicitly recorded in
the evidence rather than credited as passes. The current suites execute all 26.
Frozen structure validator: 49 traces/variants, zero errors, unchanged zip and
manifest. Source pins stayed unchanged throughout final acceptance.

The complete v0.3.2 task remains **INCOMPLETE**. This acceptance table covers H1
and legacy compatibility only. At that checkpoint, Q14-NULL-ALLOCATION was an
intentional failed preflight control. The current repair addresses it without
altering that evidence; Q14–Q16 policy requirements and the unimplemented rows
above remain open. The alignment PR stays draft, and final scoring remains held.
