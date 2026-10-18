# Review-only Mac commands — v0.24.16, CPU then GPU

No stage runs until separately approved. If the owner approves both stages, passing
CPU permits the already-approved GPU command below; it does not authorize training.
Preserve every old app, local receipt, Dict and Volume. Never reset/delete once-only
claims or retry an ambiguous submission. Modal Secret `huggingface` contains HF_TOKEN;
credentials remain in the Mac profile/Modal Secret, never in Git or chat.

## Update and bind the reviewed commit

```bash
cd ~/taa-lab
git status --short
git fetch origin
git pull --ff-only origin main
python3.12 -m venv ~/modal-study-d-gemma
~/modal-study-d-gemma/bin/python -m pip install 'modal==1.6.2'
REVIEWED='PASTE_FULL_OWNER_APPROVED_COMMIT_HERE'
test "$(git rev-parse HEAD)" = "$REVIEWED"
```

If absent, clone `https://github.com/metaphysika/taa-lab.git` to `~/taa-lab` first.
Stop on local conflicts or failed fast-forward; do not discard work. Existing
Modal authentication is used; if absent, run the venv's `modal setup` yourself.
Keep Python 3.12/Modal 1.6.2 pins. The CPU and GPU must use this identical commit.

Obtain the CURRENT total Study D usage, including all prior attempts/builds. The
owner supplied $2.59 used / $27.41 left after v02415: $0.42 displayed increase
from $2.17. Use the current actual used total, at least $2.59; do not reuse $2.17. Confirm no
other Study D work is running, no card attached, prices unchanged. Supply the
current numeric total below, not credit balance. Keep the dashboard evidence.

## Stage 1 — approved CPU tokenizer/scripted dry-run only

This builds the same pinned image but uses two CPU cores/8 GiB, NO GPU. Only pinned
tokenizer/template/config files may download; no weights or model engine. One
frozen case is replayed through the shared token formatting, guards, event logging,
canned-reply request interface, parser and scorer. All replies are scripted and
excluded from scientific base counts. Reservation is $0.130111 (about 13 cents),
including CPU/startup/build allowance, inside the unchanged $25 cumulative cap.

```bash
ACTUAL_TOTAL='PASTE_CURRENT_NUMERIC_DASHBOARD_TOTAL'
~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_base_v02416.py \
  --stage cpu --preflight-only --approved --actual-total-usd "$ACTUAL_TOTAL" \
  --approval-receipt "Owner approved Gemma tokenizer CPU dry-run v02416, commit $REVIEWED" \
  --billing-attestation 'Dashboard prior reconciled; no other Study D workloads; no card attached; current prices unchanged'
```

After preflight succeeds, submit **once**:

```bash
caffeinate -dis ~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_base_v02416.py \
  --stage cpu --approved --actual-total-usd "$ACTUAL_TOTAL" \
  --approval-receipt "Owner approved Gemma tokenizer CPU dry-run v02416, commit $REVIEWED" \
  --billing-attestation 'Dashboard prior reconciled; no other Study D workloads; no card attached; current prices unchanged'
```

Keep the laptop OPEN and connected until the exact line appears with real IDs:

```text
SUBMITTED — safe to close laptop | app_id=ap-... | call_id=fc-...
```

This confirms acknowledged submission, not successful completion. The client never
waits for the remote result. Image built/app created is insufficient. Missing line,
error or lost connection means STOP FOR REVIEW, never resubmit or remove receipts.
The call might have been accepted even if acknowledgement was lost.

```bash
~/modal-study-d-gemma/bin/modal app list
~/modal-study-d-gemma/bin/modal app logs CPU_APP_ID
mkdir -p ~/study-d-results/gemma-base-v02416-cpu-return-001
cd ~/study-d-results/gemma-base-v02416-cpu-return-001
~/modal-study-d-gemma/bin/modal volume get taa-study-d-gemma-base-v02416-evidence / .
```

After CPU is terminal, its `cpu-check/report.json` AND `cpu-check/receipt.json` must
say PASS. Preserve/download them, events, scripted episode, tokenizer metadata,
local attempt/submission receipts and dashboard cost. Any failure stops the plan;
no GPU command. A passing CPU receipt binds exact commit, manifest, model revision,
pinned library versions, frozen case and hashes of all six required evidence files.
The remote GPU controller also checks the durable CPU closure; it refuses before
GPU reservation/spawn if absent, stale, incomplete or changed.

## Stage 2 — approved GPU base gate only, after CPU PASS

If GPU was not already approved, stop for that approval. Same A100 80 GB/bf16/vLLM,
utilization 0.95/context 16,384, no adapter and all 34 frozen primaries unchanged.
Update `ACTUAL_TOTAL` to include CPU charges. In the same reviewed repo:

```bash
cd ~/taa-lab
test "$(git rev-parse HEAD)" = "$REVIEWED"
ACTUAL_TOTAL='PASTE_UPDATED_NUMERIC_DASHBOARD_TOTAL'
~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_base_v02416.py \
  --stage gpu --preflight-only --approved --actual-total-usd "$ACTUAL_TOTAL" \
  --approval-receipt "Owner approved Gemma base-format gate v02416, commit $REVIEWED" \
  --billing-attestation 'Dashboard prior reconciled; no other Study D workloads; no card attached; current prices unchanged'
```

Then, once only after approval and successful preflight:

```bash
caffeinate -dis ~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_base_v02416.py \
  --stage gpu --approved --actual-total-usd "$ACTUAL_TOTAL" \
  --approval-receipt "Owner approved Gemma base-format gate v02416, commit $REVIEWED" \
  --billing-attestation 'Dashboard prior reconciled; no other Study D workloads; no card attached; current prices unchanged'
```

Again WAIT FOR THE EXACT SUBMITTED LINE before closing the lid. Each stage has its
own original marker and `.submission.json` under `~/.local/state/taa-study-d/`:
`gemma-base-v02416-cpu-local-attempt.json` and
`gemma-base-v02416-gpu-local-attempt.json`. Keep both; never reset or resubmit.
The two launches have separate app/call IDs but the same new evidence Volume.

After GPU is terminal with zero live containers:

```bash
mkdir -p ~/study-d-results/gemma-base-v02416-gpu-return-001
cd ~/study-d-results/gemma-base-v02416-gpu-return-001
~/modal-study-d-gemma/bin/modal volume get taa-study-d-gemma-base-v02416-evidence / .
cd ..
zip -r gemma-base-v02416-gpu-return-001.zip gemma-base-v02416-gpu-return-001
```

Use NEW EMPTY download folders and destination `.`. Return the unmodified outputs,
all app/call IDs/local receipts/Terminal logs and latest dashboard total for audit.

Both stages: window **October 18, 2026 13:00 CDT inclusive to October 24 13:00 CDT
exclusive** (18:00 UTC both dates). New CPU/GPU/closure keys only; old evidence is
untouched. New CPU + GPU reservation is $3.931889; prior full accounting $13.105333
is retained, for $17.037222 conservative total under $25. Higher current actual
usage replaces the lower accounting floor; over-cap execution refuses. No refunds,
training, extra run, weight cache, context reduction or scientific-rule changes.
