# v02422 speed smoke — FAIL / STOP_FOR_REVIEW

Commit `258ff726d95565efcfb8e2c29cb0dfdce37ff674`.
App `ap-tOeYK2AtbdQ74oqw0dki8e`; call `fc-01M5A95YDEWJ8H16F1YQH5PRP2`.
Owner reports one attempt October 19, 2026, 9:29–9:50 AM America/Chicago.
Local attempt UTC 14:29:32; acknowledged submission UTC 14:31:20; these are
separate milestones, not identical launch timestamps.

Returned evidence confirms the sampler guard PASS and no nvcc failure. Diagnostic
training completed 8 steps / 64 examples / 10,438 tokens in 106.940762 s, with
410 modules verified in lora-coverage.json. Live LoRA benchmark completed both cells, each
8 requests / 512 tokens over two rounds. Native events contain 18 closed 64-token
outputs including two excluded warmup requests; all are engineering measurements,
not scientific acquisition/transfer outcomes.

Throughput discrepancy retained for Claude/owner review: owner supplied about
62.7 tok/s cold and 72.5 cached. The frozen policy uses total tokens divided by
SUM of round durations. Saved cold rounds total 16.322197591 s, giving
31.368325 tok/s; retained-prefix rounds total 14.129252522 s, giving 36.236878
tok/s. The supplied figures are approximately twice these values. No serving
winner, cross-revision speedup factor or arm projections inferred from this
incomplete experiment.

KV preflight PASS: native available 14.26 GiB, graph upper allowance 0.14 GiB,
conservative remaining 13.865 GiB vs requirement 13.765 GiB, margin 0.100 GiB.
Sampled device-wide peak 80,534,175,744 bytes; sampling is not an exact allocator
peak. Engine load 305.099577 s; worker software wall 1104.070789 s.

Merge child failed the unchanged preregistered bf16 logits comparison:
max_abs 1.125 > 0.5 AND relative_l2 0.0518121943 > 0.01. Full error and traceback
are preserved in merge-failure.json / process log. Merged benchmarking did not
run. This is an engineering stop excluded from science, not a scientific null or
format-gate verdict. no_restart=true; once-only approval consumed. The report's
training_authorized=false does not negate the completed diagnostic training.

Submission billing $5.89 used / $24.11 credit; reservation $2.452888889 under
$30 cap. Actual post-attempt cost and updated dashboard totals were not supplied;
reservation and worker time are not substituted for an invoice.

Preserved all four unmodified uploads and all 64 extracted files after safe-path
and ZIP CRC checks. Carried CPU evidence is byte-identical to the prior return;
listed hash references verify. Native engine-log hashes verify against its saved
prefixes (13,249 and 15,040 bytes); later shutdown output extends the file to
15,844 bytes. These append-only snapshots are not full-final-file hash mismatches.
Original ZIP, safetensors and full tokenizer remain private locally and ignored
by Git. Private GPU adapter retention follows review-stop policy; no remote
retention/deletion check or action was performed.

Record only. No code change, fix preparation, launch, rerun, ledger reset or
Volume modification. Pair and virtue remain unapproved. Await Claude's diagnosis
and next-stage design, then owner review.
