# EXPLORATORY step 4 Modal adapter (v0.24.52)

Build only. No execution approval. Run offline from the repository root:

```
python -m exploratory.audit_tool.step4 --mode mock --output NEW_DIRECTORY
python -m unittest exploratory.audit_tool.test_modal_adapter exploratory.audit_tool.test_audit -v
```

`modal_adapter.mock` is also a factory for audit.py adapters mode. Adapter wraps
an injected request transport with generate(system, history, turn). The live
launcher batches both A (neutral/contrary) and B (neutral/neutral) into one GPU
allocation. Each pass has 33 fresh episodes and the original 12-turn scorer.
Unknown outcomes keep the audit tool's uncertainty bounds. Mock output tests
plumbing only; it does not test weights or estimate behavioral differences.

Checkpoint verification mirrors verify_reused_adapter's identity, exact roster,
symlink and streaming SHA-256 checks, then binds the index and every file to
private-adapter-deletion-plan.json before loading any model. It supports all
three final arms. A/B use neutral and contrary; virtue is mounted separately
read-only for future use, not evaluated. No historical evidence is modified.
The native model revision, engine and default sampling parameters come from
Study D v02428; max_tokens=4096 and skip_special_tokens=False are explicit.
Seeds follow a Study D style per-episode, per-turn rule rather than a fixed seed:
248017 + case_index * 12 + turn - 1 (zero-based case order in transfer-cases.json).
Run A shares this seed schedule across neutral and contrary arms (paired).
Run B adds pass_id * 396 (33 cases * 12 turns), so its two neutral passes use
disjoint seeds. A and B pass 0 reuse seeds; the comparisons are not independent
replications. Native transcripts record comparison, pass, case, turn and seed.
First decoded replies are retained without repair or retry. Native transcripts,
each finished episode, reports and caught failures are committed to the new
evidence Volume. Forced termination may leave the in-flight episode unresolved.

The live CLI requires --mode live --confirm-spend, refuses CI, and requires a
clean committed checkout. It reserves the entire $12 once in a dedicated Modal
Dict before building or scheduling; failed attempts consume the reservation.
No automatic restart or refund. One A100-80GB worker, no retries, single-use,
3.5-hour timeout, 120-second startup, 300-second idle setting. Source upload is
Git HEAD only, never local credentials. Existing private Volumes are read-only.

Budget limitation requiring review before execution: the reservation computes
(12600 + 300 + 120) / 3600 * $3.20 + $0.40 = $11.9734, using the historical
Study D all-resource hourly ceiling and a build allowance. It is a conservative
launcher reservation under those assumptions, not a provider billing limit.
Current pricing and image-build charges must be checked before approval; this
build does not establish an unconditional hard billing cap. No live execution,
image build, deployment, checkpoint download or model call was tested.
