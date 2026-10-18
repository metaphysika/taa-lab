# Review-only Mac commands — v0.24.15

No launch is approved by this document. Use the new exact commit only after owner
review and approval. Keep all v0249/v02413/v02414 receipts, apps, Volumes and Dicts;
never remove or reset an old marker to run again. Modal Secret: `huggingface`, key
`HF_TOKEN`; Modal credentials stay in the Mac's existing SDK profile, never Git/chat.

## Update and prepare

If absent: `git clone https://github.com/metaphysika/taa-lab.git ~/taa-lab`.
For the existing checkout:

```bash
cd ~/taa-lab
git status --short
git fetch origin
git pull --ff-only origin main
git rev-parse HEAD
python3.12 -m venv ~/modal-study-d-gemma
~/modal-study-d-gemma/bin/python -m pip install 'modal==1.6.2'
```

Stop if fast-forward fails or there are conflicting local changes. Do not discard
work. Existing Mac authentication is used; if missing, run
`~/modal-study-d-gemma/bin/modal setup` yourself. Python 3.12 must match the image.

## After separate approval only

Check the current dashboard Study D total (all failed builds included), no other
Study D jobs running, old v02414 terminal/no execution, no payment card attached,
and unchanged prices. The old Dict output was not supplied to the preparation
agent; retain its exact output and original receipt/Terminal/dashboard evidence.
Reported v02414 cost is $0; last supplied cumulative total is $2.17. Supply the
current actual total, not available credits. New reservation is $3.801778; code
retains the old $9.303556 accounting ceiling, making $13.105333 conservative total
under the unchanged $25 cap. No refunds or ledger edits.

```bash
REVIEWED='PASTE_FULL_OWNER_APPROVED_COMMIT_HERE'
ACTUAL_TOTAL='2.17'
test "$(git rev-parse HEAD)" = "$REVIEWED"
~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_base_v02415.py \
  --preflight-only --approved --actual-total-usd "$ACTUAL_TOTAL" \
  --approval-receipt "Owner approved Gemma base-format gate v02415, commit $REVIEWED" \
  --billing-attestation 'Dashboard prior reconciled; no other Study D workloads; no card attached; current prices unchanged'
```

Stop on any mismatch. After preflight succeeds, launch **once**:

```bash
caffeinate -dis ~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_base_v02415.py \
  --approved --actual-total-usd "$ACTUAL_TOTAL" \
  --approval-receipt "Owner approved Gemma base-format gate v02415, commit $REVIEWED" \
  --billing-attestation 'Dashboard prior reconciled; no other Study D workloads; no card attached; current prices unchanged'
```

**Keep the laptop open and connected until this exact confirmation appears**, with
real IDs:

```text
SUBMITTED — safe to close laptop | app_id=ap-... | call_id=fc-...
```

Image built, app created, and a dashboard link are NOT this confirmation.
`caffeinate -dis` prevents idle sleep during the command; do not close the lid
before acknowledgement. The local entrypoint submits the controller with
`spawn()`, saves its returned call ID, prints the line with flushing, and returns
without fetching the result. `modal run --detach` keeps accepted work remote.
After the line, closing the laptop does not cancel the submitted controller.
This is submission confirmation, not a completed or passing gate.

Local original attempt marker:
`~/.local/state/taa-study-d/gemma-base-v02415-local-attempt.json`.
Separate submission record beside it:
`gemma-base-v02415-local-attempt.submission.json`.
The latter records IN_PROGRESS, then SUBMITTED with server app/call IDs, or an
unconfirmed error. Both are once-only records. On any lost acknowledgement,
missing line or error, **stop for review; never resubmit or delete either file**.
The server may have accepted a call even if its reply was lost. If the line is
lost after a successful local save, the saved call ID is evidence for review,
not permission to rerun. Do not infer $0/no execution from a connection error alone.

Window: **October 18, 2026 01:00 CDT through October 24 01:00 CDT exclusive**
(**2026-10-18 06:00 UTC <= launch < 2026-10-24 06:00 UTC**).
Expiry requires review, not clock or marker changes.

## Status and terminal download

```bash
~/modal-study-d-gemma/bin/modal app list
~/modal-study-d-gemma/bin/modal app logs APP_ID_FROM_SUBMITTED_LINE
```

After the app is terminal with zero live containers, download into a NEW empty
folder (destination `.`):

```bash
mkdir -p ~/study-d-results/gemma-base-v02415-return-001
cd ~/study-d-results/gemma-base-v02415-return-001
~/modal-study-d-gemma/bin/modal volume get taa-study-d-gemma-base-v02415-evidence / .
cd ..
zip -r gemma-base-v02415-return-001.zip gemma-base-v02415-return-001
```

Return the unmodified zip, app/call IDs, both local receipts, Terminal log and
current dashboard total for audit. No training, rerun, old-ledger reset/deletion,
or interpretation as a passing format gate before the audit.
