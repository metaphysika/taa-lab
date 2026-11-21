# Final Review Report — Track B Piece P5 (`exploratory/track_b/repair_data.py`)

- **PR:** https://github.com/metaphysika/taa-lab/pull/197 (`b1b2-trackb-p5-repair-data`)
- **Base / Head:** `660e978881ee87edf132814f63fb50066b41600a` / `9e910a8a48bda2acacfde1a5e9276c6310e1109e`
- **Builder:** Sol (GPT)
- **Reviewer:** Neon (Gemini)
- **Verdict:** **PASS** (counts as **FINAL** under amendment A9 — fresh whole-diff read, piece tests re-run, and independent probes (a)–(c) executed at head `9e910a8a`)
- **Diff scope (`git diff --stat origin/main...HEAD`):**
  - `exploratory/track_b/repair_data.py` (+297 lines, new)
  - `tests/test_track_b_repair_data.py` (+255 lines, new)
- **Test edits (`git diff --stat origin/main...HEAD -- tests/`):**
  - Only `tests/test_track_b_repair_data.py` added; zero edits to existing tests or pinned fixtures. No shared modules, `results/`, or sealed paths touched.

---

## 1. Evidence: Checked and Not Checked

### Checked
1. **Piece unit suite (re-run at head `9e910a8a`):**
   - `python scripts/agent_safe_imports.py -m unittest tests.test_track_b_repair_data -v` → **6/6 tests OK in 9.602s** (no sealed imports, clean worktree).
2. **Whole-diff line-by-line review** against:
   - `origin/b1b2-trackb-wave2-rules:docs/process/TRACK_B_BUILD_LOOP_SPEC_2026-11-21.md` (Section 2 P5; amendments A2, A3.5, A5, A7, A9, A10 items 3–6, 22–26, 36, 38)
   - `docs/process/TRACK_B_WEAKNESS_MALICE_DESIGN_2026-11-21.md` (Section 8)
   - P3 modules (`exploratory/track_b/verdict.py`, `exploratory/track_b/repair_domain.py`), P4 (`exploratory/track_b/training.py`), FT1's non-sealed `exploratory/ft1/data.py` and `exploratory/ft1/training.py`, and `formation/study_b_parser_v0234.py`.
3. **Independent Probe (a) — 510 vs 509 coverage floor (own synthetic inputs, disjoint missing/prose-unknown/multi-object-JSON/invalid-value exclusions):**
   - With 50 W excluded in `weak` (20 missing, 20 prose unknowns, 10 double-answer JSON unknowns) and 40 disjoint cases excluded in `mal` (20 W prose unknowns, 20 U invalid-answer JSON unknowns):
     - **510 common (W=230/300 = 76.7%, U=280/300 = 93.3%, overall=510/600 = 85.0%):** `status='established'`, `weak` `prose_unknowns=20`, `mal` `prose_unknowns=20`, wrote `D-weak.jsonl`, `D-mal.jsonl`, `shuffled.jsonl`, `R-harmself.jsonl`, `manifest.json`.
     - **509 common (+1 U prose unknown in `mal`; W=230/300, U=279/300, overall=509/600 = 84.83%):** `status='repair data not established'`, `mal` `prose_unknowns=21`, wrote **only** `manifest.json` (zero `.jsonl` files).
   - Exact integer check `100 * len(common) < 85 * len(cases)` avoids float rounding hazards.
4. **Independent Probe (b) — Leakage injection (`family_id`, `cargo_noun`, `metric_label`, freight-only tool name, verdict prompt / answer tool):**
   - **Caught (fail-closed, output dir not created):**
     - `family_id` (`thermal_sealant`, `THERMAL_SEALANT`, hyphenated `ID-thermal_sealant-01`)
     - `cargo_noun` (`epoxy drum`, embedded in sentence)
     - `metric_label` (`cure temp (C)`, embedded in sentence)
     - freight-only tool (`dispatch_shipment`)
     - top-level `{"tool": "answer", ...}` action
     - full `detached_item(cases[0])`
   - **Boundary edge cases not caught** (logged as `S3` below): underscore-embedded `ID_thermal_sealant_01`, plural `epoxy drums`, isolated detached-item tail fragment `"Under the company rules, was that act permissible?"`, and escaped/spaced `'{\"tool\": \"answer\", ...}'` inside `R-harmself` `args`.
5. **Independent Probe (c) — Output cleanliness, format, parser, and FT1/P4 training compatibility across all 6 datasets (`standard=True`):**
   - Scanned all 12,000 emitted records (`D-weak`, `D-mal`, `shuffled`, `R-harmself`, `R-oracle`, `R-harmless`; 2,000 each):
     - Zero occurrences of `"Here is what an assistant did."`, `"Act taken:"`, `"was that act permissible?"`, `'"tool":"answer"'`, `'"tool": "answer"'`, `"answer_key"`, raw `reason` strings, `"The assistant marked permit"`, or `RD-XX-YY-W`/`-U` case IDs.
     - Every record has exact top-level key `{"messages"}`, roles `["system", "user", "assistant"]`, valid alternating roles (`validate_roles`), `SYSTEM == 'One JSON object: reason, tool, args. null ends.'`.
     - Every assistant payload parses with `formation.study_b_parser_v0234.parse_action`, has exact key order `("reason", "tool", "args")`, `reason == ""`, and satisfies `exploratory/ft1/training.py:record()`'s `text.index('"reason":') == 1`.
     - Approximate token lengths via `CharacterCounter` are well within FT1's 1,024 total / 640 trained caps (`max_prompt_tok~=273`, `max_trained_tok~=31`).
     - Observed dataset counts:
       - `D-weak`: 2,000 rows, 2,000 unique, `eligible=2100`, `repeated=0` (`decline_order: 300`, `report_issue: 283`, `set_record_status: 858`, `None: 559`).
       - `D-mal`: 2,000 rows, 1,800 unique, `eligible=1800`, `repeated=200` (`set_record_status: 1326`, `None: 674`).
       - `shuffled`: 2,000 rows, 2,000 unique, `eligible=2100`, `repeated=0` (`decline_order: 300`, `report_issue: 284`, `set_record_status: 855`, `None: 561`).
       - `R-harmself` (1,200 parsed): 2,000 rows, 1,200 unique, `eligible=1200`, `repeated=800`.
       - `R-harmself` (2,500 parsed): 2,000 rows, 2,000 unique, `eligible=2500`, `repeated=0`.
       - `R-oracle`: 2,000 rows, 2,000 unique, `eligible=2100`, `repeated=0`.
       - `R-harmless`: 2,000 rows, **600 unique**, `eligible=1200`, `repeated=800` (see `S2`).
6. **Extra edge-case probes:**
   - `R-harmself` wrong `model_id` rejected (`ValueError`).
   - `output_dir` containing `results/` rejected by `safe_output` (`ValueError: results is protected`).
   - Empty verdict files cleanly yield `status='repair data not established'` with `common=0`.
   - `standard=True` with `oracle_labels=None` raises `TypeError` from `Path(None)` (logged as `S4`).
7. **Builder's broad-suite evidence and CI:**
   - Confirmed Sol's `--agent-safe` log at `C:/Users/lahn0/AppData/Local/Temp/trackb-p5-agent-safe-f2e03287.log` exists and ends with `{"set": "fast", "elapsed_seconds": 207.404}`.
   - Hosted PR #197 checks (`fast`, `smoke`, `formation`, `test`, `q18`, `Live demo`, `Experiment A`, `Gemma actual CPU training rehearsal`) are green (`reference-and-foundation` still pending at check time). Broad suite not re-run per A9.3.

### Not Checked
- Full `run_fast_checks.py --agent-safe` locally (skipped per A9.3 because builder's log and hosted `fast` CI are present and green).
- Real Gemma 3 tokenizer encoding, actual GPU training, production verdict / routine reply files, and the real P2 freight family inventory (offline review scope only).

---

## 2. Spec & Amendment Compliance Summary

| Requirement | Status | Notes |
|---|---|---|
| Common parseable set across both copies (`repair_data.py:231-233`) | Pass | Sorted deterministic RD `case_id` intersection of non-`None` `score_verdict` results. |
| Coverage floor inclusive at 0.85 overall; 510 passes, 509 fails (`repair_data.py:249-250`, A10.22–23) | Pass | `100 * len(common) < 85 * len(cases)`; applies overall only; W/U reported separately. |
| W/U and per-model exclusions + prose unknowns via `verdict.py` (`repair_data.py:68-91`, A7, A10.4) | Pass | Reports `parseable`, `coverage`, `unknown_case_ids`, `missing_case_ids`, `prose_unknowns` (via `count_prose_unknowns`), and `excluded_by_other_copy` for `overall`, `W`, `U`. |
| Raw reply SHA-256 & single-model & duplicate-ID validation (`repair_data.py:47-66`, A10.4) | Pass | Rejects mismatched SHA-256, unknown/duplicate case IDs (unless `allow_repeats=True` for routine), missing/mixed `model_id`. |
| D-weak / D-mal from P3 templates in FT1 original layout with `reason: ""` (`repair_data.py:94-129`, A5, A10.25) | Pass | Imports `SYSTEM`, `action`, `dump`, `safe_output` from `exploratory.ft1.data`; key order is `reason, tool, args` with `reason: ""`. |
| Finish step its own decision-point record (`repair_data.py:122-124`, A3.5, A10.26) | Pass | Appends `action()` (`{"reason":"","tool":null,"args":{}}`) as final step; prior turns formatted identically to FT1. |
| 2,000 records, seeded order, cycling only if short with repeat count in manifest (`repair_data.py:132-151`, A10.3) | Pass (see `S1`) | Uses `DATA_ORDER_SEED = 20261121`, cycles in a fresh seeded shuffle only when `population < 2000`, logs `eligible_records`, `records`, `repeated_records`. Decision-step reservation evaluated in `S1`. |
| Shuffled arm permutes D-weak verdict array across case IDs, keeps counts, dedicated seed (`repair_data.py:274-276`, A10.24) | Pass | `SHUFFLE_SEED = 20261122` recorded in manifest; preserves exact decline count and common case set. |
| R-harmself input path, `<2000` cycling, `<1000` → not established (`repair_data.py:171-187, 278-282`, A10.5) | Pass | Parses with `study_b_parser_v0234.parse_action`, strips `reason` to `""`, validates weak `model_id`, cycles `<2000`, marks `"R-harmself not established"` with no `.jsonl` when `<1000`. |
| Standard-tier arms behind `standard=False` flag (`repair_data.py:214, 284-291`, A10.6) | Pass (see `S2`, `S4`, `S6`) | `R-oracle` uses supplied labels and reports generator agreement; `R-harmless` emits permits routine records. |
| Files given to both copies byte-identical; hashes recorded (`repair_data.py:29-38, 258-264`) | Pass | Swap arms reference the exact same `.jsonl` filename and single SHA-256 in manifest; verified byte-identical across independent builds. |
| No action-only variant (`repair_data.py`, A10.38) | Pass | Confirmed absent; all repair reasons are already `""`. |
| Only action records written; leakage scan (`repair_data.py:190-210, 254-256`, A10.36) | Pass (see `S3`) | Only `{"messages": [...]}` action records written; zero verdict prompt text or answer keys in outputs. |

---

## 3. MUST-FIX Findings

None.

---

## 4. SHOULD-FIX Findings (for reviewed follow-up / stage-thread confirmation)

### S1 — Stratified decision-step reservation when `population > 2000` vs literal flat draw in A10.3
- **Location:** `exploratory/track_b/repair_data.py:132-146`
- **Assessment (faithful implementation vs rule change):**
  - **Not a blocker / not a science-changing rule change.** Under A10.3 ("Each common case yields one decision-point record per step of its sequence ... Records are drawn in a seeded order without replacement. Only if that gives fewer than 2,000 are they cycled in a new seeded order; the repeat count goes in the manifest"), the spec does not explicitly forbid stratifying step 0 vs later steps when `population > 2000`, and P5's "Done means" explicitly asks that "the shuffle preserves the decline rate and the case set".
  - Sol's choice preserves every common case's primary step-0 decision record (`510–600` rows) and draws the remaining `2000 - len(decisions)` rows without replacement from later turns (`report_issue`, routine, finish), then shuffles all 2,000 rows together. This eliminates random sampling jitter in step-0 decline counts between `D-weak` and `shuffled` (both have identical `decline_cases` and identical `eligible_records`, so both get the exact same 600 step-0 / 1,400 later-turn split), and it leaves the `population <= 2000` cycling path completely untouched. Sol also disclosed the choice in the PR body under "Decisions and assumptions" as section 2 permits.
  - **Trade-off to note for the stage thread:** When `population > 2000`, step-0 decisions are slightly over-represented relative to flat uniform sampling (30.0% vs 28.6% at 300/600 declines; 30.0% vs 25.0% at 600/600 declines). Because P4 trains for 100 steps × 8 = 800 presentations drawn from the 2,000-row file, training still sees a uniform sample of the 2,000 rows.
- **Suggested action:** Stage thread to confirm whether to keep Sol's step-0 reservation (recommended as scientifically cleaner for the `D-weak` vs `shuffled` decline-rate match) or switch `_draw` to a single flat shuffle of `decisions + later_turns` if literal flat uniformity under A10.3 is preferred.

### S2 — `R-harmless` pre-duplicates every pair twice before `_draw`, under-reporting `repeated_records`
- **Location:** `exploratory/track_b/repair_data.py:287-291` (with `exploratory/track_b/repair_domain.py:35-61`)
- **Finding:** In `repair_domain.generate_cases()`, each of the 300 W/U twin pairs shares the exact same `routine_id` (`RD-XX-YY-INQUIRY`) and `subject_family`. Because `R-harmless` loops over all 600 `cases.values()`, `harmless` contains 1,200 records consisting of **600 unique records duplicated twice** before `_draw` runs. Probe C confirmed `R-harmless.jsonl` has only `600` unique rows while `manifest["datasets"]["R-harmless"]` reports `eligible_records: 1200, repeated_records: 800` (true repeats: `1,400`), and the first pass before cycling already repeats every record twice.
- **Fix (before standard tier B2 runs):** Iterate once per unique `(routine_id, subject_family)` / `pair_id` (giving 300 inquiries × 2 steps = 600 eligible records and an accurate `repeated_records: 1400`), or adjust `R-harmless` routine prompts if 600 distinct inquiries are intended.

### S3 — `_leakage_pattern` boundary regex edge cases
- **Location:** `exploratory/track_b/repair_data.py:190-202`
- **Finding:**
  1. Wrapping punctuation-bounded literals (`"Here is what an assistant did."`, `"Act taken:"`, `'"tool":"answer"'`) inside `(?<!\w)...(?!\w)` fails to match if a word character immediately follows the trailing punctuation (e.g. `"Act taken:issued"`).
  2. Literal `'"tool":"answer"'` misses spaced or escaped variants inside `R-harmself` `args` strings (e.g. `'{\"tool\": \"answer\", ...}'`), and `"was that act permissible?"` is not checked.
  3. Because `_` is `\w`, `(?<!\w)family_id(?!\w)` misses underscore-embedded tokens like `ID_thermal_sealant_01` (and `(?!\w)` misses simple plurals like `epoxy drums`).
- **Fix:** Separate word-bounded freight terms (optionally using `(?<![A-Za-z0-9])...(?![A-Za-z0-9])` for `family_id` and freight-only tool names) from unanchored literal/regex checks for detached-item markers (`"Here is what an assistant did."`, `"Act taken:"`, `"was that act permissible?"`, `"answer_key"`, and `r'\\?"tool\\?"\s*:\s*\\?"answer\\?"'`).

### S4 — Missing explicit `ValueError` when `standard=True` and `oracle_labels=None`
- **Location:** `exploratory/track_b/repair_data.py:284-285`
- **Finding:** Passing `standard=True` without `oracle_labels` falls through to `Path(None)` inside `_jsonl`, raising `TypeError` instead of a clear validation error.
- **Fix:** Add `if oracle_labels is None: raise ValueError("oracle_labels is required when standard=True")` before calling `_oracle`.

### S5 — No token-length guard on `R-harmself` parsed model completions
- **Location:** `exploratory/track_b/repair_data.py:171-187`
- **Finding:** `_harmself` accepts any `parse_action`-valid completion regardless of `args` length. A verbose completion could pass P5 and fail later inside P4's `exploratory.ft1.training.record()` 640-trained / 1,024-total token cap.
- **Fix:** Optionally filter or flag `R-harmself` completions whose `CharacterCounter` (or real tokenizer when available) length exceeds FT1's cap, or confirm P7's routine-reply generator caps `max_new_tokens` safely below 640.

### S6 — Standard-tier arm 8 (`mal`, `R-harmself`) reuses weak copy's routine completions
- **Location:** `exploratory/track_b/repair_data.py:34-38, 278-282`
- **Finding:** `STANDARD_ARMS` assigns `("mal", "R-harmself")` to the same `R-harmself.jsonl` built from `weak`'s routine completions. This matches A10.5's single weak-copy input path and preserves byte-identical datasets across copies, but if Design section 8 ("shuffled and R-harmself on the malicious copy") is intended to train `mal` on `mal`'s own routine completions in B2, `build_repair_data` would later need an optional `mal_harmself_replies` parameter.
- **Fix:** Confirm intent before B2 (standard tier); no change needed for B1.

### S7 — Defensive empty-pool guard in `_draw`
- **Location:** `exploratory/track_b/repair_data.py:132-146`
- **Finding:** `_draw` loops `while len(drawn) < RECORD_COUNT:` without checking `if not pool:`. Unreachable via `build_repair_data` (guarded by `>= 510`, `>= 1000`, and `600` cases), but defensive for direct helper callers.
- **Fix:** Add `if not pool: raise ValueError("Cannot draw from an empty pool")`.
