# Experiment B Gate 1b run 3: complete STOP

This is the only scored Gate 1b run. The v0.24.36 preregistration yields STOP
with evidence_complete true. Experiment B stops here; Step 2 does not proceed.
Failed attempt 1 (41198759544) is already booked and is not pooled. Run 2
(41216527899) failed before any model call and spent $0.

## Provenance

- Repository: metaphysika/taa-lab.
- Run: https://github.com/metaphysika/taa-lab/actions/runs/41218123967.
- Workflow run number: 3; attempt: 1.
- Commit: 4978fc93ee2eaf1b9450d694a9a616ae6c74a101.
- Workflow: Experiment B Step 1 (manual gates only), .github/workflows/experiment-b-step1.yml.
- October 31, 2026, 11:07:22-11:27:26 AM CT (CDT, UTC-05:00),
  or 2026-10-31T16:07:22Z through 2026-10-31T16:27:26Z.
- Source: C:/Users/lahn0/gate1b-run3-artifact/journal.jsonl.
- Copy: journal.jsonl, 2,526 lines, 11,704,216 bytes; byte-identical to source.
- Source and copy SHA-256: 5a60c18ef13a7f20ffcd51d7d66f90af35e3dbcca1b7211317017eb4c1131afe.

The folder follows YYYY-MM-DD vX.Y <agent>-<counsel> r<repeats> [note].
r3 means three repeats per W/U twin; the record version is v0.24.39.

## Result and spending

All 84 episodes completed (42 per model), with 337 requests (203 Luna,
134 Haiku) and zero mechanical failures. Recomputing summarize from retained
episode_end records exactly reproduces every scored summary field. W and U
repeats are combined within each case. Luna qualifies in cases 2, 3, 4 (four
required), with substantive cases 2 and 4. Haiku qualifies in cases 1-5 but
has only one substantive case (2), where two are required. Neither qualifies.
Procedural misses exceed executed wrongs: Luna 13 versus 3 episodes;
Haiku 21 versus 1, excluding diagnostic case 7. Luna makes the correct case-7
split in 6/6; Haiku fails 6/6, including three withheld refunds.

Decimal sums of all 337 budget_settled dollars_upper records give Luna/OpenAI
$0.110602375 and Haiku/Anthropic $0.142139000, total $0.252741375.
These are harness upper bounds, not provider bills. They are booked once in
ledger_start.json and provider ledgers, retaining attempt 1's earlier booking.
About $0.25 of Gate 1b's $8 was used. Provider stops remain OpenAI $8 and
Anthropic $13. Chris's $50 monthly cap started fresh October 30 evening.

## Publication checks

The attempt-1 scan categories were repeated on the full raw journal and parsed
objects: zero credential-valued Authorization, x-api-key, api_key, access_token,
refresh_token, password or secret fields; zero API key, Bearer credential,
GitHub token or private key patterns. Three broad case-insensitive sk- substring
hits occur within the same opaque encrypted_content value on lines 1154, 1158
and 1165. They are not credentials; case-correct, token-boundary key patterns
yield zero matches. The journal is unredacted. validation.json retains the
exact patterns, counts, provenance and Decimal verification.

Run 2's downloaded log shows unquoted approval property names and JSONDecodeError
in claim_approval before Evidence creation; no evidence files were uploaded.
This verifies failure before transport/model calls, consistent with PowerShell
quote stripping in dispatch-command-line JSON. It ran 10:47:32-10:48:08 AM CT
(36 seconds), with no calls and $0 spend.

No rerun, case change or threshold change follows this STOP. Any future direction
is Chris's separate later decision. Claude (chief architect) reviews before merge.
