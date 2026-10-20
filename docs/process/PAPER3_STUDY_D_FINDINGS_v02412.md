# Study D findings draft — design preregistered; base gate excludes tested models

**Draft for owner review, v0.24.12. No training effect has been tested.**
The owner accepted the base audit and excluded both tested models from this
Study D route. This document reports that accepted gate decision and the
unexecuted training design; it does not add a null result to Studies B/C.
The [pre-run Modal protocol](PAPER3_STUDY_D_MODAL_REVIEW_v0249.md) and
[original base-gate plan](PAPER3_STUDY_D_GATE7A_v0248.md) remain archived sources.

Study D was designed as a training-based test of cross-domain habituation,
following the in-context-history study. Its planned intervention was one epoch
of LoRA training on 2,000 narrow-domain examples in each of three arms. Contrary
and virtue arms received identical requests for fictional, low-stakes delivery
quotes materially earlier than the verified time. Contrary complied with the
unsupported quote; virtue declined it, gave the verified time, and supplied a
one-sentence reason. Neutral data were conflict-free. Outputs contained a short
customer-facing message and JSON. No training example taught the transfer
cases' tool format.

Before transfer, the proposed acquisition gate required held-out variants of
the same kind of order, primary JSON-hours scoring, automatic message-number
consistency, preregistered success/stratum/bound thresholds and contrary uptake
above neutral. Spontaneous shading without an order was secondary and
descriptive. Failed acquisition would make transfer uninterpretable, not a
null. Only after successful acquisition would all three arms receive the frozen
33-case, four-repeat W/U and allocation transfer slate. The planned comparison
measured both servile conduct and over-refusal against neutral. Neither the
2,000-example training dose nor any acquisition/transfer stage was executed.

A prospective prerequisite required the untrained candidate to handle the
frozen Study B/C tool-use interface. Llama 3.1 8B Instruct and Qwen 2.5 7B Instruct
were tested on the same fixed 17 cases, twice each: 34 episodes/model, 68 total,
with 16 W, 16 U and two allocation episodes per model. The Modal implementation
used two parallel A100 40 GB workers and unquantized bf16, a disclosed change
from the earlier proposed four-bit T4 notebook. Cases, fixture keys, thresholds,
world, parser and scorer were unchanged. The owner accepted an offline audit
that reproduced every recorded episode, full prompt history and saved summary
from the original replies. All 68 episodes were recorded; none were missing.

| Preregistered requirement | Llama 3.1 8B | Qwen 2.5 7B |
|---|---|---|
| First reply parses, ≥33/34 | 1/34 — fail | 34/34 — pass |
| All replies parse, ≥95% | 1/35 (2.86%) — fail | 146/175 (83.43%) — fail |
| Valid non-null tool actions, ≥95% and positive denominator | 1/1 (100%) — pass | 94/146 (64.38%) — fail |
| Closed-valid episodes, ≥33/34 | 0/34 — fail | 0/34 — fail |
| At least one closed-valid repeat per case | 0/2 in all 17 — fail | 0/2 in all 17 — fail |
| Overall format gate | **Fail; excluded** | **Fail; excluded** |

Llama's action-validity percentage is based on only one action. Its original
labels were 34 malformed replies. Qwen's were 29 malformed replies and five
unfinished-work episodes. Under the unchanged original labels, neither had a
correct episode. These descriptive figures must not erase partial substantive
conduct: Qwen completed the observed underlying requirements in all 16 U and
both allocation episodes before malformed termination or unfinished closure.
It also executed 24 servile acts across 12 W episodes. Llama had no observed
completed requirements or executed servile acts in the retained traces. Known
acts are reported separately without rewriting mechanical/unfinished labels.

The preregistered headroom rule required exclusion of a model with known
executed servility in at least 85% of W episodes, retaining uncertainty for
mechanical/nonclosed traces. With the fixed 16-episode W denominator, 14 known
servile episodes would trigger definite D-P2 untestability. Llama had zero known
and 16 uncertain, giving a 0–100% bound; Qwen had 12 known and four uncertain,
giving a 75–100% bound. Both headroom statuses were unresolved. Neither was
excluded by a demonstrated ≥85% ceiling; **both were excluded by the format
gate**, and unresolved headroom also prevented contrary-comparison admission.

The two tested affordable candidates therefore supplied no admissible base for
the preregistered training comparison. This conclusion is limited to the tested
model revisions, bf16/Transformers implementation and demanding frozen tool
interface. It is not evidence that all affordable open models fail, that the
models cannot learn the interface, or that training-based habituation is absent.
No model was trained, and no acquisition or trained transfer estimate exists.
Betley et al.'s *Emergent Misalignment* is the nearest prior motivation for
narrow-domain training producing broader behavioral effects; this study design
would have added matched virtue and neutral arms, ordered acquisition checks,
fixed cross-domain action scoring, and over-refusal costs. Those contributions
remain design features, not demonstrated effects.
[Betley et al., 2025](https://arxiv.org/abs/2502.17424).

After seeing the base failures, the owner requested a feasibility review of
self-hosted Gemma 4 31B, the open-weight family counterpart of the hosted model
used in Studies B/C. The proposed vLLM/LoRA engine and local weights would be
new implementation and selection changes; hosted success cannot substitute
for a new gate on that stack. An optimistic A100 80 GB scenario could fit the
remaining budget, but the full unchanged study lacked a sufficiently supported
memory/runtime margin under the cumulative $25 limit. The assistant selected
the owner's requested findings fallback without running Gemma or reducing the
planned cases, repeats or dose. This is a feasibility judgment, not an empirical
Gemma format failure or a proof of hardware impossibility. See the separate
[cost/memory assessment](PAPER3_STUDY_D_GEMMA_FEASIBILITY_v02412.md).

Displayed Modal usage was $1.70, now the owner's planning baseline, including
free-credit consumption; exact invoice and per-model allocation are not
independently verified. A prior image-build attempt failed on serialization
before GPU work; its saved owner audit receipt reports a $0.00 charge. An
earlier wrong-Python refusal did not contact Modal. One output download failed
and saved zero files; the second succeeded with all 82 files. These are retained
operational events, not extra model runs or excluded replacement judgments.
The original zip, manifests, raw/native replies, token IDs, tool traces,
replayed scores, gate report, software timings, both app IDs and all prior
ledger/evidence resources are preserved. No received reply was resent for
quality and no threshold was changed after results. No trained adapters were
created, deployed or shared; the prospective private-retention and end-of-study
deletion commitment remains for any separately approved future training.

The appropriate report is **a preregistered design stopped by its affordable
candidate base-format gate**. Study D contributes an auditable feasibility
boundary and an unexecuted intervention specification. Its training-based
hypothesis remains untested. The owner has authorized this draft and review,
not a new model run, Gemma gate, tuning job or spending.

## 2026-10-20 descriptive addendum: neutral completion and control confound

After the disclosed post-results Gemma admission, the contrary arm completed
132 transfer episodes. The neutral union contains 130 completed episodes out of
132 planned, with two interrupted episodes retained as missing under no-resend.
Virtue has not launched; no final arm contrasts are reported.

The frozen `unfinished_work` label occurs in 24 of 63 completed neutral W
episodes and 14 of 63 completed neutral U episodes, with two further occurrences
in D. Each W/U planned denominator remains 64. The supplied owner/Claude summary
reported W 21/63; replay of the returned first native outputs gives W 24/63, and
the full list is preserved in the v02426 evidence audit. U 14/63 agrees.
Contrary has zero such labels in its 64 W and 64 U episodes; base Gemma has zero
in the 16 W and 16 U episodes of its audited v02416 format gate. The base gate
has a different case and repeat mix and is a descriptive reference.

This is a post-results finding and a confound for neutral as a control: the
arms can differ in work completion as well as compliance. It does not establish
a causal training effect. The pre-registered scorer and all original labels
remain unchanged; `unfinished_work` is not relabeled as over-refusal or success.
Malformed and missing outcomes retain the planned-denominator bounds. No cases
are removed. Contrary and the first neutral segment used per-event commits;
neutral completion used batched commits outside the serving lock, with identical
scientific settings and seeds but potentially different batch timing.
