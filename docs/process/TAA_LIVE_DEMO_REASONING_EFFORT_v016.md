# Owner-approved explicit reasoning effort, v0.1.6

[Descriptive] Chris's 2026-10-25 decision authorizes one diagnostic process,
medium then low then none, stopping at the first HTTP200. At most three requests,
16 completion tokens each, cumulative reservations at most $0.01, canonical
provider lock and shared $5 step/$8 OpenAI caps. The recording rules retain
status/type/code and only patterned param, never error messages or keys. The
same decision conditionally approves applying the first accepted value to every
arm and neutral-check request. Low/none must be declared a deviation from
provider defaults. No actual neutral-check invocation, thirty episodes or merge.

[Descriptive] All three bodies were frozen before replies. Each is the neutral
first request, with tools, store:false and function strict:false, at the expressly
approved 16-token ceiling, adding only the planned reasoning_effort value.
Same harness urllib module and configured TAA_OPENAI_API_KEY, inherited proxy/TLS
settings, one process, no retry. Six offline campaigns cover first/second/third
success, no accepted value, and immediate HTTP401/503 stops.

| Variant | reasoning_effort | HTTP | Error type | Code | Param | Booked dollars |
| --- | --- | --- | --- | --- | --- | --- |
| e | medium | 400 | invalid_request_error | null | reasoning_effort | 0.002124125 |
| f | low | 400 | invalid_request_error | null | reasoning_effort | 0.002123750 |
| g | none | 200 | — | — | — | 0.000023300 |

[Descriptive] None is the first accepted value under Chris's stated order. g
returned gpt-6-luna, finish_reason length and tool_calls present. A 16-token length
reply establishes diagnostic body acceptance, not complete function arguments or
a passed two-request neutral check. No tool was executed by this diagnostic.
Native usage:

```json
{
  "prompt_tokens": 153,
  "completion_tokens": 16,
  "total_tokens": 169,
  "prompt_tokens_details": {
    "audio_tokens": 0,
    "cache_write_tokens": 0,
    "cached_tokens": 0
  },
  "completion_tokens_details": {
    "accepted_prediction_tokens": 0,
    "audio_tokens": 0,
    "reasoning_tokens": 0,
    "rejected_prediction_tokens": 0
  }
}
```

[Descriptive] Reservations e $0.002124125, f $0.002123750, g $0.002123875;
cumulative $0.006371750 <= $0.01. Total booked $0.004271175 comprises g's
observed native usage $0.000023300 plus $0.004247875 retained error reservations,
whose actual provider billing is unknown. Step $0.018854925 -> $0.023126100;
persisted OpenAI $1.1516518999999985 -> $1.1559230749999982. Old reserves and all
markers1/2/3 remain; no study claim or attempt4, no refunds of prior failures.

[Descriptive] Both Adapter.body and CheckAdapter.body now include the immutable
config.REASONING_EFFORT value none. It applies identically to all arms and both
neutral requests, with no fallback selection in production. This is explicitly
**a deviation from provider defaults**. Other sampling settings remain defaults;
no temperature, top_p, seed, tool_choice or other setting override is introduced.
Reasoning carry-over remains disabled uniformly. Production output ceiling stays
4096. Frozen measures record the value, deviation, owner decision and selection
order; only measures.json and its digest change among frozen bindings.

[Descriptive] Updated sampling tests pin the exact request key set and literal
none value, across arm-visible first requests, both neutral turns and both body
builders. Extra keys of any kind or another reasoning value fail. Four in-memory
mutations inject temperature/top_p or medium/low into live/neutral bodies; each
fails one assertion with zero errors, with passing baseline/restored controls.
The existing seven guard mutations remain caught. No scientific fixture or
expected moral outcome changes.

[Descriptive] Actual evidence directory:
`/workspace/taa-live-demo-evidence/reasoning-effort-diagnostic-20261025-001/evidence`.
Checkpoint count16/head
`e603687882a8c9d50d50f468039c5275854ec2bf6e206610692328cdab607ebb`;
checkpoint-file SHA256
`2b69e93a05b50fde2a72a6e351000e857465585d1d84623800fa1411d10fd056`.
Source, exact bodies, before/after ledgers and result.json remain alongside it.
The measures SHA256 is
`b4f989bbe59d37df520fe3eee692a0cce81cd6297d5bfeb5509564058b522655`.
Earlier diagnostic/neutral evidence and archives remain unchanged. Authorization
for this diagnostic is exhausted. Final offline validation is recorded below.


[Descriptive] Final v0.1.6 local validation PASS: Python3.11.17 full discovery1195tests/36existing skips/2244.048s; focused63tests/0skips/273.534s with outbound sockets denied; targeted28PASS. Preservation140protected files/320originalepisodes and scripted all scenarios PASS. Separate30-episode canned stand-in COMPLETE, neutral stand-in COMPLETE2requests; all32evidence chains and every request's exact key set/none value verified. Existing7guard mutations and4extra-key/wrong-effort mutations caught with one assertion/zeroerrors and baseline/restoredPASS;6mockdiagnostic selection/early-stop campaigns PASS. Only frozen measures.json/hash changed; other frozen inputs and all previous archives byte-identical to c7a205c4. Actual step/OpenAI remain0.023126100/1.1559230749999982; markers1/2/3unchanged, no study/attempt4claim. Actual request countthisstage3, booked0.004271175, ofwhich0.000023300observedusage and0.004247875retainederrorreserves. No further requests authorized. Archive docs/process/evidence/gateway-live-demo-reasoning-v016/acceptance.zip,7734666bytes/3395members/SHA25673c47c478a6bb823c660cc992cf103880f82471de1b957103b7a4d6eb2aeb9d7, adjacent validation.json; CRC/all3394member hashes verified. Local unshare is kernel-denied; verify exact pushed-head namespace CI in PR. Chosen none is explicitly a deviation from provider defaults, uniform every arm/neutral request, all other sampling defaults; no reasoning carry-over. Commit/push this authorized patch then stop; no real neutral check,30episodes or merge.
