# Mac launch route — review now; do not launch until separately approved

The owner reports the first Modal launch failed after an image build and before GPU work. Its build charge counts as Study D spend. No new execution is approved. Copy commands from this file only after the relevant
base/study approval. The owner chooses the model only after the base audit.
This review revision expires at 2026-10-23T00:00:00Z (before the seven-day
Modal Dict inactivity expiry can reopen a slot); later execution needs review.
The base launches Llama and Qwen in two parallel A100-40GB containers, each
with its own one-hour slot/$3.125 reservation; the total stays $6.25.
Run the base exactly once; any interruption or missing output requires review,
not another launch. The 500 dose and Kaggle route are inactive.

## 1. Get the reviewed repository (Mac Terminal, no remote compute)

If you do not have a checkout:

```bash
git clone https://github.com/metaphysika/taa-lab.git "$HOME/taa-lab"
cd "$HOME/taa-lab"
```

If you already have that checkout:

```bash
cd "$HOME/taa-lab"
git status --short
git switch main
git pull --ff-only origin main
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
under environment **main**. The owner screenshot confirms the renamed Secret;
no further rename or local HF token is needed. Do not paste token values into
source/chat. Modal auth remains private in ~/.modal.toml outside Git.

Owner confirms no payment card is attached, Starter's $30 free credit is the
provider backstop, and whole-worker rate is about $2.45/hour (A100 + two CPU cores
+ 32 GiB), below the code's $3 ceiling. There is NO Starter environment budget.
The commands record that verified control with `--credit-cap 30` and the rate
with `--hourly-ceiling 2.45`; the software reservation cap remains $25, not $30.
No independent $25 provider account cap is required. Check actual billing at
boundaries; retained private Volume storage is billable until deletion.

## 2. Base gate — ONLY AFTER review/approval of the fixed Modal revision

Replace the receipt text with the owner's exact approval reference; it must
identify the reviewed Modal commit. These are not current execution instructions.

```bash
cd "$HOME/taa-lab"
# Only after owner review/approval: replace these from that approval and audit.
REVIEWED_COMMIT=REPLACE_WITH_REVIEWED_FIX_COMMIT
PRIOR_BUILD_USD=REPLACE_WITH_ACTUAL_TOTAL_FAILED_BUILD_CHARGE
PRELAUNCH_AUDIT_RECEIPT='REPLACE WITH STOPPED APP, ZERO GPU INPUTS, EMPTY LEDGER/EVIDENCE AND BILLING AUDIT'
test "$(git rev-parse HEAD)" = "$REVIEWED_COMMIT" || exit 1
PYTHONPATH=scripts "$HOME/modal-study-d/bin/modal" run --env main --detach \
  scripts/formation_study_d_modal_base_v0249.py \
  --approved \
  --approval-receipt "Owner approved one Modal base-gate relaunch at commit $REVIEWED_COMMIT" \
  --prelaunch-audit-receipt "$PRELAUNCH_AUDIT_RECEIPT" \
  --prior-usd "$PRIOR_BUILD_USD" --hourly-ceiling 2.45 --credit-cap 30
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
headroom/missing/closure/timing/billing audit. It now includes per-model measured
CUDA/wall output TPS and per-arm runtime projections against the training guards.
Review those projections and actual base billing BEFORE any training approval. Both models must be reported; the
gate alone does not select a model. Actual billing/quota and deletion of ephemeral
containers must be checked in the Modal dashboard. Stop here for review.

## 3. Three-arm study — ONLY AFTER accepted base audit and separate training approval

Owner explicitly selects ONE base with format PASS and headroom available. Replace
MODEL_ID with exactly `meta-llama/Llama-3.1-8B-Instruct` OR
`Qwen/Qwen2.5-7B-Instruct`; never automatically choose whichever looks better.
Keep the SAME confirmed `--prior-usd "$PRIOR_BUILD_USD"` from the renewed base: it includes the failed build; the same once-only ledger
already includes the base's full reservation. Do not put the base cost in again
or reset the ledger. Any charges outside the original reservation need review.

```bash
cd "$HOME/taa-lab"
PYTHONPATH=scripts "$HOME/modal-study-d/bin/modal" run --env main --detach \
  scripts/formation_study_d_modal_train_v0249.py \
  --approved \
  --approval-receipt 'REPLACE WITH SEPARATE TRAINING APPROVAL AND COMMIT' \
  --base-audit-receipt 'REPLACE WITH OWNER ACCEPTANCE OF BASE AUDIT' \
  --projection-review-receipt 'REPLACE WITH OWNER ACCEPTANCE OF MEASURED TPS AND ARM PROJECTIONS' \
  --model 'MODEL_ID' \
  --prior-usd "$PRIOR_BUILD_USD" --hourly-ceiling 2.45 --credit-cap 30
```

Three arms run concurrently; each has a two-hour gross reservation, including
load/train/acquisition/wait/conditional transfer. Acquisition uses primary JSON
hours and a separate automatic message-number check, never exact prose or human
pending coding. A failed peer gate blocks all transfer and retains ALL trained
adapters privately for review. This is uninterpretable, not a training null.
No run is repeated, and no adapters are resumed without a new explicit decision.

```bash
"$HOME/modal-study-d/bin/modal" app list --env main
"$HOME/modal-study-d/bin/modal" app logs APP_ID_FROM_TRAINING_LAUNCH --env main --follow
"$HOME/modal-study-d/bin/modal" volume get \
  taa-study-d-v0249-evidence / "$HOME/study-d-results-v0249/study-boundary" --env main
```

Return the complete evidence folder plus actual dashboard charges. Trained
adapters and partial checkpoints stay in the private, non-shared Volume
`taa-study-d-v0249-private-adapters`; they never enter the ordinary result download.
If all arms complete transfer, the controller deletes adapters at the study's end
and saves per-file deletion receipts. If anything stops for review, it preserves
all available adapters until the owner's decision; no worker deletes them on exit.
A hard kill may leave only the last committed partial checkpoint, not the latest
update: inspect its integrity/step record. No deployment/sharing is permitted.
Preserve the once-only Dict; never delete it to restart a stage.

## 4. Delete retained adapters ONLY AFTER the owner's review/end decision

First confirm in Modal that ALL study apps/containers are stopped. This CPU-only
command neither loads a model nor starts a GPU, and can run after the GPU launch
window expires. Replace the decision receipt with actual owner authorization.
It removes only the private study adapter tree, keeping raw result evidence.

```bash
cd "$HOME/taa-lab"
"$HOME/modal-study-d/bin/modal" run --env main \
  scripts/formation_study_d_modal_delete_v0249.py \
  --decision-receipt 'REPLACE WITH OWNER DECISION TO END STUDY AND DELETE RETAINED ADAPTERS' \
  --all-apps-stopped
"$HOME/modal-study-d/bin/modal" volume get \
  taa-study-d-v0249-evidence / "$HOME/study-d-results-v0249/deletion-boundary" --env main
```

Return the deletion receipt as well. DELETE_INTENDED alone is not proof of
completion; require DELETED plus verified absence and the actual billing total.
The private Volume is not publicly shared and there is no adapter download or
endpoint command here. Retained storage continues to count until deletion.

If an active app must be stopped for safety/budget, use the exact app ID:

```bash
"$HOME/modal-study-d/bin/modal" app stop APP_ID_FROM_LAUNCH --env main
```

Stopping may bypass cleanup; retain all evidence and report that fact. Never
claim the $25 invoice cap is independently verified by the code: the code bounds
reserved compute, while the owner-confirmed no-card/$30-credit backstop and billing reconciliation
are the separate provider control; no $25 environment budget is claimed.

## 5. Failed attempt: READ-ONLY audit before any renewed approval

Preserve app `ap-oF13XLMy4ugiiud3zxk3wb` and its full original Terminal output.
Use the already-authenticated Mac; these commands list/read only, not run apps.
The assistant has not executed them. Do not run `dict clear`, `dict delete`,
`volume rm`, or recreate renamed resources to bypass historical claims.

```bash
"$HOME/modal-study-d/bin/modal" app list --env main
"$HOME/modal-study-d/bin/modal" app logs ap-oF13XLMy4ugiiud3zxk3wb --env main
"$HOME/modal-study-d/bin/modal" dict list --env main --json
"$HOME/modal-study-d/bin/modal" dict items taa-study-d-v0249-budget-once --all --json --env main
"$HOME/modal-study-d/bin/modal" volume ls taa-study-d-v0249-evidence / --json --env main
"$HOME/modal-study-d/bin/modal" volume ls taa-study-d-v0249-evidence /base --json --env main
```

If a Dict/Volume/path is not found, preserve that result and distinguish it from
permission/network failure. A missing path is not permission to clear anything.
Dict must be absent or empty. In particular, any `study-manifest`,
`stage-once/base`, `stage-once/study`, or `base-worker-once/MODEL_ID` blocks
renewal. Any `base-reservation.json`, `study-reservation.json`, or partial base
results also blocks renewal. The controller repeats known-claim checks, but the
owner must review all evidence, including unexpected keys/files.

In the dashboard verify the old app is stopped, no GPU inputs/containers ran,
and record actual image-build charges for ALL failed Study D attempts. Image
builds are Study D spend even when charged against free credit. Wrong-Python
refusal is separately logged as local/no Modal contact. If the bill is pending,
unknown, or above $0.50, STOP for review; do not use zero or round down. A known
zero is usable only if the dashboard confirms it. Prior build spend consumes the
existing $0.50 overhead pool; it never changes $6.25 base/$18.25 study workers or
$25 total. Keep the same confirmed prior amount at the later training boundary.

Return the audit and billing evidence before owner approval. The section 2
command is a FUTURE template; it does not authorize or execute the relaunch.
