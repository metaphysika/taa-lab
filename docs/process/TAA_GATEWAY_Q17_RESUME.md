# Q17/Q17.1 continuation record

As of 2026-10-24, PRs #33, #34 and #35 are merged in order. #35 merge is `a4ca466bee830dc38a2136321237c146664547bd`, after all eight checks passed at `1eb71b1c`.

Implementation branch: `fix/gateway-q17`, worktree `/workspace/taa-comparison-v02`. Python: `/workspace/scratch/gateway-py311/bin/python`. Use `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`. No model calls, Modal operations, spending, deletions, Notion edits or public releases.

The final post-IR1 code passes 1,132 tests (36 optional skips), 77 component tests and scripted scenarios. Final normative acceptance passes on reference/core/conventional: 153 scenarios and 1,079 source assertions each, zero discrepancies/incomplete. Frozen v0.2.2 and W0 remain unchanged. The failed first discovery and all pre-repair results are retained and labeled. Never change an expected outcome to match an implementation.

Inspect existing processes, exit files and manifests before restarting anything:

- `/workspace/scratch/gateway-q17/discovery-final.{log,exit}`: complete, exit 0.
- `acceptance-final.{json,log,exit}` in that directory: complete, exit 0.
- `components-ir1-repair.{log,exit}`: 77 tests, exit 0.
- `all-arm-replay-final.{json,log,exit}`: final engineering replay; inspect its current status. The older `all-arm-replay-q171` is pre-IR1-repair evidence.
- `freeze-and-verify.exit` is 1 from the intentionally stopped old controller. **Do not restart `freeze_and_verify.py` or reuse its obsolete guard.** No scoring episode ran through it.

The remaining scoring verification is authorized exactly once, under the unchanged protocol, ten programs, controllers, matching keys and fixed contracts. Use the clean verified implementation commit with `/workspace/scratch/gateway-q17/run_verification.py`, output `/workspace/scratch/gateway-cross-arm-scoring-v02-q17`. The driver rejects a dirty tree, changed protected inputs or an existing output directory. A retained partial run requires review; never auto-retry it.

After a completed manifest, run `/workspace/scratch/gateway-q17/compare_verification.py` with the original `/workspace/scratch/gateway-cross-arm-scoring-v02` and the new output directory. It compares every arm/controller/episode score and stops on any changed cell. **If any score changes, stop and report to Claude.** Retain v0, v0.1 and the original v0.2 score evidence unchanged.

Package final logs, source hashes, the new journal and the complete metric comparison as separate Q17 evidence. Update the verification report, this continuation record and the draft PR. Record every unavailable TraceGrant task and any known floor/static non-atomic fault discrepancies explicitly. TraceGrant reconstruction remains limited to its ten predeclared contracts; no new contracts are authored after outcomes.

Q17/Q17.1 and Astra's exact limitations are recorded in the requested documents. The demo protocol must prospectively decide whether the model can read the MCP session decision log. Q17 merge needs green CI and Claude review; Astra confirms Q17 before demo sign-off. A merge does not authorize launch or spending.
