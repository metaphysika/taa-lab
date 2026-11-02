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
