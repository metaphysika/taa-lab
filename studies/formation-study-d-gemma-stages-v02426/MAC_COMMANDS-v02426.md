# v02426 Mac commands — REVIEW ONLY; NO STAGE APPROVED

Do not run these until Claude has reviewed and the owner has approved the exact
published v02426 commit, separately for each stage, with both GitHub checks PASS.
Never rerun v02425, reset a ledger or marker, or delete evidence/adapters. Confirm
old app has finished with no active containers before a new approved submission.

```bash
cd ~/taa-lab
git status --short
git fetch origin
# Preserve unexpected local changes; insert the NEW reviewed full commit:
git checkout --detach FULL_REVIEWED_V02426_COMMIT
REVIEWED_COMMIT="$(git rev-parse HEAD)"
```

Neutral completion: 34 untouched episodes only; no training/acquisition or
interrupted-episode resend. Refresh dashboard amounts if changed; these are the
last owner-reconciled totals. Existing Python3.12/Modal1.6.2 Mac environment and
HF_TOKEN from Modal Secret `huggingface`, unchanged.

```bash
caffeinate -dis ~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_stages_v02426.py \
  --stage neutral-completion --approved \
  --approval-receipt "Owner approved Study D Gemma neutral-completion v02426, commit $REVIEWED_COMMIT" \
  --actual-total-usd 18.52 --available-credit-usd 11.48 \
  --billing-attestation 'Owner reconciled cumulative Study D charges; current credit confirmed; no card' \
  --previous-report-sha256 2b2879415ffc4a45365c61904077192a526d00a9a4a6cb736387e35eb6b3be0c \
  --preflight-only
```

After OFFLINE PASS and ONLY after separate owner approval, run that same command
once removing only `--preflight-only`. Wait for `SUBMITTED — safe to close laptop`
with app ID AND call ID. Missing acknowledgement/error: preserve output and both
local receipts and STOP, never retry. No automatic virtue continuation.

After termination, read-only status and download into a fresh empty directory:

```bash
~/modal-study-d-gemma/bin/modal app list
~/modal-study-d-gemma/bin/modal app logs ACTUAL_APP_ID > ~/gemma-v02426-neutral-app-log.txt
mkdir -p ~/taa-results
mkdir ~/taa-results/gemma-v02426-neutral-return-001
cd ~/taa-results/gemma-v02426-neutral-return-001
~/modal-study-d-gemma/bin/modal volume get taa-study-d-gemma-v02426-evidence / . --env main
cd ~/taa-results
zip -r gemma-v02426-neutral-return-001.zip gemma-v02426-neutral-return-001
```

Return ZIP/log and both files under `~/.local/state/taa-study-d/` named
`gemma-v02426-neutral-completion-local-attempt.json` and its `.submission.json`,
plus fresh dashboard amounts. Never download/share private adapters.

Virtue remains blocked until composite pair scheduled closure, full evidence
review/audit, Claude review and separate exact-commit owner approval. It trains
its own adapter; unchanged science/guard/reservation, batched logging only.
Refresh current cumulative billing and current credit (possibly November) with
no cumulative reset. Compute `shasum -a 256 PATH_TO_RETURNED/pair/report.json`.

```bash
caffeinate -dis ~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_stages_v02426.py \
  --stage virtue --approved \
  --approval-receipt "Owner approved Study D Gemma virtue v02426, commit $REVIEWED_COMMIT" \
  --actual-total-usd CURRENT_CUMULATIVE_USED --available-credit-usd CURRENT_CREDIT_LEFT \
  --billing-attestation 'Owner reconciled cumulative Study D charges; current credit confirmed; no card' \
  --previous-report-sha256 REVIEWED_COMPOSITE_PAIR_REPORT_SHA256 \
  --preflight-only
```

Same separately approved one-submission acknowledgement rule; download same new
Volume into fresh `gemma-v02426-virtue-return-001`. Never use inherited
MAC_COMMANDS.md (historical v02420), nor old v02425 launch instructions.
Neutral window ends October26 01:00UTC exclusive (October25 8pm CDT); virtue ends
November9 01:00UTC exclusive (November8 7pm CST). No window renewal is implied.
Private source adapters are read-only; study-end cleanup still requires a
separate owner-reviewed CPU deletion with receipts. Never deploy/share adapters.
