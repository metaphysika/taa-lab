# K1 run, 2026-11-05 (EXPLORATORY)

Gemma 4 31B (Study D checkpoints), contrary and neutral, one repeat. K1 tests "knowing servility" (H8) against the persona / general-misalignment account with five arms: two knowledge wordings, unprompted, unauthorized (with an authenticated stop), and free-form values. See `docs/process/K1_IMPLEMENTATION_2026-11-05.md`.

The pre-run predictions and decision rules are in the LAB_NOTEBOOK.md entry "v0.24.61 K1 servility vs general misalignment: pre-run predictions". The results are in the entry that follows it.

- Commit: `8e26d0318f56bdeef13235c40cc2341c050faa39`. Approval ID: `k1-20261105-01` (Chris Lahn). Modal cap: $12. Haiku grading cap: $0.50.
- Modal run `f07092261f50401591e0b166343a1e15`, app `ap-rdyGCmvhVuvrVcME2Qj0lG`, function call `fc-01M6P6RNSKYCGHJ2CN6RVFN3EB`.
- 191 of 256 planned cells ran and 432 requests returned, ending in a clean `stage_end` (elapsed 9,089 s). Cell 191 (unprompted, neutral, `B-WU-cold-r3-pressure-W`) is recorded as `generation_failed` / ValueError at 9,130 s, after the 9,083 s stop-new time, which is consistent with the session time guard refusing the next request. That episode had dispatched ROUTINE only. 65 cells are unrun: 44 knowledge and 21 unprompted. The unauthorized and values arms are complete.
- The startup inventory phase took 1,148 s (about 19 minutes), much longer than in the crossing, and this is the main reason the run did not finish.
- Values answers were graded after the run by `scripts/k1_grade_values.py` (Claude Haiku 5.5, `claude-haiku-5-5`, one call per answer, no retries, question and answer only). 24 of 32 returned valid grades and 8 are grading failures (5 contrary, 3 neutral): 4 replies cut off mid-rationale and 4 empty. All are retained in `value-grades.jsonl` and count as unknown.

## Files

| File | Contents |
| --- | --- |
| `events.jsonl` | Full run journal: every request, partial stream, returned reply, cell row and attempt ledger |
| `app-logs.txt` | `modal app logs` (without timestamps) |
| `receipt.json` | Approved execution receipt (binds commit, archive, cells, cap and settings) |
| `launch.json`, `launch-stdout.txt` | Launcher output |
| `value-grades.jsonl` | Haiku grades for the 32 value answers, with raw grader replies and grading failures |
| `analysis.txt` | Output of `python scripts/k1_score.py events.jsonl receipt.json value-grades.jsonl` (pre-registered counting in `exploratory/step4_harness/k1_analysis.py`) |

Verify with `sha256sum -c MANIFEST.sha256` from this folder, in an LF checkout. The `-text` attribute keeps the bytes stable.
