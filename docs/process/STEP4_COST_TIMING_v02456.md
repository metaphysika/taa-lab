# Step 4 cost and timing v0.24.56

EXPLORATORY, $0 offline analysis. This is a planning sensitivity, not execution approval or a billing ceiling. No Modal, model, GPU, tokenizer or workflow calls are needed.

Reproduce from the repository root with `python scripts/step4_cost_timing_v02456.py`. Standard output is this document. Sources: retained attempt-4 `container.log`, `receipt.json`, `billing-today.txt`, `native.jsonl`, all individual episode files, and `exploratory/step4_cases/cases.json`. No source file is modified.

## Attempt-4 baseline

Measured: 726 native replies, 132 episode files; episode reply totals match native records. Turns per episode: mean 5.500, range 1–12. All failures and long replies are included.

Measured log durations: weights 37.01 s; model loading 42.687168 s; engine initialization 160.01 s. These overlap and must not be added. Derived receipt-to-first-template readiness proxy: 361.140 s; receipt-to-shutdown window: 4351.140 s. The receipt precedes container logging and is not a GPU-allocation timestamp.

Derived readiness-to-shutdown window: 3990 s. Dividing it by replies gives 5.496 s/turn and by episodes gives 30.227 s/episode. These are amortized wall-time proxies including tool handling, request overhead, idle and shutdown tail, not measured generation latency. Individual generation times and idle seconds are unavailable: native records have no timestamps/durations. Idle within the serving window is bounded only by 0–3990 s (derived trivial bound).

Measured reply characters/turn: mean 244.83, range 49–14942, total 177749. Measured message-content characters/turn: mean 12378.04, range 3974–33976. Characters mean Unicode code points, not UTF-8 bytes. Native records contain no token counts or usage fields; no empirical characters-per-token ratio can be derived. Token estimates are therefore unavailable, including for fresh prefixes. No tokenizer was downloaded.

Measured retained billing-table sum for the receipt app's truncated ID: $3.75532210 (includes GPU, CPU, memory and egress; approximately the reported $3.76). Derived blended effective cost: $3.107 per receipt-window hour. This is an all-resource cost per elapsed GPU-session-hour proxy, not a measured GPU tariff: exact allocation/billing duration is absent. Do not add CPU/memory a second time or treat this as current pricing.

## Fresh prefix character lengths

Measured canonical JSON characters use ensure_ascii=False, sorted keys, compact separators. Prefix-only counts serialize `visible.prefix`; full-input counts serialize `visible` (system, task, tools and prefix). These are reproducible payload measures, not final chat-template lengths. Probe wording and future tool observations add unmeasured input. No cache savings are assumed.

| Group | Cases (measured) | Prefix min / mean / max (measured chars) | Full input min / mean / max (measured chars) |
| --- | ---: | ---: | ---: |
| fact | 32 | 766 / 778.62 / 788 | 1691 / 1714.88 / 1746 |
| development | 8 | 806 / 821.75 / 841 | 1726 / 1744.38 / 1755 |
| held-out | 8 | 814 / 826.62 / 854 | 1722 / 1750.50 / 1766 |

## Two-repeat block estimates

Derived roster counts from the plan: development 8 cases × base/neutral × 2 repeats = 32 action episodes; main 32 conditions × 4 checkpoints × 2 repeats = 256 action continuations plus 512 single-answer probes; held-out 8 cases × 4 checkpoints × 2 repeats = 64 action episodes. Repeats are already included. Each probe is one generation after the common scripted prefix; scripted reads do not generate replies.

Assumed point model: action episodes use the historical amortized seconds/episode, probes use one amortized seconds/turn. This conservatively retains historical full-episode work despite scripted reads, but shorter probes are not demonstrated to be faster. Assumed range scales all branch work by 0.5–2 times the point proxy to expose shorter answers versus longer prefixes, truncations, cache misses and checkpoint differences; it is not a confidence interval or worst-case ceiling. No empirical prefill slope is available.

Assumed independent sessions per block: development has 2 full startup allowances and 1 switch at 60 s; each held-out block has 4 full startup allowances and 3 switches at 60 s. Each startup uses the receipt-to-readiness proxy. This deliberately budgets a full engine reload per checkpoint even if future adapters can switch cheaply. There is no measured adapter switch time. Low/high cases scale startup and switch allowances by 0.5–2 too. No cross-block load reuse is credited. Optional slope tests, training, failed launches, new image builds and storage outside the retained session are excluded and need separate allowances.

All table numbers below are derived conditional estimates. Buffered point and buffered high multiply by the assumed 1.25 buffer; the buffer is not a cap.

| Block | Point hours | Range hours | Point $ | Range $ | Buffered point hours / $ | Buffered high hours / $ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| development | 0.486 | 0.243–0.972 | 1.51 | 0.75–3.02 | 0.607 / 1.89 | 1.215 / 3.77 |
| main fact | 3.382 | 1.691–6.765 | 10.51 | 5.25–21.02 | 4.228 / 13.14 | 8.456 / 26.27 |
| held-out borderline | 0.989 | 0.494–1.977 | 3.07 | 1.54–6.14 | 1.236 / 3.84 | 2.472 / 7.68 |
| total | 4.857 | 2.429–9.714 | 15.09 | 7.55–30.18 | 6.071 / 18.86 | 12.143 / 37.73 |

## Six-hour sessions and stop points

Assumed session limit: 6 hours. Development and held-out borderline fit within one session even at buffered high. Main facts fit at the point estimate but exceed the limit at high and buffered high. This is conditional, not evidence of actual completion within the timeout. Use separate sessions for development and held-out borderline. Split main facts into two stages of two checkpoints each: 128 action continuations plus 256 probes per stage. Half the main allowance gives 1.691 hours point and 4.228 hours buffered high per stage (derived); retain half of the original switch allowance in each stage as conservative overhead. Both stages include their own two startup allowances. Persist and stop for review between stages. Do not combine the total into one six-hour session. Approve development first and compare actual usage, prefix throughput and generation times before authorizing held-out work.

Proposed stop points: persist every reply and completed episode, and stop/report after each checkpoint and each repeat. In the main block, keep each action and its two wording probes together in the persisted cell record; never replace a missing branch silently. Stop starting new cells at 5 hours (assumed operational margin), or earlier if remaining time/budget cannot cover the next cell and shutdown. At timeout or a guard failure retain partial output and unknowns, stop for review, and require a separately approved continuation of untouched cells. No automatic resume, quality retry or timeout extension. If development invalidates the buffered high estimate, split later work into one-checkpoint stages, budgeting a fresh startup per stage; re-estimate before approval.

## Budget gate

Owner cap: $50/month (supplied planning constraint). The month's spend so far must come from Chris's live balance check. $4.33 was one day's reported spend, not the month's total. Do not subtract it from $50 as if it established remaining monthly funds. This offline report does not query billing or establish current prices. Chris must approve an exact commit, roster, settings, staged cap and sufficient monthly headroom before any paid execution. The estimates do not authorize calls or guarantee completion. See NEXT_STEP_PLAN_v02456.md, “Cost and execution gate.”
