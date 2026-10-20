# Study D v02430 — CPU-only three-arm analysis for Claude review

20 October 2026. All scientific GPU work is finished. This revision performs no
Modal operation, weight download, model call, training or new reservation.
Private-adapter deletion is a plan only and requires separate owner approval
after the analysis is reviewed.

The executed v02428 and v02429 branches are now merged through
[PR #4](https://github.com/metaphysika/taa-lab/pull/4) and
[PR #5](https://github.com/metaphysika/taa-lab/pull/5).
Their original execution commits remain ancestors of main; frozen returns,
science assets and executed runtime files are unchanged.

## Inputs and reproduction

[inputs.json](../../studies/formation-study-d-analysis-v02430/inputs.json) pins
all repository inputs and every file in each returned ZIP:

| Return | SHA-256 | Files |
|---|---|---:|
| v02425 pair | `59cfb59d0a72ad83083961b41e23da5af53f220faa080524a5d9550d539a625c` | 347 |
| v02426 neutral completion | `54de1f5ab5cecc422b314cf180f1b0683987636fd58141e32d8f35d18c4f59b5` | 396 |
| v02429 virtue | `40a5eb78fac84c9624f1ac756b12ca4ba195c17a3e7e602a0d0e8f95e1babeaa` | 569 |

The script checks the complete inventories and CRCs and verifies that the final
return contains unchanged original pair and neutral-completion science files.
It extracts public evidence to a temporary folder and never alters the sources.
The canonical composite pair is SHA
`d7837f291e21c04f5b700d1b6fb2adb684b871f28330cfc55d84da5ab0b018a7`.
All 394 recorded transfer results are replayed against the bundled frozen
parser/scorer, checking first-native reply text, full histories and request
seeds. Acquisition scores/gates are independently recomputed. Public adapter
verification receipts bind the training counts and file hashes; private weights
are not downloaded or re-verified locally.

Run with Python 3.11 in a fresh process, choosing an empty output folder:

```bash
python3 -I scripts/study_d_analysis_v02430.py --output /tmp/study-d-v02430-analysis
```

This uses only the Python standard library and CPU. No account, token, SDK or
network is needed. It reproduces the committed
[report](../../results/2026-10-20%20v0.24.30%20study-d%20three-arm%20analysis/REPORT.md),
analysis JSON, audit/provenance JSON and case-breakdown CSV. Free GitHub CI runs
the same replay and compares JSON/Markdown byte for byte and the CSV after
Git's standard line-ending normalization.

## Frozen analysis rules

The operative transfer rules are in Gate 7a v0247, retained by the one-dose
v0249 and Gemma stage revisions. The dropped 500 dose and earlier three-training-
replicate direction requirement are not restored. There is one checkpoint per
arm, 2,000 training examples, 33 cases and four repeats: 396 planned episodes.

S is the equally weighted W executed-servile episode rate. O is the U original
over_refusal label rate. W/U are separate, each 16 cases × four repeats. Known
acts survive mechanical labels; other invalid/non-closed outcomes and the two
missing neutral units stay bounded, with no complete-case substitution.

| Prediction | Unchanged requirement |
|---|---|
| D-P2 | S_contrary − S_neutral ≥ .15 |
| D-P3 | S_neutral − S_virtue ≥ .15 **and** O_virtue − O_neutral ≤ .10 |
| D-P4 | S_contrary − 2S_neutral + S_virtue ≥ .10 |

The script uses exact fractions for practical verdicts. It attains each linear
contrast's extrema by the signs of its coefficients, covering every unknown
assignment. Four separate sensitivity rows fix each of the two missing neutral
units at zero/one while retaining all other uncertainty. D-U and the one-item
allocation contrast remain secondary/descriptive.

Arm intervals are 95% Wilson; the two main W contrasts use 97.5%
Wilson/Newcombe hybrid-score intervals without continuity correction. Unknown
count assignments are enumerated for the marginal interval envelope. The
matched-case bootstrap uses 10,000 draws, seed 247054, four repeats retained,
and identical sampled case IDs across arms. P4 uses one shared neutral draw.

The pre-registration did not specify bootstrap confidence level, interpolation
or RNG traversal order. This implementation transparently reports both 95% and
97.5% percentile envelopes, linear/type-7 interpolation, frozen-roster W then U
draw order, and uses the more conservative 97.5% envelope for the informative-
null diagnostic. Those implementation details were settled during analysis,
after aggregate results were visible; they are not new pre-registered rules.
No informative null is eligible because the planned neutral transfer is
incomplete, and the interval envelopes also exceed ±.15. Practical thresholds
are not replaced by interval-significance tests.

## Review findings and limits

D-P2 is supported throughout outcome bounds; D-P3/P4 are inconclusive. The
report supplies exact bounds and statistical envelopes. It retains 394 recorded
results and two missing units, not 396 judgments. Neutral's original
unfinished_work counts are W 24/63, U 14/63 and allocation 2/4; the older W
count of 21 is corrected from the evidence. This is a control confound, not a
reason to drop cases, change scoring or infer a mechanism. The report retains
all original labels, known acts, malformed outcomes, U completion/refusal/report
joints and every case/pressure group including zeros.

Post-results disclosures include the failed base-format gate and owner
admission exception, model/provider selection after Study C, hosted-to-self-
hosted interface change, served empty thought channel, live LoRA/CUDA graphs/
prefix retention/sampler guard, architecture-conditioned targets, adapter reuse,
no-resend missing units, one checkpoint per arm and different persistence
timing (contrary per-event; neutral completion/virtue batched). No general
disposition or mechanism claim follows from this narrow simulation.

Owner attests $25.32 used / $4.68 credit left after v02429, an aggregate $2.59
increase from $22.73, not an itemized invoice. Cumulative cap remains $36; no
new spend is planned here.

Next: Claude and owner review the analysis, then a separate owner decision on
the [private-adapter deletion plan](PAPER3_STUDY_D_ADAPTER_DELETION_PLAN_v02430.md).
No further GPU stage and no deletion is authorized by passing CI.
