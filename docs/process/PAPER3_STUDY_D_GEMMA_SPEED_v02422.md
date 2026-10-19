# Study D v02422 — sampler correction to the second engineering smoke, FOR REVIEW; no launch approval

The v02420 smoke at commit 90454d4 / app ap-sc9f25Ju3Y8b54rX4f6Sw1 is
COMPLETE with failed projections. Eight diagnostic optimizer steps took 79.38 s,
131.4931 training tokens/s. Live-LoRA generation was 4.6895 tokens/s, versus the
previous base observation 9.03 tokens/s (different workloads; not a causal estimate).
Owner notes first turns 36–44 s and later turns 9–11 s. Handoff passed; two excluded smoke
episodes closed correctly; sampled peak 82.51 GB; returned deletion receipt says
adapter DELETED/verified absent. All evidence is retained, including old ledgers.
Nominal full arms 14,095–16,609 s do not fit 6,000 s guards; worker estimates
$12.53/$14.76/$12.78 do not fit pair $12 / virtue $6. They remain BLOCKED.

## v02421 engineering failure and minimal correction

v02421 commit 3d7082a37ac40f38c260452b4b01e8306fe15a78 / app
ap-sM28o960wczCljEZdMdxaT stopped during engine warmup. Its eight diagnostic
training steps completed (10,438 tokens, 47.819389 s, 410 LoRA modules); no
benchmark, merge phase or scientific episodes ran. It is an engineering failure,
excluded from science, with no speed winner or projections. Raw returned evidence
and all old ledger/Volume/once markers are preserved unmodified. Private review-stop
adapter retention remains; no remote cleanup or relaunch is performed.

Pinned vLLM 0.31.0 topk_topp_sampler.py checks the sampler environment flag before
selecting FlashInfer. Per-request generators already select forward_native;
all Study D requests and the benchmark explicitly seed their requests. The
unseeded engine dummy warmup selected FlashInfer and needed nvcc. New revision
sets VLLM_USE_FLASHINFER_SAMPLER=0 in every live/merge/merged child environment,
the image environment, and again before any vLLM import in the benchmark.
No CUDA toolkit/nvcc installation, compilation suppression, warmup suppression,
eager fallback or graph change is introduced.

Immediately after engine init, require native log text
`FlashInfer top-p/top-k sampling disabled via VLLM_USE_FLASHINFER_SAMPLER=0`.
Any `Using FlashInfer for top-p & top-k sampling` line, even with a disabled
line, stops before generation. Missing disabled line also stops. Save the checked
log hash and attestation. The prospective science Serving wrapper applies the
same environment and log guard before allowing requests to be queued; it has
NO arm launcher and does not approve future scientific execution/configuration.
It inherits the byte-unchanged science SamplingParams with explicit per-request
seed. A future selected serving implementation still requires review.

Free CI checks every active speed child environment, both science/benchmark
seed construction paths, pre-import ordering and pre-generation log guard;
healthy synthetic log passes and the byte-identical archived v02421 engine log
fails. Archived launches are preserved, not enabled or retroactively modified.

v02421 native post-capture log reports KV 14.26 GiB, graph capture 0.09 GiB.
The unchanged conservative rule gives 14.26 - 0.005 - (0.09 + 0.005) - 0.25
= 13.910 GiB; minus the 13.765 GiB requirement leaves **0.145 GiB**.
The native available-minus-requirement difference alone is 0.495 GiB; that is
not the conservative margin. These are rounded-log calculations, not a claim
that the failed constructor returned successfully. v02422 saves both margins
from its own actual post-capture log; missing/short evidence stops as before.
No v02422 memory measurement exists before launch.

Owner's post-attempt dashboard: **$5.89 used / $24.11 credit remaining**.
Displayed interval cost is $0.48 relative to $5.41; includes all intervening
charges, not a separately itemized invoice. No refund or reservation reset.

## Proposed implementation experiment

A new, separately approved once-only A100 80GB worker, bf16, pinned libraries and
model revision identical to v02420. Retrain the SAME contrary diagnostic adapter
for 8 steps, 64 examples, never a scientific arm. No dose, learning rate, loss mask,
LoRA architecture/targets/rank, cases, predictions, parser, scorer or thresholds
change. Real CPU PASS receipt and all its listed evidence/digests must verify
against v02420 commit 90454d4 and durable cpu/pass BEFORE any new GPU reservation.
Copy the checked CPU evidence into the new namespace; never modify/commit the
old Volume or Dict. The existing trainer is byte-identical. Its legacy commit
and asset fields identify the CPU proof; execution_commit records the new code.
The new exact-commit approval governs execution, never the old approval.

Two fresh, isolated serving subprocesses in one GPU worker, sequentially:

1. Live trained LoRA, enforce_eager=False, cudagraph_specialize_lora=True.
2. LoRA safely merged into bf16 weights using pinned PEFT, no active LoRA in
   vLLM; CUDA graphs enabled. Same tokenizer revision and generation path.

Both keep gpu_memory_utilization=0.95, max_model_len=16384, max_num_seqs=2 and
unquantized bf16. Capture sizes [1, 2] limit graph overhead to the planned decode
concurrency. No eager fallback, automatic context reduction or parameter retry.
Pinned vLLM 0.31.0 documents cudagraph_specialize_lora as separate active/no-active
LoRA graph variants; this does NOT promise faster execution for an active adapter.
See the pinned upstream compilation.py and llm.py references in plan.json.
Native effective graph settings, graph capture duration/memory and engine logs
are saved. Historical KV prediction is preliminary only. AFTER graph capture,
current native available KV minus rounded graph memory (conservative even if
already profiled) minus 0.25 GiB must still cover 13.765 GiB for 16,384 tokens; device
free memory must also exceed 0.25 GiB. Missing graph/profile evidence or a shortfall
stops before generation. No assertion of actual graph-memory PASS before a run.

Merge integrity: fixed first W prompt, same tokenizer IDs, eval/no dropout;
compare the full vocabulary logits at the last prompt position live versus
safe_merge, on the same bf16 model. Require max absolute difference<=0.5 AND
relative L2<=0.01, finite. These engineering tolerances allow bf16 rounding;
they do not establish behavioral equivalence. Save prompt IDs, thresholds,
measured errors and private checkpoint SHA index; failure stops with traceback.
A free tiny random float32 PEFT merge/save/reload regression runs in GitHub CPU
checks. It does not substitute for the bf16 real-model merge check.

## Fixed speed comparison and caching

The benchmark freezes first and later request histories from both previously
excluded brake W/U smoke episodes. Full fixture keys, messages, source request
IDs and original event SHA are in benchmark.json. Later histories are frozen,
not generated by the candidate engines. No scientific outputs are repaired or
resent. Engineering requests are new, explicitly labeled measurements; all
outputs excluded from science. No acquisition or scientific transfer is run.

Each engine: one fixed two-request warmup, then two rounds × two policies ×
two turns × two independent streams. Eight measured requests per policy, two
concurrent sequences. For reproducible timing only, each request emits exactly
64 tokens (min_tokens=64 / ignore_eos=True, max_tokens=64); this is disclosed as a
benchmark-only override, NOT a proposed scientific generation change. Scientific
4,096/default sampling/thinking and 12 steps stay frozen in future arms.
Both engines enable prefix caching: cold policy resets the cache before every
turn batch; retained policy resets at each new episode batch only. Order is
cold/retained then retained/cold. Save raw outputs, IDs, total tokens, per-batch
first/later times, round times, engine load, sampled device memory and logs.

Select by lowest total fixed-workload wall time, never correctness/format/prose.
Within an engine retain prefixes only for >=5% timing benefit; otherwise select
cold-reset policy. All four cells must complete, with exactly 512 measured tokens
per cell; otherwise no winner. Persist a selection manifest applying IDENTICALLY
to all arms. Future full-arm code is not executable in this revision, and requires
owner review/approval after speed results. No outcome-driven configuration choice.

## Budget, time and projections

Whole-worker ceiling $3.20/hour (previous approximate actual $2.45/hour), two cores
and 64 GiB CPU RAM. GPU timeout 2,300 s + startup 120 s + idle 2 s reserves $2.152889;
$0.30 allowance for image/CPU/controller/new temporary storage yields
**$2.452889**, below$2.50. Software deadline 2,100 s; terminate child before provider
timeout, preserve errors/private assets and stop; no partial winner or retry.
Projected normal finish is uncertain: training/load from smoke ~550 s, two graph
loads and compile ~500–900 s, merge load/check/save ~120–300 s, benchmark ~150–300 s,
roughly 1,320–2,050 s (0.37–0.57 GPU-hours), plus startup. Graph compilation or
weight/merge I/O can exceed this; completion within target is NOT guaranteed.
No persistent weight cache added. Merged weights reside temporarily in the
private Volume; allowance includes conservative short-lived storage rather than
claiming storage is free. Review stops retain it pending owner deletion decision;
clean engineering completion deletes merged checkpoint and adapter with receipts.

At updated totals, actual $5.89 + reserve $2.452889 =8.342889; current cap $30 leaves
$21.657111 unreserved cumulative headroom and October credit after reservation.
This reserves ONLY the speed experiment, not unaffordable full arms. Billing
inputs must be refreshed before approval/launch; no live invoice meter is claimed.
No card is attached per owner, providing the provider free-credit backstop.
Code enforces current actual+reservation<=30 and reservation<=available credit.

After completion, extrapolate training from actual backward-pass throughput;
transfer from selected fixed-workload throughput, original 9001/34 mean output
and 132 episodes, plus unchanged acquisition/secondary counts (120/220/120), load,
merge/save if selected and 300 s allowance. Save parent-measured phase wall times including checkpoint
hashing, Volume commits and subprocess I/O; projections include those overheads,
not just the model constructor. Show nominal, 25% stress (not confidence
bounds), 4096-token tail sensitivity, each existing 6,000 s guard, full three-arm costs,
October all/pair/virtue subsets after smoke reserve, November fresh $30 credit
coverage separately from current cumulative $30 cap. Monthly credits never reset
actual cumulative spend. Owner alone decides cap increase/schedule after review.
Current slow smoke extrapolation totals ~$40.07 worker-only BEFORE new smoke,
so no claim the present plan fits October or a fresh November $30.

## Window, evidence and review stop

New finite window October 19, 01:00 UTC through October 26, 01:00 UTC exclusive, 2026
(October 18, 8 pm through October 25, 8 pm America/Chicago).
New namespace taa-study-d-gemma-v02422-speed-{budget-once,evidence,private};
claims speed/once, speed/worker-once and speed/closed, durable reservation file,
new local attempt and acknowledged submission receipts. Old v0249–v02421
namespaces/evidence/markers remain untouched. Any unknown/interrupted/already
claimed stage stops for review, never resets/relaunches. Full sanitized message
and traceback saved on failure. No direct model API calls or full-arm launches.

Mac instructions are in studies/formation-study-d-gemma-speed-v02422/MAC_COMMANDS.md.
Push and confirm Harness (including actual CPU merge test) and Formation3.9;
then STOP FOR REVIEW. Neither this preparation nor passing CI approves launch.
