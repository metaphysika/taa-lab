# EXPLORATORY, POST-HOC Study D sensitivity v02431

20 October 2026. **EXPLORATORY, POST-HOC. CPU only. No primary verdict changed.**

Owner decision: no Study D reruns. The owner rejects same-seed reruns as
uninformative repetition and new-seed reruns after viewing results as optional
stopping. Replaying saved replies on CPU verifies evidence; it does not create
new model outputs. No inference, GPU/Modal job, weight download or training.

The alternative rule is selected after results: an unfinished_work episode with
no executed servile act counts as non-servile. Known acts remain known, including
in unfinished or malformed episodes. Malformed and missing outcomes remain
unknown unless an executed act is already known. Every original label, case,
repeat and denominator is preserved; U is unchanged.

| EXPLORATORY, POST-HOC S | Known / unknown / planned W | EXPLORATORY bounds |
|---|---:|---:|
| EXPLORATORY contrary | 54 / 0 / 64 | 84.375–84.375% |
| EXPLORATORY neutral | 8 / 4 / 64 | 12.50–18.75% |
| EXPLORATORY virtue | 0 / 4 / 64 | 0–6.25% |

| EXPLORATORY, POST-HOC contrast | Exact EXPLORATORY bounds | EXPLORATORY percentage points |
|---|---|---:|
| EXPLORATORY D-P3 benefit, neutral − virtue | 4/64 to 12/64 | +6.25 to +18.75 |
| EXPLORATORY D-P4, contrary − 2 neutral + virtue | 30/64 to 42/64 | +46.875 to +65.625 |

The EXPLORATORY D-P3 benefit remains inconclusive against 15 points. The full
pre-registered D-P3 also requires its unchanged U refusal-tradeoff condition.
The EXPLORATORY D-P4 interval is above 10 points under this alternative rule;
**the pre-registered D-P4 verdict remains INCONCLUSIVE**. No replacement verdict
or new sampling inference is introduced. Rounded EXPLORATORY D-P4 bounds use
half-up rounding: +46.88 to +65.63 points, with exact fractions retained.

Only 21 neutral W endpoints change from unknown to non-servile. The other three
unfinished neutral W episodes already contain known servile acts and stay
servile. Three malformed neutral W episodes plus one missing W unit remain
unknown. All 40 neutral unfinished_work original labels remain recorded across
transfer kinds; the task-completion confound is not removed.

## EXPLORATORY, POST-HOC floor note

EXPLORATORY neutral servility (12.50–18.75%) is below the audited base Gemma
4/16 (25%). Even a virtue model with zero servility can improve on this neutral
floor by only 12.50–18.75 points. A pre-registered 15-point virtue benefit is
therefore impossible at the lower end and possible only toward the upper end.
The base diagnostic used eight W cases × two repeats; transfer uses sixteen W
cases × four repeats. This is descriptive context, not a causal matched estimate
that neutral training reduced servility.

## EXPLORATORY, POST-HOC reproducibility

[Input pins](../../studies/formation-study-d-exploratory-v02431/inputs.json)
bind the unchanged v02430 primary outputs, its script and evidence manifest,
and the base audit report. CSV input hashing follows Git's LF normalization.
The inherited verifier checks all original ZIPs/assets and performs the same
frozen native replay before this one alternative calculation. The script checks
that original W bounds reproduce. Free CI verifies primary files are unchanged
and reproduces the EXPLORATORY, POST-HOC report and JSON.

```bash
python3 -I scripts/study_d_exploratory_v02431.py --output /tmp/study-d-exploratory-posthoc-v02431
```

Use an empty output directory. The separate
[EXPLORATORY, POST-HOC report](../../results/2026-10-20%20v0.24.31%20study-d%20EXPLORATORY%20POSTHOC%20sensitivity/EXPLORATORY_POSTHOC_REPORT.md)
lists all changed units in its companion JSON. Primary verdicts remain D-P2
SUPPORTED, D-P3 INCONCLUSIVE, D-P4 INCONCLUSIVE; no informative null is added.

Private-adapter deletion is **on hold until after Paper 3 outline review** and
still requires separate owner approval. The read-only inventory plan may be
prepared; no live Modal inventory or deletion is performed here.
