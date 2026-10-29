# Study D private-adapter deletion plan v02430

**ON HOLD UNTIL THE PAPER 3 OUTLINE IS REVIEWED. NO DELETION AUTHORIZED OR PERFORMED.**

Owner decision, 20 October 2026: hold deletion until after review of the Paper 3
outline. Analysis review remains required, followed by separate explicit owner
approval of the exact deletion manifest and named private Volumes. Read-only
inventory preparation is allowed; no live inventory or deletion has been run.
This document is a plan,
not an executable cleanup script. All adapters remain private and unshared
until that decision. No deployment, Hugging Face upload or distribution.

## What must eventually be removed

| Physical private Volume | Checkpoint | Used by |
|---|---|---|
| `taa-study-d-gemma-v02424-private-adapters` | `science/contrary/final` | trained v02424; served v02425 |
| same Volume | `science/neutral/final` | trained v02424; served v02425 and v02426 |
| `taa-study-d-gemma-v02428-private-adapters` | `science/virtue/final` | trained v02428; served v02429 |

v02426's executed neutral-completion path mounted the **v02424 Volume read-only**.
It did not create an additional neutral adapter. The code contains an unused
virtue branch naming `taa-study-d-gemma-v02426-private-adapters`; that name is
not evidence a Volume exists. A later approved read-only inventory must check
it and any other adapter copies. An unexpected Volume requires an explicit
manifest amendment/owner decision, never a wildcard deletion.

[Machine-readable draft](../../studies/formation-study-d-analysis-v02430/private-adapter-deletion-plan.json)
records all three final checkpoint index hashes, adapter/config/README hashes,
sizes and the pinned public verification-receipt paths. The v02426 neutral
receipt has the same index and three file hashes as v02425's reused neutral
checkpoint. These hashes are public receipts; no weights were copied into Git.

## Proposed sequence after approval

1. Confirm Paper 3 outline and analysis review are complete. Record separate
   exact owner approval, analysis commit, target manifest SHA, operator,
   UTC time, Modal workspace/environment and the two unique approved physical
   Volume names. Confirm all Study D apps/workers are terminal and none mount
   these Volumes. Use read-only metadata/inventory commands first; no launch.
2. Inventory each approved Volume recursively, including final adapters,
   intermediate checkpoints, optimizer/training artifacts and any other private
   adapter copies. Preserve credential-free file paths, sizes and hashes in a
   pre-deletion receipt. Verify final checkpoint integrity against the pinned
   training-time index. A mismatch or unexpected path stops for review.
3. Confirm whether any local downloads, extra private Volumes, notebooks,
   snapshots or external model registries hold copies. The current evidence
   reports no sharing/deployment and read-only reuse. Do not infer that this
   is a complete live inventory. Add any copies to the reviewed manifest
   before deleting them. Do not download weights solely for this inventory.
4. Delete the approved private adapter contents, including intermediate
   checkpoints, using a future reviewed CPU-only cleanup action on the exact
   names. Prefer deleting each whole **verified adapter-only** Volume so no
   forgotten checkpoint survives. Deduplicate the v02424 neutral/v02426 alias;
   do not delete it twice. If a Volume contains unrelated material, stop and
   replace whole-Volume removal with an explicitly approved path manifest.
5. Verify absence through provider metadata/listing. Write an after-deletion
   receipt with command outcome, timestamp, exact Volume IDs/names, before
   manifest hash, deletion/absence evidence and any failed/remaining copies.
   Provider deletion receipts cannot prove physical media erasure; state that
   limit. A failed deletion remains pending and is reported, never marked done.
6. Commit only the credential-free manifests and receipts for review. State
   whether every known adapter copy is gone. Never recreate an adapter or
   retrain to verify deletion.

**Always preserve:** all returned ZIPs and extracted scientific evidence,
native journals, public training proofs, reports, source hashes, budget Dicts,
once-only markers, failed-stage records and billing attestations. Base-weight
caches and unrelated Volumes are outside this deletion plan. No ledger reset.

The existing stopped/review-stage retention rule remains in force through the
Paper 3 outline review and until the owner's separate deletion decision. Study D
has no further approved scientific reruns. No new inference or GPU work is
requested or implied.
