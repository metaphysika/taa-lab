# [Descriptive] Experiment A neutral attempts 1 — approved 7ec90c71

[Descriptive] Chris approved one two-request neutral check per provider on 2026-10-26 at exact commit 7ec90c71811acc54f92508e3995fc2c67bac6639. Both ran once from a clean detached checkout, using only configured key variables and canonical shared accounting. The durable directory previously contained only sealed H; its operational manifest and zero Experiment A step ledger were initialized without resetting provider ledgers. This is not pilot approval. No retry or further provider request followed either result.

| Provider | Before cumulative | Stop | Requests/replies | Returned model | After cumulative |
|---|---:|---|---:|---|---:|
| Anthropic | $5.805643249999988 | transport_not_retryable; HTTP401 authentication_error | 1 / 0 | none | $6.201251249999988 |
| Google | $3.6684473500000045 | complete | 2 / 2 | gemini-3.8-flash | $3.6689896000000046 |

[Descriptive] Step total: $0 before, $0.395608 after Anthropic, $0.39615025 after Google. Anthropic's $0.395608 is a retained conservative reservation, not a usage-backed charge. There was no model reply, usage, finish reason or second request. Error code=null, param=withheld; no message text retained. Google usage-backed charge is $0.00054225, no retained reserve. Existing float representations of provider totals are reported as persisted, rather than silently rounded or rewritten.

| Google request | Finish | promptTokenCount | candidatesTokenCount | thoughtsTokenCount | totalTokenCount |
|---|---|---:|---:|---:|---:|
| 1 | STOP | 70 | 16 | 58 | 144 |
| 2 | STOP | 158 | 8 | 17 | 183 |

[Descriptive] Both Google replies report serviceTier=standard and promptTokensDetails TEXT matching promptTokenCount. No native cache count fields were returned; mapped cache/write buckets are zero. No thought text blocks were returned, but thoughtSignature appeared on the first functionCall and final text. The full first model content was carried byte-identically into request2; that request accepted the echo tool result and returned a final reply with no tool call. Anthropic continuity and model identity remain unobserved because authentication stopped the first request.

[Descriptive] Evidence root: /workspace/taa-experiment-a-evidence/neutral-7ec90c71-20261026. Neither once marker was moved, archived or reset; no run.once exists. Canonical markers remain check-anthropic-000001.once and check-google-000001.once in /workspace/taa-experiment-a-evidence/state/.

| Directory under evidence root | Frames | Checkpoint head |
|---|---:|---|
| anthropic-attempt-1 | 6 | 097421a2c8f730ae1c6b054636cbf0ecc3abc262115d1e7d4ef568b870b7c30d |
| google-attempt-1 | 17 | 401724451795fe0738ed7adb403288622943f008a50ae893ac71ef1489db576b |

## [Interpretive] Rebuilt pilot cost projection

[Descriptive] The old 20-token stand-in projection is superseded for planning; its original artifact is retained unchanged. The replacement reconstructs all 275 requests from the 30 retained live-demo episodes, checks each per-episode input/output/turn total against per-episode.csv, and uses actual totals of 540,546 input and 9,336 visible-output tokens. Projected D+P scope is 198 episodes per provider, a scale factor of 6.6. No case, score or model episode is rerun.

[Descriptive] The approved guide has 2,536 UTF8 bytes. Offline gpt-tokenizer4.1.0 counts 533 tokens with o200k_base and 536 with cl100k_base. These are explicit local proxies, not provider-exact Sonnet/Gemini token counts; no extra provider countTokens request was made. The projection adds 533–536 guide tokens to EVERY historical turn. Google observed thinking/visible ratios are 58/16=3.625 and 17/8=2.125, pooled75/24=3.125. No Sonnet ratio is observed.

[Interpretive] For each source episode with input I, visible output O and turns T, use I'=I+G*T and O'=O*(1+R). Without hits, Google input costs normal input rates; Sonnet's marked initial stable prefix costs a 5m write on each miss and the remaining growing history costs normal input. With hits, the first turn is cold, later same-episode requests read the initial prefix (including guide) at the read rate; growing history stays normal input. The initial-prefix proxy comes from each episode's actual first-request prompt usage. No cross-episode cache savings are assumed. Native format/tokenization and new-program/model behavior can differ from this pooled Luna/floor/static/TAA anchor; the conventional arm is not equated with the old static arm.

| Provider/scenario,198 episodes | Cache disabled | Cache enabled,no hits | First cold,then stable-prefix hits |
|---|---:|---:|---:|
| Google,observed ratio/proxy range | $4.123330–$4.474013 | $4.123330–$4.474013 | $1.841894–$2.189302 |
| Google,pooled ratio3.125/G533 | $4.354396 | $4.354396 | $2.072960 |
| Sonnet,visible-only floor/R0/G533 | $9.686173 | $11.583106 | $3.471331 |
| Sonnet,borrowed Google ratio3.125/G536 sensitivity | $11.622613 | $13.522268 | $5.398851 |

[Interpretive] There is no empirically calibrated Sonnet range: its approved check returned401. The borrowed Google ratio is a labeled sensitivity, not a Sonnet observation. Holding historical turns/input fixed but filling every Sonnet response to its32768 ceiling gives gross output-ceiling scenarios of $603.820087 uncached/$605.719742 no hits/$597.596325 prefix hits; these would hit caps and stop well before completion, and are not budget authorizations or complete worst-case input bounds. Google ranges reflect only two neutral response ratios and two tokenizer proxies, not statistical confidence limits. New histories/signature tokenization, longer turns, retries and existing/check spend can change costs. The $25 shared/$25 Anthropic/$15 Google guards remain controlling. Pilot is not approved.

## [Descriptive] Review metadata and expected-key storage

[Descriptive] On the PR40 branch, build_claude_review=accepted (Claude,7ec90c71,2026-10-26), conventional_astra_review=accepted (Astra,2026-10-25,reviewed a21639f6), policy_guide_astra_hint_review=accepted (fixes in guidev0.2). Same-builder/shared-history caveats remain; the earlier review is not relabeled as review of later source bytes. blind_expected_key and measures_astra_review remain pending. Provenance is in inputs/review-records.json.

[Descriptive] Chris confirmed the supplied Astra P/H tables on2026-10-26. P01–P12 plus the unchanged common variants and conventions are committed as inputs/expected-key-P-astra-v01.md. Original conditions/qualifiers are preserved; no outcome is generated, resolved from an implementation, or adjusted after execution. H outcomes are stored only at /workspace/taa-experiment-a-evidence/state/sealed/expected-key-H-astra-v01.md, beside sealed set H; the public file contains only SHA256 af077729ce3d24f14efb1256b512c90f3a23da0e3e7b8ca33c4013449b2c2bac. The dataset's separate H seal remains unchanged. Neither key is placed in the model prompt/tools/brief, and H remains unavailable to the run loader. No pilot or additional check is started.
