# Final Whole-Diff Review Report — Track B Piece P6 (Analysis and Pass/Drop Rules)

- **Reviewer:** Neon (Gemini), fresh final whole-diff review (review 3 of 3)
- **PR:** https://github.com/metaphysika/taa-lab/pull/196
- **Branch / Head SHA:** `b1b2-trackb-p6-analysis` / `b53d5c5e9b83315f92a48d659b4df2ec64067c08`
- **Base SHA:** `660e978881ee87edf132814f63fb50066b41600a` (`origin/main`)
- **Rules judged against:**
  - `origin/b1b2-trackb-wave2-rules:docs/process/TRACK_B_BUILD_LOOP_SPEC_2026-11-21.md` (Section 2 P6, A6.3, A9, A10, A11 and A11 clarification)
  - `origin/main:docs/process/TRACK_B_WEAKNESS_MALICE_DESIGN_2026-11-21.md` (Sections 2.1, 4, 6, 7, 11)
- **Verdict:** **PASS** (0 MUST-FIX blockers; 4 minor SHOULD-FIX items for the pre-B0a reviewed follow-up under A9.6)

---

## Raw Evidence

- Fresh detached worktree checked out at exact head `b53d5c5e9b83315f92a48d659b4df2ec64067c08` (`C:\Users\lahn0\AppData\Local\Temp\neon-final-p6-b53d5c5e`, removed after verification). Read-only on the PR (no commits, pushes, or GitHub comments).
- `git diff --stat origin/main...HEAD`:
  - `exploratory/track_b/SCHEMA.md` (+135)
  - `exploratory/track_b/analysis.py` (+847)
  - `tests/test_track_b_analysis.py` (+483)
  - Total: 3 files changed, 1,465 insertions(+), 0 deletions(-).
- `git diff --name-status origin/main...HEAD -- tests/`:
  - `A	tests/test_track_b_analysis.py` (sole test edit; no existing tests modified, loosened, or skipped).
- `git diff origin/main...HEAD --check`: clean (0 whitespace/conflict issues).
- Piece unit tests re-run at `b53d5c5e` via `python scripts/agent_safe_imports.py -m unittest tests.test_track_b_analysis -v`: **20 tests ran in 0.703s, OK**.
- Independent probe script (`probe_p6_final.py`) executed at `b53d5c5e` via `python scripts/agent_safe_imports.py` (including full `BOOTSTRAP_RESAMPLES = 10_000` independent recomputation): **ALL PROBES COMPLETED SUCCESSFULLY** (details below).
- Hosted CI snapshot at `b53d5c5e` via `pull_request_read`: `fast`, `smoke`, `q18`, `Live demo offline isolation / offline`, `Gateway offline alignment / scope / scope`, `Harness checks / scope / scope` already green; remaining workflows still pending at time of check. PR body records fresh local `run_fast_checks.py --agent-safe` (727 tests + scripted scenarios, 207.718s).

---

## Checked / Not Checked

### Checked
- Read the **entire diff** fresh line by line: `exploratory/track_b/analysis.py` (lines 1–847), `exploratory/track_b/SCHEMA.md` (lines 1–135), `tests/test_track_b_analysis.py` (lines 1–483), plus `exploratory/track_b/verdict.py` (lines 1–87) to confirm `score_verdict(None)` handling.
- Verified scope isolation: only `exploratory/track_b/analysis.py`, `exploratory/track_b/SCHEMA.md`, and `tests/test_track_b_analysis.py` added; zero edits to shared modules (`taa/`, `formation/`, `scripts/`, `.github/`, `exploratory/ft1/`, etc.), `AGENTS.md`, `CLAUDE.md`, `LAB_NOTEBOOK.md`, or `results/`; stdlib + `.verdict` only.
- Verified every threshold constant appears once as a named constant with a design-section comment (`analysis.py:16-77`), clean ASCII comments throughout, and inclusive boundaries verified against Design §§2.1, 4, 6, 7, 11 and A10.
- Verified precondition ordering in `analyze()` (`analysis.py:782-835`): (1) FT1 floor & eligible starting candidate (`starting candidate not eligible` distinct from `FT1 floor failed`), (2) B0a headroom & instrument, (3) both recipes take on MB, (4) rates matched on MB + `chosen_steps` provenance verification, (5) PB separation with individual `conditions`, (6) RD common coverage (`>= 510`), (7) VB headroom (`>= 8` worst-case on both copies), (8) B1–B4 & drop rules, plus isolated descriptive EB audit.
- Re-ran `python scripts/agent_safe_imports.py -m unittest tests.test_track_b_analysis -v` (20/20 OK).
- Verified every earlier blocker (Neon M1, M2; Fable M1) and round-2 additions (checkpoint-ID verification, malformed-EB isolation, candidate-eligibility distinction, separation conditions, schema updates) with an independent probe script.

### Not Checked
- Did not re-run the broad 727-test `scripts/run_fast_checks.py --agent-safe` suite (per A9.3; fresh log reported in PR body and hosted `fast` CI check is green at `b53d5c5e`).
- Did not run P7's writer against `SCHEMA.md` (P7 is separate) or cross-check `_primary_effect` against P2's `batteries.executed_primary_act` (P2 is not merged into this base).
- Did not read `keys.env`, `~/.kaggle/`, `~/.modal.toml`, `exploratory/ft1/sealed.py`, any sealed output, `C:/Users/lahn0/T3/ft1-sealed/`, or `results/`; no GPU or model calls were made.

---

## Independent Probe Verification (Head `b53d5c5e`)

1. **Unanimous drop with uncertain co-reason (Neon M1 / A11 clarification):**
   - `Δ1=6`, `Δ5=5` known, `Δ2 ∈ {4, 5}` (malicious headroom 9, half = 4.5): returned `verdict="drop"`, `drop_reasons=("any training heals",)`, `possible_drop_reasons=("heal alike", "any training heals")`, `drop_reason_status={"any training heals": "in every resolution", "heal alike": "in some resolutions"}`, and `possible_verdicts` listing both reason tuples. **PASS.**
   - Definite reversal (`Δ1=6, Δ2=9`) + uncertain `"any training heals"` (`Δ5 ∈ {4, 5}`): `verdict="drop"`, `drop_reasons=("reversal",)`, `drop_reason_status={"reversal": "in every resolution", "any training heals": "in some resolutions"}`. **PASS.**
   - Definite `"any training heals"` (`Δ1=6, Δ5=5`) + uncertain reversal (`Δ2 ∈ {8, 9}`): `verdict="drop"`, `drop_reasons=("any training heals",)`, `drop_reason_status={"any training heals": "in every resolution", "reversal": "in some resolutions"}`. **PASS.**
   - Mixed drop + inconclusive (`Δ1=6, Δ5=0, Δ2 ∈ {4, 5}`): `verdict="inconclusive"`, `drop_reasons=()`, `possible_drop_reasons=("heal alike",)`, `drop_reason_status={"heal alike": "in some resolutions"}`. **PASS.**

2. **Mechanical W and U row handling (Fable M1 / Design §11 / A10.1):**
   - Via `analyze()` (retained snapshot path, `_load_partitions` -> `_validate_episode`, `analysis.py:711-725`):
     - Mechanical W row with no retained primary effect and `act_unknown=False` -> raises `ValueError("Mechanical row without a retained primary act requires act_unknown")`. **PASS.**
     - Mechanical W row with no retained primary effect and `act_unknown=True` -> accepted and counted as `unknown` (never `"no"` / "did not act"). **PASS.**
     - Mechanical W row WITH retained primary effect and `act_unknown=False` -> accepted and counted as known `yes`. **PASS.**
     - Mechanical U row with `lawful_success=False` (even when primary effect was retained) -> raises `ValueError("Mechanical U row requires lawful_success to be true or null")`. **PASS.**
     - Mechanical U row with `lawful_success=None` and retained primary effect -> accepted and counted as `unknown`. **PASS.**
     - Mechanical U row with `lawful_success=None`, no retained primary effect, and `act_unknown=False` -> raises `ValueError("Mechanical row without a retained primary act requires act_unknown")` (also protects EB's U-act cells). **PASS.**
     - Mechanical U row with `lawful_success=None`, no retained primary effect, and `act_unknown=True` -> accepted and counted as `unknown`. **PASS.**
   - Direct Python API note (`Probe 2h`, logged as **SF1** below): calling `repair_verdict()` directly on in-memory dicts bypasses `_validate_episode()`, so a malformed mechanical dict with `act_unknown=False` is not rejected unless read through `analyze()`/`_load_run()`. Because Track B's analysis entry point is `analyze()` over retained snapshot files (`SCHEMA.md:3`, Spec P6) and `_validate_episode()` matches Fable's exact requested fix, this is non-blocking and belongs in the pre-B0a follow-up.

3. **Five between-arm differences & paired-family bootstrap (Neon M2 / Design §11 / A10.13):**
   - Verified all five keys present in `report["comparisons"]`: `B2a_arm1_minus_arm2`, `B2b_arm4_minus_arm3`, `B3a_arm1_minus_arm5`, `B3b_arm1_minus_arm6`, `descriptive_arm1_minus_arm3`.
   - Independently recomputed all five exact differences and 80% paired-family cluster bootstrap intervals at full `BOOTSTRAP_RESAMPLES = 10_000`, `BOOTSTRAP_SEED = 20261121`, `BOOTSTRAP_PERCENTILES = (10, 90)` with unknowns on both `weak` and `malicious` baselines:
     - `B2a_arm1_minus_arm2`: `diff=(4, 6)`, `boot=(0.0, 10.0)` — exact match.
     - `B2b_arm4_minus_arm3`: `diff=(2, 4)`, `boot=(-1.0, 7.0)` — exact match.
     - `B3a_arm1_minus_arm5`: `diff=(5, 5)`, `boot=(2.0, 8.0)` (shared `weak` baseline cancels cleanly inside each family) — exact match.
     - `B3b_arm1_minus_arm6`: `diff=(5, 5)`, `boot=(2.0, 8.0)` — exact match.
     - `descriptive_arm1_minus_arm3`: `diff=(5, 7)`, `boot=(1.0, 11.0)` — exact match.
   - Verified descriptive-only: on clean `Δ=(6, 1, 0, 3, 1, 1)`, `verdict="supported"` even though `B2a` bootstrap 10th percentile is `1.0 < 5` and `B2b` bootstrap 10th percentile is `0.0 < 3`. Also confirmed by code inspection that `_between_arms` (`analysis.py:692`) runs strictly after `_repair_options` and never feeds any rule.
   - Verified `unavailable_arms=(6,)` sets `B3b_arm1_minus_arm6` to `{"verdict": "not established"}` while computing all other four pairs. **PASS.**

4. **Checkpoint-ID (`chosen_steps`) verification & malformed-EB isolation cannot silently change a verdict:**
   - `chosen_steps` (`analysis.py:809-812`): tested 8 invalid values (`None`/omitted, wrong weak step, wrong malicious step, float `50.0`, bool `True`, extra key, missing key, list) when MB matching selected `{"weak": 50, "malicious": 25}` -> all 8 raised `ValueError` (fail loud; never silently alter a verdict). Confirmed absent `chosen_steps` is cleanly allowed when stage is `B0a` or when MB matching fails (`"rates not matched"`). **PASS.**
   - Malformed EB (`analysis.py:747-755, 833-835`): `repair_verdict` completes before `_load_eb(root)` runs, and `_load_eb`'s output is isolated solely under the `"EB"` key. Tested 7 EB modes (`valid`, `empty`, `bad_json`, `non_dict`, `bad_utf8`, `missing_detached`, `mech_bad`) across 3 distinct VB verdicts (`supported`, `drop`, `not testable`) via CLI `main()`: in all 21 runs, every non-EB field of the printed JSON report matched the no-EB baseline identically, while all 6 malformed modes reported `EB: {"verdict": "not established", "error": ...}`. **PASS.**

---

## MUST-FIX Findings

None. All prior blockers (Neon M1, Neon M2, Fable M1) and all prior non-blocking review items (Neon S1–S4, S6; Fable S1–S5) are resolved cleanly at `b53d5c5e`.

---

## SHOULD-FIX Findings (Non-blocking; batch into the pre-B0a reviewed follow-up per A9.6)

### SF1. Direct Python entry points bypass `_validate_episode` mechanical-row checks
- **Location:** `exploratory/track_b/analysis.py:126-131, 144-145, 711-725`
- **Detail:** `_validate_episode` is called only inside `_load_partitions` (`analysis.py:738`), so retained snapshot runs via `analyze()` / CLI are fully protected. However, direct Python callers of `b0a`, `checkpoint_search`, `match_checkpoints`, `pb_measure`, `dependency_scores`, or `repair_verdict` bypass `_validate_episode`, allowing an in-memory row with `mechanical=True, effects=[], act_unknown=False` (or U with `lawful_success=False`) to score as `False` (`Probe 2h`).
- **Fix:** Enforce the mechanical invariants directly inside `_act` and `_outcome` (or validate episode rows in a dedicated `_index_episodes` helper called by all episode-taking public functions), and add a direct-API unit test.

### SF2. Reject `bool`/non-`int` for `manifest["ft1_seed"]`, MB `row["step"]`, and `unavailable_arms`
- **Location:** `exploratory/track_b/analysis.py:736-737, 758-769, 793-795, 834`
- **Detail:** Because `bool` subclasses `int` (`True == 1`) and `25.0 == 25` in Python, `manifest["ft1_seed"] = True` matches eligible seed `1` (`Probe 5a`), MB `step: 25.0` matches `25`, and `unavailable_arms: [True]` matches arm `1`. `ft1_floor`, `chosen_steps`, and `common_coverage` already enforce `type(...) is int`; applying the same check here makes manifest/row typing uniform.
- **Fix:** Check `isinstance(manifest["ft1_arm"], str)` and `type(manifest["ft1_seed"]) is int` in `_load_run`, `type(row["step"]) is int` in `_load_partitions` for `battery == "mb"`, and `isinstance(unavail, list) and all(type(x) is int for x in unavail)` for `unavailable_arms`.

### SF3. Minor schema-strictness checks in `_validate_episode`
- **Location:** `exploratory/track_b/analysis.py:115-123, 711-725`
- **Detail:** `SCHEMA.md:47` says `lawful_success` is `null` on W rows, and `_primary_effect` assumes every item in `row["effects"]` is a dict with `"tool"` and dict `"args"`. `_validate_episode` does not currently assert `row["kind"] != "W" or row["lawful_success"] is None` or validate each effect dict shape upfront (malformed effects still fail loud later via `KeyError`/`TypeError`/`AttributeError`).
- **Fix:** Add explicit `ValueError` checks for `row["kind"] == "W" and row["lawful_success"] is not None` and effect dict structure in `_validate_episode`.

### SF4. Cross-check `_primary_effect` against P2's `executed_primary_act` after P2 merges (carried from round 1 S5)
- **Location:** `exploratory/track_b/analysis.py:115-123`
- **Detail:** As noted in `analysis.py:116-118`, on P2's freight world `PRIMARY-CARGO` dispatch requires `PRIMARY == RELEASED`, so checking `set_record_status(PRIMARY, ordered_status)` is equivalent when replay effects are complete. Once P2 merges, pin equivalence with `batteries.executed_primary_act` (or check `dispatch_shipment(PRIMARY-CARGO)` too) in a cross-piece test.

---

## Decisions and Assumptions

- Judged `SF1` as SHOULD-FIX rather than MUST-FIX because: (a) the frozen P6 spec and `SCHEMA.md` define P6 as reading retained snapshot files via `analyze()` / CLI, where `_validate_episode` unconditionally enforces both mechanical W and U invariants on MB, PB, VB, and EB; (b) Sol implemented Fable's exact 4-point fix; and (c) A9.6 guarantees any P6 follow-up merges before B0a produces any result.
- Accepted the existing `BOOTSTRAP_RESAMPLES = 10_000` / `BOOTSTRAP_SEED = 20261121` family-draw semantics, including that a family drawn multiple times retains one resolved outcome across occurrences within a draw.

---

## Plain-Language Summary

P6 at `b53d5c5e` is ready to merge. Every gate, threshold, precondition order, joint-unknown rule, unanimous-drop reason split, paired-family bootstrap comparison, mechanical-row check on retained snapshots, checkpoint-step verification, and malformed-EB isolation matches the frozen Track B design and amendments A6.3, A10, and A11. All 20 unit tests and all independent probes pass, and four minor hardening items are queued for the pre-B0a follow-up.
