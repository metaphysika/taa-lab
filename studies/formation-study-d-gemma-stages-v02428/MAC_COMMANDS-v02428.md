# v02428 virtue — ARCHIVAL; executed once, STOP_FOR_REVIEW

Do not relaunch. The commands below document the consumed approval at commit 0c4946574f32d305b8e4272459a004d6cb460fc3; v02429 requires its own review and approval.

Wait for Claude review, exact-commit owner approval and both GitHub checks. These commands do not authorize launch. Confirm all old apps have finished; never restart/reset/delete old ledgers, markers, evidence or adapters. Preserve unexpected local changes.

```bash
cd ~/taa-lab
git status --short
git fetch origin
git checkout --detach 0c4946574f32d305b8e4272459a004d6cb460fc3
REVIEWED_COMMIT="$(git rev-parse HEAD)"
```

Existing Python3.12 / Modal1.6.2 environment; HF_TOKEN only from Modal Secret huggingface. Refresh actual cumulative Usage-tab total and current available credit if changed. The previous-report hash is the NEW reviewed composite pair record, staged under its intentionally retained canonical filename composite-pair-v02427.json (the same reviewed bytes used by v02428, not a v02427 launch instruction) and CPU-rebuilt as pair/report.json in the NEW evidence Volume. Original v02426 pair/report.json is preserved as source-composite-v02426.json; it is not the CLI-bound record.

```bash
caffeinate -dis ~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_stages_v02428.py \
  --stage virtue --approved \
  --approval-receipt "Owner approved Study D Gemma virtue v02428, commit $REVIEWED_COMMIT" \
  --actual-total-usd 19.67 --available-credit-usd 10.38 \
  --billing-attestation 'Owner reconciled cumulative Study D charges; current credit confirmed; no card' \
  --previous-report-sha256 d7837f291e21c04f5b700d1b6fb2adb684b871f28330cfc55d84da5ab0b018a7 \
  --preflight-only
```

ONLY after new approval and offline PASS, run the same command ONCE removing only --preflight-only. Wait for **SUBMITTED — safe to close laptop** with app ID AND call ID. Do not close the laptop before acknowledgement. Error/missing acknowledgement: preserve output and both receipts and stop; no automatic retry. This revision exposes no pair, neutral completion or smoke launch.

After termination:

```bash
~/modal-study-d-gemma/bin/modal app list
~/modal-study-d-gemma/bin/modal app logs ACTUAL_APP_ID > ~/gemma-v02428-virtue-app-log.txt
mkdir -p ~/taa-results
mkdir ~/taa-results/gemma-v02428-virtue-return-001
cd ~/taa-results/gemma-v02428-virtue-return-001
~/modal-study-d-gemma/bin/modal volume get taa-study-d-gemma-v02428-evidence / . --env main
cd ~/taa-results
zip -r gemma-v02428-virtue-return-001.zip gemma-v02428-virtue-return-001
```

Return ZIP, log, fresh billing and both ~/.local/state/taa-study-d/gemma-v02428-virtue-local-attempt.json and its .submission.json. Never download/share private adapters. Window ends Nov9 01:00UTC exclusive. No launch until exact approval.

The old v02427 ledger remains untouched with pair/closed and STOP_FOR_REVIEW; no virtue/once. Never reset it. v02428 uses a new ledger and evidence Volume. CPU admission streams journals, repairs once and hashes the canonical record before a reservation or worker claim. A stage directory alone is not a claim.
