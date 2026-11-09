# Fable review of the CI clock fix (2026-11-09)

Verbatim, at commit `fcf6a854`. Advisory.

---

# Fable review: PR 128, CI clock isolation for Study D rehearsals

Reviewed commit `fcf6a85428128b70e41d23e4015b5f266d7b14db` against `origin/main`, checkout `C:/Users/lahn0/T3/wt-128`. Read-only. Hosted run 42548566656 ("Harness checks") confirmed via `gh run view`: head `fcf6a854`, conclusion success.

## Verdict

**GO after one small must-fix** (a notebook sentence). Everything else checks out. One non-blocking hardening suggestion.

## What the PR does, in plain terms

The frozen Study D policy files contain `window()`, which reads the real clock and refuses to run after 2026-11-09 01:00 UTC. CI rehearsals of the finished study call that function through hash-pinned scripts that cannot be edited. The PR leaves all of that alone and instead runs the three rehearsal commands under `libfaketime`, which lies to those processes about the date. The fake clock starts at 2026-10-20 12:00:00 UTC each time and ticks forward normally (the `@` prefix in `FAKETIME` means "start here and keep running"). Monotonic time is also faked, by a constant offset, so elapsed-time arithmetic is unchanged.

Changed files: `.github/workflows/tests.yml`, `LAB_NOTEBOOK.md`, new `tests/study_d_frozen_clock.py`, and two test files. Nothing else.

## 1. Frozen material untouched; real guard still refuses

- `git diff --stat origin/main fcf6a854 -- formation studies results scripts` is empty. No pinned script, policy, manifest, asset or evidence file changed.
- New test `test_real_window_still_rejects_expired_launches` loads the actual `formation/study_d_gemma_stages_v02428.py` and `_v02429.py`, checks that 2026-10-20 passes and that 2026-11-10 raises `ValueError('finite launch window closed...')`. It passes explicit `now` values, so it does not depend on the real or fake clock and will keep meaning the same thing on any date. Good.

## 2. Can this mask a real failure?

**Reach into production or a real launch: no.** The fake clock is set only in the `env` dict handed to the child `subprocess.run` inside `run_frozen`; `LD_PRELOAD` is never exported to the job shell or to any other step. The helper lives under `tests/` and nothing in `formation/` or the launch scripts imports it. A real Modal or Kaggle launch would still need credentials and the owner's exact-commit approval regardless of what the clock says.

**Silent skip in the job meant to run them: no.** `tests.yml` sets `TAA_REQUIRE_FAKETIME: "1"` at the job level. With that set, a missing `libfaketime` raises `AssertionError` instead of `SkipTest`: the CLI wrapper exits non-zero and the unit tests fail rather than skip. The helper also runs a probe before every use: a `python -I` child spawning another `python -I` child must see 2026-10-20 and must see monotonic time advance by 0.03–5 s across a 0.05 s sleep. If the preload does not reach the isolated grandchild, or monotonic time is frozen or broken (the first version's OSError), the step fails loudly.

**Nightly: same path.** `full-suite.yml` calls `tests.yml` via `workflow_call`. The apt install step and the job-level env variable are inside the called job, so the nightly inherits both. The `Unit tests` discovery step (`python -m unittest discover tests -v`, non-PR only) runs in that same job, so the three affected tests execute under faketime there too, not skipped. `scripts/run_fast_checks.py` does not include the `test_study_d_virtue_*` files, so the fast tier is unchanged. On a developer Linux machine without libfaketime, the three tests skip with a visible message (disclosed in the notebook); on Windows they already could not run (`resource` module, CRLF hashes).

**Peak-RSS and timing assertions: not weakened.** `peak_rss_bytes` comes from `resource.getrusage(...).ru_maxrss`, kernel memory accounting that libfaketime does not touch. The only test assertions on the report are `peak_rss_bytes < controller_memory_limit_bytes * 0.5` (both test files); nothing asserts on `seconds`. The pinned scripts' 90 s and 120 s deadlines use `time.monotonic()` differences, and a constant offset at rate 1 leaves differences unchanged. The hosted log reportedly shows `peak_rss_bytes` reported, consistent with the rehearsals actually running.

**Future dates: keeps passing.** The fake clock always starts at 2026-10-20 12:00 UTC. The virtue window is 2026-10-19 01:00 to 2026-11-09 01:00 and the smoke window ends 2026-10-26 01:00; a CI run lasts minutes, so it stays inside both forever. The only future breakages are an Ubuntu image without `libfaketime` in apt or a moved library path, and both fail loudly under `TAA_REQUIRE_FAKETIME`, not silently.

**Scope filter.** `tests/study_d_frozen_clock.py` does not match `tests/test_study_d*`, so `ci_scope.py` treats it as unknown and selects all groups; `.github/workflows/**` is also listed. The PR run confirms the Harness `test` job ran and passed.

**Import style.** `from tests.study_d_frozen_clock import run_frozen` relies on `tests` being a namespace package with the repo root on `sys.path`; 55 existing test files already do this, so it is the established pattern.

## 3. Notebook note

Mostly accurate: "ticking clock at 2026-10-20 12:00:00 UTC only for the historical rehearsal subprocesses, including python -I children" (correct), "first version left monotonic time real and failed ... time.sleep raised OSError" (matches the commit history), "skips only the three affected tests" (one in v02428, two in v02429: correct), "the Harness test job requires it" (correct), "No frozen file differs from main" (verified).

**Must-fix (notebook only):** the entry records the failed first-version run (job 128938034727, run 42548267388, head 85fb412a) and ends with "Stopped for review under the requested design-failure rule," but never records that the current head passed. As written, the lab record says the PR is stopped when it is actually green. Add one sentence to the same entry, roughly: "Final version at fcf6a854 (monotonic time faked consistently) passed hosted Harness checks run 42548566656; rehearsals executed rather than skipped and peak_rss_bytes was reported." Merge after that.

## Non-blocking suggestion

`tests/study_d_frozen_clock.py` will fake the clock for any command it is given. A short allowlist (only the three `scripts/study_d_gemma_*_ci_v0242[89].py` rehearsal scripts) would make it useless as a future shortcut around `window()` on anything else, which is the one thing that guard exists to prevent. Not required for this merge; the risk today is low because real launches have independent gates.
