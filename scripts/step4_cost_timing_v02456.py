"""CPU-only retained-file cost sensitivity; prints the companion Markdown report."""
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
import re
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'results/2026-11-02 v0.24.55 gemma4-31b-none r1 audit attempt-4'


def main():
    records = [json.loads(line) for line in (EVIDENCE / 'native.jsonl').read_text(encoding='utf-8').splitlines()]
    receipt = json.loads((EVIDENCE / 'receipt.json').read_text(encoding='utf-8'))
    log = (EVIDENCE / 'container.log').read_text(encoding='utf-8')
    billing = (EVIDENCE / 'billing-today.txt').read_text(encoding='utf-8')
    # Retained table truncates object IDs, so match the receipt's visible prefix.
    costs = [float(re.findall(r'\d+\.\d+', line)[-1]) for line in billing.splitlines()
             if receipt['app_id'][:9] in line and re.findall(r'\d+\.\d+', line)]
    billed = sum(costs)
    def stamp(marker):
        line = next(line for line in log.splitlines() if marker in line)
        return datetime.strptime('2026-' + re.search(r'\d\d-\d\d \d\d:\d\d:\d\d', line)[0], '%Y-%m-%d %H:%M:%S')
    start = datetime.fromisoformat(receipt['started_utc']).replace(tzinfo=None)
    ready = stamp('Detected the chat template')
    end = stamp('[shutdown] Process manager')
    startup = (ready - start).total_seconds()
    serving = (end - ready).total_seconds()
    wall = (end - start).total_seconds()
    episodes = Counter((r['comparison'], r['pass_id'], r['case_id']) for r in records)
    files = [json.loads(p.read_text(encoding='utf-8')) for p in EVIDENCE.glob('[AB]-[01]-*.json')]
    assert len(files) == len(episodes) == 132
    assert sum(f['replies'] for f in files) == len(records)
    chars = [len(r['reply']) for r in records]
    input_chars = [sum(len(m['content']) for m in r['messages']) for r in records]
    turn = serving / len(records)
    episode = serving / len(episodes)
    rate = billed / (wall / 3600)
    cases = json.loads((ROOT / 'exploratory/step4_cases/cases.json').read_text(encoding='utf-8'))
    def size(value):
        return len(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')))
    print('''# Step 4 cost and timing v0.24.56

EXPLORATORY, $0 offline analysis. This is a planning sensitivity, not execution approval or a billing ceiling. No Modal, model, GPU, tokenizer or workflow calls are needed.

Reproduce from the repository root with `python scripts/step4_cost_timing_v02456.py`. Standard output is this document. Sources: retained attempt-4 `container.log`, `receipt.json`, `billing-today.txt`, `native.jsonl`, all individual episode files, and `exploratory/step4_cases/cases.json`. No source file is modified.

## Attempt-4 baseline
''')
    print(f'''Measured: {len(records)} native replies, {len(files)} episode files; episode reply totals match native records. Turns per episode: mean {mean(episodes.values()):.3f}, range {min(episodes.values())}–{max(episodes.values())}. All failures and long replies are included.

Measured log durations: weights {re.search(r'Loading weights took ([0-9.]+)', log)[1]} s; model loading {re.search(r'Model loading took .*?memory and ([0-9.]+)', log)[1]} s; engine initialization {re.search(r'init engine .*?took ([0-9.]+)', log)[1]} s. These overlap and must not be added. Derived receipt-to-first-template readiness proxy: {startup:.3f} s; receipt-to-shutdown window: {wall:.3f} s. The receipt precedes container logging and is not a GPU-allocation timestamp.

Derived readiness-to-shutdown window: {serving:.0f} s. Dividing it by replies gives {turn:.3f} s/turn and by episodes gives {episode:.3f} s/episode. These are amortized wall-time proxies including tool handling, request overhead, idle and shutdown tail, not measured generation latency. Individual generation times and idle seconds are unavailable: native records have no timestamps/durations. Idle within the serving window is bounded only by 0–{serving:.0f} s (derived trivial bound).

Measured reply characters/turn: mean {mean(chars):.2f}, range {min(chars)}–{max(chars)}, total {sum(chars)}. Measured message-content characters/turn: mean {mean(input_chars):.2f}, range {min(input_chars)}–{max(input_chars)}. Characters mean Unicode code points, not UTF-8 bytes. Native records contain no token counts or usage fields; no empirical characters-per-token ratio can be derived. Token estimates are therefore unavailable, including for fresh prefixes. No tokenizer was downloaded.

Measured retained billing-table sum for the receipt app's truncated ID: ${billed:.8f} (includes GPU, CPU, memory and egress; approximately the reported $3.76). Derived blended effective cost: ${rate:.3f} per receipt-window hour. This is an all-resource cost per elapsed GPU-session-hour proxy, not a measured GPU tariff: exact allocation/billing duration is absent. Do not add CPU/memory a second time or treat this as current pricing.

## Fresh prefix character lengths

Measured canonical JSON characters use ensure_ascii=False, sorted keys, compact separators. Prefix-only counts serialize `visible.prefix`; full-input counts serialize `visible` (system, task, tools and prefix). These are reproducible payload measures, not final chat-template lengths. Probe wording and future tool observations add unmeasured input. No cache savings are assumed.

| Group | Cases (measured) | Prefix min / mean / max (measured chars) | Full input min / mean / max (measured chars) |
| --- | ---: | ---: | ---: |''')
    for group, subset in [('fact', [c for c in cases if 'pair' in c]),
                          ('development', [c for c in cases if c.get('split') == 'development']),
                          ('held-out', [c for c in cases if c.get('split') == 'held_out'])]:
        if not subset:
            raise ValueError(f'No cases in {group}; inspect split names')
        p = [size(c['visible']['prefix']) for c in subset]
        v = [size(c['visible']) for c in subset]
        print(f'| {group} | {len(subset)} | {min(p)} / {mean(p):.2f} / {max(p)} | {min(v)} / {mean(v):.2f} / {max(v)} |')
    print('''
## Two-repeat block estimates

Derived roster counts from the plan: development 8 cases × base/neutral × 2 repeats = 32 action episodes; main 32 conditions × 4 checkpoints × 2 repeats = 256 action continuations plus 512 single-answer probes; held-out 8 cases × 4 checkpoints × 2 repeats = 64 action episodes. Repeats are already included. Each probe is one generation after the common scripted prefix; scripted reads do not generate replies.

Assumed point model: action episodes use the historical amortized seconds/episode, probes use one amortized seconds/turn. This conservatively retains historical full-episode work despite scripted reads, but shorter probes are not demonstrated to be faster. Assumed range scales all branch work by 0.5–2 times the point proxy to expose shorter answers versus longer prefixes, truncations, cache misses and checkpoint differences; it is not a confidence interval or worst-case ceiling. No empirical prefill slope is available.

Assumed independent sessions per block: development has 2 full startup allowances and 1 switch at 60 s; each held-out block has 4 full startup allowances and 3 switches at 60 s. Each startup uses the receipt-to-readiness proxy. This deliberately budgets a full engine reload per checkpoint even if future adapters can switch cheaply. There is no measured adapter switch time. Low/high cases scale startup and switch allowances by 0.5–2 too. No cross-block load reuse is credited. Optional slope tests, training, failed launches, new image builds and storage outside the retained session are excluded and need separate allowances.

All table numbers below are derived conditional estimates. Buffered point and buffered high multiply by the assumed 1.25 buffer; the buffer is not a cap.

| Block | Point hours | Range hours | Point $ | Range $ | Buffered point hours / $ | Buffered high hours / $ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |''')
    totals = 0
    for name, actions, probes, loads in [('development', 32, 0, 2), ('main fact', 256, 512, 4), ('held-out borderline', 64, 0, 4)]:
        seconds = actions * episode + probes * turn + loads * startup + (loads - 1) * 60
        totals += seconds
        row(name, seconds / 3600, rate)
    row('total', totals / 3600, rate)
    print('''
## Six-hour sessions and stop points

Assumed session limit: 6 hours. Development and held-out borderline fit within one session even at buffered high. Main facts fit at the point estimate but exceed the limit at high and buffered high. This is conditional, not evidence of actual completion within the timeout. Use separate sessions for development and held-out borderline. Split main facts into two stages of two checkpoints each: 128 action continuations plus 256 probes per stage. Half the main allowance gives 1.691 hours point and 4.228 hours buffered high per stage (derived); retain half of the original switch allowance in each stage as conservative overhead. Both stages include their own two startup allowances. Persist and stop for review between stages. Do not combine the total into one six-hour session. Approve development first and compare actual usage, prefix throughput and generation times before authorizing held-out work.

Proposed stop points: persist every reply and completed episode, and stop/report after each checkpoint and each repeat. In the main block, keep each action and its two wording probes together in the persisted cell record; never replace a missing branch silently. Stop starting new cells at 5 hours (assumed operational margin), or earlier if remaining time/budget cannot cover the next cell and shutdown. At timeout or a guard failure retain partial output and unknowns, stop for review, and require a separately approved continuation of untouched cells. No automatic resume, quality retry or timeout extension. If development invalidates the buffered high estimate, split later work into one-checkpoint stages, budgeting a fresh startup per stage; re-estimate before approval.

## Budget gate

Owner cap: $50/month (supplied planning constraint). The month's spend so far must come from Chris's live balance check. $4.33 was one day's reported spend, not the month's total. Do not subtract it from $50 as if it established remaining monthly funds. This offline report does not query billing or establish current prices. Chris must approve an exact commit, roster, settings, staged cap and sufficient monthly headroom before any paid execution. The estimates do not authorize calls or guarantee completion. See NEXT_STEP_PLAN_v02456.md, “Cost and execution gate.”''')


def row(name, hours, rate):
    dollars = hours * rate
    print(f'| {name} | {hours:.3f} | {hours*.5:.3f}–{hours*2:.3f} | {dollars:.2f} | {dollars*.5:.2f}–{dollars*2:.2f} | {hours*1.25:.3f} / {dollars*1.25:.2f} | {hours*2.5:.3f} / {dollars*2.5:.2f} |')


if __name__ == '__main__':
    main()
