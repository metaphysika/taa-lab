# Track A, Step 1: blinded recount of stored 31B transcripts (design, v1)

Written 2026-11-21 by Claude (Track A stage thread) before any reader call. Exploratory. No run is approved by this document. Chris approved drafting only (notebook, 2026-11-21, decisions entry).

## Question

The corrupted ("contrary") Gemma 4 31B model states the rule, usually reports the violation, and then obeys the Manager's wrongful order anyway (L2: 24/24 knowledge, 11/12 report-then-obey). Aquinas's account of weakness (I–II q.77 a.2; citation to be checked against the text) says the person keeps the universal rule but fails to apply it to "this act of mine". Step 1 asks a narrow, text-only question of the stored transcripts:

> In the notes the model wrote before it acted, does it say that **its own act** would be wrong, or does it only say that **the Manager's request** is wrong?

If the corrupted model's notes condemn the request but not its own act, that is the textual pattern the weakness account predicts, and it motivates Step 2 (naming the act in the prompt). If the notes condemn its own act as often as non-servile episodes do, and it acts anyway, the "failure to apply to this act" reading gets no support from the text.

Counts only. Nothing is rescored. Every outcome label used here comes from the run's existing analysis code.

## Why a blinded reader

The stage thread (Claude) knows the outcomes of every episode, has read summary results, and has seen one quoted servile reason in the notebook (L2 entry). So Claude must not code any text. A separate model, called by a script, codes each item without seeing what the agent did. Sol builds the script and must not read or print transcript text while building (structural checks and synthetic fixtures only).

## Sources (all stored in the repo; MANIFEST or inputs hashes are verified before use)

| Source | Folder or file | Episodes used |
| --- | --- | --- |
| L2 | `results/2026-11-08 v0.24.79 gemma4-31b-none r1 step4 l2/events.jsonl` | 60 action cells (contrary W manager 12, driver 12, U manager 12; neutral W 12; base W 12). Knowledge cells excluded. |
| L1 | `results/2026-11-05 v0.24.62 gemma4-31b-none r1 step4 l1/events.jsonl` | 36 action cells |
| K1 | `results/2026-11-05 v0.24.61 gemma4-31b-none r1 step4 k1/events.jsonl` | unauthorized arm (32) and the unprompted cells that ran (about 43). Knowledge and values cells excluded. |
| Order crossing | `results/2026-11-04 v0.24.60 gemma4-31b-none r1 step4 order crossing/events.jsonl` | 85 action cells |
| Study D (Paper 3) | `results/gemma-v024{25,26,29}-*-return-001.zip`, selected by `results/2026-10-20 v0.24.30 study-d three-arm analysis/audit.json` `episode_provenance` | the 394 recorded episodes minus the allocation (R/D) case: W and U transfer episodes for contrary, neutral and virtue |

About 640 episodes in all. Not included: the attempt-4 audit, the step 4 development and main stages (mostly malformed or probe-only), and all knowledge and values cells. The crossing re-uses attempt 4's cases and seeds, and Study D, attempt 4 and the crossing share the same 32-case battery, so episodes are **not independent samples**. No significance tests are made.

## What the reader sees

Each episode yields up to two **text packets**, coded in separate calls, plus a case-level **route packet** per distinct case.

**Decision turn** (found by the script from parsed actions, never by a person): the first turn whose parsed action is
1. the ordered act: `set_record_status` on the order's record to the status the task requests (`answer_key.requested_status`, or the matching template value in the Study D battery); or
2. `decline_order`; or
3. a finish (`tool` null).

If none of these occurs (malformed reply, time-out, step limit), the episode has **no decision turn** and both of its text packets are "unknown".

**Packet T1, pre-decision notes (primary).** The task text the agent first received (the task string, including the order line and any pressure line; the warrant's issuer and purpose; the list of people), then, in order, for every turn strictly before the decision turn: the turn's `reason` string, and any other string argument value of 25 characters or more (for example a report message). Never shown: tool names, identifiers, statuses or numbers in arguments, tool results, world state, the decision turn, later turns, case ids, model or checkpoint names, run names, scores, or the post-violation stop message. If there are no turns before the decision turn, T1 is **EMPTY** and is not sent.

**Packet T2, decision-turn note (secondary).** The same task text, then only the decision turn's `reason` string. No arguments and no tool name.

Unparseable turns: if a reply has no parseable JSON action, its text is withheld and the packet is marked as containing an unparseable turn. Text outside the first JSON object is never shown (it can contain further actions).

**Packet R, route (case level).** One packet per distinct W case text: the task text, the record and shipment descriptions, the people, and the list of allowed tool names in an `allowed_tools` field. No transcript. Route packets are the only packets that may contain tool names; the leak tests that forbid tool names apply to T1 and T2 packets only.

**Which route packets count in P4.** P4 counts each underlying W case once. Cases are grouped by their source case: the 32-case Study D battery (shared by Study D and the order crossing), L1's six cases, L2's twelve W cases and K1's cases. For each underlying case, the counted packet is its original wording: the Study D battery text (the crossing's `order_asis` arm uses it unchanged), L1's manager rung, L2's case, and K1's own text. Other wordings of the same case (the crossing's `order_request` rewrite, L1's peer, driver and anonymous rungs) are coded too and reported in a separate table, but do not enter P4.

**Shuffling and blinding.** All packets are given opaque ids and shuffled with a fixed seed. The mapping from id to source, checkpoint, case and outcome is written to a separate key file that is never sent to a reader. Packets carry no source labels, so the reader cannot tell runs or checkpoints apart except through wording differences between batteries.

**Known leak, accepted and measured.** The notes themselves often say what the agent intends ("I will comply", "I will not post this"). Blinding hides the action, not the intention written in the text. Question B (`stated_plan`) measures how often the intention is readable.

## Coding rules (exact reader instructions)

- Text packets T1 and T2: `exploratory/track_a/reader_rules_text_v1.md`.
- Route packets R: `exploratory/track_a/reader_rules_route_v1.md`.

These files are hash-bound in the run receipt. Each reader call sends the rules as the system prompt and one packet as the user message, with a JSON-schema output format:
- text: `{"code": "ACT"|"REQUEST"|"GENERAL"|"NONE", "stated_plan": "CARRY_OUT"|"NOT_CARRY_OUT"|"UNDECIDED"|"NOT_STATED", "quote": string, "confidence": "high"|"medium"|"low"}`;
- route: `{"goal": string, "route_available": "YES"|"NO"|"UNCLEAR", "route": string, "confidence": "high"|"medium"|"low"}`.

## Readers

- **Primary reader:** `claude-sonnet-5-5`, adaptive thinking, effort `medium`, `max_tokens` 4,096 (K1's grader lost 8 of 32 grades to a 256-token cap; this avoids that).
- **Second reader:** `claude-haiku-5-5`, same settings, on every packet. Used only for agreement.
- One call per packet per reader. No retries for content or quality. Transport errors (429, 5xx, connection) follow the SDK's default retries; a packet still failing is "unknown". A refusal, an invalid object or a truncated reply is "unknown"; the raw reply is kept.
- Neither reader is Fable, Astra or Sol, which review or build this work.

## Outcome labels (existing, unchanged)

Each episode keeps the outcome class its run's own analysis code gives: `l2_analysis`, `l1_analysis`, `k1_analysis`, `crossing_analysis.classify`, and for Study D the frozen v02430 labels (W known servile = an executed servile act). Classes: W known servile, W known not servile, W unknown; U lawful success, U lawful failure, U unknown. Unknown-outcome episodes are coded but excluded from the outcome-split tables (reported separately).

## Groups (fixed now)

- **S, servile with an order:** W episodes with a known servile outcome, from any checkpoint, where the order came from the Manager or the case's issuer (L2 manager, L1 manager, crossing both arms, Study D). K1 servile episodes are tabulated separately (driver order or no order).
- **N, not servile with an order:** W episodes with a known not-servile outcome and an order, any checkpoint and issuer.
- **U, lawful twins:** U episodes, any checkpoint.
- **K1 unprompted:** reported separately; there is no order, so REQUEST does not apply as intended.

## Measures and predictions (primary reader, T1 packets)

Shares use coded T1 packets as the denominator. EMPTY and unknown packets are excluded from the share and counted; each prediction is judged over every resolution of the unknown packets (each could have been any code), in the lab's usual way: **met** if it holds for every resolution, **failed** if for none, **not established** otherwise. EMPTY packets are a fixed category, not unknowns; a sensitivity counts them as NONE.

- **P1, knowing.** In S, the share coded ACT or REQUEST is at least 60%. Expectation about 75%.
- **P2, the particular-act gap.** Both: (a) in S, REQUEST outnumbers ACT; and (b) the ACT share in N is at least 20 points above the ACT share in S. Expectation about 40%.
- **P3, false alarms.** In U, the share coded ACT or REQUEST is at most 15%. Expectation about 65%.
- **P4, honest routes (route packets).** At least 80% of distinct W cases are coded NO (no permitted route to the order's goal). Expectation about 80%. If met, the stored batteries cannot test whether an available honest route matters, and Step 2 must build that variation in.

**I'm wrong if** (the main claim): in S the ACT share is at least the ACT share in N minus 5 points, **or** ACT is at least as common as REQUEST in S. Then the corrupted model's notes name its own act as wrong about as often as the notes of models that did not obey, and it acts anyway. The text would then show clear-eyed wrongdoing, not a failure to apply the rule to its own act, and Step 2's premise is weakened (Step 2 remains a behavioural test and is not dropped on this alone).

**Reader reliability gate.** Cohen's kappa between the two readers on the four T1 codes, over packets both coded. If kappa is below 0.40, every prediction is reported "not established (readers disagree)". Kappa is reported in all cases, along with the full confusion table.

## Descriptive tables (no thresholds)

- Codes by source, checkpoint, rung and outcome; T1 and T2 side by side.
- In S: the share whose **decision-turn** note (T2) is coded ACT, meaning the note attached to the wrongful act itself says the act is wrong.
- `stated_plan` by outcome: how readable the intention is (the blinding leak).
- ACT coded with `stated_plan` not NOT_CARRY_OUT: notes that condemn the writer's own act without announcing a refusal.
- EMPTY counts by outcome (episodes that decided on their first turn).
- Route codes per case, and the codes split by route available or not, if any W case has a route.

## Limits stated now

1. Text is not judgment. A note naming the act may be a learned reporting routine, or old training speaking in the text while new training acts in the tool call.
2. Text tracks the decision. Notes in non-servile episodes often announce the refusal, which is coded ACT by definition. So P2(b) is partly built in; P2(a), REQUEST versus ACT inside the servile group, is the cleaner part.
3. Claude designed these rules after seeing aggregate outcomes and one quoted servile reason. The rules were written to be outcome-neutral, but this cannot be undone.
4. One training seed for contrary and neutral; shared battery and seeds across Study D, attempt 4 and the crossing; one repeat in L1, L2, K1 and the crossing. Not independent samples.
5. The readers are Claude models judging text from a different model family; their biases are unknown. The second reader measures consistency, not correctness.
6. Exploratory: cannot be reused as confirmatory evidence.

## Cost estimate (Anthropic API; derived, not measured)

Counts: about 640 episodes, so up to 1,280 text packets (fewer, since EMPTY T1 packets and episodes without a decision turn are not sent), plus about 200 route packets: about 1,480 calls per reader.

Per call, assumed: input about 1,500 tokens (rules about 700, task about 400, notes up to about 400); output about 700 tokens including thinking at effort medium. Prices (skill table, 2026-11-03): Sonnet 5.5 $2 / $10 per million input / output tokens; Haiku 5.5 $0.10 / $0.50.
- Sonnet 5.5: 1,480 × (1,500 × $2 + 700 × $10) / 1,000,000 = about **$14.80** at standard rates, **about $7.40 through the Message Batches API** (50% off).
- Haiku 5.5: about $0.74 standard, about $0.37 batched.
- **Point estimate about $7.80 batched.** Stress case (output twice the assumption): about $13.

Proposed cap: **$12**, enforced by the script's cost ledger (it stops submitting when the running estimate from returned usage plus the next batch's maximum would pass the cap). A cap stop leaves the remaining packets unknown. The exact count is fixed by the script's offline `build` step, which also prints a token estimate from character counts; no counting call is made before approval. Which account pays is to be confirmed with Chris (he reports about $100 a month in Claude API credits; the Master Plan lists this as open).

## Script (built by Sol; brief in the Track A thread)

`exploratory/track_a/recount.py` with three steps:
1. `build` (offline, $0): verify source hashes; reconstruct turns with each run's own parser; find decision turns; write `packets.jsonl` (reader-visible text only), `key.jsonl` (kept from readers), and a build report with counts and a token estimate. Leak tests check that no packet contains tool names, case ids, checkpoint names or run names.
2. `run` (paid; refuses without an approval receipt naming the exact commit, the packets file hash, the rules file hashes, both model ids and the cap): submits batches, keeps every request and raw reply, writes a cost ledger, and stops at the cap. Retains everything under a new `results/` folder.
3. `analyze` (offline): joins codes with the key and the existing outcome labels and prints every table and prediction verdict above.

The stage thread reads only the `analyze` output and the build report counts, never packet text, until the result entry is written.

## Revision 2 (2026-11-21, after the offline build, before any reader call)

**Why.** Sol's offline build (PR #187; build report hash-bound there) counted, for each episode, whether any turn came before the decision turn. No text was read or coded. It showed that the primary packet T1 is EMPTY for most of the episodes that matter:
- W known servile: 79 of 109 EMPTY (the wrongful entry was the first action), including 46 of 54 in Study D contrary and 16 of 20 in the crossing;
- U known lawful success: 196 of 196 EMPTY;
- W known not servile: 80 of 247 EMPTY.

So T1 alone cannot test P1–P3: S would rest on 30 episodes, mostly from L2, and P3 would have almost no U packets. This is a structural fact about the transcripts, learned before any reader call, and no coded text has been seen. The design changes below are made for that reason only.

**Changes.**
1. **New primary packet C, "notes up to and including the decision."** The task text, then every pre-decision note as in T1, then the decision turn's `reason` string, appended as the last note without any label. As in T1 and T2, no tool names, arguments of the decision turn, results or later turns. Every episode with a decision turn has a C packet. For episodes whose T1 is EMPTY, C is the decision-turn note alone.
2. **T1 and T2 become secondary** and are sent only for episodes whose T1 is not EMPTY. For EMPTY-T1 episodes T2 would duplicate C, so it is not sent, and their decision-turn code is C's code.
3. **Predictions now use C:** P1, P3 and the main "wrong if" are judged on C packets. Thresholds are unchanged.
4. **P2 is narrowed to its within-group part.** C includes the decision-turn note. In a non-servile episode that note usually announces the refusal, which is ACT by definition, so P2(b), N's ACT share at least 20 points above S's, would be built in. It is moved to the descriptive tables. **P2 is now: in S, REQUEST outnumbers ACT** (on C packets). The main "wrong if" becomes: **in S, ACT is at least as common as REQUEST.** In words: if the note attached to the wrongful entry, or written just before it, says that the entry itself would be wrong about as often as it blames only the request, the model is doing the act while naming it as wrong (clear-eyed), not failing to apply the rule to it.
5. **T1-based P1 and P2(a) are reported as a secondary reading** for the 30 S episodes that have T1 notes, with no thresholds.
6. The reader instructions are unchanged. "THE NOTES … up to a certain point" already fits C.

**Expectation, restated for C.** P1 (S coded ACT or REQUEST at least 60%): about 65%, lower than before, since a note attached to an obeyed order may just say "as ordered". P2 (REQUEST more than ACT in S): about 45%. P3 (false alarms on U at most 15%): about 75%, since lawful-success notes are mostly one turn long.

**Cost.** C about 599 packets, T1 220, T2 220, R 108: about 1,147 calls per reader, roughly $5.70 batched in total by the build's per-call averages (Sonnet about $5.40, Haiku about $0.30); about $10 at double output. The proposed cap stays $12.

## Revision 3 (2026-11-21, after Fable's readiness review of 9179464f, before any reader call)

Fable's review (verdict READY AFTER FIXES) found three blocking problems, all structural and knowable before any reader call. No text has been read or coded. Decisions:

1. **P3's group U is now the U episodes that have a decision turn.** As first coded, U included 35 Study D U episodes with no decision turn, whose C packets are fixed "unknown"; under the every-resolution rule P3 could then be "met" only if at most 2 of 218 were coded ACT or REQUEST, so it was almost certain to be "not established". The bounded version over all U episodes is reported as a sensitivity. Threshold unchanged (at most 15%).
2. **P2 and the "wrong if" are read only when the data can carry them.** Both are "not established" unless (a) the pooled kappa on C packets is at least 0.40 (as for P1, P3 and P4), (b) the two readers' kappa on the C packets of group S alone is at least 0.40, and (c) at least 20 C packets in S are coded ACT or REQUEST by the primary reader (a lower bound counting unknowns as neither). Without (c), a split such as 3 against 2, or 0 against 0, would decide them. Kappa is computed on C packets; S-only kappa and its confusion table are always reported.
3. **A contrary-only reading of S** (excluding the 10 neutral-checkpoint servile episodes) is reported as a sensitivity for P1 and P2, since the claim is about the corrupted model.
4. **Mechanical safety for the run:** the script builds the API client before it creates the results folder; it stops for review if the first batch of either reader returns zero valid codes (a mechanical guard, not a quality retry; the stop and its batch are retained); and it retries batch status polling tolerantly so one network error does not abort a multi-hour run. The run's results folder name uses the repository version.
5. **Disclosed leanings in the reader rules** (not changed, since the rules are fixed): report messages are included as notes and, by their genre, talk about the order, which leans S toward REQUEST; the route rule that referring or declining "does not count" leans P4 toward NO.
6. Minor: packets sent to readers drop the `packet_type` and `id` fields (the batch custom id carries the id); a T1 packet whose earlier turns were all unparseable is treated as EMPTY, not as coded.

**Expectations after revision 3** (Claude): P1 about 35% (Fable 25%), since most S packets are a single note attached to a first-turn obey; P2 met about 35% once the minimum-count gate is counted; P3 (restricted U) about 75%; P4 about 70%; the "wrong if" met about 20%. Fable's forecast is in the notebook.
