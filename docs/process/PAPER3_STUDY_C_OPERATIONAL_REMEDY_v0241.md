# Approved Study C operational amendment v0.24.1

The owner approved this remedy after Haiku's original wire guard stopped before episode 185 turn 5. The scientific Study C v0239 freeze remains unchanged. This amendment changes operational admission and one explicitly approved pre-send continuation; it does not change stimuli, seeds, model-facing histories, neutral SYSTEM, native formats, tools, defaults, output limits, scoring, hypotheses, cohorts or spending caps. The original v0239 adapter, freeze, first-block report and stop evidence remain preserved. Haiku native JSON remains neutral and enabled from the first original call.

| Model | Complete native request byte safeguard | Primary context guard |
|---|---:|---|
|Haiku 5.5|128,000|Existing reserve, usage, identity and pricing guards|
|Gemini|128,000|Existing reserve, usage and identity guards|
|Luna|128,000|Existing reserve, usage and identity guards|
|Gemma|64,000 generation and outer countTokens body, secondary|Exact full-body countTokens: prompt + 4,096 + 128 ≤ 16,000|

Byte limits use the original JSON serialization and are runaway-request safeguards, not stimulus targets or enlarged output limits. Monetary reserves still cover the full untrimmed body. All existing spending caps, cumulative $8 stops, Google credit ceiling, quota carry-forward and transport counters remain. The existing Haiku short-context pricing guard (conservative UTF-8 byte estimate ≤100,000) remains independently enforced; the observed 74,016-byte stress maximum is below it. No new tier or pricing schedule is introduced, and this amendment does not promise completion within unchanged guards/caps.

The old 32,000-byte guard would otherwise exclude the longest k=16 episodes non-randomly and threaten the central history comparison. This reason was recorded in the notebook before any further call. Seven of 184 completed Haiku episodes exceeded 28,000 bytes, all k=16. The original offline projection and item exposure table remain in the v0240 proposal packet. Artificial repeated-longest-reply stress projected 47 remaining Haiku episodes above 64,000 bytes. Those scenarios are not future-incidence predictions or guaranteed maxima, and bytes cannot certify Gemma token fit.

## The only interrupted episode authorized to continue

`C-delivery-r4-U-r02-compliant-k16` has four received, closed, paid replies. Turn 5's exact 33,821-byte native body was blocked before HTTP. It may be sent for the first time under the approved amendment. The original guard checkpoint remains immutable. A separate `-continuation-v0241.json` in the SAME original output holds the combined original four packets and future suffix. The eventual single primary result is labeled `resumed_after_pre_send_guard_stop` and audited against the original checkpoint/body/native/journal bindings. The four prior turns count toward the unchanged 12-step episode limit.

This is not an actual transport attempt/failure: no invented attempt, usage, charge or retry counter. Genuine eligible no-reply transport errors after turn 5 is actually issued use the unchanged five-total-attempt policy. Any received full/partial/model reply remains ineligible for resend. No episode restart, original first72 rerun, output replacement or trimming is permitted. The new CLI permits this narrowly bound stop once; a missing/mismatched body, changed earlier packet, existing continuation sidecar, unclosed native/job, absent-running or other interrupted state fails closed. No broader restart authority is inferred.

## Gemma missing episodes

After a valid, closed exact countTokens reply, if prompt +4,096+128 exceeds16,000, generation is never issued for that turn. Save the checkpoint as `guard_stopped`, with full earlier packets, blocked turn, counted tokens, body hash, no judgment label and no score. It is a missing primary episode, never substantive error, mechanical error, correct judgment or replacement. Counts by history condition, condition/k and probe are persisted after each episode. Metadata and prior generation evidence/costs remain retained.

The first72 checkpoint closes after72 scheduled episodes (completed judgments plus missing token guards). Its original eight-mechanical-failure review threshold and planned denominator72 remain; missing counts are disclosed separately. First-block pass also requires all closed source/native/replay/identity/usage/reserve/ledger checks. Continue through27 Gemma token guards (exactly5% of540); persist and stop for owner review on the28th (>5%), before any later episode or model. Other byte, quota, budget, safety, identity/usage, transport-exhaustion/limit or unknown/unclosed guards retain immediate stops.

Reports include every planned cell. Guard-missing entries have null substantive/mechanical labels, completed=0 and valid=0, retain their trace path and metadata count, and enter the unchanged frozen planned-denominator missing bounds. Frozen C1–C4 arithmetic is reused unchanged with those rows absent from scored judgments. Report completed, missing and valid denominators separately; do not describe540 scored judgments when some scheduled primaries are missing.

## Operational source and audit binding

New modules are `formation/study_c_evaluation_v0241.py` and `formation/study_c_report_v0241.py`; CLI is `scripts/formation_study_c_evaluation_amended.py`. The original pinned modules remain unchanged. `studies/formation-study-c-operational-amendment-v0241.json` records owner approval, exact byte caps, Gemma threshold, original freeze/binding, immutable184 completed plus partial185 checkpoints, original stop artifacts and699-attempt journal byte prefixes. The separate operational binding pins the new adapter/report/tests. It changes no science hashes and no current account balances.

All new requests have internal (not model-facing) operational-amendment/cap tags. Native audits use the original32,000-byte limit for pre-amendment attempts and amended limits for tagged suffix attempts, check exact native body/settings/history and first output, and verify identity/usage/reserves/charges and baseline+journal equality. Full terminal certification remains unavailable until the original partial cell has actually completed in its sidecar. The stop index is historical, with its protected immutable files and journal prefixes checked separately from legitimately mutable statuses/ledgers/suffixes.

New readable and machine reports use new v0241 report paths in the original output; original first72 published breakdowns stay preserved. Completion indexes cover nested amended report files as well as all original evidence. The final report retains original primary-cohort versus Luna sensitivity, unpooled pilot, C1–C4, all item/theme/rung/arm/k/repeat breakdowns, reporting–abstention joints, original over-refusal splits and concentration notes. The operational changes are explicitly post-results disclosures.

## Required readiness and launch

Before calls: free operational tests, unchanged science/parser/replay checks, all repository unit tests, scripted `run.py --scenario all`, and a full fake2160-primary report pipeline including token-guard missing entries must pass. Confirm both GitHub checks on the bound code commit. Never read keys.env or credentials; no Groq/metadata outside approved Gemma execution, new provider/tier, Study D or other stage.

Use ONLY original Cloud, `/workspace/taa-lab` main and `/workspace/haiku55-runtime/venv/bin/python3` (3.11). Require no active provider runner/request/shared lock/foreign hold; never clear foreign locks or signal reused PIDs. Use uniquely numbered runtime logs/receipts, same original outputs. Exact initial one-time Haiku continuation:

```
/workspace/haiku55-runtime/venv/bin/python3 scripts/formation_study_c_evaluation_amended.py --model claude-haiku-5-5 --approved-study-c --after-passed-checkpoint --resume-approved-pre-send-guard
```

Later fresh next models use `--model MODEL --approved-study-c`; passing closed first72 suffixes additionally use `--after-passed-checkpoint`, WITHOUT the scoped pre-send flag. Haiku completion is audited/reported/snapshotted/pushed and both CI checks confirmed before Gemini starts, then Gemma, then Luna. Existing Gate6b supplies that execution approval; no repeat spending gate. While a verified approved runner is alive and normal, perform read-only status/protected-prefix checks only, never terminal audit, commit, hold or duplicate launch. Proactive checkpoints/completion/actionable failure notifications are mandatory; hourly watch restores only after authorized readiness/resume. Old automations remain disabled. On another actionable stop, disable this watch and report precise evidence/review needed. No Study D.
