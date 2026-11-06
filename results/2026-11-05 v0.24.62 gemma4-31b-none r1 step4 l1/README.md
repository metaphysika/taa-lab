# L1 legitimacy ladder run, 2026-11-05 (EXPLORATORY)

Gemma 4 31B (Study D checkpoints), contrary and neutral, one repeat. L1 asks whether contrary's obedience to a wrongful order depends on who issues it. The same six W cases are given with only the issuer varied: **manager** (holds authority), **peer** clerk, contract **driver** and **anonymous** note (the last three explicitly lack authority). Neutral gets the manager rung only, and contrary also gets the six manager U (lawful) twins. An authenticated Compliance Director stop follows the first executed wrongful entry. See `docs/process/L1_IMPLEMENTATION_2026-11-05.md`.

The pre-run predictions and decision rules are in the LAB_NOTEBOOK.md entry "v0.24.62 L1 legitimacy ladder: pre-run predictions". The results are in the entry that follows it.

- Commit: `bcf9ff1813a768df7d7e697b760598bd08d503b1`. Approval ID: `l1-20261105-01` (Chris Lahn). Modal cap: $8.25. Owner-attested headroom: $9.80. No Haiku grading.
- Modal run `93a9bb83c6134148a4397dc1e9547131`, app `ap-A6m6wg2hi5cGeDbu5Kvx9w`, function call `fc-01M6QK5J9EXMQBBFGPNQHQ167G`.
- All 36 planned cells ran (all `agent_stop`), and 166 requests returned, ending in a clean `stage_end` (elapsed 2,336 s). No generation failures, no unknowns.
- Startup was fast this time: inventory 78 s, engine ready at 373 s (K1's inventory took 1,148 s). The plan had assumed 1,321 s.

## Files

| File | Contents |
| --- | --- |
| `events.jsonl` | Full run journal: every request, partial stream, returned reply, cell row and attempt ledger |
| `app-logs.txt` | `modal app logs --timestamps` |
| `receipt.json` | Approved execution receipt (binds commit, archive, cells, cap, settings and stop authority) |
| `launch.json`, `launch-stdout.txt` | Launcher output |
| `analysis.txt` | Output of `python -m exploratory.step4_harness.l1_analysis events.jsonl` (counting in `exploratory/step4_harness/l1_analysis.py`, merged before the run) |

Verify with `sha256sum -c MANIFEST.sha256` from this folder, in an LF checkout. The `-text` attribute keeps the bytes stable.
