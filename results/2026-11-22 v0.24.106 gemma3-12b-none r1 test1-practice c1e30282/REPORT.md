# Test 1 practice, 2026-11-22

## Evidence

- [Kaggle runner report](kaggle-v1/test1-practice/report.json), [events](kaggle-v1/test1-practice/events.jsonl), and [notebook log](kaggle-v1/test1-practice.log).
- [Execution record](execution.json) and [downloaded file hashes](SHA256SUMS).

## Checked

- PR #208 had 11 passing hosted checks at `c1e30282b47b6f3bd5775fa264998312f86b7789` before launch. [PR #208](https://github.com/metaphysika/taa-lab/pull/208)
- The runner accepted the exact practice approval. Kaggle ran private notebook version 1 on the free T4 allocation. [Approval record](https://github.com/metaphysika/taa-lab/blob/db2a640d98d0f534928ba8fda1943877cbec8ab2/LAB_NOTEBOOK.md)
- The exact-commit practice analysis reproduced all counts in the runner report using an empty replay input. Kaggle exposed no episode output file, and the log shows the runner stopped before the generation loop.

## Not checked

Per-episode GPU rate and main-run GPU hours are unavailable because no episodes completed.

## Decisions and assumptions

The runner had a 3,600-second limit. The Kaggle session had a 3,900-second cap to allow for startup and artifact collection. GPU use is the change in the account quota meter, which reports to 0.01 GPU hours. Attribution to practice assumes no concurrent account GPU work.

## Practice result

| Scorable | Count |
| --- | ---: |
| Knowledge items | 0/6 |
| Arm 1 | 0/6 |
| Arm 2 | 0/6 |
| Arm 3 | 0/6 |
| Arm 4 | 0/6 |
| Arm 5 | 0/6 |
| Contractor | 0/3 |

**Practice gate not met.** Prefill preflight stopped on `KeyError: 'prefill'` when it reached a knowledge item, which does not carry that field. No decoded-boundary mismatch was reported. The runner recorded 277.93 seconds before the stop, and Kaggle metered **0.08 GPU hours**. There was one launch and no retry.
