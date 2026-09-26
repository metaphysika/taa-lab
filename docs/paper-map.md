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
| 3.3 | Counsel approves the acts and refers a question about the end to the issuer | `approve_and_refer` in `review_plan` and `send_notice`, `taa/counsel.py` (v0.8) |
| 4.2 | Partial approval; one revised plan after a stop | `approved_part` and `review_plan` in `taa/counsel.py`; the revision in `run.run_once` (v0.8) |
| 4.2 | Plan review; approved plan covers only what it specifies; departures return to review | `TAAGate._step_check`, `TAAGate._rereview`; `PlanLockedGate` is the comparator that refuses departures instead of re-reviewing them |
| 4.3 | Live warrant; tool registry; step check; unregistered tools most consequential | `Warrant.is_live`, `ToolRegistry`, `TAAGate._step_check`; an act with no effect spends no authority (`_GateBase._execute`, v0.8) |
| 2.6, 5.2 | Acts no authority can license (M); refuse, preserve, report | `scenarios/wrongful_order.json`; the "grave" rule in `purpose_rules` and grave notices in `taa/counsel.py`; `report_to_human` (always allowed) in `taa/gate.py` (v0.10) |
| 5.3 | Harm in a consequence of a routine act | `scenarios/medical_bump.json` (v0.10) |
| 4.4, 4.5 | Harm split across acts each permitted | `scenarios/split_credits.json` (v0.10; one agent, no delegation); `scenarios/split_credits_linked.json` (v0.14.1; split across linked accounts, which the per-account cap can't catch) |
| 3.3 | A reviewer does not re-decide a refusal from scratch | Refusal memory in `_GateBase` (`_recall`, `_refused_on_review`), `taa/gate.py`; grave refusals only since v0.11 |
| 4.2, 4.3 | Plan review plus a check at the moment of consequential acts | `HybridGate` in `taa/gate.py`; what counts as consequential in `taa/consequence.py` (v0.11) |
| 4.2 | An approved plan covers only what it specifies, per target | Per-target limits (`Plan.limits`, `normalize_targets` in `taa/records.py`; enforced in `TAAGate._step_check`; narrowed by `narrow_limits` in `taa/counsel.py`) (v0.11) |
| 2.3, 4.3 | Fixed limits (a *determinatio* of the warrant) enforced by code, not judged | `taa/determinations.py`; checked by every gate in `_GateBase._cap_check` (v0.13) |
| 3.3, 4.2 | An approval states exactly what may proceed; prose is never permission | `scope_unclear`, `model_scope`, and the scope step in `review_plan`, `taa/counsel.py` (v0.13) |
| 4.3; ST I-II q.18 a.3 | Circumstances at the moment of acting: re-review when an approval's facts change | `taa/premises.py`; `TAAGate._premise_rereview` in `taa/gate.py` (v0.13) |
| 3.3, 5.3 | Counsel judges consequences the system computes; it is not asked to do the arithmetic | `taa/preview.py`, shown in every reviewer prompt in `taa/counsel.py` (v0.14) |
| 3.3 | While a referral waits, the undisputed part may proceed | `ask_portion`, `model_portion` in `taa/counsel.py` (v0.14) |
| 4.5 | Purpose defeat | `scenarios/purpose_defeat.json`, `scenarios/purpose_defeat_wide.json`; witnesses and steward not yet built |
| 6.2 | Model-mediated judgment can fail | `taa/counsel_check.py` (false approvals and refusals) |
| 7 | Comparators; defeat conditions | Six gates in `taa/gate.py`, including the per-step purpose judge (`StepJudgeGate`, `judge_act` in `taa/counsel.py`); metrics, referrals, and reviewer calls in `run.py` |

Not yet implemented: encoded core and charter review (4.1), delegation and shared budgets (4.4),
witnesses and the purpose steward (4.5), emergency envelope (5.3), content-bound communication (3.2).
