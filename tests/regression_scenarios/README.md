# Astra spot-check regressions

Sol-authored from Astra's 2026-10-21 spot check; expectations reviewed by Claude.

These are separate regression inputs, **not independently authored acceptance fixtures**. The frozen v0.2.2 bundle is unchanged. `astra_spot_check.yaml` uses its trace vocabulary. R-B2 removes the acknowledgment that masked escalation; R-B3 extends T30 with two notices of REF1; R-B4-packed/split compare identical event sequences; R-cache checks the corrected diagnostic. The three R-B1 traces retain T39/T34/T38 expectations and use out-of-band, harness-only hidden-state fault descriptors in `mutations.json`.

The unmodified trace inputs can later run against the production gateway. Its fault adapter must mutate its actual state, not merely alter a returned description. A negative control passes only when the mutation produces a discrepancy and no incomplete observation; raw poisoned-run discrepancies are reported separately from detection-guard results.

Run `python -I scripts/check_gateway_spot_review.py --report /tmp/spot-review.json`.
For pre-fix evidence use `--implementation-root PATH_TO_9ddf84a4 --expect-baseline`.
The baseline guard requires failure of **every defect-targeted regression**, plus all three missed-detection guards and the cache diagnostic. The packed-event scenario is a positive control: it passes before and after, while the split encoding fails before. Thus the packaging-equivalence contract fails on baseline.

Full observed assertion reports are CI artifacts. No expected outcomes are generated from either implementation. This is bounded offline engineering evidence, not empirical validation of H3.

## Q11/Q12 clarification regressions

Sol-authored from Claude's Q11/Q12 clarification; expectations reviewed by Claude.

`q11_q12.yaml` adds ten scenarios to permanent acceptance, including positive
controls for authorized acceptance and already-correct behavior. They exercise
AU1 versus DU4, authenticated-message acceptance, unchanged fallback expiry,
concurrent voluntary/fallback offers, either winner, the last remaining window,
and expiry into a dispatched unowned-duty report. They are Sol-authored from
Chris's relayed clarification, not additional frozen Claude-authored fixtures.

`python -I scripts/check_gateway_q11_q12.py --report /tmp/q11-q12.json` runs them
against both implementations using the current common observer. For causal
before evidence, point `--implementation-root` at commit
`59e48fcf5bcf6da5ae99cb0523f602187bb7e71a` and add `--expect-baseline`.
The implementation package paths and source hashes are recorded; runner and
expectations remain current. The baseline detection gate requires every targeted
pre-change scenario to fail in its designated backend. Existing correct cases
remain positive controls. Old unhandled exceptions, incomplete descriptions and
unreached assertions are reported honestly; they are not passing validation.
The original eight-case `9ddf84a4` spot-check baseline remains separately pinned.

## Q13 citation regressions

Sol-authored from Claude's Q13 clarification; expectations reviewed by Claude.

`q13.yaml` adds fourteen scenarios: missing issued/denied citations, existing
settlements for the wrong claim, claimant, order or currency, unsettled/insufficient
settlements, explicit allocation elsewhere, contradicted denial, and lawful
issued/denied/partial notices. Missing citations in ordered requests produce no
report; an ordered false settlement notice produces its report duty.

Run `python -I scripts/check_gateway_q13.py --report /tmp/q13.json`.
The sensitivity run uses `--implementation-root PATH_TO_80831009 --expect-baseline`;
required failures are named by backend, and already-correct cases remain controls.
No expected result is generated from the reference. All 32 regressions, including
the original eight and the ten Q11/Q12 scenarios, remain in permanent acceptance.


## H1 isolated-world suite (v0.3.2 implementation checkpoint)

`h1.yaml` is Sol-authored from Claude's H1 clarification; expectations reviewed
by Claude as specified in the ruling. Implementation review is still pending.
Every scenario declares `setup.host_events: [roster_change]`. This is trusted
world configuration, outside the agent interface; frozen W0 and v0.2.2 are
unchanged. The five scenarios cover removal/restoration with history, non-root
rejection, no-op, token invalidation and no-op token survival, and two same-step
entries in listed order. Events are phase 1; event expectations observe the state
after the common phase-2 reconciliation. `roster` reads actual latest party
records; jurisdiction and may-receive memberships are normalized alphabetically.
All other list semantics retain the existing exact/ordered runner rules.

These scenarios are a separate CI suite (`scripts/check_gateway_roster_h1.py`)
while Q14–Q16 implementation is incomplete; they do not replace or silently
shrink the permanent acceptance regressions. `R-Q12-parallel-L` and `R-Q11-authorized-standing` are now superseded by
the explicitly linked Q16 successors below. Their original files are retained.
No complete Q14/Q15/Q16 coverage is claimed by the H1 host-event checks.

## Q14 null allocation ruling (permanent, separate acceptance suite)

`q14_null_allocation.yaml` covers absent and explicit-null settlement allocation
and the cross-claim duty mirror. `tests.test_gateway_null_allocation` permanently
checks the original executed-payment/notice control against the common oracle
for production, conventional and floor without rewriting actual arm records.
It also checks the mirror correction, allocation ledgers in both reference
models, and same-claim notice reuse. Run `scripts/check_gateway_null_allocation.py`;
its pinned-before mode exposes the defects while mirror/absent controls stay
passing. This adds acceptance separately without changing historical source
counts or any frozen fixture. New scenario expectations await the completed
alignment PR's Claude review.

`scripts/check_gateway_all_arm_replay.py` replays original inputs using the same
runner/state audits for every arm. It does not compute behavioral/semantic/oracle
scores. Normal frozen/regression verdicts remain enforced separately on reference,
production and conventional. TraceGrant has only ten frozen task contracts;
other IDs are listed individually as unavailable, never assigned a fabricated
contract or silently treated as covered. This pre-existing limitation remains
incomplete coverage. Frozen contracts, controllers and original matching keys
are unchanged.

Business floor/static fault replay observes actual non-atomic writes at its
permission, effect and receipt boundaries. Common audit failures for effects
without receipts remain in reports. The four boundaries per host with no
counterpart are classified "not applicable by design" with reasons. This
supersedes the historical unsupported label; historical evidence is unchanged.
TraceGrant has only ten predeclared development contracts. Missing contracts
remain unrun; no new ones may be authored after these outcomes. Wider coverage
requires Astra's blind authorship. Cross-arm scoring is limited to those ten
declared development programs, and remains held pending the complete alignment.

`q15.yaml` adds nine Q15/H1 scenarios (32 source assertions per normative
implementation), including payment-route implication and unowned-report routing.
The common runner reads actual dispatches in commit order, rather than inferring
sends solely from changes to a duty's recipient. Original W0/frozen files and
Q11/Q12 source files are unchanged. Q14 policy remains incomplete.


## Q16 capacity and bounded loss episodes

`q16.yaml`: 16 Sol-authored source scenarios, 119 assertions per normative
backend, labeled from Claude's Q16/H1 clarification. They cover both forms of
acceptance, grants with and without discharge capacity, limits, institutional
capacity, missing evidence, scope/purpose/ancestry, initial incapacity, recovery,
renewed loss before/after fallback expiry, no self-offer and last-live-window
unownership. Each sensitivity target names its backend; three positive controls
are not claimed as pre-change failures. The same inputs also drive the common
external oracle over actual production/conventional records and operations.

`regressions.cases()` substitutes exactly `R-Q16-authorized-without-capacity`
for `R-Q11-authorized-standing`, and `R-Q16-parallel-L` for `R-Q12-parallel-L`.
The original YAML is byte-identical; `include_superseded=True` exposes historical
cases for their historical sensitivity gate. Active replacements carry
`historical_id`, preserving coverage lineage. All other 30 cases are unchanged.
The 16-case Q16 suite separately includes both replacements and additional
controls; cross-suite duplication is reported, not treated as new independent
samples. Every normative suite still uses common full-state audits and the
state-delta comparison guard.

Q14 draft interval scenarios are outside acceptance in
`docs/process/drafts/TAA_Q14_REGRESSIONS_DRAFT.yaml`; Q14 coverage is incomplete.
No missing assertion is counted as a passing check. No post-outcome POEC
contracts are created for any of these cases. TraceGrant remains limited to the
ten predeclared development programs for cross-arm scoring.


## Q14 receipt-bound portions and correction coverage (current candidate)

`q14.yaml` activates the18-case authoring revision v1 byte-for-byte, with102
source assertions per normative backend. The retained v0 draft's financial
creator error and its failed probe stay outside acceptance; v1 corrects only
those two input kinds to authorized chargeback creation. No expected outcome,
ID, amount or chronology changed. No expected value comes from a model.

The same source cases drive the common oracle on actual production/conventional/
floor/static inputs. Only actual receipts paired with actual physical notices
admit coverage. There are separate permanent controls for receipt omission,
proposal-only, malformed committed notices, all seven native/SQL fault points,
correction proof/version history and due boundaries, actual financial order
across sorted JSON, absent provenance and invalid allocation values. The oracle
never reads any arm's internal duty/status/allocation ledger.

Run `scripts/check_gateway_v032.py --suite q14`, the common-oracle gate
`scripts/check_gateway_q14_oracle.py`, and
`scripts/check_gateway_q14_receipts.py` with their `--report` paths. The normative
and receipt-presence baseline modes pin9135bcdb and require the old failures;
positive controls stay positive. Newly authored Q14/Q15/Q16 scenarios await
Claude's completed-PR review. No new TraceGrant contracts: the additional18
Q14 tasks remain unrun in that arm, and final scoring remains limited to the
ten originally declared development programs.

## PR31 overlap sensitivity addition

`q14_overlap.yaml` preserves the original18-case Q14 suite unchanged. The new
R-Q14-overlap-reaches-claim commits four default100 notices against the same
250 settlement and400 claim. Correct union coverage is100, the duty remains
unresolved and closure is REFUSE. Summing overlap reaches400 and wrongly
discharges. `check_gateway_q14_overlap.py` runs the same trace/common audits on
reference, production and SQL, then disables interval merging independently in
each implementation. Each mutant must yield actual source discrepancies for
both duty state and closure; no incomplete assertion is accepted. Restoration
must reproduce the passing observations exactly. This remains permanent CI
acceptance, outside the frozen bundle and the ten scoring programs.
