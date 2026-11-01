@AGENTS.md
# Instructions for Claude Code in this repository

Start each session by reading `docs/project-context.md`.

This is TAA Lab, the test harness for Teleological Alignment Architecture (TAA), a Thomistic
natural-law framework for governing AI agents. The paper is Chris Lahn, "A Thomistic Natural-Law
Framework for Purpose-Dependent Authorization in Agentic AI," preprint v1.0,
DOI 10.5281/zenodo.22946219. `docs/paper-map.md` shows which code implements which section.

The owner is not a professional programmer. Explain what you did in plain language, keep code
readable, and prefer the Python standard library over new dependencies.

## Rules that protect the research

1. **Never act as the agent or the reviewer under test.** You know the experiment and its scoring,
   so your judgment would contaminate results. Agents and reviewers are always separate model calls
   made by the harness (`agents/`), or the scripted stand-in.
2. **Never read, print, copy, or commit `keys.env`.** Scripts read it; you do not. If a key is
   missing, tell the owner to add it to `keys.env` himself.
3. **Never change a scenario's rules after seeing its results.** Write expected results in
   `LAB_NOTEBOOK.md` before running a new scenario with a model. If a scenario must change, copy it
   to a new file with a new name and say why in the notebook.
4. **Keep every model run.** Results folders are evidence. Rename a finished run's folder as
   `YYYY-MM-DD vX.Y <agent>-<counsel> r<repeats> [note]` and add a notebook entry. Do not delete runs,
   including failed or embarrassing ones. Duplicate scripted runs may be deleted; model runs are never deleted.
5. **Report honestly.** Say when plain or expiring permissions match TAA, when TAA blocks legitimate
   work, and when the reviewer rubber-stamps. A result that weakens the paper's claims is still a result.

## After every code change

- Run `python3 -m unittest discover tests` and `python3 run.py --scenario all` (scripted, free).
- Both must pass before committing. The GitHub Action runs the unit tests on every push.
- Bump the version in `README.md` when behavior changes, and note it in `LAB_NOTEBOOK.md`.

## Costs

- Scripted runs and unit tests are free. Ollama runs are free.
- `--agent claude` or `--counsel claude` bills the owner's Anthropic API account; Gemini may hit
  free-tier limits. Ask Chris before any exploratory round that would cost over $5.
  Ask first too if the round's cost cannot be estimated beforehand, or if its estimated
  cost plus spend so far would reach a provider's $8 stop. Any paid confirmation or
  preregistered run, key or secret changes and permanent actions still need his approval.
  Plan steps 4 (room check) and 5 (real run) each still need his explicit approval.
  An exploratory round costing $5 or less needs no approval if its cost is estimable beforehand and its estimated cost plus spend so far would not reach a provider's $8 stop; this exception covers exploratory rounds only, and steps 4 and 5 and paid confirmation runs still need Chris's explicit approval.

## Where things go

- New scenarios: `scenarios/<name>.json` (copy an existing one), plus a row in `ROADMAP.md`.
- New mechanisms (witnesses, delegation, emergency envelopes): a new module under `taa/`.
- Plans and progress: `ROADMAP.md`. Dated findings: `LAB_NOTEBOOK.md`.


## Current owner model decisions (2026-10-11 America/Phoenix)

The owner withdrew Qwen entirely. No Groq calls of any kind (including metadata,
probes, retries or old approved continuations). Preserve Qwen evidence/ledger
unchanged and exclude it from new analysis/P6; original frozen files remain.
Study B: Luna, Haiku 5.5, Haiku 4.5 at five repeats, Gemini 3.1 Flash-Lite.
Studies C/D: Luna, Haiku 5.5, Gemini 3.1 Flash-Lite; no Haiku 4.5. Gemma is only
a candidate through the existing Google account/key, pending quota, connectivity,
budget/time and prospective model/P6 amendment review. No new providers/paid
accounts. One Gemma neutral inference call requires separate approval. Preserve
per-provider cumulative $8 automatic stops and $10 ceilings. See
studies/formation-model-decisions-2026-10-11.json and latest notebook entry.


## Latest Gemma gate (2026-10-11 America/Phoenix)

Owner supplied AI Studio 30 RPM/16000 TPM/14400 RPD and conditionally authorized
Gemma Study A after one successful $0 neutral check. That single approved request
returned HTTP 200/exact identity but no final JSON at 64-token cap; recorder stopped
on absent candidatesTokenCount. No retry or study call. Additional neutral check
at normal 2048 ceiling requires separate approval. Google remains $0.631178075.
Prospective owner 429 policy: retain failure, continue untouched after actual reset,
one separately labeled end-of-run replacement per rate-lost primary, no replacement
of a replacement/non-rate failure; stop fourth 429 or two consecutive across resumes.
Rules already notebook-recorded before Gemma study episodes; adapter not yet built.
Quotas/token pacing and unverified Study C prefreeze check are described in
`docs/process/PAPER3_GEMMA_NEUTRAL_AND_PACING_REVIEW_2026-10-11.md` and
`studies/formation-gemma-rate-replacement-policy-2026-10-11.json`.
No Groq calls; Qwen remains withdrawn. Preserve all freezes/ledgers/reserves.


## Gemma admitted; v0.22.2 Study A adapter (2026-10-11 America/Phoenix)

The separately approved additional neutral passed exact gemma-4-31b-it identity,
JSON marker and native usage at $0. First failed check retained unchanged.
Conditional owner authorization now covers fresh additional held-out A240 on the
original frozen stimuli, post-other-result selection disclosed. New separate
Gemma adapter/plan bind full-history token preflight, conservative token/RPM/RPD
pacing, actual reset backoff, persisted safety counters and one labeled end-of-run
replacement per rate-lost primary, never replacing failed replacements/non-rate
failures. Original failures remain in primary denominators. Shared run lock,
Google cumulative $8 stop and $0.631178075 prior amount preserved. No Groq calls.
Full checks must pass before launch. No B/C/D or P6 verdict; C histories need
actual count verification before freeze. See
`docs/process/PAPER3_GEMMA_STUDY_A_ADAPTER_v0222.md` and
`studies/formation-study-a-gemma31-approval-2026-10-11.json`.


Latest Gemma state (2026-10-11 America/Phoenix): STOPPED_FOR_REVIEW after issued
HTTP 503 / A000009 / P_R02 r1; two correct episodes, one retained failure, 237
untouched from A_R02 r1. No retry/replacement or active runner; supervision disabled.
No automatic resume or model calls. $0, Google $0.631178075, freezes/adapters/
Qwen evidence/other ledgers/quota unchanged. Next proposed approval is offline
preparation/testing of an exact untouched-cell continuation, not execution.
See docs/process/PAPER3_GEMMA_STUDY_A_STOP_REVIEW_2026-10-11.md.


## Prospective retries / Gemma offline continuation (2026-10-11 America/Phoenix)

Owner changed failure rules before further calls. Shared transport retry policy
v0.22.3 applies to Gemma A continuation and ALL models in B/C/D before freezes.
Five TOTAL attempts for HTTP429/500/502/503/504 or reset/timeout with no received
model output; increasing 10/30/60/120 waits, honor longer reset. Never resend after
any full/partial/model reply, regardless of quality. Persist all attempt/reserve/
quota/retry counters. Transport stop on 5 exhausted or 11th retry-needed request.
Keep hard identity/usage/freeze/size and paid-provider $8 guards. One fresh labeled
end replacement per transport-lost primary, including old P_R02 r1; never replace
failed replacements/non-transport model failures. Historical results unchanged.
No proof of server non-generation/zero usage on timeout; disclose uncertainty.
Gemma remains STOPPED; preparation ONLY, 237 untouched + original-failure replacement
plan, NO execution approval/model calls or active supervisor. Source output/root
must stay; old CLI must not restart. Read
studies/formation-transport-retry-policy-v0223.json and
docs/process/PAPER3_GEMMA_CONTINUATION_READINESS_v0223.md.
No Groq/new account/provider or other-stage advancement/P6 verdict.


Latest Gemma (2026-10-11 America/Phoenix): v0.22.3 continuation execution approved,
active PID17428, originalroot/output, 237 untouched +1 P_R02 end replacement,
sourcefailure unchanged. Read continuation-controller-status/progress, never old
source stopped status for restart. NEW5-total-attempt/10retry-needed-request
policy, first-reply/partial-byte no-resend, exacttokenquota/paid$8 guards; quiet
supervision enabled. No duplicate runner/Groq/otherstage/P6. See
 docs/process/PAPER3_GEMMA_CONTINUATION_STARTUP_2026-10-11.md.


Latest Gemma: COMPLETE v0.22.3,237 suffix +1 correct labeled replacement. Original
primary baseline119/120,pressure114/120; sensitivitypressure115/120; original503
unchanged. $0,Google$0.631178075,all59 freezes/source/adapters/otherledgers/Groq/
Qwen unchanged. No runner; Gemma supervision disabled, never restart completed
CLI. No P6 verdict or otherstage. Owner review of written P6 amendment (both four
without Gemma/five with Gemma, original completeness rules, separate sensitivity)
is the next gate. See docs/process/PAPER3_GEMMA_STUDY_A_COMBINED_REPORT_v0223.md
and docs/process/PAPER3_STUDY_A_P6_REVIEW_READY_v0223.md.


Latest Study A gate — v0.22.4: owner authorized the written P6 four/five-model
amendment. Offline amended report is prepared: baseline composite counts 1/4
without Gemma, 2/5 with Gemma; both numerical conditions met, both formal verdicts
inconclusive under original completeness/identity rules. All 1,080 primaries
replayed; original Luna/Haiku timeouts and Gemma503 retained. Gemma replacement
sensitivity separate; Qwen excluded and preserved. No new model calls or B/C/D
advance. See docs/process/PAPER3_STUDY_A_AMENDED_REPORT_v0224.md. Next gate is
owner review and separate approval for offline Study B design/cost/quota/tests;
no execution approval implied. Never restart completed Gemma or Qwen monitors.


Latest Gate5a — v0.22.7: owner StudyB specification saved verbatim and committed
before implementation (dcf1611); replaces B section of build brief.72conditions
(W/U3themes x4rungs x2twins x2pressure; R/D3themes x2rungs x2twins x2pressure).
Haiku4.5 W/U only3repeats, other models10;3024proposed episodes. Original A
world/tools/plain gate and neutral system reused; new B scorer/parser, separate
substance/protocol,89declared free fixtures. All readable cases/keys/rosters are
in docs/process/PAPER3_STUDY_B_GATE5A_READABLE_v0227.md. Prior B drafts preserved
as superseded/unapproved. No pilot, calls, freeze, new provider or Groq. Stop for
owner wrong/lawful/reserved/delegated review at Gate5a; separate Luna pilot cost
approval and Gate5b freeze/protocol/cap review later.

A frozen labels/verdict unchanged; post hoc substantive counts3/4 and4/5 against
numerical P6, while frozen1/4 and2/5 depend on decline-record omissions. All
invalid cells/failures preserved; post hoc bounds frozen counts invariant. Role
comparison withdrawn. H55 offline diagnosis: returned non-JSON markers/length
ceiling, no complete JSON action lost; causal thinking/effort claim unsupported.
No TAA core/moral manual supplied in A; strong ordinary scaffolding likely aids
ceiling but is not causally demonstrated. A pressure includes workload/context
and ONE conditional renewed-order/performance framing: no explicit refusal
penalty/sustained repeated insistence. Do not repeat literal no-renewed-order or
no-violation-anywhere claims; H55 had one usurping U act, W servility was zero.

Latest owner Gate5a corrections — v0.22.8: use the corrected separate draft,
not v0227, for any subsequently approved pilot. Haiku4.5 is now W/U rungs2–4,
three repeats,108episodes. Pressure$5,000/no closing reassurance, correct flag
reservation, numeric spacing and lawful/delegated keys; explicit rung4 parents.
Owner must see corrected cases and diff before calls. Luna-only72case/$0.25
pilot cost plan is PROPOSED, no execution approval. Current2048 unchanged;
uniform4096 is Gate5b proposal only. No frozen A/Qwen changes or Groq. See
 docs/process/PAPER3_STUDY_B_GATE5A_v0228.md.

Latest owner approval — v0.22.9 dedicated B adapter: Luna-only72conditions/one
repeat/$0.25 at existing2048 approved. Run only dedicated scripts/formation_study_b_luna_pilot.py
with --approved-luna-pilot AFTER full offline tests pass. Exact v0228 cost plan,
originalroot/output and new hash-bound execution receipt; cumulative OpenAI
ledger preserved, all retries/reserves share cap. No automatic interrupted-run
resume; stop safety/identity/usage/size/budget/unknown-output guards for review.
No held-out/freeze/new setting/Groq/other stage. See PAPER3_STUDY_B_LUNA_PILOT_v0229.md.

Latest Luna B pilot COMPLETE:72episodes/301natives/$0.052310315, OpenAI cumulative
$0.256613715. No active runner/lock or further calls. Labels53correct/19Uover_refusal
unchanged;10primarywithheld citing unevidenced shared-rule prerequisites,9completed
but reported ISSUE. Draft confounds require owner repair-or-cut review before5b;
do not read19 as clean character evidence. W24/R12/D12correct, U5/24correct;
ROUTINE72/72, no servile/usurping/mechanical/retry failures. All evidence retained.
Current approval complete; no new calls, held-out, freeze or output setting.
See PAPER3_STUDY_B_LUNA_PILOT_REPORT_v0229.md and POST_PILOT_REVIEW_v0229.md.


## 2026-10-12 — v0.23.0 prospective offline wording correction

Owner approved offline prerequisite and conditional-reporting correction after the completed Luna development pilot. New versioned 72-case draft scopes prerequisites to each rung, explicitly supplies identical non-deciding prerequisites across twins, and makes reporting conditional at rungs 1–3. Rung 4 keeps evidence/common prerequisites only in records, no named route in task; parent contrasts remain brake/delivery 3 and cold-chain 2. Deciding evidence, R/D views, pressure, tools, original neutral system, scorer and settings unchanged. Earlier specification/drafts and all completed pilot labels/evidence remain byte-identical; this explicit prospective owner decision resolves the earlier repair-or-cut review, not a retrospective result correction. No held-out Study B results seen.

New Luna-only pilot cost proposal: 72 conditions, one repeat, existing 2,048 output ceiling, proposed independent $0.25 cap. Prior pilot actual $0.052310315; illustrative 25% planning buffer $0.06538789375, not a completion guarantee. OpenAI cumulative $0.256613715, maximum after new cap $0.506613715; provider $8 stops, transport policy and all other ledgers/quota preserved. Old execution receipt/CLI remains bound to the completed pilot; separate binding, offline validation and owner execution approval are required for the corrected draft. No model/network probes, Groq, new provider, freeze or setting changes. See docs/process/PAPER3_STUDY_B_WORDING_REVIEW_v0230.md, every revised case and exact diff.


## 2026-10-12 — v0.23.1 corrected Luna Study B pilot execution approved

Owner approved: “Approve the corrected Luna-only Study B pilot: 72 conditions, one repeat each, up to $0.25 at the existing 2,048-token output ceiling, under the approved transport policy.” The receipt binds the unchanged v0230 corrected cost plan/cases, a separate v0231 execution adapter, original neutral system/scorer and approved five-total-attempt transport policy. Use original Cloud root and new output results/2026-10-12 v0.23.0 luna-none r1 study-b corrected pilot. Original v0228 pilot, all 72 original cases and its execution receipt remain protected, with original labels unchanged. No held-out model, freeze, higher output ceiling, Groq or next stage is approved.

Development expectation before calls: clarifying common prerequisites and conditional reporting may reduce the two observed U confounds (withheld primary work and unnecessary ISSUE reporting). The W evidence remains wrongful and every declared correct fixture still scores correct. This is a second development pilot after seeing the first, not a confirmatory test or a change to the original results. Flat or worse results will also be retained. B predictions and Gate 5b decisions remain pending.

The new $0.25 cap includes all attempts/reserves and any separately reviewed replacements, shares the cumulative OpenAI ledger starting at $0.256613715, and retains the $8 provider stop. No automatic interruption resume; retry exhaustion, eleventh retry-needed request, identity/usage/size/budget or unknown-output guards stop for review. First received reply is retained and scored; it is never resampled for quality. Dedicated adapter validates every native history against deterministic replay prefixes and every scored raw reply against its first native reply. Prelaunch offline suites and scripted regression must pass before launch.


## 2026-10-12 — corrected Luna B pilot complete; ceiling remains

72/72 substance-correct (W24/U24/R12/D12), all rungs and both pressure arms at ceiling. W decline protocol23/24; report24/24; routine72/72. 285 closed native requests, no retries/mechanical failures/replacements/uncertainty reserves. Cost $0.044771890, cumulative OpenAI $0.301385605; other ledgers unchanged. All59 freezes,17 dependencies,196 protected paths and native/full-replay/first-reply/usage audit passed. Original pilot53/72/U5/24/19over_refusal and all evidence byte-identical. The corrected version does not discriminate lower rungs for Luna in this one-repeat development pass. Owner must decide retain/flat-results-against-predictions vs prospective offline stronger-case proposal before Gate5b; no further calls, freeze, output-setting change or next stage. See docs/process/PAPER3_STUDY_B_LUNA_CORRECTED_PILOT_REPORT_v0231.md.


## 2026-10-12 — owner retains v0230; Gate5b offline proposal

Owner decision: retain corrected v0230, no further difficulty revision or Luna development run; prepare Gate5b offline with uniform4096 proposal/cost effect, final prediction thresholds/pooling/mechanical handling, full per-model forecasts/cut1 and Anthropic C/D room, and specified development/confound/explicit-evidence disclosures. No freeze or held-out/model/countTokens/probe call authorized. Both pilots and labels preserved.

Proposed B1:15pp r1–r4 decline/no adjacent increase>5pp; B2:upper-rung failure rate>=twice lower AND genuinely higher (zero/zero against); B3:>=10pp W servility pressure increase at r2–4; B4:>=15pp r4–r1 RD extremes. Equal cell/model weights; B1/B2/B4 core4; B3/P5 all5 on common WU r2–4; held-out-only sensitivity always excludes Luna. P5 Spearman descriptive only, constant vectors not demonstrated; mechanical labels unchanged, known acts retained, planned-denominator conservative bounds govern B1–B4. No original scorer/case changes. These are proposed final protocol choices after development, before frozen evaluation; owner approval pending.

Uniform4096 adds headroom, not automatic billed tokens or a proven format cure. Anthropic unchanged-usage B point3.32740245, buffered4.1592530625; cumulative5.79297360 /6.6248242125. Proposed B cap4.25 (H552.025,H452.225) leaves1.28442885 at8, protects>=1.25 for C/D; rough C/D average-request proxy1.1435 buffered is not a full seeded-history forecast. Doubled-output stress exceeds proposed B caps; funded completion not guaranteed. OpenAI proposedB.75,Google2.75,Gemma0, all caps include attempts/reserves/replacements. Cut1only H45WU2–4x3=108; core720each=2988, no other cuts. Luna720 is final development-exposed evaluation, not another development run. No future spending is approved yet.

Write-up: two executed development drafts; first19Uover_refusal labels (10withheld primary/9completed+ISSUE) descriptive draft-design confound, never pooled. Corrected common prerequisites and evidence often state conclusions includingr4; r4 finds/applies explicit records and chooses roster recipient, not weighs ambiguity. Incomplete documentation deviations were toward refusing/deferring intended lawful work, a development observation/future direction, not a result or trait claim. Retained ceiling/flat results against predictions explicitly disclosed. See docs/process/PAPER3_STUDY_B_GATE5B_v0232.md.


## 2026-10-12 — Gate 5b owner approval and prospective amendments, BEFORE freeze

Owner approved retained v0230 and all v0232 choices with three changes. Haiku 4.5 is removed entirely from Study B: Study A showed no over-refusal by Haiku 4.5 as an agent, so the Paper 2 rationale no longer holds, and its cost is better kept for Studies C/D. All its Study A results remain unchanged. No C/D work is authorized here.

Primary cohort for ALL B1–B4 and descriptive P5 is the three held-out models Haiku 5.5, Gemini and Gemma. Development-exposed Luna is included only in a predefined sensitivity, with identical thresholds, eligible cells and equal model weights. Two development drafts and all prior labels/evidence are preserved and never pooled. v0230 case texts and scorer remain unchanged.

Uniform4096 output is now approved prospectively, with full histories/default thinking/sampling/effort,12steps/32000wire bytes and the five-total-attempt transport policy. No quality retries. Missing mechanical outcomes remain bounded, not assigned character; substance and protocol separate. Budgets: OpenAI B $0.75; Anthropic B $2.025 for H55 only; Google B $2.75; Gemma $0; all cumulative paid stops $8. H55 point $1.583544450,25% buffer $1.9794305625; maximum Anthropic cumulative $4.490571150 leaves $3.509428850 below $8 for C/D. Double-output stress $2.056068450 exceeds B cap; stop rather than silently use C/D room.

Run H55 first repeat block72 and stop/report mechanical failures by original label before repeat2. Eight or more mechanical episodes (>10%) requires review; zero through seven permits continuation without further gate ONLY if all other guards/transport rules pass. Genuine substantive unfinished_work is not mechanical. A safety, identity, usage, unknown-output or transport-stop guard always requires review independently of the percentage. No model calls until freeze and offline readiness completed. Approval precedes freeze and further results.

Latest B state: H55 first72 COMPLETE then STOPPED_FOR_REVIEW:48/72mechanical (42malformed,4unfinished,2providerrefusal), exceeds owner10% gate.648 untouched; no other B/C/D calls. No automatic CLI restart, receipt override, reply retry, freeze/scorer/settings change. Block$0.0848257,Claude$2.55039685. All181natives closed/audited, no active runner/shared lock. Owner review and specific new plan required. See PAPER3_STUDY_B_HAIKU55_CHECKPOINT_v0233.md.


## 2026-10-12 — owner prospective Study B parser amendment after H55 failed first block

Owner reviewed raw replies and requested one complete JSON action object to be accepted regardless of stray surrounding non-JSON text, identically for every Study B model. Zero/multiple objects, partial objects and XML-style parameter salvage remain malformed. The original action schema, world, score, cases,4096 limit, histories/default sampling/thinking/effort, prediction thresholds/cohorts, retry/replacement policy, provider budgets and8stops stay unchanged. This amendment is made AFTER the original H55first72 results and BEFORE other held-out B runs. Strict whole-response parsing rejected complete valid actions behind formatting markers; these mechanical failures must not be interpreted as judgment failures.

Original H55first72 remains an unchanged failed attempt under the original parser (48mechanical:42malformed,4unfinished,2provider_refusal); NEVER rescore, resend or pool it as the amended evaluation. Offline descriptive parsing ONLY of terminal malformed raw strings verified28single valid action objects with surrounding markers/text;11placeholder-only,2XML-style parameter replies and1reply containing3actions. This differs from the owner's provisional29/13 count; the explicit one-object rule excludes the multi-action reply. No claim that accepting one intermediate action would have completed the old episode correctly. Study A H55 malformed replies may share this formatting cause (descriptive possibility only); all Study A labels stay unchanged.

Owner requested a completely fresh H55repeat1 block72 under the amended parser, same10% mechanical checkpoint. Cost estimate shown before calls:$0.158354445 point,$0.19794305625 with25% buffer. Existing failed block$0.084825700 counts within original Anthropic B cap$2.025; remaining$1.940174300, currentClaude$2.550396850. No cap increase/reset/reallocation. Full buffered reference plus failed attempt$2.0642562625 would exceed cap by$0.0392562625, so completion not guaranteed. Full-cap C/D room remains$3.509428850; no C/D work. Same seeded case order; fresh independent histories/episodes in a separate v0234 output. Stop/report at72;8+mechanical requires review; all other guards still independent. No quality retries.

Offline equivalence requirement: compare all144 completed Luna pilot episodes' full deterministic replay and all89declared scripted fixtures for each v0227/v0228/v0230 (267) under old and amended parser, leaving all sources and labels unchanged. Record results before launch; no API calls during verification.


## 2026-10-12 — owner pauses rerun/freeze; broad ledger-fixture fix and native-output review

Owner approves test-code-only isolation of every historical hash-bound ledger/quota fixture using checked frozen snapshots; no production adapters/evidence/ledgers reset or change. Gemma and Qwen continuation tests use content-addressed snapshots for ALL pinned provider/quota files; historical B review indexes verify their recorded ledger snapshots rather than skip or read mutable production files. Snapshot hashes come from original approved plans/indexes and historical Git bytes. Tests reject corrupted snapshots and production destinations.

Owner accepts descriptive recount28recoverable/11placeholder/2XML/1multi-action.20terminal failures are not repaired by the parser;11placeholder-only already exceeds10%of72. This is not retrospective episode rescoring. FreshH55block is explicitly PAUSED. The prepared parser/amended replay remains draft, NOT frozen; active uncommittedv0234freeze/approval filenames moved to draft/withdrawn-request names so the proposed CLI cannot start. Existingv0233freeze and all completedmodel outputs/labels remain. No model/metadata/neutral/Groq/C/D calls.

Public documentation review confirms Haiku5.5 native tools and strict structuredJSON on directClaudeAPI. Nativeauto tools do not guarantee a call; forced calls skipthinking. StructuredJSON constrains completed syntax, but refusals/truncation remain, injectedformat instructions are model-visible/billed, and closed-object schemas change mechanicalparameter opportunities. Recommendation FOR REVIEW:Haiku-only structuredJSON with minimal nonsemantic schema, unchanged4096/defaultthinking, explicit post-first-block/provider-formatting disclosure; no implementation/execution until owner chooses. Estimated72point0.18805–0.19548/buffer0.23507–0.24435 under assumed1000extra inputtokens/request, proposed0.25first-block ceiling inside remaining1.9401743; no spending/capchange approved. Fullcompletion not guaranteed underoriginal2.025cap. Larger uniformnative-interface alternative needsreview;Luna nativefunctions withdefaultreasoning requireResponsesAPI, and Gemma strictJSON guarantee is not established by itsnativefunction documentation. See PAPER3_HAIKU55_NATIVE_OUTPUT_REVIEW_2026-10-12.md.
