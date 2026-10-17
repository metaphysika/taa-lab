# Mac launch route — review now; do not launch until separately approved

No GPU work has run. Copy commands from this file only after the relevant
base/study approval. The owner chooses the model only after the base audit.
This review revision expires at 2026-10-23T00:00:00Z (before the seven-day
Modal Dict inactivity expiry can reopen a slot); later execution needs review.
Run the base exactly once; any interruption or missing output requires review,
not another launch. The 500 dose and Kaggle route are inactive.

## 1. Get the reviewed repository (Mac Terminal, no remote compute)

If you do not have a checkout:

```bash
git clone --branch review/study-d-modal-v0249 https://github.com/metaphysika/taa-lab.git "$HOME/taa-lab"
cd "$HOME/taa-lab"
```

If you already have that checkout:

```bash
cd "$HOME/taa-lab"
git status --short
git fetch origin review/study-d-modal-v0249
git switch --track origin/review/study-d-modal-v0249
# If that local branch already exists, use:
# git switch review/study-d-modal-v0249
# git pull --ff-only origin review/study-d-modal-v0249
```

If Git reports local edits or a conflict, stop rather than discard work. Confirm
the reviewed commit with `git rev-parse HEAD`; later execution approval should
name that full commit. Do not update it after approval without review.

```bash
python3.11 -m venv "$HOME/modal-study-d"
"$HOME/modal-study-d/bin/python" -m pip install 'modal==1.6.2'
"$HOME/modal-study-d/bin/modal" setup
"$HOME/modal-study-d/bin/modal" app list
```

Use Python 3.11 (or an existing Python 3.12 environment); the remote image
matches the Mac client minor version because functions are serialized. Check
`"$HOME/modal-study-d/bin/python" --version`. Python 3.13/3.14 are refused. If
Python 3.11 is unavailable, install it with `brew install python@3.11` first
(Homebrew must already be installed), then create the environment as above.
If setup/authentication is already complete, omit `modal setup`. It stores
credentials in `~/.modal.toml`; never copy them into this repository or chat.
The HF token stays in the Modal UI Secret **huggingface**, key **HF_TOKEN**,
under environment **main**. Previous `huggingface-secret` is a different name:
make the requested `huggingface` available through the Modal UI before launch.
No local HF token or other API credentials are needed.

Review https://modal.com/pricing and your account's limits first. The following
launches attest: no previous Modal Study D charges, whole-worker price ≤$3/hour,
gross-usage study limit $25, free-credit/no-paid-overflow controls verified. If
any of these are false/unknown, do not use the commands. The rate and price basis
must include CPU and RAM, not GPU price alone. A net payment limit after $30
credit is not a $25 gross-usage limit. The code cannot query a live invoice.

## 2. Base gate — ONLY AFTER separate approval of this Modal revision

Replace the receipt text with the owner's exact approval reference; it must
identify the reviewed Modal commit. These are not current execution instructions.

```bash
cd "$HOME/taa-lab"
PYTHONPATH=scripts "$HOME/modal-study-d/bin/modal" run --env main --detach \
  scripts/formation_study_d_modal_base_v0249.py \
  --approved \
  --approval-receipt 'REPLACE WITH EXPLICIT MODAL BASE APPROVAL AND COMMIT' \
  --prior-usd 0 --hourly-ceiling 3 --account-cap 25
```

Wait for Modal to finish uploading/building and print the app URL/ID. Once the
detached app is running remotely you may close Terminal/laptop. The controller
is remote; it does not rely on a live Mac process. Record the app ID and version.
Do not run the command twice. An attempted launch may have spent even if local
Terminal reports a connection error; inspect status before any review decision.

```bash
"$HOME/modal-study-d/bin/modal" app list --env main
"$HOME/modal-study-d/bin/modal" app logs APP_ID_FROM_LAUNCH --env main --follow
```

`app logs --follow` streams logs; Control-C only stops watching. Do not issue another run
to check status. You can also inspect the original app URL in Modal's dashboard.
All ordinary raw evidence is saved in the Volume; download it after the app stops:

```bash
mkdir -p "$HOME/study-d-results-v0249"
"$HOME/modal-study-d/bin/modal" volume get \
  taa-study-d-v0249-evidence / "$HOME/study-d-results-v0249/base-boundary" --env main
```

Use a fresh destination for each download; do not overwrite earlier evidence.
Return the entire downloaded folder for offline source/native/replay/parse/action/
headroom/missing/closure/timing/billing audit. Both models must be reported; the
gate alone does not select a model. Actual billing/quota and deletion of ephemeral
containers must be checked in the Modal dashboard. Stop here for review.

## 3. Three-arm study — ONLY AFTER accepted base audit and separate training approval

Owner explicitly selects ONE base with format PASS and headroom available. Replace
MODEL_ID with exactly `meta-llama/Llama-3.1-8B-Instruct` OR
`Qwen/Qwen2.5-7B-Instruct`; never automatically choose whichever looks better.
Keep `--prior-usd 0`: it is the pre-study baseline; the same once-only ledger
already includes the base's full reservation. Do not put the base cost in again
or reset the ledger. Any charges outside the original reservation need review.

```bash
cd "$HOME/taa-lab"
PYTHONPATH=scripts "$HOME/modal-study-d/bin/modal" run --env main --detach \
  scripts/formation_study_d_modal_train_v0249.py \
  --approved \
  --approval-receipt 'REPLACE WITH SEPARATE TRAINING APPROVAL AND COMMIT' \
  --base-audit-receipt 'REPLACE WITH OWNER ACCEPTANCE OF BASE AUDIT' \
  --model 'MODEL_ID' \
  --prior-usd 0 --hourly-ceiling 3 --account-cap 25
```

Three arms run concurrently; each has a two-hour gross reservation, including
load/train/acquisition/wait/conditional transfer. Pending human acquisition coding
or a failed peer gate stops all transfer and deletes the adapters. This is not a
training null and never authorizes another launch. Known sufficient successes
can pass without recoding only under the protocol's conservative bounds.

```bash
"$HOME/modal-study-d/bin/modal" app list --env main
"$HOME/modal-study-d/bin/modal" app logs APP_ID_FROM_TRAINING_LAUNCH --env main --follow
"$HOME/modal-study-d/bin/modal" volume get \
  taa-study-d-v0249-evidence / "$HOME/study-d-results-v0249/study-boundary" --env main
```

Return the complete folder plus the dashboard's actual Study D charge totals.
Adapters/optimizer files never enter the result Volume, and ordinary exits save
deletion receipts. Missing cleanup receipts after hard termination require
explicit container/ephemeral-storage audit. No deployment/sharing, retained study
adapter, extra dose, training rerun or paid overflow is authorized. Preserve the
once-only Dict; do not delete it to relaunch. Stop for final offline audit.

If an active app must be stopped for safety/budget, use the exact app ID:

```bash
"$HOME/modal-study-d/bin/modal" app stop APP_ID_FROM_LAUNCH --env main
```

Stopping may bypass cleanup; retain all evidence and report that fact. Never
claim the $25 invoice cap is independently verified by the code: the code bounds
reserved compute, while account billing controls and invoice reconciliation are
the separate final protection.
