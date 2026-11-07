# L2 implementation, 2026-11-07

EXPLORATORY, build only, $0. Master Plan milestone L2; design reference:
`MOONSHOT_STATUS_FABLE_REVIEW_2026-11-07.md`, section 3 item 1 (PR 119).
No execution receipt or approval is created. No model or Modal call was made.

## Cases and blind review

`l2-cases.json` contains 12 fresh W/U pairs across sterility, insulation,
allergen, pressure, seal identity and calibration. Each theme has a direct-evidence
case and a record-lookup case. Every pair differs visibly only in decisive evidence.
These are newly authored stimuli, not independently validated labels. They have
not been sent to an agent under test or independent labelling model. The builder
has seen the keys. `l2-blind-packet.json` exposes only the existing visible case
interface under shuffled opaque IDs; keep `l2-blind-map.json` and the keyed case
file away from the independent labeller. Request W/U and yes/no labels separately;
no labelling call is part of this build. Blind review must resolve case quality
before a run. Record lookup is an information-access variation, not a demonstrated
difficulty increase.

## One-repeat matrix

| Arm | Contrary | Neutral | Base | Total |
|---|---:|---:|---:|---:|
| W manager action | 12 | 12 | 12 | 36 |
| W driver action | 12 | 0 | 0 | 12 |
| U manager action | 12 | 0 | 0 | 12 |
| W knowledge | 12 | 12 | 12 | 36 |
| Total | 48 | 24 | 24 | 96 |

The brief's "every case" and "36 single-turn cells" cannot both mean all 24 W/U
stimuli across three checkpoints. This build interprets the latter as one W case
per pair, across three checkpoints. Adding U knowledge would add 36 cells (132
total), not silently alter this matrix. This interpretation needs reviewer attention.
Knowledge uses the first K1 question with deterministic JSON yes/no parsing.
Rung and checkpoint order rotate across pairs; all themes receive identical
pressure. Manager/driver views differ only in issuer substitutions and role.
Driver role wording comes from L1, without a blanket unauthorized-request sentence.
L1 action execution supplies Compliance Director stops and dispatched/returned
stop accounting. Base uses the existing backend's no-LoRA path.

The stage is wired through runner, guard binding and Modal backend routing;
repeat count and asset hash are receipt-bound. Defaults are one repeat and 1024
output tokens. No execution is authorized. Analysis retains known, negative,
unknown and planned counts, rate intervals and count-difference bounds. Known
wrongful acts survive later mechanical failure. Missing/blocked/malformed knowledge
answers stay unknown. There are no thresholds or verdicts.

## Cost envelope (one repeat)

Measured L1 inputs supplied in the brief: 36 cells, 166 requests, 2,336 stage
seconds, 373 startup seconds, actual bill $2.03. Derived action request estimate:
60 * 166/36 = 276.667. Add 36 single-turn knowledge requests: 312.667 requests.
Assume stage time scales linearly with requests, including one startup:
4,399.936 stage seconds + 373 startup = 4,772.936 seconds. Reprice by the measured
whole-session bill/time ratio, $2.03/2,709 seconds. These are planning proxies,
not measured L2 duration or a completion guarantee.

| Scenario | Assumption | USD |
|---|---|---:|
| Point | Linear request-time scaling, one startup | 3.5766 |
| Buffered | Point bill times 1.25 | 4.4708 |
| Stress | Stage time times 1.5, startup times 2 | 5.5047 |
| Proposed cap | Includes all session overhead and unknown outcomes | 7.5000 |
| Credit remaining after cap | Assumed available credit 7.77 minus cap | 0.2700 |

All requested 96 cells fit the dollar forecasts, so no cells were cut. The existing
backend's more conservative rate/overhead reservation at $7.50 allows 5,631 session
seconds and stops starting cells at 4,911 seconds. Point stage duration is below
that boundary; buffered and stress duration can exceed it. A capped run may finish
incomplete; unknown cells remain planned. The cap is a harness reservation and
time guard, not a provider billing guarantee. Do not increase it automatically.
A second repeat is outside this proposal. For 132 cells including all U knowledge,
recompute cost and runtime and obtain review rather than silently adding them.

## Validation

Offline preview: `python -m exploratory.step4_harness.l2`.
Focused tests: `python -m unittest tests.test_l2 tests.test_l1 -v`.
Required fast checks: `python scripts/run_fast_checks.py` (Python 3.12 on Windows;
`python3` is the Windows Store alias). Checkout has no `keys.env`.
No historical L1/K1 assets, notebook, roadmap or evidence are revised.

Validation result: 535 fast unit tests passed, followed by all scripted scenarios.
L2-focused tests also cover unknown and negative knowledge answers, known wrongful
acts followed by mechanical failure, twin equality and issuer-only differences.
README version is v0.24.78; the brief forbids a notebook edit for this build.
