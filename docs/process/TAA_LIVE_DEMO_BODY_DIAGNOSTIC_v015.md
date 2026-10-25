# Live-demo body diagnostic and error parameter filter, v0.1.5

[Descriptive] Chris approved one diagnostic round on 2026-10-25: at most four
requests from one Python process using the harness urllib client and configured
TAA_OPENAI_API_KEY; each request has a 16-token completion ceiling, total
cumulative reservations at most $0.01, and shared $5 step/$8 provider caps.
Stop early on HTTP401 or 5xx. No neutral-check invocation, thirty episodes or
merge is approved. Original attempts, markers, ledgers and evidence remain.

[Descriptive] Before calls, the runner constructed the exact first neutral body
and verified it byte-identical to attempt3's retained request, then changed only
the expressly approved ceiling. All four variants were frozen before replies:
a unchanged otherwise; b removes store only; c removes tools only (retaining
store:false as in a); d removes strict from the tool's function. No request
contains reasoning_effort. The production 4096 ceiling and frozen inputs stay
unchanged. The existing Budget books each reservation and observed native usage
under the canonical provider lock and durable step ledger; no error is retried.

| Variant | HTTP | Error type | Code | Param | Booked dollars |
| --- | --- | --- | --- | --- | --- |
| a: tools, store:false, strict:false | 400 | invalid_request_error | null | reasoning_effort | 0.002120625 |
| b: no store | 400 | invalid_request_error | null | reasoning_effort | 0.002118875 |
| c: no tools | 200 | — | — | — | 0.000011800 |
| d: no strict | 400 | invalid_request_error | null | reasoning_effort | 0.002118750 |

[Descriptive] Variant c returned model gpt-6-luna, finish_reason length and no
tool_calls. Its complete native usage, recorded without message content:

```json
{
  "prompt_tokens": 38,
  "completion_tokens": 16,
  "total_tokens": 54,
  "prompt_tokens_details": {
    "audio_tokens": 0,
    "cache_write_tokens": 0,
    "cached_tokens": 0
  },
  "completion_tokens_details": {
    "accepted_prediction_tokens": 0,
    "audio_tokens": 0,
    "reasoning_tokens": 16,
    "rejected_prediction_tokens": 0
  }
}
```

[Descriptive] Exactly four requests, one process, no retries or early-stop
statuses. Cumulative reservations $0.008449250, total booked $0.006370050.
Observed usage charge $0.000011800; the other $0.006358250 is retained error
reservation with actual provider billing unknown. Before: step $0.012484875,
OpenAI $1.1452818499999984. After: step $0.018854925, persisted OpenAI
$1.1516518999999985. No existing reservation refunded or reset.

[Open question] Tool-bearing variants returned param reasoning_effort despite
the parameter being absent from every sent body; the tool-free variant reached
its 16-token ceiling. These observations do not identify the source of that
parameter or establish native-tool compatibility. This is not a successful
two-request neutral check. No additional transport or reasoning setting changes
are made.

[Descriptive] The requested code change retains error param only when its string
fully matches `[A-Za-z0-9_.\[\]]{1,128}`. Every other value is withheld, including
missing/non-string values. Existing type/code allowlists remain; messages and raw
error bodies are never retained. One new test covers allowed paths, boundaries,
unsafe characters, newlines, non-ASCII and non-string values, and absence of
message/private fields. Existing privacy tests now pin the exact three-field
set. Removing the pattern fails one assertion with no errors; baseline/restored
controls pass. The four diagnostic stand-in campaigns verify four-error and
four-success accounting, and immediate 401/503 stops, without real requests.

[Descriptive] Actual evidence:
`/workspace/taa-live-demo-evidence/request-body-diagnostic-20261025-001/`.
Its evidence checkpoint has count20/head
`6590e33f7934bf665abad5e13e3e00d08319bc392532e9562cf801b592270da8`;
checkpoint-file SHA256
`95b4961d6ba7dd7eb0aab7b319c15017512dd1c7d8be1478964d3fc8a2a0be54`.
Exact bodies, source hashes, once-only round record, before/after accounting and
result.json remain there. All neutral markers1/2/3 remain unchanged; no study
claim or neutral attempt4 exists. Final offline validation is recorded below.


[Descriptive] Final v0.1.5 local gates PASS: Python3.11.17 full discovery1194tests/36existing skips/2273.961s; focused62tests/0skips/258.345s with outbound sockets denied; targeted11state tests PASS. Preservation140protected files/320originalepisodes and scripted all scenarios PASS; previous7reviewmutants plus newparam-pattern mutant caught with baseline/restored passes. Four mockdiagnostic campaigns PASS, including401/503early stops and native usage settlement. Actual authorization used exactly4requests in oneprocess; no more calls. Frozen inputs, other live-demo runtime files and all earlier archives remain byte-identical to fae033e0; other provider ledgers unchanged. Actual OpenAI/step remain at diagnostic after-state1.1516518999999985/0.018854925; neutral markers1/2/3unchanged, no study/attempt4claim. Evidence docs/process/evidence/gateway-live-demo-body-diagnostic-v015/validation.json and acceptance.zip,278930bytes/198members/SHA256957e222751101964d93c076b91bb3983c90575647975a4aa69a9f08648244c54; CRC/all197member hashes verified. Local unshare is kernel-denied; pushed-head namespace CI recorded in PR after push. Commit the requested param-only runtime change/test plus reports; no neutral check,30episodes or merge. This does not fix native-tool compatibility or establish the source of reasoning_effort; no other transport/reasoning setting changed.
