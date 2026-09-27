# TAA Lab follow-up: v0.19.5 final freeze

Frozen September 27, 2026, before the final paid evaluation. The paid Luna smoke and pilot are
development evidence and are excluded from final averages. No substantive policy revision was
made after smoke. v0.19.5 repairs only the count of explicit partial plan refusals. The original
v0.19.4.1 pilot files remain unchanged.

## Matrix and predictions

The core compares repaired TAA control, TAA with reservations, and the strengthened per-act judge
on F01–F09, five repeats per arm and provider: 135 Luna and 135 Haiku episodes. The free
expiring-policy arm has one saved deterministic episode per case. The paid regressions cover
`wrongful_order`, `late_booking`, and `new_closure` in the reservation TAA and judge arms, five
repeats per provider: 60 more episodes. One six-question counsel diagnostic per provider is
separate from the outcome matrix. The notebook records all predictions and contrary results to
retain. Haiku was held out from this development round, though earlier Haiku results motivated
the design.

The freeze record with scenario, code, manifest, and price hashes is
`studies/obligations-freeze-v0195.json`. Its pinned model IDs are `gpt-6-luna` and
`claude-haiku-4-5-20251001`. OpenAI uses Chat Completions with a 4,000-token ceiling and asks
for temperature 0.2, falling back to the model default if rejected. Anthropic uses Messages
with a 2,000-token ceiling and temperature 0.2. All raw replies and provider usage are saved.

## Measured budget and stops

The Luna pilot completed 15 episodes with 47 logical reviews, 48 attempts, 116,639 input tokens,
47,842 output tokens, and $0.03784378 in estimated API charges. Smoke plus pilot used $0.05094146.
At pilot patterns, the nine-case core projects about 423 reviews per provider and about $3.75
across both providers. The 60 regression episodes project roughly $0.83, plus a small diagnostic
cost. These are planning estimates. Haiku's token lengths, caching, retries, and case mix have
not been measured in this study.

The September 27 first-party prices are saved in `studies/provider-prices-2026-09-27.json` and
were rechecked before freeze: Luna $0.10 input and $0.50 output per million tokens; Haiku 4.5
$1.00 input and $5.00 output per million. Cache prices are in the JSON. Provider invoices remain
authoritative. The application stops at $7.00 cumulative estimated spend. The core stops at
$5.50 across providers, with 650 logical reviews and 800 attempts per provider; regressions stop
at $1.00 across providers, with 210 reviews and 260 attempts per provider. Each diagnostic stops
at $0.25, 12 reviews, and 18 attempts. A stop is a guard, not a guaranteed invoice ceiling.

## Run order

From the repository, run the frozen Luna core first. Review its raw results and spending before
running the Haiku core. Do not tune the policy between providers. Run the regressions and counsel
diagnostic after core results, with the same freeze. The commands are:

```bash
python3 scripts/run_study.py --manifest studies/obligations-final-core-v0195.json --provider openai
python3 scripts/run_study.py --manifest studies/obligations-final-core-v0195.json --provider claude
python3 scripts/run_study.py --manifest studies/obligations-final-regression-v0195.json --provider openai
python3 scripts/run_study.py --manifest studies/obligations-final-regression-v0195.json --provider claude
python3 scripts/run_counsel_diagnostic.py --provider openai
python3 scripts/run_counsel_diagnostic.py --provider claude
```

If a run stops or writes an incomplete episode, preserve its files and inspect them before any
resume. Use `--resume` only for missing episodes of an identical manifest with unchanged code;
the diagnostic has no resume option. Keep failed and unfavorable results in the final tables.
