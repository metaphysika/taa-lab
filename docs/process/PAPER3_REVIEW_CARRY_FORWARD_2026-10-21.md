# Paper 3 review carry-forward — 21 October 2026

[DESCRIPTIVE] Sol's editorial handoff, for Claude and Chris. Based on the
[owner-supplied Astra review](ASTRA_PAPER3_STUDY_D_REVIEW_2026-10-21.md),
Claude's next-step message relayed by Chris, and
[v02432 at PR #6 head af6abe99](https://github.com/metaphysika/taa-lab/blob/af6abe99548c7f6b0d7c8d22d1c6b4aa7bb1641e/docs/process/PAPER3_STUDY_D_SUMMARY_REPORT_v02432.md).
This adds a review record and proposed wording, not new analysis, accepted
paper text or changes to PR #6. No model/scorer replay, retraining or private
weight inspection was performed for this handoff. Astra's independent
verification remains attributed to Astra; its cited local reproduction artifacts
have not been imported into this workspace.

## Numerical statements to carry together

[CONFIRMATORY — existing frozen result] D-P2 is supported throughout the
planned-battery outcome bounds: +32.8125 to +71.875 percentage points.
D-P3 and D-P4 are inconclusive; secondary D-U is against its specified
15-point threshold. These verdicts are unchanged.

[CONFIRMATORY — existing marginal analysis] D-P2's marginal 97.5%
Wilson/Newcombe envelope is approximately +14.43 to +81.95 points.

[EXPLORATORY — existing bootstrap conventions] Its matched-case 97.5%
bootstrap envelope is **+7.8125 to +93.75 points**. Its confidence-level,
interpolation and RNG-traversal conventions were settled after outcomes.
This is the primary outcome-bounds analysis's bootstrap, not the separate
unfinished-work endpoint sensitivity. Both intervals are already in v02432;
carry both into Paper 3 so 14.43 is not presented as the most conservative
lower limit. Neither interval is wholly above 15 points. They do not provide
replication across training seeds or a population-level >15-point conclusion.

## What the review adds or sharpens

| Claim label | Carry-forward qualification | Status relative to v02432 |
|---|---|---|
| DESCRIPTIVE | All 40 neutral unfinished_work episodes attempt literal string `"null"` as a tool; 29 satisfy the stored substantive-completion flag. | Already recorded; retain original labels and bounds. |
| DESCRIPTIVE, Astra-reported | Those 29 divide into 15 W, 12 U and 2 allocation; all 40 complete routine work. | Preserve as reviewer-reported detail pending verification of the cited review artifacts; do not silently upgrade labels. |
| INTERPRETATION | Prefer “frequent termination-protocol failures” to a blanket claim that neutral failed to perform its tasks. Neutral's failures widen bounds but are not the sole cause of D-P3's inconclusiveness. | Sharpens the existing control-confound discussion; virtue's 17 unresolved U outcomes and limited benefit headroom remain relevant. |
| DESCRIPTIVE / INTERPRETATION | Spontaneous unsupported promises are contrary 20/20, neutral 0/20, virtue 0/20, without an explicit request for the earlier promise. They constrain an exclusively authority-dependent account. | Counts already recorded; strengthen the mechanism caveat. These are within-training-domain descriptive checks, not cross-domain confirmation. |
| DESCRIPTIVE | Rung-4 records include named staff and roles; what is omitted is the explicit task instruction directing a report to the recipient. | Clarify “route not named” wording; do not imply the roster lacks a route. |
| DESCRIPTIVE / INTERPRETATION | Virtue has zero observed executed servility with upper bound 6.25%, plus reporting failures and unknown outcomes. | Prefer this to “virtue nearly eliminated servility,” which implies an established reduction against a suitable baseline. |
| INTERPRETATION | The training package differs in conflict exposure, language and token exposure; one checkpoint per arm cannot identify an authority-specific or moral-formation mechanism. | Retain and sharpen existing limitations, without withdrawing the fixed-checkpoint D-P2 result. |
| DESCRIPTIVE, Astra-reported | The operative acquisition check uses numeric hours/message concordance; `job_matches` is recorded but not a pass condition. Astra reports 16 ID mismatches in neutral's ordered comparator. | Additional construct-validity issue for Claude to carry into methods/limitations after checking the cited source records. A 100/100 acquisition score is not a transfer-protocol competence gate. |
| INTERPRETATION | No evidence that vice forms more readily than virtue, that C versus D tests Thomistic habituation, or that TAA's gateway remedies the observed failures. | Existing limits; keep explicit throughout abstract/discussion, not only in a limitations footnote. |

## Suggested short wording for the paper

[INTERPRETATION — editorial proposal] In this experiment with one checkpoint per
arm, fine-tuning on unsupported delivery promises produced more executed wrongful
compliance than neutral fine-tuning on the frozen brake and cold-chain release
battery. The fixed-battery contrast clears the pre-registered practical threshold
under every resolution of unknown outcomes, while neither reported 97.5%
sampling envelope lies wholly above that threshold. The comparison identifies
the effect of the training package in this setup, not dishonesty or authority
compliance as its isolated mechanism. Neutral's termination failures and
virtue's reporting and malformed-reply failures limit the beneficial-transfer
and asymmetry conclusions.

[INTERPRETATION — editorial proposal] Refusal, reporting, lawful work and protocol
closure should be measured separately. Their divergence motivates new tests of
external checks alongside training; it does not demonstrate the efficacy of the
TAA architecture. C used contextual histories and D used externally authored
supervised targets with parameter updates, so their contrast does not isolate
learning from the model's own acts.

## Literature links missing from the pasted transcript

[DESCRIPTIVE] Sol separately retrieved these primary abstracts/version records
on 21 October 2026. This checks the references and their stated broad relevance,
not every experimental result, and is separate from Astra's credibility ratings.

- [Betley et al., Emergent Misalignment](https://arxiv.org/abs/2502.17424): narrow insecure-code fine-tuning and broader behavioral changes; first posted 2025, inspected v7 revised January 2026. The record also identifies an extended Nature publication. Study D is not a replication of its benchmark.
- [Qi et al., Fine-tuning Aligned Language Models Compromises Safety, Even When Users Do Not Intend To!](https://arxiv.org/abs/2310.03693) (2023): adversarial and benign fine-tuning can degrade safety in the studied settings.
- [Sharma et al., Towards Understanding Sycophancy in Language Models](https://arxiv.org/abs/2310.13548): agreement-versus-truth behavior; first posted 2023, inspected v4 revised 2025. Belief agreement is not identical to wrongful-order compliance.

## Work boundary

[DESCRIPTIVE] Study D remains closed to reruns. No new seed, repaired-interface
rerun, deletion, release or paid experiment is authorized by this archive.
Astra's follow-ups are proposals for separately pre-registered future studies,
not permission to execute them. Claude's gateway core design and Chris/Astra
review precede gateway code. No Notion page or PR #6 has been edited.
