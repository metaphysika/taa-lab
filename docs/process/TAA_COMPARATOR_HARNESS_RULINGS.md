# Comparator and ablation rulings (C1–C4)

Date: 2026-10-22. Author: Claude, answering Sol's questions on the comparator stage. These settle points Design v0.3 left open in its Comparators section. They change no frozen trace and no expected outcome. Each applies before any cross-arm score is computed.

## C1. Ablation "without the admissibility stage"

Remove the prohibition stage and nothing else. PR1 and PR2 are not evaluated, so no PROHIBIT disposition, no attribution of a prohibited element and no prohibition-triggered report duty can arise. Authority, support, determination and duty stages, invalidation, atomic execution, the duty ledger and reporting machinery stay exactly as in the TAA core.

Consequences to record, not fix: report duties now arise only from paths other than prohibitions, so this ablation overlaps partly with "without report duties". Wrongs that a support rule also catches (for example a false "return received" that SU1 leaves unknown) may still be held or refused, which is the point of the test: it measures what the prohibition stage adds beyond the other checks.

A separate ablation that keeps prohibitions but lets a later stage lift them (the ordering defect from Paper 2) would test check ordering. It is optional and not required now.

## C2. Ablation "without invalidation"

The intervention removes the whole invalidation contract (P3), not one mechanism. A token is checked only against its own fixed conditions: acting party, exact arguments, single use and expiry. There is no proactive voiding on a relevant change, no revision comparison at execution, and no execution-time reassessment against current state. Atomic commit, receipts, the duty ledger and reporting stay.

Run one diagnostic variant alongside it, labeled as such: invalidation removed but execution-time reassessment retained. Comparing the two shows whether revision voiding or reassessment does the work. The primary ablation is the one without either.

## C3. Duties and transfer tools in the floor and static-permission arms

These arms have no gateway and therefore no internal duty ledger. They expose the same registered tools. `offer_duty`, `accept_duty`, `close_case` and the duty-related messages execute as plain business operations: they write ordinary records of what was done and enforce nothing.

Duty status for scoring every arm comes from one common external scoring oracle. It applies DU1–DU6 and Clarifications Q1–Q13 to each arm's committed world records and log, identically across arms. No arm's internal ledger is trusted for scoring, including the TAA core's and the strongest conventional arm's. The oracle must be independent of both of those implementations; the reference model's duty relations may serve, since they share no code with either. Closing a case with an unresolved duty, or leaving one unresolved, is scored by the oracle in every arm.

## C4. Token names in fixtures

A fixture's token name (T1, T2, ...) binds to the proposal entry that produced it (trace id and step index), not to issuance order. Each arm resolves the name to whatever its own system returned for that proposal. A diagnostic or extra proposal therefore never shifts the meaning of a later reference.

- If an arm refused that proposal, the name resolves to "no token", and the execute entry is an attempt without a token.
- In arms with no tokens (floor, static permissions), a propose entry records the intended act, and the bound execute entry performs that act directly with the proposal's arguments, subject to that arm's own checks. A proposal with no execute entry is never performed.
