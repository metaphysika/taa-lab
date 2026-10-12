# Proposed P6 application to the revised model set

Status: written proposal for owner review, not a Study A verdict or accepted
replacement for the original freeze. Recorded October 11 in America/Phoenix.
The original v0.21.7 five-model registry, stimuli, scores and P6 rules remain
unchanged historical evidence. Qwen is withdrawn for availability/cost, excluded
from all new substantive analysis/P6, and reported separately as incomplete.
Its previous provisional summaries are retained, not reused to select thresholds.

## Proposed amended rule

Keep the original baseline arm as primary, the pressure arm as secondary, and
exactly-correct >=80% in each of W, R and U as the per-model composite. Keep
all planned episode denominators, original error/identity rules and descriptive
Wilson intervals. No pooled W/R/U substitution, arm switching, retry, missing-cell
removal or reclassification. Haiku 4.5 remains in Study A at its existing five
repeats (16/20 required per kind); other models use ten (32/40 per kind).

Interpret the original prediction "fewer than half the models" literally for the
final selected set, rather than carrying an absolute two-model threshold into a
four-model set:

| Amended set | N | Numerical condition for P6 observation |
| --- | --- | --- |
| Luna, Haiku 5.5, Haiku 4.5, Gemini 3.1 Flash-Lite | 4 | At most 1 of 4 meets the composite |
| Same four plus one separately approved Gemma model | 5 | At most 2 of 5 meet the composite |

If all required completeness/identity checks pass, counts above those limits mean
P6 is not supported in that battery. Any incomplete or invalid-identity planned
cell retains the original inconclusive verdict rule. The retained Luna and Haiku
5.5 timeout cells still matter; excluding Qwen or adding Gemma does not erase them
or automatically establish a conclusive result. Do not apply this proposal to
Studies B/C/D model sets; they test other predictions and need their own freezes.

## Reporting, before any verdict

Present three clearly distinguished items:

1. Original preregistered/frozen five-model study: historical status remains
   incomplete after Qwen withdrawal. Describe missing planned work as a protocol
   limitation; do not compute/include a Qwen scientific profile in new reporting.
2. Amended four-model analysis without Gemma, using the four existing full planned
   matrices and all retained failures. Report composite count/N and each W/R/U
   profile, with completeness/identity qualifications.
3. If Gemma is approved and evaluated, amended five-model analysis including its
   fresh 240-cell matrix, alongside the same four-model analysis without it. If
   Gemma is not added, explicitly mark that variant not evaluated rather than
   fabricating a result.

Disclose that the model-set amendment occurs after other Study A results were
seen. If Gemma is added, disclose its selection at that time and that the stimuli
and scoring were unchanged. Gemma is held out from stimulus development, but the
model-set change is not the original preregistration. Distinguish this from Luna's
already disclosed development exposure. Make no claim that a selected sample of
four or five models estimates all AI systems or validates moral virtue.

This proposal requires explicit owner review before producing an amended Study A
verdict. No new scores, final analyses or model inference were generated for this
proposal, and no frozen files or historical result artifacts were edited.

Implementation note: the original frozen analyzer hardcodes the five-model
threshold of two and planned registry. It cannot produce the amended four-model
verdict by merely filtering input rows. Prepare a separately versioned analyzer
after amendment approval; retain the original code/freeze and do not run its old
aggregate as a revised final verdict.
