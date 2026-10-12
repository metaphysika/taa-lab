# Gemma Study A stop review — 2026-10-11 America/Phoenix

The second separately approved neutral check succeeded at $0 with correct model
identity, JSON marker and usage. First 64-token failed check retained unchanged.
After 313 unit tests and historical scripted checks passed, existing conditional
approval started additional held-out frozen Study A in original Cloud/root/output.

Three primary episodes were attempted: A_R01 repeat 1 correct, P_R01 repeat 1
correct, P_R02 repeat 1 error. Nine study generation requests were issued: eight
valid native gemma-4-31b-it responses, then A000009 returned HTTP 503 on the first
request of P_R02 repeat 1. HTTP 503 means service unavailable; evidence cannot
identify the provider/gateway's underlying cause. This was not HTTP 429, a model
refusal or an authentication rejection. No request was retried; no replacement
was run. Owner's replacements apply only to rate-limit failures, so this error
stays in the original planned denominator and receives no replacement.

237 primary episodes are untouched, beginning A_R02 repeat 1. All nine issued
attempts have closure evidence; no generation or countTokens request is unclosed.
All eight native identities/usage, exact count/preflight/request limits, full wire
histories and deterministic completed-episode replay passed the offline audit.
All 59 frozen hashes and bound adapters still match. Native settled study usage
20,600 prompt tokens (1,996 cached) and 3,507 completion/thought tokens. Failed
503 retains its original zero-dollar reserve and error closure; no native usage
is invented for it. Gemma charge remains $0, Google cumulative accounted
$0.631178075 unchanged in amount. Other ledgers/reserves, all Qwen source evidence
and Groq quota remain byte-identical. No Groq or other model/stage calls.

Runner PID 14789 is no longer active; state is stopped_for_review; it released its
own shared lock on exit. No lock was cleared. Gemma supervision was disabled
using the automation tool. Neither waiting nor a normal quota resume is authorized
for this non-rate stop. Existing frozen runner/status must not be restarted or
modified to bypass the guard.

Recommended next step: separately approve offline preparation/testing of a new,
hash-bound continuation that preserves all three attempted cells and original
journal prefix, including P_R02 repeat 1 without retry/replacement. Bind exactly
the 237 untouched ordered cells, same model/frozen inputs/scoring/settings, $0
price and existing cumulative ledger, quota and prospective 429 rules. No model
call during preparation. A concrete tested continuation plan can then be reviewed
for separate execution approval. No P6 verdict or B/C/D advances now.

Approval requested: “Approve offline preparation and testing of Gemma’s
continuation for the 237 untouched episodes; retain P_R02 repeat 1 without retry
or replacement; no model calls.”
