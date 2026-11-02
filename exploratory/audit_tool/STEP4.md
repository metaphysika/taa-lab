# EXPLORATORY step 4 Modal adapter (v0.24.52)

Build only. No execution approval. Run offline from the repository root:

```
python -m exploratory.audit_tool.step4 --mode mock --attempt 4 --output NEW_DIRECTORY
python -m unittest exploratory.audit_tool.test_modal_adapter exploratory.audit_tool.test_audit -v
```

`modal_adapter.mock` is also a factory for audit.py adapters mode. Adapter wraps
an injected request transport with generate(system, history, turn). The live
launcher batches both A (neutral/contrary) and B (neutral/neutral) into one GPU
allocation. Each pass has 33 fresh episodes and the original 12-turn scorer.
Unknown outcomes keep the audit tool's uncertainty bounds. Mock output tests
plumbing only; it does not test weights or estimate behavioral differences.

Checkpoint verification mirrors verify_reused_adapter's identity, exact roster,
symlink and streaming SHA-256 checks, then binds the index and every file to
private-adapter-deletion-plan.json before loading any model. It supports all
three final arms. A/B use neutral and contrary; virtue is mounted separately
read-only for future use, not evaluated. No historical evidence is modified.
The native model revision, engine and default sampling parameters come from
Study D v02428; max_tokens=4096 and skip_special_tokens=False are explicit.
Seeds follow a Study D style per-episode, per-turn rule rather than a fixed seed:
248017 + case_index * 12 + turn - 1 (zero-based case order in transfer-cases.json).
Run A shares this seed schedule across neutral and contrary arms (paired).
Run B adds pass_id * 396 (33 cases * 12 turns), so its two neutral passes use
disjoint seeds. A and B pass 0 reuse seeds; the comparisons are not independent
replications. Native transcripts record comparison, pass, case, turn and seed.
First decoded replies are retained without repair or retry. Native transcripts,
each finished episode, reports and caught failures are committed to the new
evidence Volume. Forced termination may leave the in-flight episode unresolved.

EXPLORATORY v0.24.55: detached submission replaces the blocking launcher.
No execution approval. The CLI requires explicit --attempt N (N >= 4),
--confirm-spend for live/prefetch modes, no CI, and a clean committed checkout.
Live output is an immediate receipt: app_id, function_call_id, attempt,
started_utc and commit. Results use /results/<commit>/attempt-<N>/ and refuse
an existing folder. Old attempt-3 evidence is untouched.

Future owner-approved Linux launch form (do not execute as part of this build):

```sh
setsid nohup python -m exploratory.audit_tool.step4 --mode live --attempt 4 --confirm-spend --output NEW_RECEIPT.json </dev/null >launcher.log 2>&1 &
python scripts/step4_status.py --call-id RECEIPT_CALL_ID --output NEW_FINAL.json
```

The status command makes one nonblocking poll: exit 2 means pending, with no
final file; 0 means complete; 1 means failed with retained exception details.
Repeat polling externally as needed; it never resubmits. Signal handlers log
UTC time and signal name to redirected stderr and terminate nonzero. The
separate session and detached app address different cancellation risks.

Ledger: entire-step4-cap stays unchanged. attempt-3 records reserved=$20 and
actual_billed=$0.60 (approximate owner-supplied billing). New attempt-N records
reserved=$20, actual_billed=null. Unknown billing retains the full reservation;
no automatic refund/settlement. A durable launch lock serializes reservation
checks; an interrupted lock requires review, never automatic clearing. Missing
historical state fails closed. The cumulative guard sums billed costs when
known and reservations otherwise before adding the new worst case.

CUMULATIVE_CAP is the single provisional cumulative constant, default $21.
The six-hour timeout, 120-second startup, 300-second idle and historical
$3.20/hour plus $0.40 build allowance derive a rounded $20 reservation.
Attempt 3 plus attempt 4 is $20.60. Chris has not approved the cap choice;
changing the cap to $20 alone blocks this launch. A shorter timeout must also
be separately chosen/recomputed if retaining $20. This is a planning guard,
not a provider billing limit. Rates/build charges require approval-time review.
Memory remains 64 GiB. Prefetch has separate CPU costs, not automatically
settled by the GPU ledger; owner approval must account for those costs too.

--mode prefetch defines/submits a CPU-only prefetch_weights function (no GPU),
with the existing HF secret, pinned model google/gemma-4-31B-it revision
842da3794eaa0b77d5f08bae87a17459d91ff475. It downloads the snapshot to
/weights/hub in taa-step4-gemma-weights, records every snapshot file SHA-256 in
weights-manifest.json and commits the Volume. No prefetch was executed here.
The live worker mounts that Volume read-only, checks its identity/roster/hashes
before batch loading, and sets HF_HOME=/weights and HF_HUB_OFFLINE=1.
It does not attach the HF secret to the GPU worker.

policy.ENGINE uses the same model ID and revision plus tokenizer_revision,
with generation_config='auto'; those settings remain unchanged. The layout
matches HF_HOME/hub and the revision snapshot. The pinned vLLM/Transformers
combination has NOT been exercised against this read-only cache: whether it
needs additional writable cache metadata or uncached auxiliary files remains
uncertain. Missing files should fail offline. Prefetch, a CPU detach test,
optional GPU smoke, and exact-commit launch each still need owner approval.
API references: [Modal polling](https://modal.com/docs/guide/job-queue),
[HF cache layout](https://huggingface.co/docs/huggingface_hub/guides/manage-cache).

EXPLORATORY v0.24.54: the mount root accepts a directory symlink; science,
arm and final directories still reject symlinks. Load policy by file path after
the frozen evaluator installs its formation namespace. Match Study D v02428:
Python 3.12; vllm==0.31.0, transformers==5.10.4, huggingface_hub==1.31.0,
nvidia-ml-py==13.580.82, peft==0.21.2, accelerate==1.15.0. Environment:
HF_HUB_DISABLE_TELEMETRY=1, VLLM_NO_USAGE_STATS=1,
VLLM_USE_FLASHINFER_SAMPLER=0, OMP_NUM_THREADS=2, PYTHONPATH=/opt/study-d.
Source packaging differs: step 4 uploads /opt/source.zip, extracts /opt/repo
and adds it to sys.path; Study D copies helpers/assets under /opt/study-d.
No remote image build or execution was performed.


PR #75 review fixes (EXPLORATORY, 2026-11-02): reservation now runs inside
the detached app context immediately before GPU spawn. Image, Volume and app
setup failures do not reserve an attempt. A spawn/receipt failure after the
claim still retains the reservation for review; no automatic refund.

Status exit 2 applies only to the exact built-in TimeoutError with no message
from get(timeout=0). A remote timeout with a message, timeout subclass, or
confirmed remote BaseException cancellation writes a failed final JSON and
exits 1. Local KeyboardInterrupt and SystemExit pass through without writing
any file. Unconfirmed client errors use status poll_error / exit 3 and write
<output>.poll-error.json (replaceable on another poll), leaving the create-only
final path available. Remote classification uses Modal task-ID traceback
frames or explicit Modal remote failure classes, including InputCancellation,
FunctionTimeoutError, RemoteError and InternalFailure. An exception without
remote provenance is treated as a polling error, not proof the worker failed.
This follows the inspected public Modal 1.6.3 client traceback representation;
SDK changes or absent remote traceback data may reduce classification certainty.
A bare timeout from get with no remote provenance remains the pending signal.

New --mode check-weights (with --attempt and --confirm-spend) defines a
CPU-only, read-only check in a new container, using the same offline image
environment as the GPU worker and no HF secret. It does not reserve a GPU
attempt. It runs verify_weights, snapshot_download(local_files_only=True),
AutoConfig.from_pretrained and AutoTokenizer.from_pretrained at the pinned
revision, with explicit local_files_only and no remote code. The snapshot
lookup must resolve to the expected cache snapshot.

The diagnostic report lists symlink paths/targets and target existence,
lookup errors including missing filenames reported by the libraries, and
attempted file opens for writing under /weights (including lock files),
even if the read-only mount denies them. A Python audit hook observes writes;
native-library writes that bypass Python audit events are not captured.
Each lookup is attempted so a missing tokenizer is reported even if config
also fails. The report is printed; lookup errors raise with the report in
the exception for the status recorder, while success returns the report.
This check was defined and unit-tested only, never submitted. It does not
initialize vLLM or prove that vLLM's remaining initialization is compatible
with the mount. CPU check and prefetch costs still require owner approval.

Additional mocked tests cover setup-before-reservation ordering, remote
timeouts/cancellation, extra and missing cache files, HF blob symlinks, the
worker's attempt-N output expression, CPU mounts/secrets, offline lookup
arguments, and write-attempt/missing-file diagnostics. Windows may skip the
real symlink test when symlink privileges are unavailable.


PR #75 second review fixes (EXPLORATORY, 2026-11-02):

Prefetch now calls list_repo_files for the exact pinned revision, compares
the complete local snapshot roster against it, and refuses extra/missing
files. The manifest includes files, repo_files, total_bytes and per-file
SHA-256. This is code for a future approved prefetch; no listing or download
of the model repository was performed during this offline build.

The CPU check reports verify_seconds and runs two passes: explicit
cache_dir/local_files_only, then environment-only resolution with neither
argument, relying on HF_HOME=/weights and HF_HUB_OFFLINE=1 as the worker does.
Both passes check snapshot_download, AutoConfig, AutoTokenizer and
GenerationConfig (engine generation_config='auto'). AutoProcessor is also
attempted in each pass, but its failures are non-blocking diagnostics.
All lookups retain the pinned revision and trust_remote_code=False for
Transformers. This does not run the vLLM engine. The new behavior was tested
with injected library stand-ins only; no Modal call or model loading occurred.


PR #75 third review fixes (EXPLORATORY, 2026-11-02):

Modal ExecutionError messages starting with "Could not deserialize remote
exception" or "Got remote exception of incorrect type" are confirmed remote
failures: failed final JSON / exit 1, even with no remote traceback. Other
ExecutionError messages retain the poll_error classification unless another
remote marker applies. This covers a worker exception class unavailable on
the polling machine. The future owner-approved CPU detach test should
deliberately raise such an exception class and confirm the failed final file.

OutputExpiredError now writes a separate terminal status value expired
(exit 4). Expiration does not establish whether the worker succeeded or
failed; inspect retained evidence. Local interrupts still write no file.

In both CPU cache-check passes, GenerationConfig is reported as
"absent in repo" without blocking when the pinned prefetch repo file list
matches the verified snapshot roster and lacks generation_config.json.
If the file is listed, lookup errors still block. A missing/unverified repo
roster does not justify this exception. No CPU test or cache lookup was run
on Modal; these changes were mock-tested only.
