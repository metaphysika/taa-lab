# Study D v02427 virtue revision — FOR REVIEW, NOT APPROVED

Only virtue is exposed by this revision. No launch, GPU use, model downloads or scientific execution is authorized by preparation or CI. Claude review and new owner approval of the exact published commit are required. Previous stage approvals do not transfer.

## Closed pair evidence and additive provenance repair

Original v02426 ZIP: 54de1f5ab5cecc422b314cf180f1b0683987636fd58141e32d8f35d18c4f59b5, 396 files; preserved unmodified at results/gemma-v02426-neutral-return-001.zip. Source commit 0afb757c3ae317b087f5f40086665270c36f85d3. Neutral is COMPLETE: 130 completed / 132 planned, two missing under no-resend. The 34 completion episodes produced 229 starts and 229 first native returns, no resend. Neither old evidence nor old ledgers is changed.

v02426's union mistakenly left the 34 newly completed units with inherited status `untouched`, path null and empty issued IDs. v02427's CPU-only controller rebuilds provenance from transfer files and events.jsonl, validates each first native text against its saved packet, and writes a NEW composite record. All 130 non-missing units have status completed, a resolvable path, output_sha256 and nonempty issued_request_ids. The 34 retain producer v02426; the two interrupted v02425 units retain missing/no_resend. No score, label, bound, outcome, seed or episode changes.

All 396 returned source hashes are pinned. Before any GPU reservation, mount taa-study-d-gemma-v02426-evidence read-only, check its original durable pair/closed hash, copy pinned evidence into the new Volume, rebuild the composite deterministically, and require exact equality to the reviewed staged composite. The original record is copied to source-composite-v02426.json. The revised record is pair/report.json in the NEW v02427 evidence Volume. CPU copying/verification is included in the stage overhead allowance, with no new model calls.

`--previous-report-sha256` binds the **repaired composite pair record**, contrary v02425 plus the neutral v02425/v02426 union, not neutral's worker/controller report and not the old v02425 STOP record:

`d7837f291e21c04f5b700d1b6fb2adb684b871f28330cfc55d84da5ab0b018a7`

The exact bytes are staged in composite-pair-v02427.json. require_previous accepts the original pair's source commit rather than incorrectly requiring the new virtue commit. It checks the payload hash, reviewed composite hash, new durable closure, all source bytes and reconstructed provenance. The CPU regression exercises the actual require_previous success path and rejects old/incomplete provenance, a wrong hash, missing closure and the original unrepaired record. No final arm contrasts are computed until virtue completes and is audited.

## Unchanged science and serving

All 18 inherited v02420 assets are byte-identical. Runtime.py is byte-identical to v02426: A100 80GB, bf16 pinned Gemma weights/tokenizer, vLLM 0.31.0 live LoRA, CUDA graphs [1,2], LoRA specialization, retained prefixes, FlashInfer sampler disabled with native log guard, utilization 0.95, context 16384, existing post-capture KV check. Seeds, histories, parser/scorer, 2,000 examples/one epoch, seven architecture-conditioned target names, acquisition gates, repeats and full transfer schedule are frozen. Virtue trains its own adapter and transfers only after acquisition PASS. Event append/flush/fsync and timer 30 s plus episode commits outside the lock are unchanged. Private adapters retained on review stop; clean study end deletion with receipts remains required; old read-only v02424 adapters require separate reviewed cleanup. No merged weights.

## Measured timing and guard

v02426 serving load 684.2786 s; 229 requests, mean 2.8779 s, p95(nearest rank) 4.2478 s, max 15.3275 s. Summed request wall 659.0388 s / transfer span 374.5380 s = effective concurrency 1.7596. Per-episode request counts are recorded individually in projections-v02427.json (34 episodes; 1–12 requests). Worker wall 1237.8690 s. These are request-wall measurements, not decode throughput.

Virtue has 363,524 training tokens. Use measured full v02424 rates 159.4611 and262.6449 tok/s, maximum full training-load 793.1455 s, measured serving-load 684.2786 s and extra 300 s allowance. Request-count profiles: contrary 523 transfers; neutral 623/96×132=856.625 transfers; add 100 ordered acquisition +20 descriptive spontaneous requests. Apply the batched mean to all requests. Show both measured concurrency and no concurrency; multiply the entire nominal wall by 1.25 for stress. These planning assumptions are not a completion guarantee or a tail bound; p95 is descriptive and not a per-request maximum.

| Training source | Request profile | Concurrency | Nominal s | Stress s | Spare vs9600 s |
| --- | --- | --- | ---: | ---: | ---: |
| contrary | contrary | measured | 5108.8 | 6386.0 | 3214.0 |
| contrary | contrary | none | 5907.6 | 7384.5 | 2215.5 |
| contrary | neutral | measured | 5654.4 | 7068.0 | 2532.0 |
| contrary | neutral | none | 6867.8 | 8584.7 | 1015.3 |
| neutral | contrary | measured | 4213.2 | 5266.5 | 4333.5 |
| neutral | contrary | none | 5012.0 | 6265.0 | 3335.0 |
| neutral | neutral | measured | 4758.8 | 5948.5 | 3651.5 |
| neutral | neutral | none | 5972.1 | 7465.2 | 2134.8 |

Worst no-concurrency stress is8584.7 s (see full precision JSON), leaving about 1015 s spare under the requested 9600 s guard. Provider timeout 9800 s (+200). No shortening of cases/repeats or result-based model choice.

## Billing, finite window and once-only controls

Owner Usage-tab total PRIOR $19.67 (higher figure); credit $10.39; cumulative cap $36. Increase from 18.52 is $1.15 interval accounting, not an itemized app invoice. The differing displayed credit/usage totals do not imply a cumulative reset. Reservation = (9800+120startup+2idle)×$3.20/hour/3600+$0.375 = **$9.194555556**. Cumulative actual+reservation$28.864555556, cap headroom$7.135444444; current credit after reservation$1.195444444. Rounded stage target$9.20. Admission rechecks current billing/credit; software and provider timeouts bound reserved compute, not a live invoice meter. No card remains the owner-attested billing control.

Fresh ledger taa-study-d-gemma-v02427-budget-once, evidence taa-study-d-gemma-v02427-evidence, private adapters taa-study-d-gemma-v02427-private-adapters. No reset/deletion of any older resources. Existing virtue window ends2026-11-09 01:00UTC exclusive (Nov8 7pmCST); original window start remains unchanged. Spawn acknowledgement and caffeinate required. Missing acknowledgement/error means preserve receipts and stop, no automatic retry.

## Paper3 disclosure

Neutral's frozen `unfinished_work` label occurs in W 24/63 and U 14/63 completed episodes (each planned denominator remains64, one missing each), compared with zero in contrary and zero in base Gemma's audited W/U episodes. Two further neutral unfinished_work labels occur in D. This is a descriptive post-results finding and a confound for interpreting neutral as a control: the arms may differ in work completion as well as compliance. It is not recoded as over-refusal, success or a scientific null, and it does not change pre-registered scoring or planned-denominator malformed/missing bounds. No causal explanation is established. Contrary used per-event commits; neutral completion and virtue use batched commits; settings/seeds identical but batch timing can differ. No arm contrasts are finalized before virtue is complete.

Count reconciliation: the owner/Claude supplied W 21/63; independent replay of the returned bytes finds W 24/63. U 14/63 agrees. The complete 40 unfinished_work episode IDs (W24/U14/D2) are listed in the returned-evidence audit; no labels are edited. Base Gemma reference scope is the v02416 base-format gate, with 16 W and 16 U episodes, not the identical 132-unit transfer cohort. These descriptive rates do not establish a causal training effect.
