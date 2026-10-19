# v02421 speed smoke — FAIL / STOP_FOR_REVIEW

Recorded October 19, 2026 (America/Chicago). Commit
`3d7082a37ac40f38c260452b4b01e8306fe15a78`.
App `ap-sM28o960wczCljEZdMdxaT`; call `fc-01M59Y2BG46A1T7BE0Z6AH1RYS`.
Owner reports one launch at 6:16 AM CDT, stopped at 6:26 AM CDT.

The supplied controller and worker reports confirm STOP_FOR_REVIEW / no_restart.
Training completed: 8 optimizer steps, 64 examples, 10,438 tokens in
47.819389117 seconds; coverage 410 LoRA modules. This is excluded engineering
training, not a completed scientific arm. The report's training_authorized=false
field does not negate the completed training recorded in training.json; no
further training is authorized.

Live vLLM engine initialization stopped during kernel warmup, before benchmarking.
The returned native log contains the owner-reported root error:
`RuntimeError: Could not find nvcc and default cuda_home='/usr/local/cuda' doesn't exist`
(FlashInfer JIT sampling compilation). The outer child failure and engine-core
initialization wrapper errors are also preserved. This is an engineering
software/dependency stop, not a scientific format failure or null result.
No benchmark cells completed, no winner or serving tokens/s measurement, no
merged phase and no projections. No scientific acquisition/transfer ran.
Worker software wall time 553.710365725 seconds; sampled device-wide peak
79,202,942,976 bytes, with telemetry measurement_failed=false. Sampling is not
an exact allocator peak.

Submission billing: $5.41 used / $24.59 remaining. Cumulative cap $30;
reservation $2.452888888888889, target $2.50. Actual post-attempt invoice and
updated dashboard totals were not supplied; no actual cost is inferred from
reservation or worker time. Old ledgers, markers, reservations and evidence
remain unchanged. No remote retention/deletion check performed; no adapter
deletion requested here. Review-stop private-adapter retention policy remains.

Preserved the unmodified ZIP, app log and both local receipts; extracted all
56 files after checking safe paths and ZIP CRC. Verified all 39 carried CPU
hash references and all 36 carried CPU files against the previously recorded
CPU return. Added local hashes for every received/extracted file. Original ZIP,
safetensors and full tokenizer remain private locally and are ignored by Git.

Owner instruction is record only, then await Claude's instructions and owner
review. No fix, code change, launch preparation, relaunch, ledger modification
or remote execution performed. Once-only approval consumed. Pair and virtue
remain unapproved and blocked.
