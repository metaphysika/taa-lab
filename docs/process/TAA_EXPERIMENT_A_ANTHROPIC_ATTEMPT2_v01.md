# [Descriptive] Anthropic neutral attempt 2 — approved 37cf7203

[Descriptive] Chris approved Anthropic attempt2 only at `37cf72031f3ff82fb74f004334217504de592652`, following Claude's acceptance of that source for this check and reconstructed state `2d436a82005489a144607c7abf45337bdb7681f8`. The check ran once in a clean detached linked worktree `/workspace/taa-experiment-a-neutral-37cf7203`, with the exact supplied receipt outside all checkouts. It used only the configured ANTHROPIC_API_KEY and the harness's native urllib transport. No key-value/header logging, keys.env access, extra probe, retry, Google request, pilot, H access or merge occurred.

[Descriptive] Before the call, Sol reported Anthropic cumulative `$6.201251249999988` and step `$0.39615025`. The experiment-state worktree was clean/equal to origin. Both attempt1 markers were present; attempt2, run.once and active lease were absent. Attempt1 markers remain byte-identical afterward; no marker was moved or removed. The prior401 reservation remains booked.

## [Descriptive] Result and native usage

[Descriptive] Stop **complete**, two physical requests, exact returned model **claude-sonnet-5-5** on both. Finishes **tool_use**, then **end_turn**. First response contained the requested echo call; request2 replayed its entire assistant message byte-identically, supplied the matching echo result and received a final text reply with no tool call. No thinking/redacted-thinking blocks or signatures came back. Request2 therefore accepted ordinary tool continuity; thinking/signature-block carry-over was **not exercised**.

| Request | input_tokens | output_tokens | cache_read_input_tokens | cache_creation_input_tokens | 5m / 1h creation | output_tokens_details.thinking_tokens | Usage charge |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 417 | 50 | 0 | 0 | 0 / 0 | 0 | $0.001334 |
| 2 | 484 | 24 | 0 | 0 | 0 / 0 | 0 | $0.001208 |

[Descriptive] Both usages additionally report service_tier=standard, inference_geo=global and speed=standard. The actual cache_creation object contains ephemeral_5m_input_tokens=0 and ephemeral_1h_input_tokens=0. Full native usage objects are retained in check-summary.json and the raw replies. The approved generic mapping still labels thinking_tokens_reported=null / not separately reported; the newly returned native details explicitly report zero. This report/projection uses that native zero. All output tokens are already billed once at the output rate; no mapper/runtime change is made.

[Descriptive] Total native input901/output74/thinking0; newly charged **$0.002542**, no new retained reserve. After: Anthropic **$6.203793249999988**, Google unchanged **$3.6689896000000046**, step **$0.39869225**. These cumulative booked totals include historical spend/reserves, including the original401 reserve; they are not a new invoice/repricing. Caps remain step25/Anthropic25/Google15. State is clean/equal to origin after normal lease release, no run.once, and attempt2 is permanently used.

## [Descriptive] Durable state and evidence

[Descriptive] The seven state commits were pushed in order before subsequent requests: acquire709db1e83630c2c7e9d55e59c389219f8799ccf5; claim **7e9695a0b1599f084846366dc73ea36a3693b119**; reservation4cf93f84de40a22c70513e5e629a9ae7c1382c6b; settlementbff61c3185124014441aee070aeb23e0c2bbf142; reservationb6785c2d6c9fbec591b597f075b44e046ffc0e76; settlement711ca6669d4385a31cb4d4d3f60e53df33982877; release/final state **472d761352715650f1746982843e80340b6052ee**. No failed publication or retry occurred.

[Descriptive] Evidence directory: `/workspace/taa-experiment-a-evidence/neutral-37cf7203-attempt2-20261026/anthropic-attempt-2`. Common verifier passes all17frames; checkpoint **ebe3360aa4ca908f07b0dadcdb900a63d40053da551990631c0b79b2774bd66d**. Receipt, before record, launch stdout, empty stderr, exact bodies/native replies, mapped/native usage, charges and unchanged-marker hashes are retained. Actual once markers remain solely in the state worktree/branch; the review archive contains their hashes, not copies.

## [Interpretive] Rebuilt pilot-only cost projection

[Descriptive] Offline reconstruction re-reads the retained30live-demo episodes'275native requests, reconciles each input/output/turn total to per-episode.csv, and reproduces the prior episode-count table exactly:540,546input/9,336visible-output tokens. Their native reasoning counts are zero. D+P scope is198episodes/provider, scaling by6.6. Approved guide bytes remain2,536/SHA2568e47b55a72ab329500d2ccc76939328e026a6a4440033c832c42cff5ff51afd0. Reused offline o200k/cl100k guide proxies are533–536tokens added on EVERY turn; these are not native Sonnet/Gemini counts. No provider count request or source episode/controller rerun occurred.

[Descriptive] Observed Sonnet thinking/visible ratio here is **0/74=0**, individually0/50 and0/24, from explicit native output_tokens_details.thinking_tokens. Retained Google ratios are58/16=3.625 and17/8=2.125, pooled75/24=3.125, from its earlier accepted check. No new Google call was made.

[Interpretive] For each historical episode with input I, visible output O, turns T and first-prompt prefix P: use I'=I+G*T and output O'=O*(1+R). Disabled caching charges all input normally. No-hit Sonnet caching charges P+G writes on each turn at5m rates; Google misses use normal input. With hits, first turn is cold, later SAME-EPISODE initial-prefix requests hit at the read rate; growing history remains ordinary input. No cross-episode reuse is assumed. Exact formulas/source hashes are in the retained scripts and live-count-projection.json.

| Provider / observed ratio, 198 episodes | Cache disabled | Cache enabled, no hits | First cold, then initial-prefix hits |
|---|---:|---:|---:|
| Sonnet, R0, guide533–536 | $9.686173–$9.697063 | **$11.583106–$11.596718** | **$3.471331–$3.473301** |
| Google, R2.125–3.625, guide533–536 | $4.123330–$4.474013 | **$4.123330–$4.474013** | **$1.841894–$2.189302** |
| Google pooled R3.125, guide533 | $4.354396 | $4.354396 | $2.072960 |

[Interpretive] These are conditional planning calculations, not confidence intervals, performance predictions or funded-completion guarantees. The short echo's observed zero does not establish zero thinking for refund episodes. Neither provider check observed cache hits/writes, so the hit scenario is hypothetical. Historical Luna/floor/static/TAA inputs/turns may differ from Sonnet/Gemini/newP/conventional histories and native tokenization/signatures. Future longer outputs, history and retries can raise costs. Sonnet with a clearly **borrowed**, unobserved Google ratio3.125 gives no-hit13.522268/hits5.398851 as sensitivity. Fixed-history full-output-ceiling scenarios exceed caps by large margins and would stop early; they are not full worst-case bounds. Projections exclude already-booked spend/checks. Actual caps/usage control, and the pilot remains unapproved. The older Sonnet-unavailable projection/archive remains unchanged as history.

## [Descriptive] Review records and follow-up

[Descriptive] After the check, Chris directs measures_astra_review=accepted (Astra,2026-10-26, all nine additions applied at01a1d8af53dc2491999d951c23410977a81a9583), and blind_expected_key=accepted (Astra's P key committed, original H key hash recorded; H key must be re-supplied and hash-verified outside all repositories at approved unsealing). Current provenance records that private H is unavailable; no key is generated or recovered. Only reviews.json/review-records.json and their pins change among inputs. Frozen measures/cases/guide/prices/keys/hashes stay unchanged. The frozen measures status text is an archival pre-confirmation note; current approval status is in the explicit reviews/provenance records.

[Descriptive] Two tests that assumed permanently pending production reviews now assert the owner-directed acceptance/provenance and independently inject each pending field to keep rejection coverage. No provider, policy, budget, native-history, scoring, scenario or expected-key code changes. Required focused/full/scripted/preservation checks and final archive verification are recorded in the adjacent evidence. Stop after push/report; no pilot or further model request is authorized.

[Descriptive] Final validation PASS:1,836tests/36existing optional skips;87focused checks; scripted-all; preservation140protected files/original320episodes. Runtime equals approved37cf; only review metadata/pins change among inputs. Archive CRC/memberhashes and credential scans PASS. [Retained raw evidence and verification](evidence/experiment-a-anthropic-attempt2-v01/verification.json). State/once markers remain untouched after the successful check; no further call/pilot/merge.
