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
