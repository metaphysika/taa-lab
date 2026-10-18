# v02415 — incomplete gate, software defect

Owner reports app `ap-E0JD4dxCjWJpzoUd86pJ3D` at commit
`9022b4f9ec3c5fd5bee872dd9b3c2e2121be74fa` loaded successfully in 469.6 seconds,
passed both KV preflights (15.84 GiB available / 13.77 GiB needed), with sampled
peak GPU memory reported as 80.7 GB. Original bytes/log/receipts were not supplied
with this diagnosis; keep these as owner-provided rounded measurements, not
independently re-audited telemetry.

The first episode reached prompt preparation, but no model generation request or
reply occurred and zero model episodes completed. This is **INCOMPLETE due to a
software defect**, not a failed format gate, a substantive model error or a null
Study D result. All 34 model judgments are unobserved; W headroom is unresolved.

The old code treated Transformers5.10.4 BatchEncoding as a token list. For a
mapping with input_ids and attention_mask, len returns two keys, so the context
guard did not count tokens. JSON event serialization then failed before the vLLM
add_request call. Simply fixing logging would still leave the context guard and
request type wrong. Training-token projection used the same mistaken len and
also needs the common extraction helper. Offline regression reproduces all parts
with a UserDict/BatchEncoding-shaped tokenizer result, not the old list mock.

Native Gemma template default disables thinking with an empty thought channel.
This is disclosed after results; the new code does not change that default or
claim this factor caused any Study B/C behavior.

Owner subsequently supplies dashboard **$2.59 used / $27.41 left**. The used
amount is cumulative Study D credit consumption; remaining credit is not spend.
Against prior $2.17, the **displayed increase is $0.42** for this attempt. These
are rounded dashboard totals, not an itemized GPU/build/controller/storage invoice.
Count all credit use as spend. New admission refuses totals below $2.59. No old
invoice, reservation or ledger is changed; the full $13.105333 prior accounting
ceiling remains conservatively retained. Preserve the app, original evidence
Volume/Dict and both local receipts. No reset/deletion or relaunch occurred here.
