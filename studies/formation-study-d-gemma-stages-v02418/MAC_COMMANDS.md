# v02418 Mac commands — review templates, no execution approval

The v02417 Stage1 approval was used for its stopped attempt. Do not rerun it.
This revision requires a new CPU-stage approval and then a separate GPU-smoke
approval at the same full reviewed commit. Pair/virtue remain unapproved.

## Preserve v02417 before any renewed decision

Keep the old app ap-h2Mg3Vt3JDpSyEU8X0bO1e / call
fc-01M58FMB8442NP02DZ1AX0PEVA, budget Dict and both Volumes unchanged.
Keep old Mac attempt/submission receipts in ~/.local/state/taa-study-d; no reset
or deletion. The owner-reported stop/cost is logged; original raw files were not
attached to the request. To preserve/export them on the Mac (read-only):

```sh
~/modal-study-d-gemma/bin/modal app logs ap-h2Mg3Vt3JDpSyEU8X0bO1e > ~/gemma-v02417-smoke-app-log.txt
~/modal-study-d-gemma/bin/modal dict items taa-study-d-gemma-v02417-budget-once --all --json --env main > ~/gemma-v02417-dict-items.json
mkdir -p ~/taa-results
mkdir ~/taa-results/gemma-v02417-smoke-return-001
cd ~/taa-results/gemma-v02417-smoke-return-001
~/modal-study-d-gemma/bin/modal volume get taa-study-d-gemma-v02417-evidence / . --env main
cd ~/taa-results
zip -r gemma-v02417-smoke-return-001.zip gemma-v02417-smoke-return-001
```
Return that zip, app log and the two local smoke attempt/submission JSON files
unmodified. Do not download/share private adapters or clear an unexpected state.

## Get the new reviewed revision

If needed: `git clone https://github.com/metaphysika/taa-lab.git ~/taa-lab`.
For the existing checkout:
```sh
cd ~/taa-lab
git status --short
git fetch origin
```
Stop on unexpected local changes; preserve them. Replace the following placeholder
with the full newly reviewed commit from the publication message:
```sh
git checkout --detach FULL_REVIEWED_COMMIT
REVIEWED_COMMIT="$(git rev-parse HEAD)"
```
Use existing Python3.12 environment ~/modal-study-d-gemma and Modal1.6.2. If it
needs setup, `python3.12 -m venv ~/modal-study-d-gemma` and
`~/modal-study-d-gemma/bin/python -m pip install 'modal==1.6.2'` are local-only.
Mac auth stays in ~/.modal.toml, outside Git; Modal Secret **huggingface** contains
HF_TOKEN. Never paste tokens into commands/chat/repository files. No new secret
or local HF token is needed.

## CPU tokenizer stage — only after its separate approval

Refresh dashboard figures if changed from $4.31 used/$25.69 left. All future
actual totals include every Study D month and build/CPU/GPU/storage charge.
Offline preflight (no Modal backend or image build):
```sh
caffeinate -dis ~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_stages_v02418.py \
  --stage cpu --approved \
  --approval-receipt "Owner approved Study D Gemma cpu v02418, commit $REVIEWED_COMMIT" \
  --actual-total-usd 4.31 --available-credit-usd 25.69 \
  --billing-attestation 'Owner confirms all Study D charges: $4.31 used/$25.69 left; no card' \
  --preflight-only
```
After new CPU approval, run that command **without `--preflight-only`**. No GPU
is assigned. Keep the laptop lid open until the exact acknowledgement with real
IDs appears:

`SUBMITTED — safe to close laptop | app_id=ap-... | call_id=fc-...`

The local client never waits for the remote result. Missing line, disconnection,
unknown state or error means preserve receipts and stop, never rerun.

Status/download after closed/stopped:
```sh
~/modal-study-d-gemma/bin/modal app list
~/modal-study-d-gemma/bin/modal app logs ACTUAL_CPU_APP_ID
mkdir ~/taa-results/gemma-v02418-cpu-return-001
cd ~/taa-results/gemma-v02418-cpu-return-001
~/modal-study-d-gemma/bin/modal volume get taa-study-d-gemma-v02418-evidence / . --env main
cd ~/taa-results
zip -r gemma-v02418-cpu-return-001.zip gemma-v02418-cpu-return-001
```
Return zip, log, local attempt/submission receipts and updated billing. Inspect
cpu/receipt.json, cpu/report.json, tokenizer metadata and all nine decoded examples.
CPU PASS alone does **not** authorize or start GPU work. Stop for audit/review.

## GPU smoke — only after CPU PASS audit and fresh exact-commit approval

Use the SAME reviewed commit. GPU smoke checks same-commit receipt, all evidence
hashes, package versions, stop token and durable CPU closure before GPU reservation;
trainer rebuilds data and compares all counts/digests before loading weights.
Set these to fresh reconciled amounts, including CPU/build cost:
```sh
cd ~/taa-lab
REVIEWED_COMMIT="$(git rev-parse HEAD)"
ACTUAL_TOTAL_USD=REPLACE_WITH_CURRENT_ALL_MONTH_STUDY_D_TOTAL
CREDIT_LEFT_USD=REPLACE_WITH_CURRENT_AVAILABLE_CREDIT
caffeinate -dis ~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_stages_v02418.py \
  --stage smoke --approved \
  --approval-receipt "Owner approved Study D Gemma smoke v02418, commit $REVIEWED_COMMIT" \
  --actual-total-usd "$ACTUAL_TOTAL_USD" --available-credit-usd "$CREDIT_LEFT_USD" \
  --billing-attestation 'Owner reconciled CPU/build and all prior Study D charges; current credit confirmed; no card'
```
Wait for SUBMITTED, then use app list/logs. Download after closure into a fresh
empty gemma-v02418-smoke-return-001 folder using the same Volume get pattern.
Return full evidence/log/receipts/current billing, then stop for smoke audit.
No automatic Stage2/3. No model outputs enter science from this smoke.

## Later pair and virtue — still not approved

Only after smoke projections fit unchanged time guards and owner approves pair,
compute the audited previous report hash and use fresh billing values:
```sh
cd ~/taa-lab
PREVIOUS_SHA="$(shasum -a 256 ~/taa-results/gemma-v02418-smoke-return-001/smoke/report.json | awk '{print $1}')"
caffeinate -dis ~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_stages_v02418.py \
  --stage pair --approved \
  --approval-receipt "Owner approved Study D Gemma pair v02418, commit $REVIEWED_COMMIT" \
  --actual-total-usd "$ACTUAL_TOTAL_USD" --available-credit-usd "$CREDIT_LEFT_USD" \
  --billing-attestation 'Owner reconciled previous stage/all months; current credit confirmed; no card' \
  --previous-report-sha256 "$PREVIOUS_SHA"
```
Refresh actual/credit variables **again** after pair audit before separately
approved virtue. Hash the returned pair/report.json, then use identical command
with `--stage virtue`, receipt `Owner approved Study D Gemma virtue v02418, commit
$REVIEWED_COMMIT`, and that pair report hash. Keep caffeinate/spawn acknowledgement,
fresh empty result folders, private retention and deletion receipts unchanged.
The virtue window may extend into November; cumulative Study D spend never resets.
