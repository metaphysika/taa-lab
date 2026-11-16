# FT1 prefill memory diagnosis, v0.24.93

Evidence: `results/2026-11-16 v0.24.92 ft1-fit-limit 1d064efae2da/kaggle-v1/events.jsonl`
(owner-supplied path, absent in this checkout); latest v0.24.92 LAB_NOTEBOOK entry.
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
| Score/softmax/cast transient envelope `96–128*L^2` | .600–.800 | 1.536–2.048 | 3.456–4.608 | 16.224–21.632 |
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

The measured +2.15 GB at 2500 and +4.41 GB at 4000 grow 2.05-fold. Linear logits,
MLP and cache alone cannot explain that ratio. Quadratic attention plus linear
workspaces fits the direction and order of magnitude; exact attribution needs
GPU profiling. A single full fp32 softmax at 13000 already exceeds free memory.

## CPU measurement

On Torch 2.15.0+cpu / Transformers 5.20.2, random six-layer Gemma3, hidden 32,
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
The unittest compares IDs and last logits at lengths 7/19/35, chunk sizes
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
from about 16.2?21.6 GB to .319?.426 GB (`96?128 * 256 * 13000`),
plus cache and other workspaces. This is a derived allocation estimate, not a
T4 peak forecast. No sdpa repetition is proposed to conserve the session budget. No GPU result,
new prompt ceiling, Kaggle staging or launch approval is claimed.
