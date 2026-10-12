# Gemma frozen Study A execution adapter — v0.22.2

Owner's conditional authorization became applicable when the separately approved
additional neutral check passed: one request, correct gemma-4-31b-it identity,
matching neutral JSON, native prompt 56 / final 15 / thought 141 / total 212 tokens,
STOP, $0. The first failed 64-token check is unchanged and separately preserved.
Gemma was selected after the other models' Study A results were seen; this is an
additional held-out 240-cell run on the unchanged 59-file freeze. It is not a Qwen
continuation. No Groq calls or new account/provider. Original P6 is unchanged and
no amended verdict is made; the separate P6 proposal still needs review.

The isolated adapter imports the original execution/history/replay functions and
Gemini request-body builder. Same full fresh multi-turn histories, system prompt,
pressure deliveries, 12-turn protocol, 32,000-byte and 2,048 completion ceilings,
JSON reply MIME and provider defaults. No sampling/thinking/effort override or
history trimming. Frozen original adapters are unchanged.

Google countTokens measures the entire generateContentRequest before generation;
counts are cached against complete body hashes, with native request/response
closure recorded separately. Prompt + 2,048 + 128 safety buffer must fit 16,000
before generation. Rolling 61-second reservations keep input at <=14,400 tokens
and HTTP at <=24 requests, with rolling-day HTTP <=12,960. All quota events remain,
and cached inputs are not discounted from TPM. Native prompt usage must fit the
count reservation; mismatches stop for review. Actual native total/candidate/
thought usage is validated; thought-only responses with an omitted final count
may derive zero only when no final parts exist and total equals prompt + thought.
The actual native response remains intact, and the derivation gets separate
explicit evidence. This changes no historical neutral/other-model journal.

Issued HTTP 429 closes as a preserved failed original episode. Response reset
comes only from Retry-After, documented reset headers or google.rpc.RetryInfo;
missing reliable reset stops for review. No default 24-hour pause or issued
request retry. Continue untouched primaries after reset, then one separately
labeled fresh replacement per rate-lost primary in the original scenario/repeat
slot. A failed replacement never receives another replacement. Fourth rate error
or two consecutive rate errors stop, with persisted counters across resumes.
Metadata 429s count toward safety but do not lose an episode or create a replacement;
only valid native generation resets the consecutive counter (conservative).
Malformed replies/refusals/unfinished replies keep original scorer labels and
receive no replacement. Other transport/identity/usage/size/uncertainty failures
retain evidence and stop for review. Guard/inflight/unclosed checkpoints or a
review stop prevent automatic restart. Never clear a lock automatically.

A shared provider run lock covers the whole run including quota waits. The exact
checkout/output, plan, approval, frozen files, new/original adapters, other ledgers
and successful neutral are hash-bound. Google ledger amount remains $0.631178075
and cumulative $8 stop is retained. All Gemma calls are projected $0; no paid
fallback is implemented. No other provider-ledger run may run concurrently.

CLI from original repository root, using the original Python 3.11 environment:

```
/workspace/haiku55-runtime/venv/bin/python3 scripts/formation_study_a_gemma31.py --approved-gemma-free
```

Plan: studies/formation-study-a-gemma31-plan-v0222.json.
Approval receipt binds the existing conditional authorization and rate amendment:
studies/formation-study-a-gemma31-approval-2026-10-11.json.
Output: results/2026-10-11 v0.22.2 gemma31-none r10 study-a evaluation.
Offline audit: scripts/formation_study_a_gemma31_audit.py. It compares scores by
deterministic replay, full wire histories to original reconstruction, pinned
identity/usage, every count/preflight, closure and replacement order/slot.
Original primary failures stay in planned denominators; replacement sensitivity
is reported separately. Completion is not a P6 verdict.

A–D estimate remains approximately 8–14 hours of input throughput plus latency,
pauses and unfinished-design changes; full illustrative ceilings may take ~4 days
of spacing. Study C longest histories are not yet built or token-certified. Count
all C combinations before its freeze and report oversize before freeze; never
silently trim. B/C/D inclusion is planned before their freezes, not launched now.

Validation completed before launch: all 313 unit tests pass, including 13 Gemma
fixtures and the offline audit; historical scripted checks pass. Two historical
Qwen test-fixture assumptions were corrected only in tests: snapshot ledgers
instead of today's live ledgers, and allow the test controller's own status
mutation. Production Qwen guards/source/ledgers/quota are unchanged; zero actual
Groq calls. Both initially failing and final passing logs are preserved in
results/2026-10-11 v0.22.2 scripted-none gemma adapter validation.
