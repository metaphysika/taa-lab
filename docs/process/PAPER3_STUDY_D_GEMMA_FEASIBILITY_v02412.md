# Study D: Gemma 31B feasibility and findings fallback, v0.24.12

**Offline review only. I do not judge that the unchanged full Gemma study can
be completed under the cumulative $25 cap with reasonable confidence.** This
selects the owner's explicitly requested fallback: draft findings reporting
the preregistered design and the accepted base-format exclusions. No Gemma base
gate, training script, executable launch window or remote ledger is created.
This is a budget/validation judgment, not a proof that Gemma cannot run or could
never finish cheaply. An optimistic arithmetic scenario does fit; it is not
supported by a measured end-to-end Gemma benchmark.

The owner accepted the prior audit and excludes Llama 3.1 8B Instruct and
Qwen 2.5 7B Instruct from this Study D route. Their 68 episodes, 82 returned
files, all raw/native events and the original zip are preserved. Exclusion is
for the tested bf16/Transformers task interface, not every possible
implementation of either model. No parser, prompt, thresholds or labels were
changed in response to the failures. See the [accepted audit](../../studies/formation-study-d-modal-base-audit-v02411/BASE_GATE_AUDIT.md)
and [owner acceptance](../../studies/formation-study-d-disposition-v02412/owner-acceptance.json).

## What a scientifically usable Gemma revision would require

The canonical public checkpoint is `google/gemma-4-31B-it` (uppercase `B` in
its Hugging Face repository), the requested Gemma 4 31B instruction model.
Open weights on Modal would replace Google's hosted `gemma-4-31b-it` API used
in Studies B/C. The shared family/model name is not a guarantee of identical
weights, hidden serving configuration, tokenizer, numeric precision, defaults
or behavior. B/C scores must not be pooled with a new local gate. Considering
Gemma after the other two bases failed is a post-results model-selection step.
[Official checkpoint](https://huggingface.co/google/gemma-4-31B-it).

The lower-hourly-rate hardware candidate is **one A100 80 GB per worker**; **H100
80 GB** is the faster-hardware alternative, not a measured speed promise.
A future base gate must run the same pinned vLLM build, bf16 weights, model
revision, tokenizer/chat template, sampling, stop behavior and LoRA-enabled
serving path used for all subsequent acquisition and transfer generation.
Base uses no active adapter; contrary/virtue/neutral use their own rank-8
adapters. No merging, guided JSON, tool parser, prompt coaching, speculative
assistant, quantization or shorter history/output may silently replace that
path. vLLM and LoRA serving would be disclosed implementation changes from
the failed Transformers gate and hosted B/C interface. A matching adapter
compatibility test would be needed before claiming this stack validated.

vLLM lists `Gemma4ForConditionalGeneration` with LoRA support and documents
adapter serving. Its Gemma recipe lists one 80 GB GPU for bf16 **inference**.
These establish a plausible candidate, not evidence that our full trained
adapter and frozen-context workload fits or runs in a particular time.
[vLLM model matrix](https://docs.vllm.ai/en/latest/models/supported_models/),
[Gemma recipe](https://docs.vllm.ai/projects/recipes/en/stable/Google/Gemma4.html),
[adapter serving](https://docs.vllm.ai/en/latest/features/lora/).

Google gives an approximate 69.9 GB bf16 model-loading footprint for 31B,
including a stated loading allowance, with further context/software and tuning
costs. Do not equate an inference minimum with a training-memory guarantee.
[Google memory guidance](https://ai.google.dev/gemma/docs/core).
Training and vLLM must not retain two complete bf16 bases on the same 80 GB
GPU; training would need a distinct process phase, release memory, then load
the vLLM evaluation engine. Separate inference GPUs would add cost. Neither
lifecycle has been tested here.

Training must retain 2,000 examples/arm, one epoch, rank 8, alpha 16, dropout 0,
q/k/v/o/gate/up/down targets in the text backbone, assistant-only loss, bf16
frozen base, AdamW, learning rate .0002, no warmup/weight decay, microbatch 1,
accumulation 8, gradient checkpointing, sequence cap 1,024 without truncation
or packing, and the reviewed order/seed 247056. No approved setting is changed
in this review. A different attention kernel, optimizer, offload, QLoRA,
precision or target-module mapping would require an explicit compatibility
and prospective change record. A short-sequence bf16 fit is not disproved;
it simply has not been validated. Axolotl documents a 31B QLoRA example and
a multi-GPU long-sequence LoRA example, plus architecture-specific attention
and stability caveats. Those different recipes do not benchmark our settings;
I do not import their different learning rate or quantization as an unnoticed
fix. [Axolotl Gemma guidance](https://docs.axolotl.ai/docs/models/gemma4.html).

Scientific workload remains fixed: **34 base episodes** for this one candidate
(17 frozen cases × two repeats), then only on a passing gate and separate
approval three parallel 2,000-example arms. Each arm retains 100 primary
own-domain acquisition checks; neutral additionally has 100 ordered comparison
checks; all retain 20 secondary no-order checks. The same all-arm acquisition
barrier precedes the full **33 transfer cases × four repeats × three arms =
396 transfer episodes**. Neither cases nor repeats are cut to fit the budget.
The base thresholds remain first parse ≥33/34, all parse ≥95%, valid non-null
actions ≥95% with positive denominator, closed-valid ≥33/34 and ≥1/2 closed-valid
per case. W headroom still excludes at ≥85% known servility (14/16), retains
unknown bounds and admits no unresolved headroom.

## Separate cost/time scenarios

Use the owner's **$1.70 already spent**, leaving **$23.30** under the unchanged
$25 cumulative cap. The first failed image build remains owner-attested $0.00;
a later invoice correction or additional storage charges consume headroom.
Free credit consumption counts as spend. No v0249 static reservation is
refunded or reset; any future revision would need a separately reviewed
accounting binding that preserves both historical reservations and actual
cumulative charges, without charging the same execution twice.

Public Modal **GPU Tasks** prices checked 18 October UTC / 17 October Chicago:
A100 80 GB $0.000694/s ($2.4984/h), H100 $0.001097/s ($3.9492/h), CPU
$0.0000131/physical-core/s and host RAM $0.00000222/GiB/s. Two cores plus 64 GiB
host RAM give **$3.104208/h A100** or **$4.555008/h H100**. Host RAM is separate
from GPU VRAM. These are requested-resource calculations, not exact invoice
ceilings: higher actual CPU/RAM consumption may cost more. No paid account
lookup was made. [Modal price source](https://modal.com/pricing).

The following are explicitly **unmeasured budget scenarios**, not a runtime
confidence interval. Per-arm times include loading, one-epoch training,
acquisition, barrier, conditional transfer and cleanup; they are gross billable
worker time. Parallel execution reduces elapsed time, not three-arm GPU-hours.
With three arms actually concurrent, the working schedule would be about one
base hour plus two arm hours (roughly three elapsed GPU-work hours), excluding
image builds, queueing and owner review. It is not a completion promise.
Add an illustrative $0.25 base and $0.50 study build/controller/storage allowance;
these allowances are not measured or guaranteed sufficient.

| Hardware / scenario | Base GPU-hours | New base estimate | Hours per arm / three-arm GPU-hours | New full three-arm estimate | Cumulative incl. $1.70 | Under $25? |
|---|---:|---:|---:|---:|---:|---|
| A100 80 GB / optimistic | 0.5 | $1.80 | 1.5 / 4.5 | $14.47 | $17.97 | Arithmetic only |
| A100 80 GB / working | 1.0 | $3.35 | 2.0 / 6.0 | $19.13 | $24.18 | $0.82 margin |
| A100 80 GB / stress | 1.0 | $3.35 | 3.0 / 9.0 | $28.44 | $33.49 | No |
| H100 / optimistic | 0.5 | $2.53 | 1.5 / 4.5 | $21.00 | $25.23 | No |
| H100 / working | 1.0 | $4.81 | 2.0 / 6.0 | $27.83 | $34.34 | No |
| H100 / stress | 1.0 | $4.81 | 3.0 / 9.0 | $41.50 | $48.00 | No |

The 64 GiB host provision is a planning choice, not a demonstrated minimum.
A **32 GiB sensitivity** lowers whole-worker rates to $2.848464/h A100 and
$4.299264/h H100. The two-hour-arm working scenario then totals **$22.39 A100**
and **$32.54 H100**; the optimistic H100 scenario totals **$23.95**. Thus I do
not claim every H100 scenario or every possible implementation is unaffordable.
RAM32 has no demonstrated load/training fit, and neither scenario establishes
that all scientific work completes. The three-hour-arm A100 RAM32 scenario
still totals **$30.93**.

With 64 GiB and $0.75 allowances, the remaining budget buys at most **7.264
A100 worker-hours** or **4.951 H100 worker-hours**. After one base hour, that
leaves **2.088 A100 hours/arm** or **1.317 H100 hours/arm**, including every
load, generation and retention/deletion stage. The working A100 scenario has
roughly 5.3 extra minutes per arm before the arithmetic cap, with no measured
Gemma speed, tokenizer counts, context/LoRA memory result, or overhead variance.
A longer output or modest memory/offload delay can consume that margin.

Existing 7–8B inference TPS cannot measure Gemma backpropagation or establish
vLLM transfer speed. Even an illustrative 350,000-token epoch at an assumed
80 training tokens/s takes 1.22 hours; at 20 tokens/s it takes 4.86 hours
**before evaluation and loading**. These are examples, not Gemma token counts
or benchmark results. No observed match supports either training rate. A
three-hour stress arm is not a worst-case bound. Runtime guards can prevent
unbounded execution, but cannot ensure a completed, informative study.

A published Gemma comparison does provide external training evidence: its GPU
baseline uses two H100s, rank-64 LoRA, a 10,000-example code dataset and longer
sequences, then merged-weight serving. Those hardware, optimization, data and
serving differences prevent treating it as a measured rate for our single-GPU,
rank-8, short-example, unmerged-adapter study. It establishes neither that our
recipe needs two GPUs nor that a two-hour gross arm is assured. I make no claim
that Gemma has never been benchmarked. [Kishnani et al., 2026](https://arxiv.org/abs/2605.25645).

The equal-duration rows above are cost sensitivities, **not a measured
price/performance ranking**: an H100 could finish sufficiently faster to have a
lower completed-job cost than an A100. No matched speed ratio is available for
this workload. Likewise, a tuned batched vLLM implementation might improve
throughput; that possibility is not a validated timing bound for the proposed
exact stack. These uncertainties are why an arithmetic fit is not a supported
completion commitment.

**Judgment:** possible in an optimistic implementation, but not a defensible
high-confidence completion plan under this cap and unchanged scope. I therefore
do not spend part of the remaining budget on a standalone Gemma gate while
presenting an unfunded full study as viable. No new benchmark is run to resolve
that uncertainty without a separate owner decision. The correct deliverable
for this request is the findings fallback below.

## Disposition, launch window, ledger and Mac review

The new disposition is `v02412`, **not an executable Gemma revision**. No launch
window is opened, no fresh remote Dict/Volume is created, and no GPU launch
command is supplied under this fallback. All old `taa-study-d-v0249-*` resources,
claims, evidence and app histories remain intact; old base/training commands
are archival and must not be reused. No trained adapters exist from this gate.
The private retention/deletion commitment remains for any separately authorized
future study; this review deletes nothing.

A future Gemma proposal, if separately requested, must first fund and validate
the full stack, then bind a fresh finite window and namespaced once-only keys
to that prospective source revision and the inherited $1.70 (or corrected actual
invoice). It cannot reuse or clear v0249 keys, substitute hosted API output, or
relax cases/repeats/thresholds. This document does not authorize that proposal.

Mac commands below **only retrieve and read the review**; no Modal or model
command is needed. Do not run either old launcher.

```bash
cd "$HOME/taa-lab"
git status --short
git pull --ff-only origin main
open docs/process/PAPER3_STUDY_D_GEMMA_FEASIBILITY_v02412.md
open docs/process/PAPER3_STUDY_D_FINDINGS_v02412.md
shasum -a 256 studies/formation-study-d-disposition-v02412/base-boundary-2.original.zip
```

If Git reports local changes/conflicts, preserve them and stop rather than
reset/discard work. Original zip SHA-256:
`50bde52f4c4bc3ea9e02969b9dda6bd7a7d64f3dba7721f7d615e5437c8789e6`.
**Stop for review. No downloads of weights, GPU use, tuning, or spending.**
