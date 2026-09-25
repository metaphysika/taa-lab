# Where the paper lives in the code

Paper: "A Thomistic Natural-Law Framework for Purpose-Dependent Authorization in Agentic AI,"
preprint v1.0, https://doi.org/10.5281/zenodo.22946219

| Paper | Idea | Code |
|---|---|---|
| 1.2 | Governing claim: M, A, F in one context | `taa/counsel.py` (plan review), `taa/gate.py` (step check) |
| 2.3 | Normative hierarchy; warrants narrow authority | `taa/records.py` (`Warrant`) |
| 3.2 | Stages of a human act; counsel before command | Plan review before any step (`TAAGate.submit_plan`) |
| 3.3 | Counsel, judgment, command | Model counsel (`model_counsel`), Iudicium stand-ins (`standing_determination`, `ask_in_terminal`), one-time tokens (`TAAGate.request`) |
| 3.4 | Standing determinations | `standing_determination` in `taa/counsel.py` |
| 4.2 | Plan review; approved plan covers only what it specifies; departures return to review | `TAAGate._step_check`, `TAAGate._rereview` |
| 4.3 | Live warrant; tool registry; step check; unregistered tools most consequential | `Warrant.is_live`, `ToolRegistry`, `TAAGate._step_check` |
| 4.5 | Purpose defeat | `scenarios/purpose_defeat.json`; witnesses and steward not yet built |
| 6.2 | Model-mediated judgment can fail | `taa/counsel_check.py` (false approvals and refusals) |
| 7 | Comparators; defeat conditions | Three gates in `taa/gate.py`; metrics in `run.py` |

Not yet implemented: encoded core and charter review (4.1), delegation and shared budgets (4.4),
witnesses and the purpose steward (4.5), emergency envelope (5.3), content-bound communication (3.2).
