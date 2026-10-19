# v02425 science arms — FOR REVIEW, NOT APPROVED

No smoke or merged rerun. Each stage needs separate exact-commit approval.

```sh
cd ~/taa-lab
git status --short
git fetch origin
# Preserve any unexpected local changes; use the new full reviewed commit:
git checkout --detach FULL_REVIEWED_V02425_COMMIT
REVIEWED_COMMIT="$(git rev-parse HEAD)"
```

v02424 stopped after training and must NEVER be relaunched; old resources stay untouched. v02425 has no launch approval.
Only AFTER owner approves the exact v02425 commit AND both GitHub checks pass, refresh dashboard values
(last confirmed $10.93 used / $19.07 left). Before submitting, confirm the old app ap-KAVCSaqESVAEvxyYV55QNG is finished
with no active containers (Modal dashboard or read-only `modal app list`).
Never relaunch the old CLI or reset its Dict/markers. Offline preflight first:

```sh
ACTUAL_TOTAL_USD=10.93
CREDIT_LEFT_USD=19.07
caffeinate -dis ~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_stages_v02425.py \
  --stage pair --approved \
  --approval-receipt "Owner approved Study D Gemma pair v02425, commit $REVIEWED_COMMIT" \
  --actual-total-usd "$ACTUAL_TOTAL_USD" --available-credit-usd "$CREDIT_LEFT_USD" \
  --billing-attestation 'Owner reconciled cumulative Study D charges; current credit confirmed; no card' \
  --previous-report-sha256 93d13ecd18cc1b158cbbb0dd5554efbd13df6a017affe3a24fa140949feae22d \
  --preflight-only
```

After offline PASS and with approval, run the same command once removing ONLY
`--preflight-only`. Wait for `SUBMITTED — safe to close laptop | app_id=... |
call_id=...`. Error/missing acknowledgement means stop, preserve receipts/output;
never retry/reset/delete a marker or Dict/Volume. Existing Python3.12/Modal1.6.2
and Mac auth; token only from Modal Secret `huggingface`.

Read-only status / download after termination:

```sh
~/modal-study-d-gemma/bin/modal app list
~/modal-study-d-gemma/bin/modal app logs ACTUAL_PAIR_APP_ID > ~/gemma-v02425-pair-app-log.txt
mkdir -p ~/taa-results
mkdir ~/taa-results/gemma-v02425-pair-return-001
cd ~/taa-results/gemma-v02425-pair-return-001
~/modal-study-d-gemma/bin/modal volume get taa-study-d-gemma-v02425-evidence / . --env main
cd ~/taa-results
zip -r gemma-v02425-pair-return-001.zip gemma-v02425-pair-return-001
```

Return unmodified ZIP/log and both
`~/.local/state/taa-study-d/gemma-v02425-pair-local-attempt.json` and
`.submission.json`, plus new billing totals. Never download/share private adapters.
Use fresh empty destinations; disclose failed downloads, keep originals.

Virtue ONLY after pair COMPLETE/audit/review and NEW owner approval. Stay at the
same reviewed commit, refresh dashboard, compute pair report hash from returned
`pair/report.json` with `shasum -a 256 PATH_TO_PAIR_REPORT_JSON`, then:

```sh
caffeinate -dis ~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_stages_v02425.py \
  --stage virtue --approved \
  --approval-receipt "Owner approved Study D Gemma virtue v02425, commit $REVIEWED_COMMIT" \
  --actual-total-usd CURRENT_CUMULATIVE_USED --available-credit-usd CURRENT_CREDIT_LEFT \
  --billing-attestation 'Owner reconciled cumulative Study D charges; current credit confirmed; no card' \
  --previous-report-sha256 REVIEWED_PAIR_REPORT_SHA256 \
  --preflight-only
```

Then, only if separately approved and preflight PASS, remove ONLY preflight flag
for one submission. Same acknowledgement rule; new virtue local receipts. Download
the SAME evidence Volume into a fresh `gemma-v02425-virtue-return-001` folder and
return its ZIP/log/receipts/billing. No November cap/counter reset. No automatic
stage continuation. Both stages remain BLOCKED until exact-commit owner approval.

Pair is SERVING ONLY: reuse trained contrary/neutral adapters read-only. No retraining.
Its reservation is $9.855778; virtue remains $8.483444 and separately approved.
The pair previous-report hash above binds adapter-source-v02424.json, the exact
returned v02424 training/failure evidence index; no COMPLETE pair report is invented.
Each stage uses current credit independently; cumulative cap remains $36 across
months and stages. Never reset/delete the old ledger, adapters or evidence.
Pair ends Oct26 01:00 UTC; virtue ends Nov9 01:00 UTC (exclusive).

MAC_COMMANDS.md, plan.json, stages.json and integrity.json in this folder are
byte-identical inherited v02420 artifacts, preserved for audit; they do NOT
launch/configure this revision. Use ONLY this MAC_COMMANDS-v02425.md, the new
versioned launcher and integrity-v02425.json. Review stage-plan-v02425.json.

Private source adapters remain read-only even at study end. Their eventual
owner-reviewed CPU deletion must produce before/after receipts; no cleanup
command or permission is implied by the serving launch. Never download/share them.
