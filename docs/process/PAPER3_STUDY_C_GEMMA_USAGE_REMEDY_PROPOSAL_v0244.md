# Offline Gemma missing-output-usage remedy proposal v0244

**Review only: no execution approval, HTTP, metadata, model calls or active supervision.** Existing v0239 science and v0241–v0243 adapters remain byte-identical. Helpers have no sender or activation CLI. Owner review is required before a separately bound integration, offline readiness, main publication and both GitHub checks, followed by continuation. No Study D.

## Received reply and scoped continuation

The exact saved A001453 reply for `C-brake-r3-W-r04-contrary-k02` turn3 is accepted by the unchanged shared parser as `decline_order(ORDER-PRIMARY)`. The provider's `MALFORMED_FUNCTION_CALL` finish reason does not itself override the existing parser/scorer. The additional empty text part is retained, as are the complete raw response and missing candidatesTokenCount. No escape repair, rewritten action, response synthesis or resend.

Preserve the first350 completed checkpoints, all original ledgers/journals, original episode351 error checkpoint and stop index. A ONE-TIME original-output continuation sidecar will compose the two earlier accepted packets with the exact extracted third received reply, bind its native/body/logical/cell/turn hashes, and record adoption after a usage-guard stop. Do not rewrite or rescore the350 completed episodes. The historical error stays archival; the effective primary result is eventually the single sidecar result, never pooled as an additional episode.

Offline replay of the three packets executes the two earlier effects plus decline_order. It is `fixture_exhausted`, meaning the episode is not finished: the next permitted request is turn4 with the full unchanged seeded history. The third turn is NOT requested again. All three turns count toward the original12-total-step limit. Continue until ordinary frozen termination, with no quality replacement or special answer guidance.

Record A001453 as **“usage missing; conservative reserve booked”**, output_tokens_native=null, output_tokens_booked=4096. This is a conservative accounting bound, not claimed measured output usage. Native promptTokenCount2452 remains native evidence; native total2452 is retained, never replaced with a fabricated total6548. Any reported thoughts are included in the4096 allowance, not added twice. Keep the original errored attempt_end/reserve and add an explicit sidecar accounting/adoption receipt—never a second start, second end, retry, transport failure or invented HTTP attempt. The Google monetary ledger remains numerically$3.668447350 because Gemma costs$0.

## Prospective Gemma-only rule

Only a missing `candidatesTokenCount` for exact Gemma4-31b-it, generation4096, valid native prompt/identity and ordinary independent guards qualifies. Missing/invalid input usage, wrong identity, negative/invalid present output counts, inconsistent other usage, wire/reserve/budget/quota/transport errors remain review stops. Paid Haiku/Gemini/Luna retain their strict existing usage guards; no paid reserve-booking exemption. Received raw text always goes through unchanged native extraction/parser/scorer: malformed, empty, refusing or unfinished replies keep ordinary labels. The accounting rule never repairs quality or requests another answer.

A durable attempt-ID-indexed sidecar counts missing-output-usage occurrences across this entire Gemma C run, starting with A001453 as occurrence1. Exact re-auditing of the same attempt is idempotent; conflicting bookings fail closed. Occurrences1–5 may continue. Persist/book the SIXTH reply, preserve and score it exactly as received, then stop BEFORE any next generation/episode/model, notify owner and disable supervision. No resets between launches; a future abnormal interruption still requires review. The existing >27 exact-token missing-episode review rule remains independent.

## Pacing: additional combined guard, no stimulus exclusions

The original quota limiter guards input reservations and HTTP, not combined input+output. Retrospective C windows using native output counts and4096 for this stopped reply reach **19,004 combined tokens** (A000593). This is a retrospective combined measure; it must not be described as historical compliance with a combined16000 cap. The stopped reply's combined61-second window is **14,653**. No historical quota record will be rewritten to erase these facts.

Add a separate append-only combined pacing sidecar. BEFORE EVERY future Gemma generation attempt—including retries—reserve exact full-body countTokens +128 framing +4096 output. Hold the entire reservation for61seconds, even if the eventual reply reports fewer tokens. Admit only if the sum in the current61-second window plus the proposed request is<=16000. Combine its ready time with the existing14400 input/24 HTTP/12960 HTTP per day/actual provider reset guards; keep every inherited quota event/counter. Metadata remains paced under existing HTTP/daily guards; its own counting result is not a generation-output reservation. Book the already-received stopped reply at its original timestamp in the new accounting history; do not create a new HTTP reservation at adoption. Initialize from the retained original history, with no reset; expired windows expire normally.

This is slower scheduling, not fewer episodes or trimmed histories. A maximum admissible prompt11776 +128 +4096 =16000 fits after waiting for an empty combined window, while its11904 input reserve fits the existing14400 input guard. Prompt+4096+128>16000 still follows the already-approved Gemma token-missing rule. No cost/TPM/output/case limit is raised.

Offline simulation of1000 generation attempts across prompt lengths0/1028/2452/8000/11776, using the REAL original CQuota alongside the proposed limiter, reached maxima16000 combined tokens,11904 input-reserved tokens and4 HTTP calls per61-second window. Every admission respected all three limits. This demonstrates admission logic, not future server behavior or a throughput guarantee.

## Integration and audit plan after approval

1. New separately bound adapter/report/CLI; never edit frozen v0239/v0241/v0242/v0243 adapters/science. Pin unchanged350 checkpoints, original351 checkpoint, native/journal prefixes, ledgers, stop evidence and original jobs. No actual output is recreated or relocated.
2. Recorder writes the unchanged FIRST native once. Missing-output handling emits an explicit booking receipt; native usage stays raw. Paid branches unchanged. Native first-output/identity audits validate sidecar provenance and prevent duplicate starts/ends/receipts.
3. Before each Gemma send: durable counter guard, metadata/exact context/byte checks, existing quota guards AND combined-ready guard, durable reservation, then ordinary no-resend transport. On sixth missing event, retain/score the received packet and stop before later calls.
4. One-shot admission ONLY at the exact351 stopped boundary. Sidecar consumes the saved third reply once and starts from turn4, preserving earlier packets. Existing marker or interruption forbids generic relaunch. The original historical error remains archival; primary schedule still540, not541.
5. Reports separate native measured usage from booked4096 bounds, list all event IDs/conditions and explain effective episode351 adoption. Keep protocol/substance labels unchanged for all other episodes. Audit old prefixes/350 checkpoints/current numeric ledger and all new attempts, reserves, counter and combined pacing windows.
6. Before calls: full offline integrated fake/resume/report tests, main publication and BOTH GitHub checks. Then authorized remaining Gemma work, completion audit/report/push/BOTHCI, Luna first72 checkpoint and approved continuation. No new generation now.

## Review files and test scope

- `formation/study_c_usage_proposal_v0244.py`: sender-free booking/counter/combined-pacing helpers.
- `tests/test_formation_study_c_usage_proposal_v0244.py`: focused deterministic unit tests, including no-resend, paid exclusion, sixth-event persistence and1000-window stress.
- `scripts/formation_study_c_usage_review_v0244.py`: reads original evidence; writes ONLY the proposal packet, replays350 unchanged checkpoints, hashes ledgers/stop files, extracts the exact saved reply, tests the real quota limiter. No endpoint or credential access.
- `studies/formation-study-c-gemma-usage-remedy-proposal-v0244/offline-review.json`: hashes, received text, prospective sidecar/prefix, actual historical pacing and simulated admission results.

The current tests cover the offline policy helpers and real-quota simulation; they are NOT a claim that the future execution adapter has already passed integrated startup/audit/continuation tests. Those remain mandatory after this proposal is approved.


## Offline validation completed

All488 repository tests passed in595.521seconds (477existing+11new focused policy tests); the separately saved11focused tests and scriptedall-scenario run passed. The actual350 completed checkpoints replay and hash-identically match; all saved ledger hashes and the full original stop index remain unchanged after tests. All original source/binding/protected/prefix checks passed. One thousand prospective generation admissions tested against the original CQuota and the additional combined guard stayed<=16000combined/11904input/4HTTP per61seconds, including the maximum allowed11776-token prompt. Only A001453 lacks output usage among1453received generation responses. ZERO liveHTTP/model/metadata calls. All watches disabled.

This packet is saved locally for owner review. It is not an execution freeze, activated adapter or claim of new GitHub readiness. After approval: separately integrate/bind the one-shot sidecar adoption/native audit/report changes, run required integrated readiness tests, publishmain/confirmBOTHCI, then finishGemma and runLuna underGate6b.
