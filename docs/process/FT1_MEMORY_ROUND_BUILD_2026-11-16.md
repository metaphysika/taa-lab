# v0.24.92 FT1 memory round (EXPLORATORY, build only)

Evidence: tests/test_ft1_memory.py, tests/test_ft1_evaluate.py and tests/test_ft1_throughput.py contain CPU fixtures. This is code only, no run, $0.

Checked: synthetic OOM tracking, three-consecutive stop, receipt refusal, plan-only notebook, public ladder continuation and token parity. Validation totals are reported in the PR. Not checked: real attention dispatch, GPU memory reclamation, actual fit, speed or output parity. No GPU, model, Kaggle, Modal or workflow execution occurred.

The shared evaluation/throughput loader logs requested and configured attention implementations (including text_config), torch and transformers versions. These are configuration observations; they do not establish which low-level CUDA kernel dispatched.

Evaluation catches CUDA OOM and equivalent RuntimeError text during generation, releases local tensors, collects garbage and empties the CUDA cache after leaving the exception scope. The journal records mechanical_oom, prompt token count, turn index and cell identity. Prior turns remain retained. The failed episode is never assigned a conduct label or retried. Test parts continue to the next cell. Three consecutive OOM cells stop the part with stopped_mechanical_oom; a successful cell resets the streak. Three permits isolated large episodes while bounding repeated failures. Unattempted cells are not fabricated as unknowns. report.json and metadata distinguish stopped from complete and count OOMs separately.

Acquisition and format gate failures are counted separately as mechanical OOMs. The gate continues unless three consecutive episodes fail; any OOM leaves the gate mechanical_unknown with acquired=false, without recomputing the prescribed scoring thresholds from missing replies. It cannot authorize evaluation, including base evaluation. gate.json is still written. Scoring code and training code are unchanged.

The new fit_limit phase requires a separate exact-commit receipt with phase=fit_limit. Its local stager defaults PLAN_ONLY=True, internet off, one visible T4 and no FT1 data, sealed cases or adapters. It binds public execution sources without opening sealed.py. Stage after committing:

    python -m exploratory.ft1.fit_limit_stage --plan --commit EXACT_SHA --owner metaphysika --repo-dataset metaphysika/taa-k2-repo-SHORT_SHA --receipt-dataset metaphysika/ft1-fit-approval-SHORT_SHA --model-source google/gemma-3/transformers/gemma-3-12b-it/1 --output .k2-launch/ft1-fit-EXACT_SHA

Each eager/sdpa backend loads a fresh untrained NF4 base and measures public rendered prompts trimmed to 2500, 4000, 6000, 8000, 10000, 12000, 14000 and 16000 tokens. It forces exactly 1024 new greedy tokens, ignoring EOS, to test the full output allowance. These are synthetic speed inputs, not evaluation episodes. Each backend stops climbing at its first OOM; the other backend is still attempted. Later unattempted lengths have no invented fit status. A cooperative 45-minute deadline includes loading and checks each decoding step; an active forward can overrun. Handled interruption retains events, metadata and manifest.

Measurements include peak allocated/reserved bytes, prefill seconds, decode tokens/s (excluding the first generated token, which comes from prefill), generated token IDs and prompt hashes. SDPA records first divergence against eager on identical prompts; unavailable references are explicit. Equality has a null divergence; a length mismatch diverges at the shorter length. This is descriptive parity, not a correctness gate.

Open decision: three consecutive OOM cells is a proposed operational stop. The largest successful ladder point is not yet a declared evaluation prompt ceiling. After an approved measurement, propose a conservative backend-specific ceiling with headroom for adapter and real-history overhead, validate it separately, and obtain prospective approval before changing evaluation limits. No prompt truncation or scoring amendment is introduced here. Existing 0449a230 training runs need no restaging.
