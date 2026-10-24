# Gateway v0.3.2 revision 3.1 implementation — review candidate

[DESCRIPTIVE] H1 and Q14–Q16 are implemented as the draft PR31 alignment candidate.
[DESCRIPTIVE] Core, reference and conventional SQL encode their own policy and discharge logic; the common oracle reads actual external evidence.
[DESCRIPTIVE] Frozen v0.2.2/W0, original regression files, controllers, contracts and the comparison protocol remain unchanged.
[COVERAGE LIMIT] TraceGrant covers only ten predeclared development programs; no post-outcome contracts are authored.
[GATE] Local combined-tree acceptance passed; merge and final scoring stay held for Claude's completed-PR review and green CI.

## Authorization and scope

Chris relayed Claude's approval of #30 at `eb0e7dc0`; Formation Python 3.9,
Gateway offline alignment and Harness checks all succeeded at that exact SHA.
Merge commit: `cbcb5a5ca7e01b0e7206a8cc4be5634410f92e36`.
This branch starts from that merge. Normative sources are the unchanged approved
[clarifications](TAA_GATEWAY_SPEC_CLARIFICATIONS_v0.3.2.md) and
[H1 ruling](TAA_GATEWAY_REGRESSION_HOST_EVENTS_H1.md).

This remains a draft pending Claude's completed-delta review and green exact-head CI.
No merge is authorized before that review and green CI. No final scoring driver
is enabled or run; scoring belongs to its separate post-review PR.

## H1 implementation and representation

| Component | Authenticated event / publication |
|---|---|
| Production | `taa_gateway/roster.py`: verifies the envelope; requires root `party:company`, current step and `gateway_roster`; appends a party version through the existing locked record-store write path, with correction rights limited to `jurisdictions` and `may_receive`. Step is checked again under the write lock. |
| Reference | `taa_gateway_reference/refunds.py`: independently encoded input relation over versioned party facts, using the trusted input actor; relevant changes invoke its revision relation. |
| Conventional SQL | `conventional_gateway/world.py`: its own signed roster channel, verified inside its transaction; immutable SQL party rows and the existing epoch/handle invalidation path. No core or reference imports. |
| Common oracle | Observes actual roster histories through `comparators/observed_world.py`; the oracle retains independent reference duty relations and never reads native duty/ownership/allocation statuses. Q14–Q16 re-derivation uses those independent relations over actual records, notices, receipts, financial commit order, authenticated messages and committed operations. |
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

Historical H1 counts, source hashes and retained log hashes are recorded in
`evidence/gateway-v032-h1/validation.json`. Current combined acceptance is
reported separately below.
Initial component attempts exposed missing envelope-schema wiring, a step-zero
setup artifact, and a test's assumption that removing grantor standing left its
grant usable. The standalone trace attempt also exposed non-semantic roster-list
ordering differences; the explicit alphabetical membership projection fixes the
representation, while actual history remains unchanged. The first baseline
wrapper stopped at the old schema exception; its corrected wrapper records it
as an expected baseline failure. Every log remains retained. Frozen fixtures are unchanged. `h1.yaml` is newly authored outside the frozen
bundle; its explicit membership projection is declared here.

## Implemented requirements and remaining gates

- Q14: receipt-bound whole-integer portions, prohibition precedence, first-commit
  settlement layout, union coverage, correction/reopening and original proofs.
  See [Q14 implementation](TAA_GATEWAY_Q14_RECEIPT_COVERAGE.md).
- Q15: current eligibility at acknowledgment, one routing transition per step,
  least-recent dispatch, recipientless resumption and actual-send observations.
- Q16: duty-specific capacity, complete grant paths/limits or institutional
  standing, acceptance capacity, bounded loss/recovery, no self-offer/renewal,
  preserved concurrent windows and explicit retained-source supersessions.
- H1: authenticated roster changes are opt-in regression-world events. Frozen W0
  remains byte-identical. No role assignment creates tool permission.
- Final combined-tree discovery, scripted scenarios, normative, property,
  adversarial, oracle, before/after and all-arm input-only gates must finish.
  Failed/interrupted prefixes remain evidence, never passing acceptance.
- Claude reviews the completed alignment PR; CI must be green before merge.
  Only afterward, use a separate PR for the full cross-arm table under the
  original protocol, without extra interpretation. Replay/audit-window work
  remains separately reviewable.

No model calls, Modal operations, spending, deletions, Notion edits or public
release. These are bounded engineering checks, not empirical H3 validation.

## H1-checkpoint planning notes (historical)

These earlier notes record the integration boundaries subsequently implemented
by the Q14–Q16 candidate above:

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


## Q15 continuation (historical, before Q16 integration)

Q15 dynamic routing, phase-1 acknowledgment eligibility and least-recent routing
are implemented independently in the core, reference and SQL arm. The common
oracle uses its permitted independent reference duty relations over actual
inputs; its physical send reader does not read native duty/ownership ledgers.
See [Q15 and business-fault report](TAA_GATEWAY_Q15_AND_BUSINESS_FAULTS.md).
This status supersedes historical Q15-pending entries above; Q14 interval/receipt
coverage and Q16 capacity remain unimplemented. No Q11/Q12 case is superseded
before its Q16 replacement exists. Final scoring remains held.


## Q16 continuation (historical, before Q14 integration)

Q16 capacity and bounded loss/recovery episodes are now implemented independently
in the core, reference and conventional SQL arm, and re-derived by the common
external oracle. See [capacity checkpoint](TAA_GATEWAY_Q16_CAPACITY_CHECKPOINT.md).
This supersedes historical Q16-pending statements above. Exactly two Q11/Q12
source cases now have explicit active successors; their original files remain.
The permanent regression population stays 32; its assertion/audit counts can
change because those two source scenarios now exercise the approved Q16 rule.
Frozen assertions and original files are unchanged.

Q14 interval/receipt coverage remains INCOMPLETE. Source-authored draft scenarios
are retained in `drafts/TAA_Q14_REGRESSIONS_DRAFT.yaml`, outside acceptance. Their
pre-change exploration, including an invalid financial-source input, is retained
as incomplete authoring evidence, never a passing baseline or an implemented
Q14 gate. The draft must be completed against legitimate authenticated inputs
before it enters acceptance. Final scoring and PR merge remain held.


## Current Q14 integration

Q14 is now integrated in this branch, superseding the earlier incomplete status
entries above. The18 source-authored cases were activated byte-for-byte from
the retained authoring revision v1, after using legitimate chargeback creation
for the ordering case. Original draft and failed probe remain preserved. Core,
reference and SQL targeted probes pass102 source assertions each; frozen and
active permanent-regression compatibility also passed in the isolated candidate
before integration. Those probes are not a substitute for the final combined
acceptance now running. The first full Q15/Q16 discovery had one old IR1 test
checking a phase-1-only fixture: the corrected component seeds both existing
claim duties and explicitly runs phase2, preserving its final expected result.
The failed run, intermediate test attempt and corrected preflight are retained.

The production executor passes a private future receipt binding to its locked
copy-on-write duty calculation, then publishes the actual receipt in the same
transaction. SQL has its own private projection, cleared on every exit, and
reference uses an ideal copied next-state relation. No projected admission can
escape actual rollback. Only actual receipts and notices feed the common oracle;
no internal arm duty/status/allocation ledger is read for scoring.


## Final combined local acceptance — 2026-10-23

Full discovery: **1,097 methods, 36 existing optional skips, zero failures/errors**,
2773.595 seconds. All21 current workflow commands, scripted all-scenarios and
four fresh pinned sensitivity commands pass. Historical checkout-only baseline
steps remain enabled in GitHub; they were not all repeated locally.

| Suite | Scenarios | Source assertions per backend | Reference audits | Production audits | Conventional SQL audits |
|---|---:|---:|---:|---:|---:|
| Frozen v0.2.2 | 54 | 534 | 1,704 | 1,751 | 7,539 |
| Active permanent regressions | 32 | 218 | 647 | 671 | 3,090 |
| Q14 | 18 | 102 | 547 | 548 | 2,058 |
| Q15 | 9 | 32 | 191 | 211 | 1,221 |
| Q16 | 16 | 119 | 494 | 510 | 2,290 |

All current normative groups have zero discrepancies, incomplete assertions or
errors. All three hidden-state controls remain detected. P1–P6 detect all six
mutants; adversarial and existing development gates pass. The two explicit Q16
source substitutions account for permanent source count217→218; Q14 preserves
those post-Q16 counts. Original regression YAML, frozen fixtures/W0, contracts,
controllers, protocol and adversarial source inventory remain unchanged.

Before/after sensitivity needs two distinct descriptions: every targeted Q15
and Q16 case has an actual pre-change discrepancy. Seven Q14 cases instead
expose the old absent portion-schema/decision path: their baseline checks are
**incomplete**, not observed semantic disagreements. Other targeted Q14 cases
have actual discrepancies. Already-correct controls are explicitly marked.
The before counts (including11 incomplete Q14 checks per backend) are retained
in the evidence; all current Q14 checks are complete. No expectation changed.
The initial packaging assertion incorrectly demanded an actual discrepancy for
every target; preserve its failed log and correct the report classification,
without changing any implementation, scenario, gate or test result.

All-arm input replay:1,096 planned instances;961 executed,127 missing-contract
TraceGrant instances unrun,8 business boundaries not applicable by design.
42,977 state checks retain4 real floor/static missing-receipt discrepancies;
zero unexpected discrepancies, incomplete checks or errors among executed
instances. Six of the14 floor/static T23 instances really execute; the other
eight have absent boundaries with specific reasons. Actual before/after fault
states are retained. TraceGrant remains limited to ten predeclared development
programs:127 missing-contract instances = original84 +9 Q15 +16 Q16 +18 Q14.
No post-outcome contracts are authored, and overall replay coverage is incomplete.

This is engineering replay, not final cross-arm scoring or H3 evidence. Final
scoring remains held for Claude's completed-PR review. Evidence:
[evidence/gateway-v032-final/validation.json](evidence/gateway-v032-final/validation.json)
and its lossless acceptance.zip, including failed/interrupted diagnostics,
source pins, pre-Q14 source reconstruction and preserved free scripted outputs.
No model calls, Modal operations, spending, evidence deletion, Notion edits or
public releases.
