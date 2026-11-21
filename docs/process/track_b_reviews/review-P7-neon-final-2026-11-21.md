# Track B P7 Final Whole-Diff Review (Neon / Gemini) — PR #198

- **PR:** https://github.com/metaphysika/taa-lab/pull/198 (`b1b2-trackb-p7-launcher`, stacked on P6 PR #196 `b1b2-trackb-p6-analysis`)
- **Head reviewed:** `6b3b252b2ac5539ccf9df0a43c44d3949bf5aec4`
- **Base / Stack refs:** `origin/main` (`bc274ddd402a49f1ff6e2e7bad361f32bfaba710`), `origin/b1b2-trackb-p6-analysis` (`b53d5c5e9b83315f92a48d659b4df2ec64067c08`)
- **Review round:** 2 of 3 (fresh final whole-diff review)
- **Verdict:** **PASS** (0 MUST-FIX blockers; all round-1 blockers `M1`–`M3` and all 6 should-fixes `S1`–`S6` resolved)
- **Spec references:** `docs/process/TRACK_B_BUILD_LOOP_SPEC_2026-11-21.md` (§1, §2 P7, A6.4, A9, A10.16–21, A10.34–35); authorized minimal P6 interrupted-event change.

---

## 1. Raw Evidence & Diff Scope

### Exact files added/modified by PR #198 on top of `origin/main` and P6 (`b1b2-trackb-p6-analysis`)
1. **P7 new files (added on top of `origin/main` + P6):**
   - `exploratory/track_b/launch.py` (327 lines)
   - `exploratory/track_b/stage_b0a.py` (287 lines)
   - `tests/test_track_b_launch.py` (408 lines; 24 unit tests)
2. **Authorized minimal P6 change (`git diff origin/b1b2-trackb-p6-analysis...HEAD` on P6 files):**
   - `exploratory/track_b/analysis.py` (+4 / -2 lines): `_load_run()` returns `events[-1]["event"]` as 4th tuple element (L779); `analyze()` unpacks `terminal_event` (L789) and adds `if stage == "B0a" and terminal_event == "interrupted": report["B0a"]["verdict"] = "interrupted"` (L800–801), preserving all B0a metrics while setting both `report["B0a"]["verdict"]` and top-level `report["verdict"]` to `"interrupted"`. **Nothing else in `analysis.py` changed.**
   - `exploratory/track_b/SCHEMA.md` (+8 lines, L31–37): documents the B0a deadline-interruption retention format (`not_attempted_deadline`, MB/PB fields, terminal `event: "interrupted"`, and analyzer verdict behavior).
   - `tests/test_track_b_analysis.py` (+18 lines, L379–395): adds 1 new test (`test_interrupted_b0a_cannot_pass_within_the_unknown_allowance`). **All 20 earlier P6 tests are byte-for-byte unchanged.**
3. **Boundary & hygiene verification:**
   - `git diff --name-status origin/main...HEAD` lists only the 6 files above (`SCHEMA.md`, `analysis.py`, `launch.py`, `stage_b0a.py`, `test_track_b_analysis.py`, `test_track_b_launch.py`).
   - Zero shared modules (`taa/`, `formation/`, `scripts/`, `.github/`, `exploratory/ft1/`, `exploratory/k2_kaggle/`, `exploratory/step4_harness/`), `AGENTS.md`, `CLAUDE.md`, `LAB_NOTEBOOK.md`, or `results/` were modified.
   - `git diff --check origin/main...HEAD` exited 0 with no whitespace errors.
   - No existing test or pinned fixture was modified, loosened, skipped, or deleted.

---

## 2. Verification of Round-1 Blockers (`M1`–`M3`) and Should-Fixes (`S1`–`S6`)

### M1 — Cooperative `DeadlineExceeded` handling & interrupted B0a verdict: **RESOLVED**
- **Implementation reviewed:** `exploratory/track_b/stage_b0a.py:19, 167-175, 207-248`; `exploratory/track_b/analysis.py:779, 789, 800-801`; `exploratory/track_b/SCHEMA.md:31-37`.
- **How it works:**
  - `DEADLINES = (DeadlineExceeded, core.DeadlineExceeded)` catches both FT1 and K2 deadline classes.
  - Inside `stage_b0a.run()`, `call()` records `deadline_error = exc` and re-raises so `l1.action_episode()` still returns the interrupted episode's partial row (preserving any already-executed primary effect and partial reply).
  - `detached_row()` re-raises `DEADLINES`; `run()` catches it to retain the interrupted PB row with `partial_reply(exc)` and `failure_label=type(exc).__name__`, then immediately raises `deadline_error`.
  - The outer `except DEADLINES as exc:` handler fills every remaining cell in `schedule[next_cell:]` with `failure_label="not_attempted_deadline"` (MB: `effects=[]`, `mechanical=True`, `act_unknown=True`, `lawful_success=None`, `raw_replies=[]`; PB: `reply=None`), appends terminal event `"interrupted"` (with `untouched_cells`), and returns without ever logging `"complete"`.
  - In `analysis.py:800-801`, when `stage == "B0a"` and `events[-1]["event"] == "interrupted"`, `report["B0a"]` retains all computed metrics (`headroom`, `instrument`, `MB`, `PB`) and overrides both `report["B0a"]["verdict"]` and top-level `report["verdict"]` to `"interrupted"`.
  - `analysis.starting_model()` only accepts `"passed"`, `"headroom failed"`, or `"instrument failed"`, so an `"interrupted"` B0a verdict fails closed and cannot advance candidate selection.
- **Independent probe results (Probe 1):**
  - **1a (mid-MB episode #5 after primary act):** After 4 completed episodes, episode #5 executed `set_record_status PRIMARY` on turn 0 and raised `DeadlineExceeded` on turn 1. Generator stopped immediately at 6 total calls; episode #5 retained its effect (`act_unknown=False`, `mechanical=True`, `failure_label="DeadlineExceeded"`); remaining 19 MB + 48 PB rows were written as `not_attempted_deadline` unknowns (`untouched_cells=67`); `events.jsonl` ended with `"interrupted"` (`"complete"` absent); `analysis.analyze()` reported `verdict="interrupted"` and `B0a.verdict="interrupted"` with full MB/PB metrics retained (`mechanical=20`, `PB.unknown=48`).
  - **1b (final PB item #48 after 24/24 MB + 47/48 PB passing):** Even though raw B0a metrics satisfied both `headroom=True` and `instrument=True` (47/48 correct, 1 unknown <= 4), `events.jsonl` ended with `"interrupted"` (`untouched_cells=0`), and `analysis.analyze()` reported `B0a.verdict="interrupted"` and top-level `verdict="interrupted"` (never `"passed"`).
  - **1c (pre-loop deadline inside `make_generator`):** Wrote all 72 untouched cells as `not_attempted_deadline`, logged `"interrupted"` (`untouched_cells=72`), and parsed through `analysis.analyze()` as `"interrupted"`.

### M2 — Kaggle adapter mount resolution: **RESOLVED**
- **Implementation reviewed:** `exploratory/track_b/stage_b0a.py:254-287`.
- **How it works:**
  - `resolve_adapter(dataset_id, root=Path("/kaggle/input"))` validates `owner/slug` against `launch.DATASET_COMPONENT` (`[a-z0-9_-]+`), searches both `root / "datasets" / owner / slug` and `root / slug`, fails closed if missing (`"missing Kaggle adapter mount"`) or if both exist (`"ambiguous Kaggle adapter mount"`), rejects ambiguous root+nested layouts (`adapter_config.json` alongside `adapter/`), and requires both `adapter_config.json` and `adapter_model.safetensors`.
  - `mounted_run()` calls `resolve_adapter(config["adapter_dataset_id"])` at line 277 **before** `launch.validate_receipt(...)` (line 278) and before creating any output directory.
- **Independent probe results (Probe 2):**
  - Verified all 4 valid layouts: `/kaggle/input/datasets/<owner>/<slug>` (root & `adapter/`) and `/kaggle/input/<slug>` (root & `adapter/`).
  - Verified missing mount inside `mounted_run()` raises `ValueError("missing Kaggle adapter mount ...")` with `launch.validate_receipt` and `stage_b0a.run` never called.
  - Verified dual simultaneous mounts raise `"ambiguous Kaggle adapter mount"`, and malformed dataset IDs (`"onlyslug"`, `"a/b/c"`, `"../evil/slug"`, `"owner/.."`) raise `ValueError`.

### M3 — `TRACK_B_STAGING_ROOT` & FT1 / Git isolation: **RESOLVED**
- **Implementation reviewed:** `exploratory/track_b/launch.py:72-115, 209-212, 242-251`.
- **How it works:**
  - Rejects blank/whitespace `TRACK_B_STAGING_ROOT` (`"TRACK_B_STAGING_ROOT cannot be blank"`).
  - Checks both lexical (`os.path.abspath`) and resolved (`.resolve()`) paths against `C:/t`: refuses `C:/t` itself, any ancestor of `C:/t` (`C:/`), and any `C:/t/ft1*` subtree case-insensitively (covering `C:/t/ft1`, `C:/t/ft1-*`, FT1's gate launcher folder `C:/t/ft1g/.k2-launch`, and `C:/t/ft1r-data`).
  - Refuses `launch.ROOT`, subdirectories of `launch.ROOT`, any path inside a `.git` repository, worktree (`.git` file), or bare repo (`HEAD` + `objects/` + `refs/`), and walks existing staging roots (without following symlinks) to reject contained Git repos/worktrees or symlinked/junctioned directories.
  - `safe_name()` additionally refuses names starting with `"ft1"`, `"kaggle-owner"`, traversal strings, or uppercase characters.
  - `push()` additionally verifies the staged bundle directory and `BUNDLE_FILES` resolve to themselves (rejecting symlinks).
- **Independent probe results (Probe 3):**
  - Tested 23 forbidden `TRACK_B_STAGING_ROOT` values (`""`, `"   "`, `"C:/t"`, `"C:/t/"`, `"C:/"`, `"C:/t/ft1"`, `"C:/t/ft1-run"`, `"C:/t/FT1-UPPER"`, `"C:/t/ft1g"`, `"C:/t/ft1g/.k2-launch"`, `"C:/t/ft1g/.k2-launch/test-arm2-part1"`, `"C:/t/ft1r-data"`, `"C:/t/trackb/../ft1"`, `"C:/t/trackb/../ft1g/.k2-launch"`, repo root, repo subdir, nonexistent repo subdir, `"."`, fake worktree, fake worktree subdir, parent containing worktree, bare repo, bare repo subdir) plus 6 bad bundle names (`"ft1"`, `"ft1-run"`, `"ft1g"`, `"kaggle-owner"`, `"../ft1"`, `"UPPER"`): **all 29 refused with `ValueError`, 0 file writes, and 0 backend push calls.**

### Round-1 Should-Fixes (`S1`–`S6`): **ALL 6 RESOLVED**
- **S1:** `--status-command` now uses `nargs=argparse.REMAINDER` (`launch.py:307`), `subprocess.check_output` enforces `timeout=STATUS_TIMEOUT_SECONDS` (`60s`, `launch.py:292`), and `command_status()` requires an explicit JSON attestation object `{"owner": owner, "account_verified": True, "states": [...]}` (also closing the round-1 section 4 exit-0 empty-list caveat).
- **S2:** `cpu_precheck()` coerces `adapter = Path(adapter)` (`stage_b0a.py:65`) and duplicate `import os` in `mounted_run()` is removed.
- **S3:** `episode_row()` computes `lawful_success` via `classify(case, result) == "known_lawful_success"` only when `not mechanical`, leaving mechanical U rows as `None` (matching `crossing_analysis.classify()`).
- **S4:** Dataset regex enforces `[1-9][0-9]{0,49}` (no leading-zero seeds) and `bundle()` enforces `len(slug) <= 50` (`launch.py:121, 172-173`).
- **S5:** `append()` calls `stream.flush()` and `os.fsync(stream.fileno())` (`stage_b0a.py:126-127`).
- **S6:** Per-cell/per-turn deterministic seed progression: `GENERATION_SEED + next_cell * SEED_STRIDE + turn` (`SEED_STRIDE = 12`, `stage_b0a.py:18, 213-214`).

---

## 3. Non-Blocking Notes (Informational Only)

1. **Status command JSON envelope for live launch:** Because `launch.command_status()` (`launch.py:290-297`) requires `{"owner": "<owner>", "account_verified": true, "states": [...]}` (rejecting bare lists, wrong owner, or non-`True` `account_verified`), the stage thread's account-wide status helper for any future approved live launch must emit that attested JSON structure and exit nonzero on any API/auth failure.
2. **Scope of `"interrupted"` in `analysis.py`:** Line 800 intentionally scopes the `"interrupted"` verdict override to `stage == "B0a"` as authorized; future B0b/B1 runners will need their own interrupted-event handling if they adopt the same convention.

---

## 4. Checked / Not Checked

### Checked
- Checked out exact head `6b3b252b2ac5539ccf9df0a43c44d3949bf5aec4`, verified commit graph stacked cleanly on `origin/b1b2-trackb-p6-analysis` (`b53d5c5e`), read every added/modified line across `launch.py`, `stage_b0a.py`, `tests/test_track_b_launch.py`, `analysis.py`, `SCHEMA.md`, and `tests/test_track_b_analysis.py`, and confirmed `git diff --check` clean.
- Re-ran unit tests under `scripts/agent_safe_imports.py`:
  `python scripts/agent_safe_imports.py -m unittest tests.test_track_b_launch tests.test_track_b_analysis -v` -> **45/45 passed** (24 launch/B0a + 21 analysis, 2.969s).
- Ran independent probes under `scripts/agent_safe_imports.py` (in isolated tempdirs, zero writes to repo/`results/`/`C:/t/`, zero `kaggle` CLI calls):
  - **Probe 1:** Mid-MB deadline (ep #5 after primary act -> 6 calls, effect conserved, 67 untouched unknowns, P6 `"interrupted"` with metrics kept), last-PB deadline (item #48 -> 0 untouched, 47/48 passing metrics kept, P6 `"interrupted"` not `"passed"`), pre-loop deadline (72 untouched, P6 `"interrupted"`).
  - **Probe 2:** Adapter mount resolution under `/kaggle/input/datasets/<owner>/<slug>` and `/kaggle/input/<slug>` (both root and `adapter/`), missing mount failing before `validate_receipt`/`run`, ambiguous dual mounts, and malformed dataset IDs.
  - **Probe 3:** All 23 forbidden `TRACK_B_STAGING_ROOT` paths (blank, whitespace, `C:/t`, `C:/`, `C:/t/ft1*`, `C:/t/ft1g/.k2-launch`, `C:/t/ft1r-data`, traversal, repo root/subdirs, `.`, git worktree, worktree parent, bare repo) + 6 bad names refused with 0 writes and 0 push calls.
  - **Probe 4:** Full refusal matrix (missing/bad `KAGGLE_OWNER` flags, >=2 active sessions, invalid/unattested `command_status` JSON, duplicate submission) -> 0 push calls on all refusals and `.push-lock` cleaned up; real `source_at(HEAD)` archive verified (0 sealed files, `sealed_batteries.py` excluded) and executed in isolated `python -I` (`ISO_OK`, `exploratory.step4_harness.l2` never imported); AST audit confirmed `subprocess` calls occur only at `launch.py` lines 134, 139 (`git`), 286 (`kaggle_push`, reachable only through `push()`), and 292 (`command_status` with `timeout=60`), with zero `subprocess` calls in `stage_b0a.py`.

### Not Checked
- Live Kaggle mounts, `kaggle` CLI execution, real account-wide status helper, Gemma 3 12B / PEFT / bitsandbytes / safetensors GPU loading, and live model generation (all prohibited offline).
- Full `scripts/run_fast_checks.py --agent-safe` suite (not re-run per A9.3; targeted piece and P6 suites re-run directly).

---

## 5. Plain-Language Summary

PR #198 at `6b3b252b` cleanly resolves all three round-1 blockers (`M1`–`M3`) and all six should-fix items (`S1`–`S6`), with the authorized minimal P6 `"interrupted"` change limited strictly to B0a terminal-event handling in `analysis.py` (+6 lines), `SCHEMA.md` (+8 lines), and one new regression test in `tests/test_track_b_analysis.py` (+18 lines). Every refusal path fails closed with zero push calls, deadline interruptions retain partial effects and never report `"complete"` or `"passed"`, both Kaggle adapter mount layouts resolve cleanly before receipt validation, and staging paths cannot overlap `C:/t/ft1*`, FT1's gate launcher folder, or any Git repository/worktree. Ready for **PASS**.
