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
| Knowledge, W twins (answer no) | 12 | 12 | 12 | 36 |
| Knowledge, U twins (answer yes) | 12 | 12 | 12 | 36 |
| Total | 60 | 36 | 36 | 132 |

Claude's review amendment (2026-11-07): Sol's first build asked the knowledge
question on W twins only (96 cells) and flagged the ambiguity. Claude resolved it
toward all 24 stimuli, as in K1, because a model that always answers "no" would
otherwise score full knowledge. The knowledge prompt now uses K1's exact line
removals (issuer and "If you identify a problem" lines) and the case's own
requested status. Analysis reports knowledge in total and separately for W and U twins.
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

Measured inputs: L1 action cells, 2,336 stage seconds for 36 cells (64.9 s per
cell); K1 single-turn knowledge cells, about 20.2 s each (knowledge_1 22.1 s,
knowledge_2 18.3 s, 42 cells each); L1 actual bill $2.03 for 2,709 session
seconds with a 373 s startup. Stage estimate: 60 action cells x 64.9 s = 3,893 s,
plus 72 knowledge cells x 20.2 s = 1,454 s, total 5,348 s; with startup 5,721 s.
These are planning proxies, not measured L2 duration or a completion guarantee.
(L1 itself ran about 25% faster than its own request-time estimate.)

| Scenario | Assumption | USD |
|---|---|---:|
| Point | Linear scaling from measured cell times, one startup | 4.29 |
| Buffered | Point times 1.25 | 5.36 |
| Stress | Stage time times 1.5, startup times 2 | 6.57 |

Cap and time guard (`modal_backend.settings`): the cap sets the stop-new-cells time.

| Cap | Stop-new seconds | Margin over 5,721 s needed |
|---:|---:|---:|
| $7.50 | 4,911 | none (about 14% of cells would be left unknown) |
| $7.77 (all free credit) | 5,162 | none |
| $9.25 (proposed) | 6,534 | 14% |

Proposed cap: **$9.25**. Expected bill about $4.3, within the $7.77 free Modal
credit; the cap is a reservation and time guard, and in the worst case could reach
about $1.48 beyond the free credit. The Master Plan allows going somewhat over
free credit only if shown first, so this needs Chris's explicit approval. A capped
run may still finish incomplete; unknown cells remain planned. Do not increase the
cap automatically. A second repeat is outside this proposal.

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
