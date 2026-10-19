# v02420 CPU rehearsal evidence received — 2026-10-19 UTC

Commit: `90454d4a508d2b373625300834d719e8f1fb5cce`.
App: `ap-Fx5VmY3ZUmACm4qqN38XwA`.
Call: `fc-01M58VDEXGTC2TDJC9NN956Y25`.

PASS confirmed in the supplied report, receipt and rehearsal evidence. Two
optimizer steps processed 16 examples / 2,624 tokens on a tiny random CPU model;
this is diagnostic training, excluded from science. All three 2,000-example
data sets were built; the training masking check passed for 2,000 contrary
examples. Coverage passed: 13 target modules, 7,808 trainable parameters;
adapter reload passed for 26 tensors. No GPU, pretrained weights download or
model generation is reported. vLLM adapter loading remains untested.

Preserved unmodified ZIP (36 files), app log and both local receipts, plus all
36 extracted files. Verified ZIP CRC and every listed receipt, rehearsal and
checkpoint SHA-256 against the received bytes (39 references including repeated
checkpoint references). The rehearsal index itself lists 26 files. The owner's
earlier download note reports a Modal 500 truncating five bulk-download files;
these were individually re-fetched and the 26 rehearsal hashes verified. The
received archive passes those checks; the initial truncated download is not
supplied and is not reconstructed.

Owner dashboard after CPU: $4.72 used / $25.28 left, unchanged at displayed
precision. This does not establish a zero invoice charge; actual invoice amount
remains unknown. Original CPU reservation $0.22852777777777777 retained. No
ledger edits, inferred refunds or reservation resets. Cumulative approved cap
$30; later stage targets remain unchanged.

Earlier owner approval covered GPU smoke only at this commit. Latest instruction
places launch preparation and code changes on HOLD pending Claude's review and
owner approval. Pair and virtue are unapproved. No launch prepared or executed
while recording this return; no code or original evidence changed.

ZIP, safetensors and full tokenizer JSON remain in this private local archive
and are ignored by Git, preserving the non-sharing commitment for adapters.
Other readable evidence and hashes can be reviewed without publishing weights.
