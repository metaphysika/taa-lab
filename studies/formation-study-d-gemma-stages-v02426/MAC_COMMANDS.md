# v02420 Mac launch templates — NOT APPROVED

Preserve all old attempts, ledgers and Volumes. No old approval transfers.
Clone if needed: `git clone https://github.com/metaphysika/taa-lab.git ~/taa-lab`.
Existing checkout: `cd ~/taa-lab`, `git status --short`, `git fetch origin`.
Preserve unexpected changes; then `git checkout --detach FULL_REVIEWED_COMMIT`.
Use existing Python3.12 environment `~/modal-study-d-gemma` and Modal1.6.2.
If missing: `python3.12 -m venv ~/modal-study-d-gemma` then
`~/modal-study-d-gemma/bin/python -m pip install 'modal==1.6.2'`.
Auth remains in ~/.modal.toml; HF_TOKEN only in Modal Secret huggingface. No keys
in Git/chat/commands. No auth or model downloads needed for offline review.

## Separately approved CPU data + tiny-model rehearsal

Read the plan: this stage performs two diagnostic optimizer steps on a tiny
random CPU model, no pretrained weights or GPU. Owner now confirms $4.72 used/$25.28 left after v02419 CPU. Refresh actual cumulative
spend and available credit again if dashboard changes.
The full remaining reserve is $20.181750; current actual must be <=$9.818250 under the owner-approved $30 cap.
Set variables to actual numbers, not placeholders:

```sh
cd ~/taa-lab
REVIEWED_COMMIT="$(git rev-parse HEAD)"
ACTUAL_TOTAL_USD=4.72
CREDIT_LEFT_USD=25.28
caffeinate -dis ~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_stages_v02420.py \
  --stage cpu --approved \
  --approval-receipt "Owner approved Study D Gemma cpu v02420, commit $REVIEWED_COMMIT" \
  --actual-total-usd "$ACTUAL_TOTAL_USD" --available-credit-usd "$CREDIT_LEFT_USD" \
  --billing-attestation 'Owner reconciled every Study D charge; current credit confirmed; no card' \
  --preflight-only
```
Only after exact-commit CPU approval, run without `--preflight-only`.
Wait for `SUBMITTED — safe to close laptop | app_id=ap-... | call_id=fc-...`.
The controller is spawned, not waited on. No line/error/disconnection/unknown
state: preserve receipts, stop, never relaunch or reset anything.

```sh
~/modal-study-d-gemma/bin/modal app list
~/modal-study-d-gemma/bin/modal app logs ACTUAL_APP_ID > ~/gemma-v02420-cpu-app-log.txt
mkdir -p ~/taa-results
mkdir ~/taa-results/gemma-v02420-cpu-return-001
cd ~/taa-results/gemma-v02420-cpu-return-001
~/modal-study-d-gemma/bin/modal volume get taa-study-d-gemma-v02420-evidence / . --env main
cd ~/taa-results
zip -r gemma-v02420-cpu-return-001.zip gemma-v02420-cpu-return-001
```
Return the unmodified ZIP, log, both local receipts and updated billing. No GPU
auto-launch. CPU receipt, exact sliding/full coverage (v_proj absent in full only), trainable counts, masking,
training-load info, two steps, callbacks, checkpoint hashes and reload must pass.

## Later stages — separate approval after preceding audit

At SAME reviewed commit, refresh billing for EVERY stage. Smoke requires CPU
PASS. Pair/virtue require prior measured projection/closure and reviewed report
hash. Same caffeinate command above, replacing stage and matching receipt with
`smoke`, then `pair`, then `virtue`. Pair and virtue additionally supply:
`--previous-report-sha256 SHA256_OF_AUDITED_PREVIOUS_REPORT`.
Smoke report is previous for pair; pair report is previous for virtue. Compute:
`shasum -a 256 PATH_TO_PREVIOUS_STAGE/report.json`.
Use new fresh empty folders gemma-v02420-smoke-return-001 (then pair/virtue) for
the same Volume get and ZIP pattern. Preserve private adapters on review stop;
never download or share them. Study-end deletion includes tiny CPU model and
adapter artifacts, with receipts. Stages never auto-authorize one another.

Expected real model: 60 layers, 50 sliding/10 full, 410 target modules, rank8
61,214,720 trainable parameters; tiny CPU expected13 modules/7,808 parameters.
CPU/smoke/pair window: October19 01UTC to October26 01UTC exclusive; virtue
throughNovember9 01UTC. New CPU must PASS before any GPU reservation; later
stages remain separately approved. Code caps cumulative actual+remaining reserves
at $30 AND requires all remaining reserves fit available free credit. Old
v02419 stop/ledger/evidence are never cleared. All per-stage targets unchanged.


GitHub now runs a free automatic tiny-model CPU diagnostic on every commit.
Its PASS is NOT a Modal CPU receipt: it uses frozen real-tokenizer IDs and a
CPU torch build, with no HF secret. Follow the separately approved real-tokenizer
Modal CPU step above anyway; there is no automatic GPU launch.
