# Retained-log replay / audit window v0.1.1

[IMPLEMENTATION] Read-only local HTML, with no external assets, network calls or episode execution.
[DATA] All 320 v0.1 corrected episodes: ten programs, four controllers, eight arms.
[DETERMINISM] Identical retained evidence and renderer produce identical page bytes and checksums.
[PROVENANCE] Checked record effects, returned decisions, input schedules and external-oracle states are distinguished.
[LIMITATION] Historical native event streams are incomplete; missing token/report/duty events are never reconstructed as facts.

Generate and open `index.html` locally:

```sh
python -m replay.build \
  --validation docs/process/evidence/gateway-cross-arm-scoring-v01-corrected/validation.json \
  --output /tmp/taa-replay-new-directory
```

The output must be a new directory. The builder verifies the retained archive,
every archived member and all input-schedule source hashes. Schedules supply
step/entry positions only. No backend, rule evaluator or oracle runs. It applies
the runner's phase order: events, duty reconciliation, all proposals, all
executions. Every scheduled action must match a retained observation.

There are 320 individual episode pages, 40 arm-comparison pages and an index.
Select arms and scheduled steps to compare the same episode. Raw check facts,
record versions, proposed arguments, returned dispositions, observed effects,
post-v0 supplementary evaluations and state audits remain inspectable. A final
external duty board and chronological oracle histories are explicitly normative;
they are not the comparator's internal ledger or proof of physical dispatch.
Actual report-delivery totals are separately labeled.

## Historical coverage gaps

The v0.1 scorer retained returned token issuance/expiry summaries and execution
outcomes, checked record effects, selected actual pre-commit evidence, final
worlds and independent-oracle duty histories. It did not retain every native
token status, intermediate duty transition, report envelope/recipient or
correction event. These cannot be recovered faithfully from final state alone.
Each historical page says so. No new replay is silently substituted for v0.1.
The two gap categories in `MANIFEST.json` apply to all 320 historical episodes;
this is viewer coverage, separate from the original scoring's incomplete count.

## Full native logs

```sh
python -m replay.build --native-log episode.jsonl \
  --trusted-checkpoint separately-retained-checkpoint.json \
  --output /tmp/taa-native-replay-new-directory
```

Full native events show the actual retained token, record, duty, report,
correction, receipt and decision payloads in order. Chain and ending count/head
are checked against the separately supplied checkpoint. The viewer does **not**
possess a signing key or verify the HMAC authentication tag. A self-consistent
chain does not establish event truth or protect against host compromise.

All dynamic text is escaped. Inline style/script hashes permit only the fixed
viewer code under a restrictive CSP. The page has no telemetry, external
libraries, remote assets, model client or mutation controls. Input filenames,
current time and machine paths do not enter output bytes.

Keyed metrics still apply only to matching ordinary-core contexts. Early
floor/static divergence is unassessed, not safe. The ten-program TraceGrant
limit and separate partial-write supplement remain unchanged. The supplementary
measure was defined after v0, is development only, and must be pre-registered
before Experiment A. This viewer adds no empirical validation or launch approval.

The retained generated bundle is [pages.zip](../docs/process/evidence/gateway-replay-v01/pages.zip).
Extract it into a new directory and open index.html. The [stage report](../docs/process/TAA_GATEWAY_REPLAY_v011.md)
records coverage and verification.
