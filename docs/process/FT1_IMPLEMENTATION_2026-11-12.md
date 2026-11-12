# FT1 implementation (2026-11-12)

EXPLORATORY offline build against main dcac4037, implementing the adopted
revision-2 design in FT1_PRERUN_DRAFT_2026-11-12.md, sections 2â€“8 and 10.1.
No run is approved. Frozen sources and repository results are unchanged.
No sealed output has been generated.

## Built

The exploratory/ft1 package contains deterministic compact accounts-office
record generators for five arms, refusal-only and neutral controls, action-only
histories, whole-line restatement matching, per-record token tables and hashes,
a separate 40-item acquisition partition, knowledge and format scorers,
versioned freight scorer additions, an explicit sealed-generation command,
a 12-training/13-model evaluation plan, injected FT0b training and evaluation
functions, and synthetic threshold analysis.

The training generator produces 2,000 records per arm. Arms 2, 2u and 3 share
prompts, histories and actions. Matching refuses records or datasets that miss
the specified gates. The actual chat-template prompt and end-of-turn training
counts are measured with the local tokenizer at data-write time. Stub counts
in unit tests establish generator logic only.

## Offline commands

From the repository root:

    python -m unittest tests.test_ft1_offline -v
    python scripts/run_fast_checks.py
    python -m exploratory.ft1.plan --plan
    python -m exploratory.ft1.data --tokenizer LOCAL_GEMMA_TOKENIZER --output NEW_DATA_DIRECTORY

The tokenizer path must point to the same locally mounted Gemma 3 12B IT
tokenizer used by training. Loading is local_files_only, trust_remote_code=False.
No automatic download is implemented. The data-write command rechecks every
record and the aggregate matching gate, then writes the manifest. Retain any
failure; adjust templates prospectively before freezing rather than truncating.

Sealed generation is separate and must be invoked explicitly in the authorized
private environment:

    python -m exploratory.ft1.sealed --private-seed-file PRIVATE_FILE --output NEW_PRIVATE_FILE

Do not send that file or its contents to Claude or Fable. The command prints only
count, SHA-256 and counts by type. No seed is embedded in source or the public
manifest. Astra's blind labeling and the freeze remain later steps.

The Python entry points scoring.acquisition(records, replies) and
scoring.format_check(eight_raw_reply_lists) consume saved or scripted inputs.
The latter returns only parse counts and own-null finishes; it accepts no
scored conduct records. Use four W and four U development-exposed K2 episodes
per adapter. An adapter needs both checks and no more than 25 skipped training
updates to enter comparisons.

training.train accepts a locally prepared NF4 LoRA model, tokenizer, records,
arm, seed and event-retention callback. It is an injected mode, not a launch
command. It uses FT0b tables and chunked loss, 250 steps, accumulation eight,
shared seed-index ordering, AdamW and detached action/reason loss sums.
evaluation.episode likewise accepts an injected generator and token counter.
No backend or launcher is provided. plan --plan never starts either function.

analysis.evaluate consumes per-seed rates after eligibility checks.
analysis.bounds consumes known/unknown/planned count triples and enumerates
integer resolutions. P1â€“P5 are reported separately. Mechanical rates are
reported beside P1; interpreting a gain mainly caused by formatting still
requires review of separate counts. Known violations remain known.

## Choices made

- Standard-library templates and two sentence variants; no model-authored data.
- Seeds 247056, 247057 and 247058; index ordering is identical across arms.
- Whole-line prefixes in fixed field order for arm 2, choosing the closest
  trained-token length. No line repetition or partial-line padding.
- Refuse an existing output path and any path with a results component.
- Reason-value token masks use exact tokenizer offsets; ambiguous boundary
  tokens cause refusal.
- Reuse the existing world and replay, extending their output in new files.
- Keep outside-sphere permission a scoring constraint, as software permission
  alone cannot establish substantive authority.
- Use an exact small synthetic unknown enumerator rather than approximate
  confidence bounds.

## Open risks and remaining readiness work

This is not an exact-commit readiness verdict. Actual Gemma token matching,
reason-boundary offsets, GPU execution and loss accounting have not been
validated here. The injected trainer requires caller-side NF4/LoRA preparation
and approval binding; there is no Kaggle training notebook integration or
launch path. Seed initialization must precede adapter creation in that caller.
The complete FT1 evaluation aggregation, missing-cell bounds and mechanical
attribution still need an evidence-level integration pass. Unknown enumeration
can be prohibitively large and currently treats count dimensions independently.

The compact training examples are highly templated. The held-out acquisition
partition uses fresh identifiers with the same template family. It is an
acquisition check, not independent evidence of generalization. Case generation,
blind labels, freeze, throughput measurement, exact-commit Fable review and
owner execution approval remain outstanding.

## Validation

Ten FT1 unit tests pass, covering 10,000 records, matching, refusal on limits,
shared inputs, restatement provenance, acquisition isolation, subject exclusion,
knowledge replies, format checks, scripted scorer effects and synthetic
prediction/unknown/noise rules. Fast checks are run unchanged in a temporary
archive of the checkout to keep scripted output out of repository results.
No model, training, Kaggle, Modal or API call was made.

Fast checks: PASS, 645 tests (one skip) plus all scripted scenarios, 101.164 s,
in temporary checkout C:/Users/lahn0/AppData/Local/Temp/ft1-offline-checks-wkg7pjg3.
The first attempt omitted retained fixtures and failed; restoring the archived
fixtures made the unchanged check runner pass. Original repository results
were not modified. FT1 tests: 10 passed, final run 1.728 s.
