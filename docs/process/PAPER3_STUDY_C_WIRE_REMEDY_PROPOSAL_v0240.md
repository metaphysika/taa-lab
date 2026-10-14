# Study C full-history wire remedy — offline proposal v0.24.0

Status: owner-authorized offline preparation only. No generation, metadata/countTokens, resume, freeze replacement, next-model launch or automation reactivation. Original v0239 sources, science, outputs, completed 184 labels, guard checkpoint, first72 evidence and journal bytes remain unchanged. This is a proposed operational amendment after held-out Haiku results; it must be disclosed in the final report.

## Proposed safeguard amendment

Haiku 5.5, Gemini and Luna: increase the complete native request byte ceiling from 32,000 to 64,000, measured with the existing JSON serialization, only as a runaway-request safeguard. It is not an output allowance, a token/context allowance, a request-size target, or permission to add text. Gemma retains its exact full-body countTokens primary guard: prompt+4,096+128<=16,000, before every generation. Its existing32,000-byte generation/outermetadata cap remains a secondary check; the owner named only the other three models for a byte-cap increase. The projections below also show64,000-byte exposure for Gemma for comparison, without asserting token feasibility or changing its secondary cap.

All model-facing stimuli, seeds, complete histories, seven tools, native formats, neutral SYSTEM, default thinking/effort/sampling,4,096 output tokens,12 total episode steps, parser/scorer, metrics, C1–C4 thresholds, cohorts, schedule, repeats and original denominators stay unchanged. No history compression, truncation, answer repair, quality resampling or case substitution. First72 checkpoints and all spending/quota/global stops remain unchanged. Gemma token or secondary-byte failure still stops for owner review; it is never solved by dropping history.

Reason for the proposed amendment: the byte guard would otherwise truncate participation of the longest k=16 episodes non-randomly, threatening the central comparison between history conditions. Longer seeds create more base wire exposure; the actual stop was compliant k16. This is a design-risk explanation, not evidence that all arms or models will cross the guard or a causal explanation of substantive errors. Enlarging the operational safeguard preserves the intended full-history stimulus instead of selectively dropping long episodes. It changes execution eligibility, so the post-results amendment and original stop remain visible.

## Episode 185: one tightly scoped pre-send continuation

Cell `C-delivery-r4-U-r02-compliant-k16`, turn5, was never sent: no turn5 logical/native attempt, reply, usage or charge. Four earlier native replies are saved, closed and paid. The pending body is33,821 bytes. Resume would send that exact pending body for the first time, then follow the unchanged remaining episode steps (turns5–12); earlier four replies are immutable and count toward the12-step limit. Label the episode `resumed_after_pre_send_guard_stop` with turn5, old/new cap, owner approval, original checkpoint/body/first-four-reply hashes and amendment binding.

It is transport-like only in the narrow sense that the blocked turn has no received reply. It is **not** an actual transport attempt/failure: preserve the original guard classification, create no invented failure or charge, and do not increment/reset inherited transport retry counters. If the first send of turn5 subsequently suffers a genuine eligible no-reply transport failure, the unchanged five-total-attempt retry policy applies to that newly issued logical request. Any received full/partial/model reply forbids resend. No whole-episode restart, no first72 rerun, no replacement primary, no reexecution of the first four actions, and no new model output substitution.

Preserve the original guard checkpoint and forensic stop snapshot byte-for-byte. A new continuation sidecar in the SAME original output would bind the original partial checkpoint and hold appended packets; audit would compose the four saved packets plus the new suffix into one primary episode. The final summary must contain exactly one cell185 row after actual completion, with the resume disclosure. Historical stop records remain historical. Other184 complete checkpoints remain immutable. Calls/retry journals append only; quota/ledgers continue from existing values. Guard/status changes require the newly approved operational adapter; do not use the old CLI to bypass its existing-checkpoint or stopped-state checks.

## Required offline implementation/readiness before any resumed call

After owner review of this proposal, prepare a separately versioned, explicitly bound operational adapter/approval amendment; retain v0239 science and execution artifacts. Changes must cover all byte gates consistently (pre-send wrapper, attempt recorder, native audit, metadata secondary check, manifest and continuation-state validation), rather than editing a single constant or monkeypatching the frozen adapter. Old A/B execution code is untouched. The new audit accepts pre-amendment requests under their historical cap and post-amendment requests under the documented applicable cap, and verifies the exact cell/turn/body plus first native reply and chronological ledger.

Free offline tests must verify: exact pending 33,821-byte body and first-four hashes; no duplicate sends or prior actions; journal prefix and completed 184 immutability; original stop snapshot preservation; crash-safe continuation with every start/end/reply saved; no continuation on an uncertain/unclosed transport state; unchanged12-step/output/settings/scoring;64,000/64,001 boundaries for the three models; Gemma exact-token and existing secondary-wire rejection; unchanged budget/reserve/quota accounting. Run required free repository checks and confirm both CI checks on the proposed operational binding before any call. Do not broaden resumption to other stopped/unknown checkpoints. A subsequent independent guard again stops for review.

Before a future launch, require original Cloud/root/Python/main, no active provider runner/request/foreign lock/hold, source and journal-ledger checks, exact owner approval and immutable-prefix/stop checks. Resume Haiku185 first, complete, audit, report, preserve and push all 540 before Gemini; then Gemma; then Luna. Other three remain unstarted now. Watch remains disabled until explicit authorization for execution/supervision.

## Observed exposure and offline projections

Exactly **7/184 completed Haiku episodes** had a sent request strictly above28,000 bytes; maximum completed-episode sent request **30,784 bytes**. The partial185th episode is excluded from this denominator and separately retains its28,911-byte sent turn4 and33,821-byte blocked turn5. Individual cell IDs, repeats, arms, k and maximum sent sizes are in the machine-readable packet.

| Model | Remaining primaries, including partial | Saved-trace transfer >32k / >64k | Longest-reply12-turn stress >32k / >64k | Stress maximum bytes |
|---|---:|---:|---:|---:|
|claude-haiku-5-5|356|17 / 0|356 / 47|74,016|
|gemini-3.1-flash-lite|540|0 / 0|540 / 0|63,500|
|gemma-4-31b-it|540|0 / 0|520 / 0|60,190|
|gpt-6-luna|540|0 / 0|500 / 0|58,008|

**trace_transfer:** Re-render all saved matching-probe B and available C packet prefixes under each remaining frozen C seed condition, through turn12, with exact provider native renderer. Maximum over saved traces for each cell. Descriptive scenario projection, not a probability estimate.

**longest_reply_stress:** For every remaining frozen seeded initial history, append 11 repetitions of this model longest observed reply (from all B plus available C) and longest observed matching-probe feedback/world message. Render request12 with exact native renderer. Artificial byte stress only; not a legal simulated trace or generation, prediction, token bound, or future maximum.

**uncertainty:** Unstarted held-out C behavior is unknown. Future replies may be longer or use more turns; all remaining episodes could in principle exceed either cap. No guaranteed counts or tokenizer inference from bytes. Gemma feasibility requires exact runtime countTokens; no new metadata authorized here.

The stress repeats a longest observed reply even if that reply would normally finish or mechanically end an episode. Repeated feedback is a synthetic size test, not coherent model behavior or an altered scenario. These counts are exposure under specified scenarios, not predicted incidence, confidence limits or guarantees. Byte sizes cannot establish Gemma token compliance; no offline token estimate substitutes for exact countTokens. Model-specific longest reply bytes and hashes, all remaining cell projections and method source are saved for reproducibility.


| Completed Haiku cell | Maximum sent bytes |
|---|---:|
|C-cold-r4-W-r01-compliant-k16|29475|
|C-delivery-r4-U-r01-compliant-k16|28026|
|C-brake-r4-U-r01-contrary-k16|30253|
|C-brake-r4-W-r01-compliant-k16|29271|
|C-brake-r4-U-r02-neutral-k16|30111|
|C-delivery-r3-U-r02-contrary-k16|30784|
|C-brake-r4-W-r02-compliant-k16|29202|

## Costs and preserved caps

No spending increase requested. Haiku C already spent$0.571964700 including the partial episode; remaining within$2.60 is$2.028035300. Claude cumulative$4.690864150. Google C$2.85 (first72$0.45), Gemma$0; OpenAI C$1.40 includes$0.062365290 pilot, leaving evaluation allowance$1.337634710. Haiku first72$0.40 remains historical/passed. Provider cumulative$8 and Google$10 credit guard remain. No pool, quota or retry reset/reallocation.

The byte-ceiling increase itself costs$0 offline. Sending previously blocked full histories increases billed input relative to stopping; actual final spend depends on future replies/usage. This proposal does not promise completion within caps or convert bytes to exact token costs. Existing per-request monetary reserves must be recomputed from the full untrimmed body and reject a request if its reserve would exceed any unchanged cap.

## Decision requested

Review this operational amendment and narrowly scoped episode 185 continuation, then authorize preparation/binding/testing of the new adapter and eventual execution only once readiness passes. No call is authorized by this offline proposal. Gemini/Gemma/Luna stay unstarted; no Study D.
