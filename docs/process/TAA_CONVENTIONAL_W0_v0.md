# Conventional SQL arm — W0 implementation review

1. [DESCRIPTIVE] The conventional arm implements the same bounded W0 policy and persistent obligations with independent flat constraints and SQL transitions.
2. [DESCRIPTIVE] All 89 declared scenarios pass: 782 source assertions, 10,952 state audits and three hidden-state detection guards, with zero discrepancies/incomplete.
3. [DESCRIPTIVE] Sixty-four component tests pass; the unchanged independent source traces exercise all seven real transaction fault boundaries.
4. [INTERPRETATION] Matching these development cases is success for both strongest arms, not empirical validation or a safety advantage for either.
5. [LIMITATION] Four-controller/multi-arm integration, baseline/ablation definitions and final MCP/replay remain outside this implementation packet.

## Representation and independence

[DESCRIPTIVE] The protocol was committed at `4338a7c8` before component outcomes.
`TAA_CONVENTIONAL_W0_MAPPING_v0.md` was written and hashed before the first
common-runner campaign. It maps W0 parties, grants, records, rules, dispositions,
duties and tools, and the serial Hn/Tn observation alias. Claude review is pending.

[DESCRIPTIVE] `conventional_gateway` imports no core or reference implementation.
The outer test harness uses the existing common runner and independently authored
expectations; its default reference import does not provide enforcement or
expected outcomes to this arm. `policy.py` evaluates flat current-state
constraints, selects one complete grant and fully reassesses positive alternatives.
The deciding rule is the first failed constraint in stage order, without a
fixture-specific preference. The engine never reads a case ID or expected label.

[DESCRIPTIVE] Permission handles contain actor, exact arguments, epoch, expiry
and effect-plan digest. They do not contain TAA warrants or rule-computed
authorization support sets. Duty discharge retains bound evidence because that
is a shared requirement, not an authorization-warrant representation. The ledger
is an independent state machine over append-only SQL histories. All relevant
changes invalidate live handles, and execution rechecks the current flat policy.

| Requirement | Conventional implementation |
|---|---|
| Ordered wrongdoing | PR1/PR2 over computed assertions/benefit route before authority; stored orders provide context/attribution, not permission |
| Complete authority | Live one-level parent chain, issuer standing, actor, scope and purpose in one complete grant |
| Evidence and particulars | Three-valued support; missing cited records REFUSE under Q13; contradictory existing evidence PROHIBIT; per-call and cumulative limits |
| Atomic execution | Real SQLite transaction: validation, staged SQL rows, effects, consumption, duty updates, receipt and one revision advance; rollback at seven actual boundaries |
| Duties | Claimant/owner, bound settled evidence and allocation, unique-basis coverage, acceptance-only transfer, no automatic release, unresolved-duty closure refusal |
| Corrections | Discharge/release rechecked, invalid evidence reopens the duty and case; retained history; overdue from the due step |
| Reporting | Matter = issuer/claim/prohibited element; roster/conflicts; versions and acknowledgments; unchanged repeat deadlines; fallback and supplements |
| Trust and observations | Authenticated host channels; create/correct field rights; no agent evidence promotion; full SQL histories and independent projection/delta audits |

[DESCRIPTIVE] Offer/accept execution stages an immutable logical action. The
ledger applies it inside the actual transaction at the execution step, so an
offer proposed at step 2 and executed at step 3 expires at step 8. The public
offer order comes from stored creation sequence, not JSON object-key ordering.

## Common-runner acceptance

[DESCRIPTIVE] Current strict campaign (`check_conventional_w0.py`):

| Suite | Scenarios | Source assertions | State audits | Hidden-state guards | Discrepancies | Incomplete |
|---|---:|---:|---:|---:|---:|---:|
| Frozen v0.2.2 | 54 | 534 | 7,539 | 0 | 0 | 0 |
| Permanent regressions | 32 | 217 | 3,081 | 3 | 0 | 0 |
| Additional adversarial controls | 3 | 31 | 332 | 0 | 0 | 0 |
| Total | 89 | 782 | 10,952 | 3 | 0 | 0 |

[DESCRIPTIVE] Three regression scenarios are out-of-band hidden-state controls;
their raw poisoned observations are kept separately, and their detection guards
are counted above. The ordinary regression source count is 217; the full input
format contains 242 blocks before negative-control wrapping. All guards execute
their complete raw source blocks and detect actual SQL mutations: extra settled
refund to account_X, refund written by a refused proposal with omitted description,
and overwriting REF1 version 1. No expected outcome is changed.

[DESCRIPTIVE] The same observer computes its own complete before/after delta.
Additional non-normative SQL checks compare public observations with the raw
checkpoint relations and pin all historical versions. A component negative
control hides a real SQL refund from the public record view: the independent
projection audit rejects it. Observations never come from an effect list returned
by the policy. A separate metadata control drops one checked source block from
an observed report; the coverage gate rejects 533/534 even with no ordinary
reported discrepancy. Missing blocks or guards cannot produce a clean gate.

[DESCRIPTIVE] The validator verifies the frozen bundle before and after,
requires exact scenario/source counts and no unknown statuses, and hashes the
runtime, observer, runner, regression/control inputs, mapping and harness. Runtime
and source hashes remain unchanged within each final campaign. CI runs this arm
through the permanent suites, including all three controls, without replacing
the existing reference/production gates.

## Development failures and provenance

[DESCRIPTIVE] The first campaign passed all frozen and adversarial cases and
detected all three hidden-state controls. It had four source discrepancies and
zero incomplete assertions: the Q12 concurrent-offer lists rendered F before L
after canonical JSON serialization, despite the earlier L offer. Ownership and
deadlines were correct. The fix records a creation sequence and uses it in the
primary/public offer view. The expectations stayed byte-identical. Subsequent
campaigns pass all 89 scenarios at the same check counts.

[DESCRIPTIVE] `evidence/conventional-w0/initial_evidence.zip` preserves the raw
first observations/log and the original runtime/observer/mapping bytes. Those
source bytes were reconstructed after the fix and independently byte-verified
against all eight hashes captured before the first run; the archive explicitly
records that timing. The initial results were not reconstructed or edited.
Archive SHA-256: `516a0a91b0253e9eb579e22371da027e2e94484abfc5cfbaa6b969c20d4baa12`.

[DESCRIPTIVE] Component coverage is 21 kernel + 21 flat-policy + 10 ledger +
12 host/observation tests. Examples include wrong-route staging refusal,
wrong-actor use, complete-grant isolation, same-step correction grouping,
execution-step offer windows, both acceptance boundaries, corrected overdue
discharge, report-repeat deadlines and a lying public projection. The kernel's
six deliberate mutations remain a separate required component gate. The earlier
PR #26 packet is historical kernel-only evidence; this packet supersedes its
statement that W0 policy was not yet connected.

[DESCRIPTIVE] An additional service-integrity control found that the original
report/hold/deny frame check accepted any payload containing the supplied args,
including a substituted financial template. Its test fails before the fix
(expected REFUSE, observed PERMIT), and passes after exact effect-frame checking.
Refund payload keys, logical duty-action payloads, and implicit notice recipient
and template fields are now checked completely. The before-test log is preserved
alongside the first offer-order discrepancies. No fixture expectation changed.
An additional P6 component check runs the same authenticated script twice and
requires byte-identical logs.

[DESCRIPTIVE] Repository discovery completed **979 tests, 36 skips, zero
failures/errors** in 1,825.408 seconds, exit 0. It collected the earlier 62
component tests before the notice-frame and determinism additions; the current
64 tests and hardened W0 campaign passed separately. Existing core/reference
code was unchanged. All historical scripted scenarios passed, and the native
property journal retains 29 passing programs. `broad_checks.json` records this
timing and the full log hashes; CI repeats all checks at the actual PR head.

## Limits and review gates

[INTERPRETATION / OPEN QUESTION] Q14–Q16 remain unapproved drafts. The documented
conservative behavior remains: unique settlement bases/shared denial remainder,
no recipient-eligibility recheck on a repeat, and no immediate fallback solely
because an accepting party never had discharge authority. Neither this code nor
the observed matches settle those questions.

[LIMITATION] This is one bounded simulated refunds world and finite development
scripts. Sol wrote this arm as well as the other implementations; separately
authored expectations, mutations and independent reviews are necessary. There
is no claim of blind authorship, comprehensive adversarial coverage, universal
correctness, real identity custody, production readiness, general moral judgment
or a population effect. The host and its keys remain trusted simulator components.

[LIMITATION] Four-controller integration must use the same tools, inputs and
intent-preserving routing across arms. Definitions of the floor/static duty
service and the named ablations need Claude's clarification before comparative
scoring. Source-key agreement here does not clear the whole comparator stage or
select an H3 endpoint/advantage. MCP/replay is last; training/export remains out
of scope. No model calls, Modal operations, spending, Notion edits, evidence
removal or public release. Merge requires Claude review and all green CI.
