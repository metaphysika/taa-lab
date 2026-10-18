# Review-only Mac commands — v0.24.14 Gemma base gate

Do not launch until the owner approves the new exact commit after both CI checks.
No training command exists for this revision. The accepted v0249 commands are archival.
The Modal Secret must be named `huggingface`, containing `HF_TOKEN`. Keep the HF token
in Modal, and the Modal credentials in the Mac's existing authenticated SDK profile
(`~/.modal.toml`), never in the repo, this document, Terminal command arguments or chat.

## Clone or update without discarding local work

If the repo is not on the Mac yet, clone it first:

```bash
git clone https://github.com/metaphysika/taa-lab.git ~/taa-lab
```

For an existing checkout (or after cloning):

```bash
cd ~/taa-lab
git status --short
git fetch origin
git pull --ff-only origin main
git rev-parse HEAD
```

If a fast-forward fails or local changes affect this package, stop for review. Do not
reset files or merge a new implementation into an already approved run.
Use Python **3.12**, matching the remote serialized image:

```bash
python3.12 -m venv ~/modal-study-d-gemma
~/modal-study-d-gemma/bin/python -m pip install 'modal==1.6.2'
```

Existing Mac Modal authentication is used automatically. If absent, run
`~/modal-study-d-gemma/bin/modal setup` and complete the browser login yourself.
No token needs to be pasted into chat or copied into this repo.

## After separate exact-commit approval only

Owner first checks dashboard total Study D spend, including all failed builds,
that no other Study D job is running, and that no card is attached ($30 monthly
credit provider backstop). New gate reservation is $3.801778; actual total must
be at least $2.17. Code retains the old cumulative reservation $5.501778,
then adds $3.801778, for $9.303556 conservative accounting under $25. Price/credit state must still
match the review. If any attempt already exists, stop; never delete a marker or
reset a Dict to make the command work. There is no automatic relaunch.

Set `ACTUAL_TOTAL` to the reconciled actual total **before** this gate, not a guess or
credit balance. Use `2.17` only if still the current dashboard total, including the v02413 attempt. Set `REVIEWED` to the full approved
40-character commit shown by GitHub. Commands below are templates, not approval.

```bash
REVIEWED='PASTE_FULL_OWNER_APPROVED_COMMIT_HERE'
ACTUAL_TOTAL='2.17'
test "$(git rev-parse HEAD)" = "$REVIEWED"
~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_base_v02414.py \
  --preflight-only --approved --actual-total-usd "$ACTUAL_TOTAL" \
  --approval-receipt "Owner approved Gemma base-format gate v02414, commit $REVIEWED" \
  --billing-attestation 'Dashboard prior reconciled; no other Study D workloads; no card attached; current prices unchanged'
```

If the test or preflight fails, stop. Then execute **once** with the same inputs:

```bash
~/modal-study-d-gemma/bin/python scripts/formation_study_d_gemma_base_v02414.py \
  --approved --actual-total-usd "$ACTUAL_TOTAL" \
  --approval-receipt "Owner approved Gemma base-format gate v02414, commit $REVIEWED" \
  --billing-attestation 'Dashboard prior reconciled; no other Study D workloads; no card attached; current prices unchanged'
```

The launcher writes a local durable attempt receipt BEFORE any image build at
`~/.local/state/taa-study-d/gemma-base-v02414-local-attempt.json`, then calls
`modal run --detach`. Keep this receipt even if image build or serialization fails.
Wait until Terminal confirms the app started and gives its app ID; then closing the
laptop is safe. Detached execution does not depend on leaving a local controller up.
The finite window is **2026-10-18 04:00 UTC <= launch < 2026-10-24 04:00 UTC**.
Expiry requires a reviewed revision, not changing the clock or removing markers.

## Read status and download after terminal completion

```bash
~/modal-study-d-gemma/bin/modal app list
~/modal-study-d-gemma/bin/modal app logs APP_ID_FROM_LAUNCH
```

Dashboard must show the app finished and zero live containers. A guard/unknown
terminal state requires review, never a second launch. Download into a **new empty**
folder, using destination `.` (avoids the earlier directory error):

```bash
mkdir -p ~/study-d-results/gemma-base-v02414-return-001
cd ~/study-d-results/gemma-base-v02414-return-001
~/modal-study-d-gemma/bin/modal volume get taa-study-d-gemma-base-v02414-evidence / .
cd ..
zip -r gemma-base-v02414-return-001.zip gemma-base-v02414-return-001
```

Return the unmodified zip, app ID, launch commit, local attempt receipt and the
current dashboard Study D total. The audit must check all 34 episodes, raw receipts,
format thresholds, W bounds, memory/load/speed, reservation and actual dashboard
cost. No training, rerun, adapter creation, deletion of old evidence or ledger reset.

The old v02413 ledger, local receipt and evidence must remain untouched. This revision changes utilization to 0.95, keeps 16,384 context, and requires both KV preflights before generation. No weights-cache Volume is created. Review this new commit and obtain separate approval before either launch command.
