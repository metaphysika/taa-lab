# Cross-arm scoring execution plan — frozen before outcomes

[PROTOCOL] Use the already committed cross-arm protocol v0 unchanged, over T01–T10 only.
[IMPLEMENTATION] Pin the reviewed runtime to PR31 merge a6df341d14c649467512ec98afc387a25d55001f.
[DESIGN] Eight arms and four unchanged scripted controllers yield320 scored episodes; the driver separately validates ten ordinary-core key passes.
[REPORT] Retain every common metric, raw discrepancy/incomplete/unassessed item and the separate engineering fault observations, without interpretation.
[LIMIT] TraceGrant has only ten predeclared contracts; no new contract, model call, spend, Modal operation, evidence deletion or public release.

## Authorization and unchanged inputs

Chris relayed Claude's approval of6526bccd conditional on overlap sensitivity.
The companion addition7ae8137bd6609c49509f4d69fb672da8920e74a5 passes on all
three backends and fails on all three summed-overlap mutants. All six exact-head
CI runs (push/pull-request for Gateway, Harness and Formation3.9) succeeded.
PR31 merged as a6df341d14c649467512ec98afc387a25d55001f. The runtime, source
keys, controllers, contracts, matching rules and original fixtures are unchanged
from the reviewed6526bccd snapshot; the conditional addition is test-only.

This is execution bookkeeping, not a replacement or amendment of the protocol.
Original protocol SHA-256: e8059b51eaea0399f4ffe198d5712497067e5a0f43045539ffad1a71a67b9580.
The approved Q14–Q16/H1 implementation and common oracle were reviewed before
this run. No program or contract is selected based on a comparison outcome.

## Execution and retention

Invoke the existing `comparators.cross_arm.run_suite(on_episode=...)` exactly
once in its existing order, with no backend/controller changes. Pin every
runtime/input source hash; require a clean committed tree and a unique new
output directory. Append/fsync each complete episode to a journal. Retain
partial data and stop on an error; never overwrite or automatically rerun.
Verify the journal against the driver's canonical JSON serialization and verify
all input hashes again at completion. No semantic label comes from an arm's
returned decision. The driver uses the original frozen source keys and the
pre-declared source/context matching. Changed/extra requests remain unassessed.

Archive raw results, journal, source/driver hashes, logs and all observations.
Report all25 common metrics (24 integer metrics and the per-episode list of
currently closed claims with unresolved duties). Sum scalar metrics without
relabeling; preserve every list and every unassessed observation. Provide
full arm totals and controller/episode tables, raw nonpassing checks and
coverage limits. No numerical outcome forecast, new threshold or tolerance.

The separate floor/static T23 fault supplement is the reviewed engineering
replay from PR31, not additional scoring programs:6 actual injections,8 absent
boundaries not applicable by design,4 actual receipt-mismatch audits retained.
Keep those observations outside the320-episode totals. TraceGrant's broader
engineering tasks with missing contracts stay unrun. No wider coverage claim.

## Report-only utilities (authored and hashed before outcomes)

These utilities only journal the existing driver and format its returned
metrics; they add no policy, authorization, discharge, controller or key logic.
Their complete source will accompany the data archive.

- `run_scoring.py`: SHA-256 `dc5ae245c72f0ca984e3b5c2c89909d8f451b4831fd88f63702b64adad4a353c`.
- `render_scoring.py`: SHA-256 `14cee7b5436ebf0110370e672494b45487185575eb5bcab9482eddf578da1a6e`.

After completion, add a second report/data commit and open a separate draft PR
for Claude's review. Do not merge that new PR under the earlier PR31 approval.
No empirical H3 inference or interpretation beyond the protocol definitions.
