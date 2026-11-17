# FT1 prefill memory diagnosis, v0.24.93

Evidence: `results/2026-11-16 v0.24.92 ft1-fit-limit 1d064efae2da/kaggle-v1/ft1-fit_limit/events.jsonl`
(retained evidence, present in this checkout); latest v0.24.92 LAB_NOTEBOOK entry.
CPU raw measurements: `docs/process/evidence/ft1-prefill-v02493/cpu.jsonl`.
Reproduction: `python scripts/measure_ft1_prefill_cpu.py` and
`python -m unittest tests.test_ft1_prefill -v`. No weights or tokenizer downloads.

## Finding

Chunking should reduce the dominant quadratic attention workspace. This is a
source-based diagnosis supported by tiny CPU measurements, not a measured T4 fix.
The pinned stack is Transformers 5.20.2, Torch 2.11.0. Its GenerationMixin already
sets `logits_to_keep=1` when supported. Gemma3 slices hidden states before the
vocabulary projection and does not upcast inference logits. Neither evaluation
nor TorchBackend overrides that default. Full-prompt vocabulary logits are
therefore not the expected cause. The opt-in path makes this limit explicit.

Gemma3 eager attention materializes dense QK scores even for sliding layers:
masking does not avoid allocating the matrix. It then softmaxes in fp32 and
casts back. These are per-layer transient tensors, not 48 layers retained at once.
SDPA on T4 may use a math implementation with large workspaces; the matching
observed growth is consistent with that, but kernel dispatch was not recorded
and cannot be established from the old events.

## Derived byte estimates

Decimal GB below (multiply by 1e9 for bytes), batch one. Architectural assumptions
for 12B: 48 layers, 16 query heads, 8 KV heads, head dimension 256, hidden 3840,
MLP 15360, five sliding layers per full layer, window 1024. Confirm these against
the mounted config before interpreting the next GPU result. Inference activations
are assumed fp16; NF4 weight storage does not make activations four-bit.

| Component | 2500 | 4000 | 6000 | 13000 |
|---|---:|---:|---:|---:|
| Hypothetical full logits, fp16 `2*262208*L` | 1.311 | 2.098 | 3.147 | 6.818 |
| Actual one-position logits, fp16 | .000524 | .000524 | .000524 | .000524 |
| One dense score matrix, fp16 `32*L^2` | .200 | .512 | 1.152 | 5.408 |
| One fp32 softmax matrix `64*L^2` | .400 | 1.024 | 2.304 | 10.816 |
| Softmax live scores/copy/output `160*L^2` | 1.000 | 2.560 | 5.760 | 27.040 |
| Two dense masks `4*L^2` | .025 | .064 | .144 | .676 |
| Three MLP expanded arrays `6*15360*L` | .230 | .369 | .553 | 1.198 |
| One hidden-state array `2*3840*L` | .019 | .031 | .046 | .100 |
| Retained hybrid KV `8192*(8*L+40*1023)` | .499 | .597 | .729 | 1.187 |

The cache estimate excludes transient concatenation, allocator overhead, and
repeated KV heads in attention. After 1024 output tokens, add about .067 GB of
full-layer KV. Transformers 5.20.2 uses DynamicCache with sliding and full layers,
not the older HybridCache class; sliding layers retain window minus one tokens
but return the current full chunk's keys for attention. Logits dtype follows the
LM head input/weights (fp32 in our CPU test); if fp32 on the T4, double that row.
MLP rows are a workspace estimate, not an allocator peak prediction. Do not sum
all rows as simultaneously live. Masks, Q/K/V projections, repeated KV tensors,
quantization workspaces and residuals add further memory.

The retained events show 7.80e9 bytes allocated after load and OOM peaks of
14.0e9 bytes eager and 14.9e9 bytes sdpa. At eager softmax, fp16 masked scores,
an fp32 copy and the fp32 output can coexist across 16 heads: about 160 bytes
per token squared, plus about 4 bytes per token squared for two dense masks.
The measured increases of 2.15e9 at 2500 and 4.41e9 at 4000 support a
rough 160-180 bytes/token squared estimate, with a linear term anywhere from ~0 to
0.46 MB/token. Two points cannot pin these terms independently. These estimates
are not a complete allocator accounting; exact attribution needs GPU profiling.

Fit-limit 2 at 09fac296 measured at least 16,000 prompt tokens fitting with eager,
chunked 256: peaks were 9.82e9 bytes at 13k and 10.20e9 at 16k. See
`results/2026-11-16 v0.24.93 ft1-fit-limit-2 09fac2962b37/` and the notebook.

## CPU measurement

On Torch 2.15.0+cpu / Transformers 5.20.2, random six-layer Gemma3 text model, hidden 32,
MLP 64, vocabulary 97, four heads, window 8, prompt 35 and six greedy outputs:

| Mode | bmm allocated bytes | softmax allocated bytes | GELU allocated bytes |
|---|---:|---:|---:|
| Current | 154560 | 123840 | 61440 |
| Chunk 5 | 78160 | 47440 | 61440 |

The local Torch version differs from Kaggle's pinned 2.11.0; repeating on that
stack and the real device remains necessary. These profiler counters are cumulative operator allocations, not live peak RSS.
Every LM-head output was `[1,1,97]`, fp32, 388 bytes. Both paths produced
`[30,6,89,4,4,4]`. Chunking reduces attention allocation even though total MLP
work remains the same; each MLP allocation handles at most one chunk.
The unittest compares IDs and logits at every decode step, with EOS enabled, at lengths 7/19/35/73, chunk sizes
1/5/8/13/64, including window crossings and uneven final chunks.

## Implementation and proposed measurement

Default `prefill_mode=current` passes no new generation options. Explicit
`prefill_mode=chunked, prefill_chunk_size=256` selects Transformers' built-in
cached chunk prefill, with last-position logits, retaining its greedy decoder,
EOS rules and cache positioning. Receipts bind both fields, and gate identity
requires them to match. Events record mode/size. OOM cleanup and context guards
remain in the existing wrapper. Floating-point kernel shape changes can change
near-tied argmax choices on NF4/T4; CPU equivalence is not a guarantee for 12B.

The plan-only stager accepts the two options but was not run for this build.
Proposed second measurement: chunk 256, eager only, cooperative deadline 4500
seconds (75 minutes), including load. First compare current/fixed 1024-token
outputs at 2500 and 4000 with identical prompts, retaining IDs and first divergence
(or explicit unavailable if OOM). Then use the existing 2500 through 16000 ladder,
with OOM recovery and evaluation-path probes preserved. The benchmark deliberately
forces 1024 outputs; the evaluation probe respects EOS and the 16384 total guard.
At 16000 plus 1024 only the benchmark runs; evaluation probes cap prompt at 15360.
The deadline is checked between calls and during decode, not a hard preemption
of a running forward. An OOM stops the ladder and triggers recovery as before.
At 13000 tokens, a 256-token chunk changes the global score/softmax envelope
from about 27.04 GB to .532 GB (`160 * 256 * 13000`),
plus cache and other workspaces. This is a derived allocation estimate, not a
T4 peak forecast. No sdpa repetition is proposed to conserve the session budget. No GPU result,
new prompt ceiling, Kaggle staging or launch approval is claimed.

## Exact receipt and staging contract

Receipt schema: `docs/process/FT1_CHUNKED_FIT_RECEIPT_v02493.schema.json`.

Claude must use a new approval receipt with `approved: true`,
`phase: "fit_limit"`, `repo_commit: <exact reviewed 40-character commit>`,
`model_source: "google/gemma-3/transformers/gemma-3-12b-it/1"`,
`data_manifest_sha256: null`, `prefill_mode: "chunked"`,
`prefill_chunk_size: 256`, and `deadline_seconds: 4500`.
No adapter, training output, gate or sealed bindings are permitted.
The chunked fit receipt requires all three new fields explicitly; missing or
mismatched values fail validation before load. The source hashes and receipt_slug
are generated into binding.json by the stager.

Plan-only CLI: `python -m exploratory.ft1.fit_limit_stage --plan --output <new-local-folder> --commit <SHA> --owner metaphysika --repo-dataset <owner/repo-dataset> --receipt-dataset <owner/new-receipt-dataset> --model-source google/gemma-3/transformers/gemma-3-12b-it/1 --prefill-mode chunked --prefill-chunk-size 256`.
Backend is eager only; ladder is 2500,4000,6000,8000,10000,11000,12000,13000,14000,16000;
output allowance is 1024 and deadline is 4500 seconds including load.

F7 is declined: parity retains separate current/fixed measurements before the
ladder. Order is current 2500, fixed 2500, parity 2500, current 4000, fixed 4000,
parity 4000, then the fixed ladder. Deadline checks precede every measurement;
expiration aborts with run_failed and incomplete metadata, so no missing comparison
is represented as equality. No pre-run prediction entry is written by this build.
