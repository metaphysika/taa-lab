# Order crossing run, 2026-11-04 (EXPLORATORY)

Gemma 4 31B (Study D checkpoints), contrary and neutral, one repeat, on the exposed attempt-4 W/U battery.
- Arm `order_asis`: the cases exactly as attempt 4 ran them.
- Arm `order_request`: the explicit order becomes a decision request (`docs/process/STEP4_ORDER_DIFF_v02460.md`).

The pre-run predictions and counting rules are in the LAB_NOTEBOOK.md entry "v0.24.60 order crossing: pre-run predictions". The results are in the entry that follows it.

- Commit: `13afaf458514962aa74bf8bcd4e44d20d7eee8ae`. Approval ID: `step4-crossing-20261104-01` (Chris Lahn). Cap: $8.
- Modal run `84ebd2a36b574b22b1687bed025b7074`, app `ap-Uh3PlCK2kkzEwG5adizXwj`, function call `fc-01M6MFQ2DANX6674E331H86JDD`.
- 85 of 96 planned cells ran and 364 requests returned, ending in a clean `stage_end` at 5,383 s. The session time guard refused the next request in cell 85, which is recorded as `generation_failed` / ValueError "session time limit; no new request". That episode had already executed the wrongful act. The 11 unrun cells are all rung-4 pressure cases.

## Files

| File | Contents |
| --- | --- |
| `events.jsonl` | Full run journal: every request, partial stream, returned reply, cell row and attempt ledger |
| `app-logs.txt` | `modal app logs --timestamps` |
| `receipt.json` | Approved execution receipt (binds commit, archive, cells, cap and settings) |
| `launch.json`, `launch-stdout.txt` | Launcher output |
| `analysis.txt` | Output of `python scripts/step4_crossing_score.py events.jsonl receipt.json` (pre-registered rules in `exploratory/step4_harness/crossing_analysis.py`) |

Verify with `sha256sum -c MANIFEST.sha256` from this folder, in an LF checkout. The `-text` attribute keeps the bytes stable.
