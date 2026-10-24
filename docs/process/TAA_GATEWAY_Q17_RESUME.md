# Q17/Q17.1 continuation record

As of 2026-10-24, PRs #33, #34 and #35 are merged in order. #35 merge is `a4ca466bee830dc38a2136321237c146664547bd`, after all eight checks passed at `1eb71b1c`.

Implementation branch: `fix/gateway-q17`, worktree `/workspace/taa-comparison-v02`. Python: `/workspace/scratch/gateway-py311/bin/python`. Use `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`. No model calls, Modal operations, spending, deletions, Notion edits or public releases.

The final post-IR1 code passes 1,132 tests (36 optional skips), 77 component tests and scripted scenarios. Final normative acceptance passes on reference/core/conventional: 153 scenarios and 1,079 source assertions each, zero discrepancies/incomplete. Frozen v0.2.2 and W0 remain unchanged. The failed first discovery and all pre-repair results are retained and labeled. Never change an expected outcome to match an implementation.

Verification is complete. Do not restart the obsolete freeze controller or the scoring driver. All final exit files in `/workspace/scratch/gateway-q17/` are 0: discovery-final, components-ir1-repair, acceptance-final, all-arm-replay-final, scoring-verification and metric-verification. The failed first discovery and its guard exit 1 remain historical evidence.

The clean runtime is `a91ffa91716d28d438caeb233a74d1e58597defc`. The completed new run is `/workspace/scratch/gateway-cross-arm-scoring-v02-q17`; all 320 episodes match the original v0.2 journal byte-for-byte. Full metrics, manifests, scripts and raw state audits are retained in `docs/process/evidence/gateway-q17-verification/`. No verification rerun is needed.

The final engineering replay has zero unexpected discrepancies and zero incomplete assertions in executed cases. Four known floor/static financial fault audits remain explicit; 143 TraceGrant tasks are unrun without frozen contracts, and eight floor/static fault boundaries are not applicable by design. No wider coverage is claimed.

PRs #33–#35 are merged on green CI. Q17/Q17.1 is PR #36, awaiting Claude review and Astra confirmation before demo sign-off. On continuation, inspect this PR's latest head/reviews/CI first. Do not infer permission for a model call or launch from a merge.

Q17/Q17.1 and Astra's exact limitations are recorded in the requested documents. The demo protocol must prospectively decide whether the model can read the MCP session decision log. Q17 merge needs green CI and Claude review; Astra confirms Q17 before demo sign-off. A merge does not authorize launch or spending.
