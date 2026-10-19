# v02424 science arms — FOR REVIEW, NOT APPROVED

No smoke or merged rerun. Each stage needs separate exact-commit approval.

```sh
cd ~/taa-lab
git status --short
git fetch origin
# Preserve any unexpected local changes; use the new full reviewed commit:
git checkout --detach FULL_REVIEWED_V02424_COMMIT
REVIEWED_COMMIT="$(git rev-parse HEAD)"
```

v02423 is superseded and must NOT launch. v02424 has no launch approval.
Only AFTER owner approves the exact v02424 commit AND both GitHub checks pass, refresh dashboard values
(last confirmed $6.85 used / $23.15 left). Offline preflight first:

```sh
ACTUAL_TOTAL_USD=6.85
CREDIT_LEFT_USD=23.15
caffeinate -dis ~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_stages_v02424.py \
  --stage pair --approved \
  --approval-receipt "Owner approved Study D Gemma pair v02424, commit $REVIEWED_COMMIT" \
  --actual-total-usd "$ACTUAL_TOTAL_USD" --available-credit-usd "$CREDIT_LEFT_USD" \
  --billing-attestation 'Owner reconciled cumulative Study D charges; current credit confirmed; no card' \
  --previous-report-sha256 6f4654e4eb472fd99a43cd198c85a014d16c93673990362380f27b8ebbbb13d4 \
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
~/modal-study-d-gemma/bin/modal app logs ACTUAL_PAIR_APP_ID > ~/gemma-v02424-pair-app-log.txt
mkdir -p ~/taa-results
mkdir ~/taa-results/gemma-v02424-pair-return-001
cd ~/taa-results/gemma-v02424-pair-return-001
~/modal-study-d-gemma/bin/modal volume get taa-study-d-gemma-v02424-evidence / . --env main
cd ~/taa-results
zip -r gemma-v02424-pair-return-001.zip gemma-v02424-pair-return-001
```

Return unmodified ZIP/log and both
`~/.local/state/taa-study-d/gemma-v02424-pair-local-attempt.json` and
`.submission.json`, plus new billing totals. Never download/share private adapters.
Use fresh empty destinations; disclose failed downloads, keep originals.

Virtue ONLY after pair COMPLETE/audit/review and NEW owner approval. Stay at the
same reviewed commit, refresh dashboard, compute pair report hash from returned
`pair/report.json` with `shasum -a 256 PATH_TO_PAIR_REPORT_JSON`, then:

```sh
caffeinate -dis ~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_stages_v02424.py \
  --stage virtue --approved \
  --approval-receipt "Owner approved Study D Gemma virtue v02424, commit $REVIEWED_COMMIT" \
  --actual-total-usd CURRENT_CUMULATIVE_USED --available-credit-usd CURRENT_CREDIT_LEFT \
  --billing-attestation 'Owner reconciled cumulative Study D charges; current credit confirmed; no card' \
  --previous-report-sha256 REVIEWED_PAIR_REPORT_SHA256 \
  --preflight-only
```

Then, only if separately approved and preflight PASS, remove ONLY preflight flag
for one submission. Same acknowledgement rule; new virtue local receipts. Download
the SAME evidence Volume into a fresh `gemma-v02424-virtue-return-001` folder and
return its ZIP/log/receipts/billing. No November cap/counter reset. No automatic
stage continuation. Both stages remain BLOCKED until exact-commit owner approval.

Pair credit admission covers only its $16.255778 reservation; virtue later checks
its own $8.483444 against then-current credit (possibly November). The cumulative
$36 cap still covers all stages and prior spend, with no monthly reset.
Pair window ends Oct 26 01:00 UTC; virtue ends Nov 9 01:00 UTC (exclusive).
Stage ceilings rounded UP to cents are $16.26 and $8.49; the unrounded
reservations, not displayed two-decimal rounding, are used for admission.
