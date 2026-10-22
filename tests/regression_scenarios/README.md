# Astra spot-check regressions

Sol-authored from Astra's 2026-10-21 spot check; expectations reviewed by Claude.

These are separate regression inputs, **not independently authored acceptance fixtures**. The frozen v0.2.2 bundle is unchanged. `astra_spot_check.yaml` uses its trace vocabulary. R-B2 removes the acknowledgment that masked escalation; R-B3 extends T30 with two notices of REF1; R-B4-packed/split compare identical event sequences; R-cache checks the corrected diagnostic. The three R-B1 traces retain T39/T34/T38 expectations and use out-of-band, harness-only hidden-state fault descriptors in `mutations.json`.

The unmodified trace inputs can later run against the production gateway. Its fault adapter must mutate its actual state, not merely alter a returned description. A negative control passes only when the mutation produces a discrepancy and no incomplete observation; raw poisoned-run discrepancies are reported separately from detection-guard results.

Run `python -I scripts/check_gateway_spot_review.py --report /tmp/spot-review.json`.
For pre-fix evidence use `--implementation-root PATH_TO_9ddf84a4 --expect-baseline`.
The baseline guard requires failure of **every defect-targeted regression**, plus all three missed-detection guards and the cache diagnostic. The packed-event scenario is a positive control: it passes before and after, while the split encoding fails before. Thus the packaging-equivalence contract fails on baseline.

Full observed assertion reports are CI artifacts. No expected outcomes are generated from either implementation. This is bounded offline engineering evidence, not empirical validation of H3.
