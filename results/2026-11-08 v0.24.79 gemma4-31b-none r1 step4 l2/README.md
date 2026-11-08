# L2 fresh-case legitimacy ladder run, 2026-11-08 UTC (EXPLORATORY)

Gemma 4 31B on Modal: the Study D contrary and neutral adapters and the base model, one repeat. L2 asks whether contrary's obedience to a wrongful order tracks the issuer's authority on 12 fresh W/U case pairs written before the run, with neutral and base controls. Pressure is identical at both rungs. Cells:
- contrary: W at the manager and driver rungs, plus the U twins at the manager rung;
- neutral and base: W at the manager rung;
- all three: a K1-style knowledge question on all 24 stimuli.

An authenticated Compliance Director stop follows any executed wrongful entry. See `docs/process/L2_IMPLEMENTATION_2026-11-07.md` and `docs/process/FABLE_READINESS_L2_SCREEN_2026-11-07.md`.

Pre-run predictions, thresholds and reading rules: the LAB_NOTEBOOK.md entries "v0.24.79 EXPLORATORY L2 fresh-case legitimacy ladder: pre-run predictions" and "L2: launch cap lowered to $7.77 (recorded before launch)". The results are in the entry that follows them.

- Commit `f86ad3b40fe5fc2a896a3b599327cc3eaf4f50a1`. Approval ID `l2-20261107-01` (Chris Lahn). Modal cap $7.77; owner-attested headroom $7.77 (Chris approved $10, then chose $7.77 because the workspace had $7.77 left). No Haiku or other model grading.
- Modal run `9cb19659590d4f97b14461af39678dd7`, app `ap-NrZ6jmizLMgJ1VwPQGUBtY`, function call `fc-01M6WR3MVRCGCRVA686RC18004`.
- All 132 planned cells ran: 60 action cells ending in `agent_stop` and 72 single-turn knowledge cells. 355 requests returned, and the run ended with a clean `stage_end` at 4,595 s, under the 5,162 s stop-new limit. No generation failures and no unknowns.
- Startup: inventory 76 s; engine ready at 365 s.

## Files

| File | Contents |
| --- | --- |
| `events.jsonl` | Full run journal: every request, partial stream, returned reply, cell row and attempt ledger |
| `app-logs.txt` | `modal app logs --timestamps` |
| `receipt.json` | Approved execution receipt (binds commit, archive, cells, cap, settings and stop authority) |
| `launch.json`, `launch-stdout.txt` | Launcher output |
| `analysis.txt` | Output of `python -m exploratory.step4_harness.l2_analysis events.jsonl` (counting in `exploratory/step4_harness/l2_analysis.py`, merged before the run) |

Verify with `sha256sum -c MANIFEST.sha256` from this folder, in an LF checkout. The `-text` attribute keeps the bytes stable.
