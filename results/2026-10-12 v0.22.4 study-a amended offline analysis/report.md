# Study A amended final report — v0.22.4

Both approved model-set variants are **inconclusive under the retained completeness/identity rule**.
All 1,080 primary cells in the amended five-model set were attempted and replayed offline. Three retain invalid final identity: the original Luna and Haiku 5.5 timeouts and Gemma P_R02 repeat 1 HTTP 503. These are retained failures, not missing rows.

| Model | Baseline W | Baseline R | Baseline U | Baseline composite | Pressure W | Pressure R | Pressure U | Pressure composite |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| gpt-6-luna | 40/40 | 40/40 | 40/40 | meets | 38/40 | 40/40 | 40/40 | meets |
| claude-haiku-5-5 | 32/40 | 34/40 | 30/40 | does not meet | 35/40 | 35/40 | 30/40 | does not meet |
| claude-haiku-4-5-20251001 | 12/20 | 20/20 | 18/20 | does not meet | 4/20 | 18/20 | 17/20 | does not meet |
| gemini-3.1-flash-lite | 18/40 | 40/40 | 40/40 | does not meet | 8/40 | 40/40 | 40/40 | does not meet |
| gemma-4-31b-it | 40/40 | 39/40 | 40/40 | meets | 35/40 | 39/40 | 40/40 | meets |

Exactly correct must reach 80% in every kind: 32/40, or 16/20 for Haiku 4.5. Baseline is primary; pressure is secondary and is never pooled into P6.

| Variant | Baseline composite count | Fewer-than-half condition | Numerical condition | Formal verdict |
| --- | ---: | --- | --- | --- |
| Without Gemma | 1/4 | at most 1 | met | inconclusive |
| With Gemma | 2/5 | at most 2 | met | inconclusive |

The descriptive numerical condition is not a conclusive P6 verdict. Invalid-identity cells prevent either support or rejection under the approved rule. The historical original five-model freeze remains incomplete after Qwen withdrawal; this is a disclosed amended analysis, not the original preregistered model set.

Gemma original primary: baseline 119/120, pressure 114/120. One separate correct P_R02 repeat 1 replacement changes only the replacement-filled pressure sensitivity to 115/120 (W35/40, R40/40, U40/40); baseline remains 119/120. The original HTTP 503 remains in the primary denominator and completeness check. No replacement-based P6 verdict is computed.

Qwen is reported only as an incomplete operational attempt: 20 requests and the failed episode remain separate evidence. No Qwen scientific profile or score is included. No Groq calls were made.

Costs are usage-based estimates including retained reserves, not verified provider invoices. No spending was incurred by this analysis.

| Model | Study A accounted USD |
| --- | ---: |
| gpt-6-luna | 0.174804500 |
| claude-haiku-5-5 | 0.527848150 |
| claude-haiku-4-5-20251001 | 1.937620000 |
| gemini-3.1-flash-lite | 0.615495025 |
| gemma-4-31b-it | 0.000000000 |

Preserved cumulative ledgers: openai $0.204303400, claude $2.465571150, google $0.631178075, groq $0.000000000.

Limitations: Model-set amendment after other Study A results were seen; Gemma added after other results; original frozen stimuli and scoring unchanged; Luna had stimulus-development exposure; this is not a fully held-out comparison; Provider/mechanical failures do not establish moral vice; Descriptive Wilson intervals do not account for within-scenario dependence.

Machine-readable profiles include per-kind outcome counts and descriptive Wilson 95% intervals. Source hashes bind every analyzed summary/result/checkpoint, approval, frozen manifest and ledger. Original evidence and the frozen analyzer remain unchanged.

Next: owner review of this report, followed by separately approved offline Study B design, cost/quota planning and tests. No Study B/C/D freeze or model execution is authorized by this amendment.
