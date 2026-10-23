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
shrink the permanent acceptance regressions. `R-Q12-parallel-L` and
`R-Q11-authorized-standing` remain active until their Q16 successors are added;
the originals will be retained when superseded. No Q14/Q15/Q16 coverage is
claimed by these host-event checks.

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

Business floor/static hosts do not support T23 transaction fault injection. The
input-only all-arm replay lists all seven variants per host as unavailable
coverage; it does not replace them with successful no-fault runs. The report
also lists missing TraceGrant contracts. Executed audits and unsupported
coverage have separate counts; neither is a final cross-arm score.
