# v02422 speed smoke — REVIEW ONLY, NOT APPROVED

No commands below authorize execution. Await a NEW exact-commit owner approval.
Do not run pair/virtue or re-run any v02420 stage. Keep every marker/Dict/Volume.

```sh
cd ~/taa-lab
git status --short
git fetch origin
# Preserve any unexpected local work, then use the full NEW reviewed commit:
git checkout --detach FULL_REVIEWED_V02422_COMMIT
REVIEWED_COMMIT="$(git rev-parse HEAD)"
# Refresh from the dashboard at launch; these are the latest owner-reported values:
ACTUAL_TOTAL_USD=5.89
CREDIT_LEFT_USD=24.11
```

Only after separate approval of this commit, the offline check (no Modal contact):

```sh
caffeinate -dis ~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_speed_v02422.py \
  --approved \
  --approval-receipt "Owner approved Study D Gemma speed smoke v02422, commit $REVIEWED_COMMIT" \
  --actual-total-usd "$ACTUAL_TOTAL_USD" --available-credit-usd "$CREDIT_LEFT_USD" \
  --billing-attestation 'Owner reconciled all Study D charges; current credit confirmed; no card' \
  --preflight-only
```

After that passes, remove ONLY `--preflight-only` to submit the approved smoke
once. Existing Python3.12/Modal1.6.2 environment and Mac authentication remain;
HF_TOKEN read only from the Modal Secret `huggingface`. Never paste keys into
commands/chat/repository. New local receipt:
`~/.local/state/taa-study-d/gemma-v02422-speed-local-attempt.json`, plus its
`.submission.json`. Controller uses spawn; client does not wait for the result.
**Wait for `SUBMITTED — safe to close laptop | app_id=... | call_id=...`.**
Missing acknowledgement/error/disconnection means STOP; never rerun/reset/delete.

Status and download after termination (not a second launch):

```sh
~/modal-study-d-gemma/bin/modal app list
~/modal-study-d-gemma/bin/modal app logs ACTUAL_NEW_APP_ID > ~/gemma-v02422-speed-app-log.txt
mkdir -p ~/taa-results
mkdir ~/taa-results/gemma-v02422-speed-return-001
cd ~/taa-results/gemma-v02422-speed-return-001
~/modal-study-d-gemma/bin/modal volume get taa-study-d-gemma-v02422-speed-evidence / . --env main
cd ~/taa-results
zip -r gemma-v02422-speed-return-001.zip gemma-v02422-speed-return-001
```

Use a fresh empty destination. Preserve errors/truncated files and re-fetch
individual files if necessary; disclose the download history. Return unmodified
ZIP, app log, both local receipts and new dashboard totals. Do not download/share
the private adapter/merged-weight Volume. On review stop retain private weights;
on clean speed completion code deletes them with receipts. No next-stage approval
or automatic spending follows completion.
