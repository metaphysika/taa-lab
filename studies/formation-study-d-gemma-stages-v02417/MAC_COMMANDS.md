# Mac commands — review templates, not launch approval

Each stage needs its own new owner approval **after** reviewing the preceding
stage and fresh actual billing. Never execute all three as a shell batch.
Keep old local attempt/submission receipts, apps, ledgers and Volumes unchanged.
The old base-format FAIL remains; the owner exception is separate.

## Repository and local tools

If not cloned:
```sh
cd ~
git clone https://github.com/metaphysika/taa-lab.git
cd ~/taa-lab
```
If already cloned:
```sh
cd ~/taa-lab
git status --short
git fetch origin
```
Stop on local changes; preserve them. Check out the **full reviewed commit**
from the publication message (replace the placeholder, do not use an old SHA):
```sh
git checkout FULL_REVIEWED_COMMIT
REVIEWED_COMMIT="$(git rev-parse HEAD)"
python3.12 -m venv ~/modal-study-d-gemma
~/modal-study-d-gemma/bin/python -m pip install 'modal==1.6.2'
~/modal-study-d-gemma/bin/modal profile current
```
Your Mac is already authenticated. If a later machine needs it, `modal setup`
stores auth outside Git in ~/.modal.toml. Do not paste token values into chat,
commands or repository files. Modal Secret `huggingface` must hold `HF_TOKEN`;
Llama/Kaggle secrets are irrelevant to this Gemma route. No weights are stored
in the repository or downloaded by the local preflight.

## Stage 1 — only after its separate approval

Refresh dashboard used/remaining amounts first. The confirmed starting values
were $4.30 cumulative Study D used /$25.70 current credit; update if changed.
`--actual-total-usd` is cumulative across **all months** and all Study D apps,
including build/CPU/storage, not just the current monthly display.

Offline preflight (no Modal import/backend/build; also requires the receipt):
```sh
caffeinate -dis ~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_stages_v02417.py \
  --stage smoke --approved \
  --approval-receipt "Owner approved Study D Gemma smoke v02417, commit $REVIEWED_COMMIT" \
  --actual-total-usd 4.30 --available-credit-usd 25.70 \
  --billing-attestation 'Owner reconciled all Study D apps; current dashboard $4.30 used/$25.70 left; no card; no other active spending' \
  --preflight-only
```
After approval, use the same command **without `--preflight-only`** to launch.
The client calls controller.spawn once and does not wait on the result. Keep the
lid open until it prints, with real IDs:

`SUBMITTED — safe to close laptop | app_id=ap-... | call_id=fc-...`

Only then close the laptop. If missing/error/disconnection, preserve both local
files in ~/.local/state/taa-study-d and inspect the app before any new decision.
Do not rerun, delete local markers, clear Dict keys or create another window.

Status and log commands (substitute actual app ID):
```sh
~/modal-study-d-gemma/bin/modal app list
~/modal-study-d-gemma/bin/modal app logs ACTUAL_APP_ID
~/modal-study-d-gemma/bin/modal dict items taa-study-d-gemma-v02417-budget-once --all --json --env main
```
Download only after stopped/closed; use a **fresh empty destination**:
```sh
mkdir -p ~/taa-results
mkdir ~/taa-results/gemma-v02417-smoke-return-001
cd ~/taa-results/gemma-v02417-smoke-return-001
~/modal-study-d-gemma/bin/modal volume get taa-study-d-gemma-v02417-evidence / . --env main
cd ~/taa-results
zip -r gemma-v02417-smoke-return-001.zip gemma-v02417-smoke-return-001
```
Return the zip unmodified, local attempt/submission JSON, app log, dashboard total
and remaining credit. Smoke report is `smoke/report.json`. It contains measured
training/decode TPS, memory, handoff and projections; no scientific training result.
**Stop for audit/owner review. Do not run Stage2 yet.**

## Stage 2 — only after smoke fits guards and new approval

Use the same reviewed source commit; hash the returned smoke report:
```sh
cd ~/taa-lab
REVIEWED_COMMIT="$(git rev-parse HEAD)"
PREVIOUS_SHA="$(shasum -a 256 ~/taa-results/gemma-v02417-smoke-return-001/smoke/report.json | awk '{print $1}')"
```
Set `ACTUAL_TOTAL_USD` and `CREDIT_LEFT_USD` to **new reconciled numbers**, not the
old $4.30/$25.70 values. Placeholders below deliberately fail numeric parsing:
```sh
ACTUAL_TOTAL_USD=REPLACE_WITH_CURRENT_ALL_MONTH_STUDY_D_TOTAL
CREDIT_LEFT_USD=REPLACE_WITH_CURRENT_AVAILABLE_CREDIT
caffeinate -dis ~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_stages_v02417.py \
  --stage pair --approved \
  --approval-receipt "Owner approved Study D Gemma pair v02417, commit $REVIEWED_COMMIT" \
  --actual-total-usd "$ACTUAL_TOTAL_USD" --available-credit-usd "$CREDIT_LEFT_USD" \
  --billing-attestation 'Owner reconciled smoke and all prior build/CPU/GPU/storage; no card; no other active spending' \
  --previous-report-sha256 "$PREVIOUS_SHA"
```
Wait for SUBMITTED with app/call IDs. It submits contrary and neutral in parallel;
no virtue job is submitted. Use the status commands above with this new app ID.
Download the whole evidence Volume into a **new** pair-return-001 folder using
the same `volume get ... / .` pattern. Preserve all preceding files too. Return
zip/receipts/log/current spend, then stop for audit and separate virtue approval.

## Stage 3 — only after pair audit and new approval

Same code, fresh virtue once-key. This month if funded; otherwise the fixed
virtue window permits November1–7, with new available credit attestation and
**no cumulative Study D budget reset**. If expired or predecessor missing, stop
for reviewed renewal; never reset old once-keys. Hash the audited pair report:
```sh
cd ~/taa-lab
REVIEWED_COMMIT="$(git rev-parse HEAD)"
PREVIOUS_SHA="$(shasum -a 256 ~/taa-results/gemma-v02417-pair-return-001/pair/report.json | awk '{print $1}')"
ACTUAL_TOTAL_USD=REPLACE_WITH_CURRENT_ALL_MONTH_STUDY_D_TOTAL
CREDIT_LEFT_USD=REPLACE_WITH_CURRENT_AVAILABLE_CREDIT
caffeinate -dis ~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_stages_v02417.py \
  --stage virtue --approved \
  --approval-receipt "Owner approved Study D Gemma virtue v02417, commit $REVIEWED_COMMIT" \
  --actual-total-usd "$ACTUAL_TOTAL_USD" --available-credit-usd "$CREDIT_LEFT_USD" \
  --billing-attestation 'Owner reconciled all months/stages/storage; current credit verified; no card; no other active spending' \
  --previous-report-sha256 "$PREVIOUS_SHA"
```
Again wait for SUBMITTED. Download into a new virtue-return-001 folder after
closure. Clean three-arm completion deletes private scientific adapters with
receipts. Any stage review stop retains them privately/nonshared until the
owner decides; storage charges must be included. Do not deploy/share adapters,
launch extra probes or restart a stopped arm. Raw outputs and ledgers remain.
