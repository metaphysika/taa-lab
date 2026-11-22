# Track B P7 Review (Neon / Gemini) — PR #198

- **PR:** https://github.com/metaphysika/taa-lab/pull/198 (`b1b2-trackb-p7-launcher`)
- **Base / Head:** `origin/main` (`451ace15bcbf299257c2a48ec48401eba25d3009`) ... `4bc105679df58f2379e49fc08a4d0ca51a64ab27`
- **Verdict:** **FIX NEEDED** (3 MUST-FIX blockers: `M1`, `M2`, `M3`; 6 SHOULD-FIX items: `S1`–`S6`)
- **Spec references:** `docs/process/TRACK_B_BUILD_LOOP_SPEC_2026-11-21.md` (§1, §2 P7, A6.4, A9, A10.16–21, A10.34–35); `docs/process/TRACK_B_WEAKNESS_MALICE_DESIGN_2026-11-21.md` (§2.1, §5, §6); P6 `SCHEMA.md` & `analysis.py` from `origin/b1b2-trackb-p6-analysis` (`b53d5c5e9b83315f92a48d659b4df2ec64067c08`).

---

## 1. Evidence & Diff Scope

### Changed files (`git diff --name-status origin/main...HEAD`)
- `A exploratory/track_b/launch.py` (283 lines)
- `A exploratory/track_b/stage_b0a.py` (224 lines)
- `A tests/test_track_b_launch.py` (263 lines)

### Test edits (`git diff origin/main...HEAD -- tests/`)
- Only the single new test file `tests/test_track_b_launch.py` (14 unit tests). No existing test or pinned fixture was modified, loosened, skipped, or deleted.
- Zero shared modules (`taa/`, `formation/`, `scripts/`, `.github/`, `exploratory/ft1/`, `exploratory/k2_kaggle/`, `exploratory/step4_harness/`), `AGENTS.md`, `CLAUDE.md`, `LAB_NOTEBOOK.md`, or `results/` were modified.

---

## 2. MUST-FIX Blockers

### M1 — Cooperative `DeadlineExceeded` (and fatal generation errors) are silently swallowed, causing truncated runs to log `"complete"` and potentially pass B0a
- **Files:** `exploratory/track_b/stage_b0a.py:124-125, 154-160, 186-201` (interacting with `exploratory/step4_harness/l1.py:107-108` and `exploratory/ft1/runner.py:12`)
- **Finding:**
  - `mounted_run()` creates `check = deadline(launch.KAGGLE_TIMEOUT_SECONDS - 300)` (`stage_b0a.py:211`), which raises `DeadlineExceeded` (a subclass of `RuntimeError` → `Exception`).
  - `prepare()` passes `check` into `generation_functions(model, tokenizer, check)`, which invokes `check()` before every generation call (`evaluate_runner.py:380`).
  - Both `l1.action_episode()` (`l1.py:107: except Exception as exc:`) and `stage_b0a.detached_row()` (`stage_b0a.py:156: except Exception as exc:`) catch `Exception` without re-raising `DeadlineExceeded`.
  - `stage_b0a.run()` does not check for `DeadlineExceeded` between cases and never stops when the deadline fires.
  - **Independent probe evidence (B5 & B6):**
    - When `DeadlineExceeded` fired on MB episode #5, `run()` did **not** stop: it ran 68 more iterations (20 remaining MB + 48 PB), wrote 68 fake `DeadlineExceeded` rows, and appended `{"event": "complete", "detail": {"mb_episodes": 24, "pb_detached": 48}}` to `events.jsonl`, exiting normally.
    - When `DeadlineExceeded` fired on PB detached item #47 (the last 2 items), `run()` logged `"complete"` in `events.jsonl` and P6 evaluated the snapshot as **46/48 correct + 2 unknowns (≤ 4)** → `"verdict": "passed"` on a deadline-aborted run whose last 2 items were never attempted.
  - By contrast, both K2 (`exploratory/k2_kaggle/core.py:125-130, 174`) and FT1 (`exploratory/ft1/evaluation.py:19-22`, `evaluate_runner.py:318`) propagate `DeadlineExceeded` (and non-`MechanicalUnknown` errors) immediately so an interrupted run stops and logs failure rather than `"complete"`.
- **Fix:**
  - In `call()` inside `stage_b0a.run()`, catch `DeadlineExceeded` (from `exploratory.ft1.runner` and `exploratory.k2_kaggle.core`), record a `deadline_hit = True` flag, and re-raise so `l1.action_episode()` still builds and returns the interrupted episode's partial row (preserving any already-executed effects).
  - In `detached_row()`, re-raise `DeadlineExceeded` (or let `call()` set `deadline_hit` and break immediately).
  - In `stage_b0a.run()`, after appending the interrupted row (if any), check `if deadline_hit: raise DeadlineExceeded(...)` so `run()` stops immediately, logs `event="failed"` in `events.jsonl`, and never iterates through remaining unattempted cases or logs `"complete"`.
  - Add a unit test exercising `DeadlineExceeded` mid-MB and mid-PB to verify early stop, retained partial row/effects, and `"failed"` (not `"complete"`) terminal event.

### M2 — `mounted_run()` hardcodes `/kaggle/input/datasets/<adapter_dataset_id>`, breaking on Kaggle's `/kaggle/input/<slug>/` mount convention
- **Files:** `exploratory/track_b/stage_b0a.py:213-218`
- **Finding:**
  - `mounted_run()` hardcodes `dataset = Path("/kaggle/input/datasets") / config["adapter_dataset_id"]`.
  - As documented in `exploratory/ft1/mounts.py:3-4`, Kaggle mounts datasets at **both** `/kaggle/input/<slug>/` and `/kaggle/input/datasets/<owner>/<slug>/` — and FT1 job (a) attempt 1 failed specifically because of this mount-path variation.
  - While `stage_b0a.py` already handles mount-path variation for the base model via `core.resolve_model_path()` and for wheels via `core.install_wheels()`, it does not do so for the adapter dataset.
  - Because `launch.push()` permanently creates `submitted-<bundle_sha256>` to prevent duplicate pushes, hitting `/kaggle/input/<slug>/` on Kaggle would fail immediately with `ValueError("missing snapshot folder")` and burn the receipt/launch.
- **Fix:**
  - Add a small resolver (e.g. `resolve_adapter(adapter_dataset_id, root=Path("/kaggle/input"))`) that checks both `root / "datasets" / owner / slug` and `root / slug` (failing closed if neither exists or both exist, and preserving the existing ambiguity check when both `dataset/adapter_config.json` and `dataset/adapter` exist).
  - Keep the exact `core.digest(core.inventory(adapter)) == config["adapter_sha256"]` check in `cpu_precheck()`.
  - Add unit tests covering both `/kaggle/input/datasets/<owner>/<slug>` and `/kaggle/input/<slug>` (both nested `adapter/` and root `adapter_config.json`), plus missing and ambiguous mount layouts.

### M3 — `staging_root()` allows `TRACK_B_STAGING_ROOT="C:/t"` (permitting writes into `C:/t/ft1-*`) and allows blank `TRACK_B_STAGING_ROOT=""` (resolving to the repo root)
- **Files:** `exploratory/track_b/launch.py:70-77, 170-173`
- **Finding:**
  - `staging_root()` checks `if path.is_relative_to(reserved): parts = path.relative_to(reserved).parts; if parts and parts[0].lower().startswith("ft1"): raise ValueError(...)`.
  - **Independent probe evidence:**
    - `TRACK_B_STAGING_ROOT="C:/t"` yields `parts == ()`, so `staging_root()` returns `C:\t`. Because `safe_name("ft1-run")` passes `[a-z0-9][a-z0-9-]{0,60}`, `stage("ft1-run", ...)` writes directly into `C:\t\ft1-run`, breaching the FT1 staging boundary (`C:/t/ft1*`).
    - `TRACK_B_STAGING_ROOT=""` resolves `Path("").resolve()` to the current working directory (the git repository root), staging bundles inside the repo instead of failing closed.
- **Fix:**
  - In `staging_root()`:
    - Read `override = os.environ.get("TRACK_B_STAGING_ROOT")`; if `override is not None` and not `override.strip()`, raise `ValueError("TRACK_B_STAGING_ROOT cannot be blank")`.
    - Reject `path == reserved` (i.e. `C:/t` itself, `not parts`) as well as any `parts[0].lower().startswith("ft1")`.
  - In `safe_name()`: also reject names starting with `"ft1"` as defense in depth.
  - Add unit tests for `TRACK_B_STAGING_ROOT="C:/t"` and `TRACK_B_STAGING_ROOT=""`.

---

## 3. SHOULD-FIX Items

### S1 — CLI `--status-command` uses `nargs="+"`, rejecting any status command that takes `-` flags, and lacks a subprocess timeout
- **Files:** `exploratory/track_b/launch.py:258-269`
- **Finding:**
  - With `nargs="+"`, `argparse` refuses any token starting with `-` inside `--status-command` (confirmed in probe: `--status-command python -c ...` fails with `error: unrecognized arguments: -c ...`). Any realistic command using flags (`python -m ...`, `kaggle kernels list --mine`, `pwsh -File ...`) fails CLI parsing unless wrapped in a no-arg wrapper script.
  - `subprocess.check_output(args.status_command)` has no `timeout=`, so a stalled status command would hang indefinitely while holding `.push-lock`.
- **Fix:** Use `nargs=argparse.REMAINDER` (with a check that it is non-empty and help text noting it goes last) or accept a JSON argv array, and pass `timeout=60` (or a named constant) to `subprocess.check_output`.

### S2 — `cpu_precheck()` assumes `adapter` is a `Path`; redundant `import os` in `mounted_run()`
- **Files:** `exploratory/track_b/stage_b0a.py:60-82, 208`
- **Finding:** Line 80 evaluates `adapter / "adapter_model.safetensors"`, which raises `TypeError` if a caller passes a `str` path (whereas line 62 `core.inventory(adapter)` accepts `str`). Line 208 repeats `import os` (already imported at line 4).
- **Fix:** Add `adapter = Path(adapter)` at the start of `cpu_precheck()` and remove line 208.

### S3 — `lawful_success` on mechanical U episodes is slightly more optimistic than `crossing_analysis.classify()`
- **Files:** `exploratory/track_b/stage_b0a.py:134-136`
- **Finding:** On a mechanical U episode (`terminal_status != "agent_stop"`), `episode_row()` sets `lawful_success = True` if `lawful_primary_done(case, result)` and `not result["score"]["flags"]["over_refusal"]`. While P6's `SCHEMA.md` permits `true or null` on mechanical U rows, `crossing_analysis.classify()` returns `'unknown'` whenever `not stopped` and `not over_refusal` (because the episode did not finish normally and could still have over-refused on a later turn).
- **Fix:** Either conservatively leave `lawful = None` on all mechanical U rows to match `crossing_analysis.classify()`, or document the intentional divergence in the PR/code comment.

### S4 — Guard Kaggle's 50-character kernel slug/title limit and leading-zero seeds
- **Files:** `exploratory/track_b/launch.py:84, 134`
- **Finding:** `exploratory/k2_kaggle/launch.py:178` documents that Kaggle rejects kernel titles > 50 chars (HTTP 400). Real 6-digit FT1 seeds produce 32–33 char slugs, so normal inputs pass, but `([0-9]+)` accepts arbitrarily long or zero-padded seeds.
- **Fix:** Use `([1-9][0-9]*)` in the dataset regex and assert `len(slug) <= 50` in `bundle()`.

### S5 — Crash-durability `fsync` on JSONL appends
- **Files:** `exploratory/track_b/stage_b0a.py:119-121`
- **Finding:** `append()` flushes on close without `os.fsync(stream.fileno())`, unlike `exploratory/ft1/evaluate_runner.py:446-447`.
- **Fix:** Call `stream.flush(); os.fsync(stream.fileno())` inside `append()`.

### S6 — Constant `GENERATION_SEED` across all turns and items
- **Files:** `exploratory/track_b/stage_b0a.py:16, 186-188`
- **Finding:** Every episode turn and detached item receives the identical `GENERATION_SEED = 448017`. Because `generation_functions` runs greedy decoding (`do_sample=False`), this is deterministic and benign today, though per-case/per-turn seed progression (as in FT1) is cleaner provenance.

---

## 4. Assessment of Status Command Fail-Closed Behavior

Sol noted that a live launch requires *"a verified account-wide Kaggle status command."*

- **When the status command is unavailable, fails, or returns malformed/unrecognized output: YES, the launcher FAILS CLOSED (refuses with zero push calls).**
  - Omitting `--status-command` exits nonzero in `argparse` (`launch.py:262-263`) before `push()` runs.
  - Missing binary (`FileNotFoundError`), nonzero exit status (`CalledProcessError`), invalid JSON (`JSONDecodeError`), non-list JSON (`ValueError`), non-string entries, or any state string outside lowercase `{"queued", "preparing", "running", "complete", "error", "cancelled", "canceled"}` (`ValueError`) all abort inside `push()` before `write_files(submission, ...)` and before `backend(submission)`, cleaning up `.push-lock`.
- **Two operational caveats:**
  1. **S1 (`nargs="+"`)** prevents passing commands that include `-` flags directly on the CLI (see S1 above).
  2. **Exit-0 empty-list risk (inherent to external command injection):** If a caller supplies a misconfigured command that exits 0 and prints `[]` despite failing to query the whole account (e.g., wrong scope or swallowed API error), `launch.py` treats `[]` as 0 active sessions and allows the push. Thus the stage thread must verify the real account-wide status command (and ensure it exits nonzero on any auth/API error) before any approved launch.

---

## 5. Spec & Requirement Verification Matrix

| Requirement | Status | Notes / Evidence |
|---|---|---|
| Plan-only default | PASS | CLI without `--push` only calls `stage()`; staged `trackb.ipynb` sets `RECEIPT = None` and only prints `CONFIG`. |
| Receipt has exact 9 A10.34 fields + exact commit/adapter/bundle/UTC binding | PASS | `RECEIPT_FIELDS` matches A10.34 verbatim; `validate_receipt` rejects extra/missing fields, bool `schema_version`, blank approval fields, wrong commit/stage/adapter/bundle hash, and non-UTC timestamps; `read_json` rejects duplicate JSON keys. |
| `KAGGLE_OWNER` must be exact bytes `b"trackb"` | PASS | Checked pre-lock (`launch.py:206`) and again post-status inside lock (`launch.py:235`); rejects absent, symlink, dir, whitespace/newline, uppercase, and wrong text. |
| ≥2 `queued`/`preparing`/`running` sessions refuses; injectable `status` | PASS | Confirmed in Probe (a) across `running`, `preparing`, `queued` combinations; 1 active (`["queued", "complete"]`) permitted; unknown states and exceptions fail closed. |
| `TRACK_B_STAGING_ROOT` override + FT1 separation (`C:/t/ft1*` untouched) | **FAIL (M3)** | `C:/t/ft1*` refused, FT1 files untouched, `sealed.py` absent from `SOURCE_PATHS` and archive — **but** `TRACK_B_STAGING_ROOT="C:/t"` + `name="ft1-*"` writes into `C:/t/ft1-*`, and `TRACK_B_STAGING_ROOT=""` resolves to CWD (repo root). |
| B0a loads ONE given adapter id | PASS | Regex allows one eligible-arm FT1 dataset (`2`, `2u`, `1` at `0449a230200c`); `dataset_sources` has `[adapter_dataset_id, "metaphysika/k2-wheels"]`. |
| CPU pre-check of nonzero LoRA B & trainable set before GPU work | PASS | `prepare()` runs `cpu_precheck()` (`init_empty_weights` skeleton + P4 `_check_adapter_config` + CPU `safetensors.torch.load_file` + `check_adapter_tensors`) before `torch.cuda.device_count()` and `core.load_model()`. |
| MB on stored rewritten cases via `crossing.replay` / `l1.action_episode`, never `l2.rewrite` | PASS | `stage_b0a.py` calls `l1.action_episode(case, generate, stop=False)`; `l2` is never imported or called (verified in Probe (b)). |
| PB detached items as single-turn prompts via `render_detached_prompt` and same generation settings | PASS | `detached_row()` renders via `batteries.render_detached_prompt(item)` and calls the same `call(system, history, CAP)` (`CAP=1024`, `GENERATION_SEED=448017`). |
| Outputs match P6 `SCHEMA.md` and parse through P6 analyzer | PASS (with **M1**) | Verified on passing, headroom-failed, instrument-failed, and mixed mechanical snapshots in Probe (b). However, **M1** breaks deadline-interrupted provenance/completeness. |
| Kaggle mount & deadline execution readiness | **FAIL (M1, M2)** | Real isolated archive imports and runs cleanly (`ISO_RUN_OK 24 48 74`, 0 sealed hits), but `mounted_run()` hardcodes `/kaggle/input/datasets/...` (**M2**) and swallows `DeadlineExceeded` (**M1**). |
| Zero paths to real Kaggle push without receipt + owner flag | PASS | Static AST audit of `launch.py` & `stage_b0a.py` shows only 1 `kaggle` invocation (`kaggle_push`, `launch.py:247`), reachable only through `push()` after `require_owner` (×2), `validate_receipt`, exact git archive match, `.push-lock`, `status()`, and fresh `submitted-<hash>` creation. |

---

## 6. Checked / Not Checked

### Checked
- Checked out exact head `4bc105679df58f2379e49fc08a4d0ca51a64ab27` and inspected the entire diff (`launch.py`, `stage_b0a.py`, `tests/test_track_b_launch.py`) plus `git diff origin/main...HEAD -- tests/` and `git diff --check`.
- Re-ran `python scripts/agent_safe_imports.py -m unittest tests.test_track_b_launch -v`: **14/14 passed** (0.576s).
- **Independent Probe (a) (fake backend refusals):** Verified zero backend calls on missing receipt, wrong commit, missing/wrong/dir `KAGGLE_OWNER` (`""`, `ft1`, `trackb\n`, `trackb\r\n`, ` trackb`, `trackb `, `TRACKB`), 2 active sessions (`running+running`, `queued+running`, `queued+preparing`, `queued+queued`, `preparing+preparing`, `running+preparing+complete`), unknown/mixed-case/non-string states, status raising `FileNotFoundError`/`CalledProcessError`, and duplicate submission (`FileExistsError`).
- **Independent Probe (b) (scripted B0a outputs through P6 `origin/b1b2-trackb-p6-analysis:exploratory/track_b/analysis.py`):**
  - Passing snapshot (0/16 W wrongful, 8/8 U lawful, 0 mechanical, 48/48 PB): P6 returned `verdict="passed"`.
  - Instrument-failed snapshot (39/48 PB): P6 returned `verdict="instrument failed"`.
  - Headroom-failed snapshot (4/16 W wrongful): P6 returned `verdict="headroom failed"`.
  - Mixed mechanical snapshot (1 W post-act failure, 1 U post-primary failure, 1 U pre-primary failure): P6 parsed cleanly and returned `mechanical=3`, `wrongful.yes=1`, `lawful.yes=7`, `lawful.unknown=1`, `verdict="headroom failed"`.
  - Confirmed `exploratory.step4_harness.l2` is never imported or called.
  - Deadline probes (B5 & B6) exposed **M1**.
- **Independent Probe (c) (push-path & CLI audit):** AST audit of all `subprocess` calls in `launch.py` and `stage_b0a.py`; CLI checks with `kaggle_push` mocked confirmed fail-closed on missing `--receipt`, missing `--status-command`, failing command, non-array JSON, invalid JSON, and missing binary (0 pushes), and exposed **S1** (`nargs="+"` rejecting `-c` flags).
- **Independent Probe (d) (real git archive isolation):** Verified `launch.source_at(HEAD)` is deterministic (704,207 bytes, 185 files, 0 `sealed` hits), submitted notebook is 940,775 bytes, and executing the extracted archive in `python -I` (without the repo on `sys.path`) successfully validated the receipt, loaded `batteries.DEV_DIR` from inside the extracted archive, and ran `stage_b0a.run()` to completion (`24` MB, `48` PB, `74` events).
- **Edge-case check on `staging_root()`** (without writing to `C:/t`) exposed **M3**.

### Not Checked
- Live Kaggle mounts, `kaggle` CLI execution, account-wide Kaggle status output, real Gemma 3 12B / PEFT / bitsandbytes / safetensors weight loading, and GPU generation (all prohibited offline).
- Full `scripts/run_fast_checks.py --agent-safe` suite (not re-run per A9.3 since Sol's final-head run log was provided and blockers were found on the piece itself).
