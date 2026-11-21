# Track A Step 1: blinded transcript recount (EXPLORATORY)

- Approved by Chris Lahn on 2026-11-21: "Approve 1, use the current API account and approve your recommendation for number 2." Approval id `track-a-step1-20261121-01`, run commit `efc939af4828ed74140129da4a02461dcd5ccf5e`, cap $12, Anthropic API account whose key is in `keys.env`.
- Attempt 1 (about 10:40 CST) was refused by the receipt check before any call: the receipt carried a mistyped text-rules hash. `after-run/run-attempt1-refused.log`.
- Attempt 2 started 10:42 CST and was killed at about 12:42 CST by the Claude Code 2-hour background limit, with 496 of 1,147 packets coded by both readers and one batch in flight. `after-run/run-attempt2-killed.log`.
- Resume approved by Chris ("Finish A"), approval id `track-a-step1-20261121-02-resume`, run from a detached process at commit `e2b97665411517dccd7c71770e73a1626b07df90` (PR #194). It retrieved the in-flight batch by id, then coded only uncoded packets. Ledger `resume-end` outcome `complete`.
- Readers: `claude-sonnet-5-5` (primary), `claude-haiku-5-5` (agreement), Message Batches API. Primary: 1,147 valid codes. Second: 1,115 valid, 32 unknown.
- **Cost (ledger, from returned usage): $2.7319594**, against a point estimate of $5.68 and the $12 cap.
- The top-level files are the run's own unchanged outputs, appended in place by the resume. `after-run/` holds the build key (`key.jsonl`, SHA-256 `b485067b…ed72`) and build report, both receipts, both launchers (they name the path to `keys.env` but contain no key), the logs, and the offline analysis (`analysis.json`, `analysis.txt`).
- Analysis: `python -m exploratory.track_a.recount analyze --key after-run/key.jsonl --codes codes.jsonl --output <dir>` at the resume commit.
- `MANIFEST.sha256` pins every file.
