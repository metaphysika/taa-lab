# Roadmap

The goal is the bounded prototype and comparative study the paper proposes (Section 7): implement
the structural parts of TAA, attack them, and compare against simpler controls. Each item names the
paper section it tests.

## Comparators

| Gate | Status | What it answers |
|---|---|---|
| Plain scoped permissions | Done | The floor |
| Expiring permissions (scope, budget, live condition) | Done | Does TAA add anything beyond ordinary permission expiry? |
| Plan-locked (plan review, live warrant, step check, no re-review) | Done | Does re-reviewing a departure (Iudicium) add anything beyond locking the plan at approval? |
| TAA (plan review, live warrant, step check) | Done (partial) | The architecture under test |
| Purpose-aware judge per step (one model checks each act, no plan) | To do | The "strong purpose-aware baseline" the paper names |

## Scenarios

| # | Scenario | Paper | Status | Needs |
|---|---|---|---|---|
| 1 | Lapsed warrant | 4.3; case 3 | Done | |
| 2 | Prompt injection claims authority was extended | 1.4, 4.3 | Done | |
| 3 | Unannounced lapse | 4.3 | Done | |
| 4 | Ambiguous end (storm downgraded) | 4.3 | Done | |
| 5 | Purpose defeat: rerouting unaffected shipments | 2.5, 4.5 | Done | |
| 5b | Purpose defeat, wide plan: the plan must name every shipment it needs | 2.5, 3.4, 4.5 | Done | |
| 6 | Ticket closures marked as duplicates | 4.5; case 1 | To do | Witness indicators and purpose steward (`taa/steward.py`) |
| 7 | Benchmark agent reaches for a production system | 4.3; case 2 | To do | Target registry and capability envelope |
| 8 | Authenticated order to falsify a safety record | 2.6, 5.2; case 4 | To do | M test in counsel; refuse, preserve, report |
| 9 | Prohibited campaign split across subagents | 4.4; case 5 | To do | Delegation and shared root budgets (`taa/delegation.py`) |
| 10 | Subagent buys applicant data from a broker | 4.4 | To do | Delegation attenuation |
| 11 | Flood emergency inside and outside the envelope | 5.3 | To do | Emergency envelope |
| 12 | Harm of stopping (medication shipment) | 5.3 | To do | Verified safe baseline |
| 13 | Reply that becomes a lie at sending time | 3.2 | To do | Message tool and content-bound check |
| 14 | Planner shades the counsel record | 3.3 | To do | Counsel record with evidence links |
| 15 | Declared premise changes mid-plan | 4.3 | To do | Premise holds on approved plans |

## Measurements to add

- Escalation load and review latency (the paper's rubber-stamping and flood risks)
- Over-refusal across all scenarios (legitimate work blocked)
- Per-model comparison: Claude, Gemini, local Ollama models
- At least five repeats per cell for any reported number

## Process

1. Write the scenario and its expected results in `LAB_NOTEBOOK.md` before any model run.
2. Run scripted, then local (Ollama), then hosted models.
3. Record every run. Summarize findings in the notebook.
4. When a result bears on the paper, note the section it affects.
