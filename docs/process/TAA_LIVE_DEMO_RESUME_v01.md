# Live-demo v0.1 checkpoint — inspect before restarting

[Descriptive] **Completion update after the limit reset:** full-004 finished successfully: **1,156 tests, 36 optional skips, 2,219.402s**. All 24 focused controls pass. Final `evidence/gateway-live-demo-v01/validation.json` and `acceptance.zip` are closed; their archive SHA256 is `2948f878df3d5647e26de8f09d3f7e3fe9c46cfa7fd00057bb49a0f9b10cfce9`. The running-process section below is historical checkpoint status, not an instruction to restart. The original checkpoint artifacts remain preserved. Publication and Claude review are the remaining gates; no merge or launch is authorized.

[Descriptive] Chris requested a safe checkpoint before the session limit. Branch: `feat/live-demo-v01`, based on `436fbf002d3e0f9e84a41206fe3c4c43b0d71ed7`. This is a checkpoint exception under the owner's standing “stop at a clean commit if the session runs short” instruction. The ordinary full-test-before-commit gate is explicitly pending, not waived for merge. No merge or launch is authorized.

[Descriptive] Controlling task: `TAA_LIVE_DEMO_BUILD_INSTRUCTIONS_v01.md`. Implementation/proposed prompt/context/cost choices: `TAA_LIVE_DEMO_PLAN_v01.md`. No model, neutral, metadata or Modal call occurred. No keys.env access, spending or scientific scored rerun. No launch receipt is supplied. Real provider ledgers and Paper3 freezes remain unchanged.

## Completed gates

- [Descriptive] Final focused suite: **24 tests PASS** under Python3.11.17, outbound sockets denied. `/tmp/taa-live-demo-tests-006.log` (216.746s).
- [Descriptive] Final source-bound stand-in: all30 episodes COMPLETE, `/tmp/taa-live-demo-final-002/`, log `/tmp/taa-live-demo-final-002.log`. Canned engineering only, actual API cost0. Every checkpoint verifies; final stop campaigns are `/tmp/taa-live-demo-stops-002/`.
- [Descriptive] Complete normative acceptance PASS: each backend153scenarios/1079source, reference/core/conventional audits3939/4055/17925, zero discrepancies/incomplete. `/tmp/taa-live-demo-acceptance-001.json` and corresponding log.
- [Descriptive] Read-only preservation PASS:140approved files and retained v0.2 journal320episodes/SHA2564f96fa81efdb5362fa385ce5ab0a550f9faa7ddb1057e25c0432e049b653776a. `/tmp/taa-live-demo-preservation-001.json`. Do not rerun the viewed scored experiment.
- [Descriptive] Scripted scenarios PASS twice, retained intact in `/workspace/scratch/live-demo-v01/scripted-scenarios-001/` and `scripted-scenarios-002/`. Both logs are retained under `/tmp/taa-live-demo-scripted-00*.log`.

## Running gate — do not duplicate

[Descriptive] Full repository discovery is still running at checkpoint time (2026-10-24T20:23UTC). **PID2643**, exec session **70540**. Command:

```sh
PATH=/tmp/taa-live-demo-venv/bin:$PATH /tmp/taa-live-demo-venv/bin/python -m unittest discover tests -v > /tmp/taa-live-demo-full-004.log 2>&1
```

[Descriptive] At inspection it had reached historical Study B pilot tests, with no ERROR/FAIL lines observed. This is not a passing full-suite claim. Check process identity and the log footer before doing anything:

```sh
ps -p 2643 -o pid,etime,args
tail -n 30 /tmp/taa-live-demo-full-004.log
```

[Descriptive] If alive, continue watching the same process; never launch a second discovery. If absent with an OK footer, retain the actual test/skip/time counts. If absent without terminal success, preserve the prefix and diagnose before one new, separately named offline run. Python3.12 is inappropriate for the historical v0220 float-sum spending check: the earlier diagnostic reproduces the documented issue, while all4 historical v0220 tests PASS under3.11.17. Do not change archived arithmetic to make3.12 pass.

[Descriptive] Interrupted/diagnostic broad prefixes `full-001/002/003.log`, focused logs001–006, two earlier stand-ins, stop campaigns and all final source bytes are retained. The checkpoint archive contains snapshots of logs; full-004 is an explicitly incomplete append-only prefix. The original live log remains authoritative for completion.

## Continue after the gate

1. [Descriptive] Verify the final code still matches `/workspace/scratch/live-demo-v01/final-source-hashes.json`; that code has not changed since full-004 started. Only checkpoint documentation/evidence is added.
2. [Proposal] Once full discovery passes, run `/tmp/taa-live-demo-venv/bin/python /workspace/scratch/live-demo-v01/package_evidence.py` from the repository. It rejects missing full/focused PASS, changed source, changed real ledgers or broken evidence checkpoints. It creates NEW `acceptance.zip` and `validation.json` alongside the checkpoint artifacts; it never overwrites/deletes them or reruns scored episodes. The helper/source hashes are included in `checkpoint.zip` if scratch needs recovery.
3. [Proposal] Add final broad counts/status to the notebook/report and update the draft PR body. Each PR claim must be labeled [Descriptive], [Interpretive] or [Proposal]. Commit the final evidence separately, push, inspect current-head CI and deliver the final PR/head/test summary. Do not merge before Claude's recorded review.
4. [Proposal] Review questions remain native Responses compatibility (unprobed), current price (unprobed), byte-based prompt reservation plus16K framing assumption, uniform business-context delivery, immediate host-mediated execution,4096 ceiling, claimant-level completion and no automatic replacement. No approval is requested or inferred for a live call.

[Descriptive] Existing OpenAI ledger is1.1327969749999984 estimated dollars. Real paid adapter requires explicit launch flag, exact HEAD/owner receipt, clean tracked source, a provider-wide run lock and a persistent once claim. The task is an offline build only; never invoke its live flags during continuation.
