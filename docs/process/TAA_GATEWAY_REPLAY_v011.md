# Replay / audit window v0.1.1

[DATA] The corrected v0.1 archive supplies all 320 historical episodes across ten programs and eight arms.
[IMPLEMENTATION] Static local HTML exposes proposals, retained checks/facts, token-return summaries, effects and external duty histories.
[COMPARISON] Forty pages compare the same program/controller across arms, with arm and scheduled-step filters.
[DETERMINISM] Independent processes, including PYTHONHASHSEED=17, produce identical bytes for all 362 files.
[LIMITATION] Historical native token/report/duty/correction streams are incomplete and remain explicitly unavailable.

## Artifact and use

Download [pages.zip](evidence/gateway-replay-v01/pages.zip), extract it into a new
directory and open index.html. The archive contains 320 individual episode
pages, 40 comparison pages, an index and a checksum manifest. It has no remote
assets, network calls or model connection. [Validation](evidence/gateway-replay-v01/validation.json)
records every page hash and the source archive hash. [Builder instructions](../../replay/README.md)
cover regeneration and the separate full-native-log reader.

Inputs are the unchanged retained corrected scoring archive and its verified
input schedule sources. The latter supply scheduled step numbers and entry
positions only; every proposed/executed action must align with the retained
journal. Grouping follows the runner: input events, duty reconciliation, all
proposals, all executions. No backend, policy or oracle is executed to generate
a page, and no new episode is collected.

## What is actually retained

Each action view includes the actual agent input, origin binding, returned core
result, available checks with rule facts and record versions, observed record
effects, source-key/context label and common state audits. A cautious agent's
withheld request is labeled “gateway not called”; it is not a gateway refusal
or a missing check result. Returned token summaries and execution outcomes are
identified as such. They do not become reconstructed token statuses.

The retained independent pre-commit snapshots and final external duty board
show claimant, owner, status, deadline and available report-recipient fields.
Chronological oracle histories remain labeled normative. They are not an arm's
internal ledger and are not proof of delivery. The actual report-delivery
aggregate is separately displayed. Complete historical per-dispatch native
envelopes, recipients and token lifecycle events were not retained by the v0.1
scorer. Those channels cannot be recovered faithfully from final state alone.
This artifact does not replace the original evidence with a new replay. All
320 historical episode views have partial native-event coverage (zero have a
complete native history). This is separate from the original scoring
acceptance’s zero incomplete assertions.

The full-native-log reader displays actual retained decision, token, record,
duty, report, correction and receipt event payloads. It verifies canonical JSON,
sequence/hash chain and the count/head against a separately supplied checkpoint.
It does not verify the HMAC authentication tag or claim host integrity.

## Verification

Five component methods cover all 320 schedules/2,912 observations, deterministic
rendering and input non-mutation, withholding and missing-channel attribution,
XSS escaping, safe filenames, and native edit/truncation controls. Independent
full-site generation reproduces all file bytes. The fixed JavaScript passes a
Node syntax check and arm/step filter controls; this is not a browser-layout test.
The site's inline script/style hashes are included in a restrictive CSP.

Repository-wide and scripted acceptance results accompany the final PR evidence.
The earlier pre-label rendering and stopped test prefix remain in the execution
workspace; source scoring records and expected fixtures are unchanged.

## Research limits and review

Keyed metrics remain conditional on matching ordinary-core context. Floor/static
unassessed actions are not safety evidence; keyed counts cannot establish a TAA
advantage over SQL. TraceGrant remains limited to ten predeclared programs.
The supplementary measure was defined after v0, is development only and must
be pre-registered before Experiment A. Separate partial-write observations are
not added to this 320-episode population. The viewer adds no empirical evidence
for H3 and no permission for model calls, spending or release.

This is a separate PR for Claude's review. Historical coverage gaps are data
limits, not silently skipped or invented event assertions.
