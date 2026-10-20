# Study D v02428 virtue CPU-admission fix — FOR REVIEW, NOT APPROVED

[Mac commands](../../studies/formation-study-d-gemma-stages-v02428/MAC_COMMANDS-v02428.md) · [shared CPU admission](../../scripts/study_d_gemma_admission_v02428.py) · [memory regression](../../scripts/study_d_gemma_admission_ci_v02428.py)

No launch, model download, GPU work or scientific training is approved by this preparation. Claude review and owner approval of the exact new commit remain required. The v02427 failed attempt cannot be restarted or its markers reset.

## Read-only v02427 result

Owner supplied the authenticated Mac read-only command output for taa-study-d-gemma-v02427-budget-once. Exactly two keys are present:

- pair/closed: COMPLETE, report_sha256 d7837f291e21c04f5b700d1b6fb2adb684b871f28330cfc55d84da5ab0b018a7
- STOP_FOR_REVIEW: stage virtue

There is no virtue/once. The returned ZIP has no virtue/reservation.json or virtue worker output. Thus no reservation was claimed; owner/Claude report no worker/GPU billed. This cloud runtime has no Modal credentials/allowlist access; the live inventory is owner-supplied, not independently queried here. No ledger writes or resets were performed.

Original ZIP SHA d6b42590aa8761a0c79be694a8c13db3ea2606ddffba5e1bf801776344344f13, 398 files, CRC PASS, preserved in results/gemma-v02427-virtue-return-001.zip. Every file has an inventory hash. The source and repaired composites exist; repaired hash matches review. Only the restarted controller's stage-directory guard error is directly captured. The initial stalled instruction is not proven by that ZIP. Owner/Claude report a 900-second heartbeat loss and controller restart, most likely during resource-constrained repeated admission. Record as an engineering pre-worker failure, no science. Older failures in prior-* are historical inputs.

## Minimal operational changes

Controller reservation increases from 0.25 CPU / 256 MB to **1 CPU / 2,048 MB** (explicit request and limit). Worker resources, software guard **9,600 s**, provider timeout **9,800 s**, controller timeout +450 s, startup/idle/retry configuration are unchanged.

The shared admission helper is the actual production CPU path and the CI path: validate approval/budget and asset/source hashes; check old v02426 closure read-only; copy all 396 pinned v02426 files into the NEW evidence Volume; perform exactly one streaming repair; save directly to root/'pair/report.json'; verify the canonical hash; persist; create only the new pair/closed record; verify carried CPU proof and call require_previous. It stops before reservation or worker submission. Source hashes are checked during copying (and copied bytes checked), rather than re-reading all sources in require_previous. That function now checks only source-composite/canonical hashes, metadata, durable closure and the existing billing floor, without another repair.

The streaming repair retains start IDs and SHA-256 hashes of returned raw text, not full start/history objects or the journal's full text. Each completed packet's raw-text hash must match its first native return. Repaired provenance and canonical composite bytes remain **identical to reviewed v02427**, including the repair-schema version field. Producer labels remain v02425/v02426; no score, label, bound, seed or case changes. The inherited administrative filename composite-pair-v02427.json is intentional.

A stage directory by itself is not an attempt signal. Only stage/once or stage/reservation.json signal a claim, with STOP_FOR_REVIEW retained as an independent review stop. Explicit root-relative composite save avoids mkdir on virtue/../pair. Failure evidence may create a stage folder; it must not be mistaken for a reservation. Atomic once claim and reservation persistence still precede any worker spawn. No automatic relaunch/reset after a review stop.

## Free CPU regression and memory criterion

scripts/study_d_gemma_admission_ci_v02428.py runs the same full admission helper against the committed v02426 ZIP in an isolated process: source copying, single repair, carried CPU proof and require_previous. It profiles repair calls (must equal one), asserts no virtue folder/reservation, and checks the canonical hash. Peak RSS must be below **50% of 2,048 MiB = 1,024 MiB**. This is measured local/CI process RSS, not claimed Modal telemetry. New tests also prove that a harmless stage directory alone does not block admission, but either a once key or reservation file does.

First local Python 3.11 rehearsal: 0.924 s admission time; peak RSS **60,846,080 bytes (58.03 MiB, 2.83% of controller limit)**. Full source ZIP extraction/imports are included in the process peak; timed admission starts before validation/copy. Inputs are filesystem-cached locally, so time is not a remote promise. No Modal API call, GPU, pretrained weights or model generation is involved. Free GitHub CI repeats the full shared path and the memory assertion on every commit. The no-backend Modal serialization regression and pinned tiny CPU training rehearsal remain required.

## Budget and science unchanged

PRIOR **$19.67**, the higher attested Usage figure, remains authoritative despite displayed dashboard $19.62. Credit **$10.38**, cap **$36**. No lower prior or monthly reset. No itemized CPU/image cost for v02427 is invented or called zero.

Same formula: (9800 +120 startup +2 idle)×$3.20/hour÷3600 +$0.375 = **$9.194555556**. Actual prior plus reservation **$28.864555556**, cap headroom **$7.135444444**, current credit after reservation **$1.185444444**. At the already recorded CPU price $0.0000131/core/s and RAM $0.00000222/GiB/s, the enlarged controller's full 10,312-second provider envelope estimates **$0.18087248**, inside the unchanged $0.375 overhead allowance; no GPU-reservation increase. These are existing planning rates, not a newly queried invoice or live spend meter.

Measured timing projections remain v02427's: serving load 684.2786 s, request mean 2.8779 s/p95 4.2478 s, effective concurrency 1.7596. Same request-count and full-training-rate scenarios; worst no-concurrency stress 8,584.7 s, spare 1,015.3 s. No outcome-based selection or final contrasts.

All 18 inherited scientific assets and the entire science runtime remain byte-identical. No changes to engine, live LoRA, CUDA graphs, retained caching, sampler/KV guards, data/dose, training settings, acquisition, parser/scorer, seeds, transfer cases or repeats. Existing private-retention/deletion commitments unchanged.

Fresh namespaces: taa-study-d-gemma-v02428-budget-once, taa-study-d-gemma-v02428-evidence, taa-study-d-gemma-v02428-private-adapters. v02427 evidence and its two ledger keys remain immutable. Original v02426 input Volume and closure ledger remain read-only. Virtue window still ends **November 9, 2026 at 01:00 UTC** (November 8 at 7 pm CST), exclusive. Mac caffeinate/spawn/SUBMITTED acknowledgement route unchanged. Exact previous-report hash in Mac commands remains `d7837f291e21c04f5b700d1b6fb2adb684b871f28330cfc55d84da5ab0b018a7`. No launch until new review and exact-commit approval.
