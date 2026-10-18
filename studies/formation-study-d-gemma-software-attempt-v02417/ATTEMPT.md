# v02417 smoke: software stop before weights or training

Owner approved Stage 1 only, once, at commit
94ac5092fcb0e64fa718c8f0fb319380229eb4ae. Reported app
ap-h2Mg3Vt3JDpSyEU8X0bO1e, call fc-01M58FMB8442NP02DZ1AX0PEVA.
Owner reports a stop after approximately 24 seconds in dataset(), before model
weights loaded, with `assistant-only prefix mask/1024 context failed`.
No training steps, adapters or transfer episodes were produced according to that
report; the code builds the dataset before loading weights or creating LoRA.
This is an incomplete engineering smoke due to a software formatting defect,
not a format-gate failure, acquisition failure, or scientific null.

The saved Gemma template includes an empty thought channel when requesting a
generation prefix, but omits it when rendering a completed assistant turn.
Consequently the served prefix cannot be a token prefix of the completed render.
The owner reports maximum example length 187; the old combined guard misleadingly
included a length error in the same message. No truncation remedy is appropriate.

Owner supplies $4.31 used/$25.69 credit left, versus previous $4.30/$25.70.
Displayed increment is $0.01, rounded and not an itemized invoice export. Count
all costs, including image build, CPU and the allocated-but-untrained GPU worker.
This is **no training**, not a claim that no GPU container was allocated.
The original $1.969556 reservation/once claims remain archival and unmodified;
new admission uses additive actual-spend reconciliation, never erases prior spend.

Raw v02417 Volume return, app log and Mac local receipts were not attached to
this request and have not been fetched independently. Preserve them on Modal
and the Mac; do not reset/delete the Dict, Volume, local markers or app record.
`owner-report.json` records this provenance rather than presenting it as an
independent raw-evidence audit. Return those files later using the preservation
commands in the new Mac checklist. The already uploaded v02416 evidence remains
byte-identical, including its original FAIL and separate admission exception.

New v02418 is prepared offline only. The old smoke approval does not authorize
its new tokenizer CPU stage, GPU retry, pair or virtue. Each needs its own
reviewed exact-commit approval. No new Modal action occurs during preparation.
