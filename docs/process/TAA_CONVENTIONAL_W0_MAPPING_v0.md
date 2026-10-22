# Conventional SQL arm: W0 mapping before first common-runner evaluation

Status: Sol-authored implementation mapping, Claude review pending. Governing
protocol: `TAA_CONVENTIONAL_COMPARATOR_PROTOCOL_v0.md`, committed before outcomes.
The fixture bundle remains unchanged. This document generates no expectation.

| W0 names | SQL representation | Public runner representation |
|---|---|---|
| Parties A, B, L, F, R, C, K1, K2 | Same identifiers; host-issued sessions | Same identifiers |
| Grants G0, G1 and source-issued grants | Version rows in `grants` | Current row with the same identifier |
| Records ORD/PAY/CL/RET/DEL/REF/CB/WD/RES and setup IDs | All versions in `records` | All versions, adding the SQL version number |
| PR1, PR2, AU1, SU1–SU3, DT1–DT2, DU1–DU6, IR1 | Independent flat predicates / ledger transitions | Same rule identifiers; internal template-evidence requirements have descriptive names |
| W0 tool names | Independent deterministic service functions and frame checks | Same names and arguments |
| D_resolve(claim), D_refund(claim,amount) | Current and historical `duties` rows | Same generated identifiers |
| D_report(order), supplements, D_unowned_report(claim) | `duties`, `reports`, authenticated inbox | Same identifiers; recipients and routing deadlines come from state |
| PERMIT, ALTERNATIVE, HOLD, REFER, REFUSE, PROHIBIT | Same vocabulary and strict rank | Same dispositions; deciding rule is first failed constraint in stage order |
| T1, T2, … | Opaque epoch handles H1, H2, … | Serial identity mapping Hn ↔ Tn, without changing policy or selecting outcomes |
| RPT1, RPT2, … | `reports` version relations | Same report IDs and content versions |
| Executed offer/accept | `duty_actions`, applied by the independent ledger inside the real SQL transaction | Actual owner/offer changes, with execution-step deadlines |

DESCRIPTIVE: Offer creation sequence is stored explicitly. The public offers
object iterates in that sequence, so JSON's alphabetical object-key ordering
cannot reorder concurrent offers. The first campaign exposed four list-order
discrepancies; its unchanged expectations and raw results remain preserved.

INTERPRETATION / IMPLEMENTATION CHOICE: Constraints read current rows and choose
one complete grant. There are no stored TAA warrants or rule-computed support
sets. Every relevant write advances the epoch and invalidates live handles.
SQLite rollback protects actual staged effects and ledger changes. Source writes
use authenticated, separate host channels; actor calls cannot choose an issuer.

DESCRIPTIVE: A step applies all source event entries in listed order, performs
one duty reconciliation after all events, then proposals and executions. Event
expectations are checked after that phase 2 by the existing runner. New expected
outcomes are never computed by the reference model.

DESCRIPTIVE: The public observation contains the actual complete SQL checkpoint
rows, with the signed audit anchor held inside `log`. This lets rejected-call
audits change without falsely changing transaction state. The common observer
independently checks projections against SQL rows and pins historical versions.
The runner still computes its own delta and compares every supplied description.
All three hidden-state controls mutate actual SQL; historical rewrite explicitly
defeats the SQL trigger only in the test hook.

INTERPRETATION / OPEN QUESTION: Q14–Q16 remain drafts. Settlement citations count
once; denial coverage uses one conservative shared unsupported remainder; report
repeats keep the current recipient; accepting without discharge authority does
not immediately create another fallback offer. No pending ruling is implemented.

LIMITATION: Component tests are Sol-authored from the specification and are not
independent acceptance evidence. The first common-runner results must be retained,
with every disagreement recorded. Matching is success for both strongest arms.
