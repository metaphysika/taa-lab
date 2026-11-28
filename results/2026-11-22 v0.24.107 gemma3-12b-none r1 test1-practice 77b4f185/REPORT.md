# Test 1 practice (version 2), 2026-11-22

## Evidence

- [Kaggle runner report](kaggle-v2/test1-practice/report.json), [outputs](kaggle-v2/test1-practice/outputs.jsonl), [events](kaggle-v2/test1-practice/events.jsonl), and [notebook log](kaggle-v2/test1-practice.log).
- [Execution record](execution.json) and [downloaded file hashes](SHA256SUMS).

## Checked

- PR #208 at exact commit `77b4f1855ecdf21097bea0387c9d025d57287a43` had 11 passing hosted checks. [PR #208](https://github.com/metaphysika/taa-lab/pull/208)
- Kaggle kernel `metaphysika/test1-practice` version 2 reached status `COMPLETE` (`failureMessage: null`), accepted `/kaggle/input/test1-practice-receipt-77b4f1855ecd/receipt.json`, and wrote all four retained artifacts.
- Independent replay with `python -m exploratory.test1.analysis practice` from exact commit `77b4f1855ecdf21097bea0387c9d025d57287a43` on `kaggle-v2/test1-practice/outputs.jsonl` reproduced every scorable count and `practice_gate_met: false` in `kaggle-v2/test1-practice/report.json`.
- SHA-256 hashes of all four downloaded files are recorded in `SHA256SUMS`.

## Not checked

- Model reply text, per-case outcomes, obedience/refusal counts, and `ALLOWED`/`NOT ALLOWED` answers were intentionally not inspected or reported here.
- The Test 1 main bundle was not pushed or run.

## Decisions and assumptions

- The runner enforced its bound 3,600-second cooperative time limit (`1.00` hour).
- GPU use is measured from Kaggle's weekly account GPU quota meter (reported to `0.01` GPU hours), assuming no concurrent GPU sessions on the account during version 2.
- Main-run projections scale the observed practice rate to the planned main volume of **132 episodes + 24 detached knowledge calls** (156 total cells; 4× the practice volume of 33 episodes + 6 knowledge calls). Both gross (all-in) and net-of-startup/load estimates (treating version 1's measured `277.93 s` / `0.08 GPU h` model load and prefill preflight as fixed per-session overhead) are reported.

## Practice result (counts only)

| Condition | Scorable / Planned |
| --- | ---: |
| Knowledge items | 5/6 |
| Arm 1 | 6/6 |
| Arm 2 | 6/6 |
| Arm 3 | 5/6 |
| Arm 4 | 5/6 |
| Arm 5 | 5/6 |
| Contractor | 3/3 |

- **Practice gate:** **Not met** (`practice_gate_met: false`). Knowledge met its `>= 5/6` threshold (5/6), and Arms 1, 2, and Contractor met `>= 90%`, but Arms 3, 4, and 5 finished at 5/6 (`83.3% < 90%`) because the run stopped at the 1-hour runner deadline with 4 of 39 planned items uncompleted (1 episode each in Arms 3, 4, and 5, and 1 detached knowledge item). All 35 completed items (30 episodes and 5 detached knowledge calls) were scorable.
- **Stop and error:** Cooperative runner deadline stop (`status: "stopped_deadline"`, caused by `DeadlineExceeded` at the 3,600-second limit). No crash, OOM stop, or preflight error occurred; Kaggle reported kernel status `COMPLETE` (`failureMessage: null`).
- **Runner elapsed time:** `3,600.08` seconds (`60.00` minutes / `1.000` hours); notebook log finished at `3,633.26` seconds (`60.55` minutes).
- **Kaggle weekly GPU meter:**
  - After version 1: `24.75h` used (`5.25h` remaining of `30.00h`).
  - At 23:40 UTC with version 2 running: `24.97h` used.
  - After version 2 finished: **`25.76h` used** (`4.24h` remaining of `30.00h`; refreshes `2026-11-28T00:00:00+00:00`).
  - Version 2 metered GPU time: **`1.01` GPU hours** (`25.76h - 24.75h`).
- **Per-episode rate (across 30 completed episodes + 5 completed knowledge calls):**
  - Gross runner elapsed rate: **`120.00 s/episode`** (`2.00 min/episode`, `0.0333 h/episode`).
  - Gross Kaggle metered rate: **`0.0337 GPU h/episode`** (`2.02 min/episode`).
  - Net generation rate (subtracting version 1's `277.93 s` model load + preflight, still including the 5 interleaved knowledge calls): **`110.74 s/episode`** (`1.85 min/episode`, `0.0308 h/episode`).
- **Projected main-run GPU time (132 episodes + 24 knowledge calls = 156 cells):**
  - Net-of-startup projection (adding `0.08h` fixed load/preflight once): **`4.14` hours** runner time at `132/30 = 4.40×` episode scaling (`~4.15–4.17` GPU hours metered), or **`4.19` hours** runner time at `156/35 = 4.457×` cell scaling (`~4.20–4.22` GPU hours metered).
  - Gross projection (scaling total v2 time proportionally): **`4.40` hours** runner time / **`4.44` GPU hours** metered at `132/30` scaling, or **`4.50` GPU hours** metered at `156/35` cell scaling.
  - Across all estimates (**`4.14–4.50` GPU hours**), the projected main run exceeds both the 4.00-hour cooperative main runner limit and the remaining weekly budget under the 5.00-hour weekly stop (combined practice v1 `0.08h` + v2 `1.01h` + projected main = `5.23–5.59` GPU hours; remaining account quota is `4.24h`).
- **Earlier failed receipt upload:** Prior to version 2, an initial receipt upload attempt at `77b4f185` failed locally with `Errno 2` in the Kaggle CLI temporary upload path before any kernel run started (`0.00` GPU hours used). Sol fixed the upload procedure before version 2 was launched.
