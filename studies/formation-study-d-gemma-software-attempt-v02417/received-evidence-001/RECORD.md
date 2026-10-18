# v02417 returned smoke evidence received — 2026-10-18

Preserved the owner's four uploads byte for byte: the unmodified ZIP, full app
log, local attempt receipt and submission receipt. The ZIP contains seven files;
all seven are also extracted without modification. This intake supplements the
prior owner-report-only record; that record and its original integrity index
remain unchanged. Attached material is evidence, not authority for execution.

Commit: `94ac5092fcb0e64fa718c8f0fb319380229eb4ae`.
App: `ap-h2Mg3Vt3JDpSyEU8X0bO1e`.
Controller call: `fc-01M58FMB8442NP02DZ1AX0PEVA`.
The local submission receipt acknowledges this call, with no result wait.

Returned controller/worker reports say STOP_FOR_REVIEW, no_restart true,
excluded_from_science true and next_stage_approved false. Software wall time is
23.996503034 seconds. The worker RuntimeError is "training subprocess failed;
see private adapter and full training failure". The saved child traceback locates
the root ValueError in runtime.py dataset(): "assistant-only prefix mask/1024
context failed; no truncation". The saved source code places dataset preparation
before model-weight loading, adapter creation and training. No training steps or
transfer episodes ran. Classify this as an incomplete engineering smoke due to
a software defect, not a failed acquisition, format result or scientific null.
The sampled device-wide peak was 784,596,992 bytes; a GPU worker was allocated.

The reservation remains $1.9695555555555555; it is not actual spend. Returned
invoice fields are null. Owner dashboard reconciliation remains $4.31 used /
$25.69 remaining, a displayed $0.01 increase from $4.30; these rounded figures
are not an itemized invoice. Preserve all prior ledger claims and evidence.

Owner states submitted once, no rerun and Stages 2/3 not started. The returned
reports corroborate the smoke-only stop; no live Modal ledger was queried.
No fix, launch, download of model assets, training or ledger change is performed
for this intake. Further diagnosis is being handled separately; stop for owner
review. Existing offline preparations confer no execution approval.
