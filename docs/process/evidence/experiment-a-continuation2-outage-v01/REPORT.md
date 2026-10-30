# Experiment A continuation 2: executor outage

[Descriptive] Chris authorized a status check and append-only closure on 2026-10-27. No experiment CLI, continuation or provider request was started. Existing process is not alive. Evidence is intact as retained; the interrupted episode has no episode_end/score row. Missing scores were not reconstructed. This is a guard stop, never resumed.

[Descriptive] Last pre-closure evidence file: `pilot/episode-0090/000040.json`, written **2026-10-27T15:48:41.317104Z** (10:48:41.317104 a.m. America/Chicago). Last recorded request: **index 90, T09/taa/Anthropic, repeat 3, turn 4, attempt 1**. The child subsequently records the host step for turn 5, but no turn-5 provider request exists.

[Descriptive] Before closure: 36 completed C2 child chains verified; the interrupted child and root had valid canonical hash-linked prefixes without checkpoints. Appended an executor_outage closure to that child, an explicit recovery observation and executor_outage closure to the root. All 94 chains now verify (3 roots, 91 children). All pre-existing files, bytes and timestamps remain unchanged. No synthetic episode_end, oracle assessment, scientific score or summary was inserted.

[Descriptive] Whole pilot: **88 complete episodes**, two earlier recorded guard stops (indices 22 and 53), and interrupted index 90 now closed as executor_outage without a score row; **91 touched indices**, **305 untouched**. C2 alone: 36 complete and one interrupted. The index-90 score is unavailable in this status report; do not silently classify it as model_done or derive a point estimate from this inventory. Earlier results and stopped rows remain unchanged.

| Provider | Arm | D complete | P complete |
|---|---|---:|---:|
| anthropic | model_alone | 6 | 9 |
| anthropic | conventional | 5 | 8 |
| anthropic | taa | 8 | 8 |
| google | model_alone | 6 | 9 |
| google | conventional | 5 | 7 |
| google | taa | 8 | 9 |

[Descriptive] Every native settlement and retained reserve in all three roots was checked using the committed read-only accounting auditor. It exactly reconciles to published/local experiment-state **40f2c28cf127a8d75aaea14083d74b3ea3a9f524**, last advanced 2026-10-27T15:48:37Z. All 232 C2 reservations, requests, replies and settlements are present; no C2 reservation is open. Earlier failed neutral-check reserve remains part of the historical baseline.

| Anthropic cumulative | Google cumulative | Step cumulative |
|---:|---:|---:|
| $7.509423449999988 | $6.2007128500000046 | $4.236045700 |

[Descriptive] Whole-pilot request/reply count: 558. Native-usage-backed charges at frozen prices (not an independent provider invoice): anthropic $1.3056302, google $2.531723250. Native token totals below preserve provider field meanings: Anthropic output includes thinking; Google prompt includes cache. Do not add nested detail fields to their parent totals.

| Provider | Native usage field | Tokens |
|---|---|---:|
| anthropic | cache_creation.ephemeral_1h_input_tokens | 0 |
| anthropic | cache_creation.ephemeral_5m_input_tokens | 96167 |
| anthropic | cache_creation_input_tokens | 96167 |
| anthropic | cache_read_input_tokens | 983007 |
| anthropic | input_tokens | 207761 |
| anthropic | output_tokens | 55139 |
| anthropic | output_tokens_details.thinking_tokens | 8377 |
| google | cachedContentTokenCount | 134900 |
| google | candidatesTokenCount | 16679 |
| google | promptTokenCount | 2008096 |
| google | thoughtsTokenCount | 281110 |
| google | totalTokenCount | 2305885 |

[Descriptive] Every confirmation observation, delay and same-commit re-push from all roots is preserved in state-confirmations.json and the raw journals, including the stranded-settlement publication before C2 request 1. No confirmation or re-push occurred during this status check.

[Descriptive] **Active lease and every marker are unchanged**, including continuation-000002.once. The approved detached code checkout was not modified. H stays sealed; no H material, verdict, bootstrap, rescore, replacement or resume. The executor failure cause and exact process death time are not established by retained evidence.

| Root | Frames | Checkpoint |
|---|---:|---|
| `/workspace/taa-experiment-a-evidence/pilot-b871cee5-20261026/pilot` | 822 | `e93bf0e39fd5c00bc2ee0438e9504a5597578b0dff0de36484cf5781543bfc05` |
| `/workspace/taa-experiment-a-evidence/continuation1-480835a8-20261027/pilot` | 1518 | `e83d50ea84f019ba14438af8d870dcac29b243a21a8f89acb8643844fe786d32` |
| `/workspace/taa-experiment-a-evidence/continuation2-be2b7c8e-20261027/pilot` | 1674 | `217cca6d261213161fc49718ebe4d50989c5f62942d3e5512c5ffa776e021eac` |

[Descriptive] Reproduction: close_outage.py records the owner-authorized closure procedure (one time only, refuses an already closed root); outage-before.json pins every pre-existing evidence file and tracked state file; outage-verification.json contains all 94 ending checkpoints and the accounting result. report_outage.py reads retained records only. Older describe.py/render.py are unexecuted pre-outage helpers, not this report’s source and not a completed-pilot analysis.

[Descriptive] Publication: retained files and raw archive are scanned with the PR #38 credential patterns, exact configured-secret comparisons, archive-member and decoded-native checks. See secret-scan.json and project-publication-scan.json for actual results. Results-only PR #41 remains draft/unmerged for Claude and Astra review.
