# C3 business hosts and common external duty oracle

Scope: business-arm hosts, shared runner infrastructure and external duty oracle.
Protocol: matching rules committed and hash-pinned before comparison results were read.
Oracle: actual records and operations; no arm's internal duty status is trusted.
Keys: Claude's existing frozen keys only, with exact source/context matching.
Order: C3 infrastructure, Q14–Q16 in four implementations, then final scoring in its own PR.

## Implementation and boundaries

| Piece | Locations | Behavior |
| --- | --- | --- |
| Floor/static business services | `comparators/business.py`, `Service.apply`, `Backend.event/propose/execute/allowed` | Registered tools; ordinary recorded offers, acceptance, messages and closure; no internal ledger or security tokens. Static permissions use a complete fixed initial grant path, customer scope and cap. |
| TraceGrant common adapter | `comparators/business.py`, `_load/_save/_admit`, `Service` | The reviewed frozen contract implementation; no TAA policy or duty engine. The final gate, budgets, certificates and receipts remain the paper reconstruction. |
| Trusted native modes | `tests/trace_support/production_backend.py`, `start/_context/_project` | Explicit host configuration survives checkpoint reconstruction. Default serialized state and behavior stay unchanged. Setup/agent fields do not select a mode. |
| Common scheduling | `comparators/cross_arm.py`, `Recorded`; existing `reference_runner` | Same events, phase grouping, four controllers and proposal-origin bindings in every arm. Security-token-free arms bind an execution to an intention; a proposal alone performs nothing. |
| Independent observation | `tests/trace_support/state_observations.py`, `Observer.audit` | Full independent state delta, retained record contents, receipt/effect consistency and mechanism-specific consumption evidence. The runner never trusts a returned state-delta description. |
| Representation decoding | `comparators/observed_world.py` | Business record histories, grants, stored orders, notices and actual dispatch artifacts. Never reads an arm's duty status or internal allocation ledger. |
| External duties | `comparators/duty_oracle.py`, `Oracle` | Independent reference DU1–DU6 relations, accepted actual operations, authenticated messages and current evidence. Applies Q1–Q13 and preserves conservative Q14–Q16 behavior. |
| Keys and metrics | `comparators/cross_arm.py`, `labels/episode/run_suite` | Only existing source keys label actions. A validated ordinary-core key follower contributes context fingerprints, not generated expectations. Unknown contexts remain unassessed. |
| Deferred comparison driver | `docs/process/archive/TAA_CROSS_ARM_DRIVER_PRE_v032.py.txt` | Incremental attempt retention and TraceGrant equivalence checks. The full-scoring CI step is held until Q14–Q16 are implemented. |

[DESCRIPTIVE] The two C2 configurations include PR #29's intrinsic-withdrawal
correction. C1/C2 mode selection is constructor-owned and passed on every native
checkpoint restore. Neither the external oracle nor its board enters a policy,
a controller's inputs or the native checkpoint. The ordinary core and strongest
SQL arm import none of this scorer's duty code. The oracle imports neither
implementation; it reuses the independently written reference relations, as C3
permits. An AST component check protects that boundary.

[DESCRIPTIVE] Duty relations reconstruct whole-claim coverage from actual settled
records and notices, counting each basis once. Their own allocation state is
independent of the arm's internal allocation ledger. Correction/reopening uses
actual retained record versions. Offers and tool acceptance come from observed
committed calls; external acceptance comes from authenticated host messages.
Tool acceptance requires AU1 and a live offer, while the message path requires
standing only (Q11). Invalid business transfer operations are reported, not
credited as ownership changes. Closures are recorded with every unresolved duty,
including duties not yet overdue.

[DESCRIPTIVE] DU3's independent prohibition predicates trigger normative report
requirements in the oracle; they never produce semantic answer keys. A normative
dispatch in the reference relations is not a physical delivery. Acknowledgments
need an actual report artifact with the same id, version, recipient, matter and
incidents. Native dispatch envelopes and the SQL comparator's committed versioned
report relation provide those artifacts. Internal `acknowledged`/duty-resolution
flags provide no proof. SQL report rows are the existing comparator's abstract
dispatch artifacts; this does not establish delivery by a production transport.
Unstructured agent reporting is recorded as a business operation; without the
required bindings it is not silently credited as acknowledgment of a duty.

## Common audits without invented capabilities

[DESCRIPTIVE] Floor/static proposal references are ordinary simulator intention
handles, not capabilities. They may be executed repeatedly. Their state has an
empty security-token collection; business receipts bind to an intention and the
actual actor/tool/arguments. Common audits check one actual operation, exact
record effects, receipt actor and pre-transaction revision, and retained business
operation/message histories. A wrong actor is permitted by the floor's physics
but does not inherit a different party's semantic source key.

[DESCRIPTIVE] The TraceGrant arm uses the reviewed one-shot-on-dispatch protocol.
The common Observer independently checks the actual certificate-store projection.
Consumed certificates must have either a successful actual receipt or a retained
POEC dispatch-abort history entry; unexplained consumption fails. The ordinary
TAA/SQL consumption checks are unchanged. All profiles retain the same independent
full-state delta and immutable-version content guard. None uses a returned list
of effects as evidence of execution.

## Semantic scope and interpretation

[PROTOCOL] The unchanged development catalog supplies ten tasks. The unchanged
controllers are the key follower, compliant, cautious and adversarial scripts.
The key follower has the source keys; it is not a learned competent model.
Cross-arm programs are derived input-only comparison programs, not claims that a
weaker arm passes every TAA-specific frozen assertion. The ordinary-core baseline
is separately checked against the independent source assertions. Existing full
frozen/regression acceptance remains in CI for the reference, production and
strongest conventional implementations. These suites and cross-arm state-audit
coverage are reported separately.

[DESCRIPTIVE] Exact source identity includes the original proposal entry, acting
party, tool, arguments and order reference. Current context must also match the
validated baseline's representation-neutral context. A borrowed token/intention
never inherits its original actor's key. Context changes, extra attacks and
unmapped requests remain unassessed; their actual effects and external duties
remain visible. This conservative matcher can leave an execution unassessed even
when its proposal had a known label, including when normative report/duty state
changed between proposal and execution. No label is widened after results.
Execution with a changed context/actor is also reported descriptively.

[DESCRIPTIVE] `committed_refund_amount` counts observed agent execution effects;
`world_refund_amount` includes current seeded and externally supplied refund
records as well. Agent withholding and gateway over-refusal are distinct counts.
Incomplete observation vocabulary and exceptions fail the comparison gate and
retain the completed episode prefix. Unsupported semantic labels remain
unassessed rather than becoming favorable outcomes.

[INTERPRETATION] Exact agreement with the strongest conventional implementation
is success for both. These are finite scripted development observations. They
are not held-out evaluation, population estimates, training-transfer evidence,
proof of H3, novelty evidence or a public/live release. Q14–Q16 are now approved; implementation follows this infrastructure PR.

## Engineering attempts

[DESCRIPTIVE] An initial integration run retains its exact source snapshot,
execution log and attempt metadata in the execution workspace. Before its aggregate results were read, a
component control exposed an execution-actor matching defect relative to the
already declared protocol. The matcher was corrected to require the exact actor,
tool and arguments. Complete initial static grant-path/scope handling and extra
business-history audits were also finished. The initial run is marked diagnostic;
its semantic labels are not accepted comparison evidence. The final acceptance
uses the completed implementation and the approved C2 withdrawal correction.
No frozen expected outcome, source key, controller, contract or matching protocol
was changed to fit either run.

[DESCRIPTIVE / COVERAGE CONTROL] A separate negative control injects an incomplete
check into the independently keyed baseline run. It exposed a reporting bug: the
baseline was correctly rejected, but its incomplete count was omitted from the
comparison gate. The old aggregation fails the control; the corrected aggregation
counts all non-passing common and baseline checks. The control passes after the
fix. The interrupted acceptance attempt and logs are retained separately; final
acceptance was restarted on the corrected source. No semantic matching rule or
expected outcome changed.

[DESCRIPTIVE / TEST API MIGRATION] Full component acceptance found an old C1
test using a constructor monkeypatch to select the mode. The common adapter now
passes an explicit host-owned configuration, so that monkeypatch's default was
correctly overridden. The test now calls the explicit host API; its authentic
order, current facts and all five behavioral assertions are unchanged. The old
invocation fails once; the migrated invocation passes. The failed run and logs
are retained, and full acceptance was restarted. No production rule or fixture
was changed for this migration.

## Approved scope update — 2026-10-23 UTC

[APPROVED SPECIFICATION] Chris supplied Clarifications v0.3.2 revision 3.1,
confirmed by Astra, during this acceptance run. The supplied specification text
is committed verbatim in `TAA_GATEWAY_SPEC_CLARIFICATIONS_v0.3.2.md` (SHA-256
`5c481f5a29fe181591439b58b74f5682c12009b52ac63c1cb7cf9dea0c74b1e7`).
The original pre-evaluation matching protocol stays unchanged as a historical
record; its statement that Q14–Q16 were pending describes its writing time.

[ORDER OF WORK] C2 is merged. This PR finishes C3 infrastructure using the
Q1–Q13 relations already reviewed. Q14–Q16 must next be implemented in the TAA
core, independent reference, independent conventional arm and common oracle,
with the specified regression and pre-change sensitivity evidence. Final
cross-arm scoring follows in its own PR under the pre-declared matching rules.
No final cross-arm score is computed or committed here. Diagnostic per-episode
matching helpers remain available for component controls; they do not establish
a final comparison result.

[RETAINED DIAGNOSTIC / INCOMPLETE COMPARISON] The interrupted pre-v0.3.2
integration prefix, source snapshots, execution logs and interruption reason are
retained. The old-source initial diagnostic was stopped too. Neither produced
an accepted final comparison. The aggregation script is preserved as an inactive text archive in
this PR for the later scoring stage; its full-comparison CI step is held. Earlier
prefix counts were state-audit progress reports, not final arm scores. The
uncompleted comparison is explicitly incomplete coverage, not a zero-gap
comparison. Frozen and regression acceptance for the existing implementations
remains in CI permanently.

[DESCRIPTIVE / HISTORICAL COMPATIBILITY] The pinned pre-interface sensitivity
gate exposed a redundant `ablation=None` keyword rejected by the historical
constructor. Ordinary mode now omits that keyword. Selected modes still pass
their explicit configuration on every restore. A component exercises start,
step entry, proposal and execution through a constructor without the new
parameter; that component and the historical sensitivity gate pass after the
fix. The prior TypeError and a fixture-wrapper default error are retained in
the execution logs. The latter was corrected to mirror the real `events=()`
default. No policy result or expected outcome changed.

[APPROVED TEST REPRESENTATION] Claude's H1 ruling is recorded in
`TAA_GATEWAY_REGRESSION_HOST_EVENTS_H1.md`. The Q14–Q16 PR will implement
authenticated root-only roster changes declared by isolated regression-world
overlays, with the single write path, version retention, no-op/rejection
revision invariance and actual-change token invalidation. Frozen W0 is unchanged.
The interrupted diagnostic prefix contains 235 of the planned 320 episodes;
the remaining 85 episodes and final comparison remain incomplete until the
approved normative changes are implemented and reviewed.

## C3 infrastructure acceptance

[REPRODUCED / LOCAL ENGINEERING CHECKS] Corrected-source full discovery: 1,052
tests in 1,512.792 seconds, 36 existing optional skips, zero failures/errors.
Gateway component suite: 265 tests including 26 new methods, all pass. Scripted
all-scenarios pass. All fourteen existing gate-count comparisons reproduce
exactly. The historical-constructor component and pinned sensitivity gate were
rerun after the compatibility fix; the evidence identifies those reruns and
the completed unchanged-policy checks separately. All nineteen named gateway
acceptance commands have successful evidence after those reruns.

| Current acceptance | Scenarios | Source assertions | State audits | Discrepancies | Incomplete |
| --- | ---: | ---: | ---: | ---: | ---: |
| Reference frozen | 54 | 534 | 1,704 | 0 | 0 |
| Production frozen | 54 | 534 | 1,751 | 0 | 0 |
| Reference regressions | 32 | 217 | 653 | 0 | 0 |
| Production regressions | 32 | 217 | 676 | 0 | 0 |

[REPRODUCED] Three permanent hidden-state detection controls remain active in
regression acceptance. The new components also catch hidden extra refunds in
all three business hosts, verify ledger-independent DU1–DU6 evidence and
reopening, and distinguish withholding from gateway over-refusal. All six
P1–P6 mutants remain detected; conventional, adversarial, Q11/Q12, Q13 and
reviewed single-arm development/TraceGrant count comparisons are unchanged.

[INCOMPLETE / DEFERRED] The interrupted Q1–Q13 diagnostic prefix contains 235
episodes and 27,361 state audits with zero discrepancies or incomplete entries
inside that prefix. Its 85 uncompleted episodes and final comparison are
incomplete coverage. No final cross-arm score is accepted. The inactive driver
archive preserves the implementation for the later scoring PR.

[PROVENANCE] `docs/process/evidence/gateway-c3/validation.json` records source,
protocol, approved-specification, frozen-bundle, attempt and result hashes.
Implementation inputs remained unchanged throughout corrected-source discovery.
Frozen fixtures, regression fixtures, scripted controllers and POEC contracts
are unchanged. Claude review and exact-head green CI remain required before
merging this infrastructure PR. Q14–Q16/H1 implementation is the next separate
PR; final scoring follows it.
