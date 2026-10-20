# v02429 serving-only virtue — FOR REVIEW ONLY; NOT APPROVED

No launch until Claude review, both exact-head checks and owner approval of the exact commit. The v02428 approval cannot authorize v02429. Confirm all old apps have finished. Never reset/delete previous ledgers, evidence, receipts or private adapters. Preserve local changes.

```bash
cd ~/taa-lab
git status --short
git fetch origin review/study-d-v02429
git checkout --detach FULL_REVIEWED_V02429_COMMIT
REVIEWED_COMMIT="$(git rev-parse HEAD)"
```

Use existing Python 3.12 / Modal 1.6.2 environment. HF_TOKEN only from Modal Secret `huggingface`. Refresh the higher cumulative Usage-tab total and available credit if changed. This revision has no training launch or fallback. The source private Volume is read-only; keep it private after any review stop. No adapter downloads.

Only AFTER exact-commit approval:

```bash
caffeinate -dis ~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_stages_v02429.py \
  --stage virtue --approved \
  --approval-receipt "Owner approved Study D Gemma virtue v02429, commit $REVIEWED_COMMIT" \
  --actual-total-usd 22.73 --available-credit-usd 7.41 \
  --billing-attestation 'Owner reconciled cumulative Study D charges; current credit confirmed; no card' \
  --previous-report-sha256 d7837f291e21c04f5b700d1b6fb2adb684b871f28330cfc55d84da5ab0b018a7 \
  --preflight-only
```

After OFFLINE PREFLIGHT passes, run the same command ONCE removing only `--preflight-only`. Wait for **SUBMITTED — safe to close laptop** with app ID AND controller call ID. Then the remote controller admits, claims, reserves, spawns the worker and returns; this acknowledgement does not mean scientific completion. A separate worker call ID is saved in `virtue/worker-submission.json`. Error/ambiguous acknowledgement: preserve both receipts and stop; no automatic retry. App must finish and the worker report/closure must be audited before any completion claim.

After termination:

```bash
~/modal-study-d-gemma/bin/modal app list
~/modal-study-d-gemma/bin/modal app logs ACTUAL_APP_ID > ~/gemma-v02429-virtue-app-log.txt
mkdir -p ~/taa-results
mkdir ~/taa-results/gemma-v02429-virtue-return-001
cd ~/taa-results/gemma-v02429-virtue-return-001
~/modal-study-d-gemma/bin/modal volume get taa-study-d-gemma-v02429-evidence / . --env main
cd ~/taa-results
zip -r gemma-v02429-virtue-return-001.zip gemma-v02429-virtue-return-001
```

Return the unmodified ZIP, app log, fresh billing, `~/.local/state/taa-study-d/gemma-v02429-virtue-local-attempt.json` and its `.submission.json`. Do not reuse a nonempty download destination. Window ends November 9, 2026 01:00 UTC exclusive (November 8, 7 pm CST). No paid retry/relaunch is authorized by passing CI.
