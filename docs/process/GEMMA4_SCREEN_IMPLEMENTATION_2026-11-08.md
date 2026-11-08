# EXPLORATORY K2b Gemma 4 base screen build, 2026-11-08

BUILD ONLY, $0. Master Plan: "Tests: done and left", K2b. No scientific pass rule or predictions are supplied here. No Kaggle launch, Modal operation, model API request or weights download was performed. Claude reviews this build before any separately approved execution.

## Model loading and identity

Four screen-only handles are accepted: google/gemma-4/transformers/gemma-4-12b-it/2, google/gemma-4/transformers/gemma-4-e4b-it/1, google/gemma-4/transformers/gemma-4-e2b-it/1 and google/gemma-4/transformers/gemma-4-26b-a4b-it/1. The source family must match the model, and a positive version is mandatory. Gemma 4 training and adapter arguments are refused before loading. The launch record and manifest retain the versioned source, model, NF4 double quantization, float16 compute, one GPU, no training and no adapters.

Chosen loader: AutoModelForCausalLM, following the supplied Kaggle usage. The exact transformers 5.20.2 wheel was downloaded without dependencies, installed in a scratch venv outside the repo, and its source inspected. Its causal-LM mapping sends gemma4 to Gemma4ForConditionalGeneration and gemma4_unified to Gemma4UnifiedForConditionalGeneration. gemma4_text and gemma4_unified_text instead select their text-only causal classes. The full Gemma4Model constructs vision/audio towers when those subconfigs are present. Unified has direct multimodal embedding components, including audio waveform projection without a separate audio tower. This loader does not deliberately remove multimodal components. Actual concrete class and memory consumption depend on the mounted config and are recorded as loaded_class.

The installed Kaggle CLI's version-download command offers only whole-version downloads; no individual-file flag. Its read-only file listing returned HTTP 404. No snapshot was downloaded. Candidate config, generation config and templates remain unverified until qualification. Claude's review added scripts/k2b_cpu_smoke.py: it executes the real, non-dry notebook path on CPU with a tiny random Gemma 4 under the pinned transformers 5.20.2, torch 2.11.0 and the retained 31B template, a stand-in tokenizer and scripted replies forced through the real generate loop. It needs torch, so it is outside the fast set. It found the empty long-context filler and confirmed stop, decode and history replay. It does not establish real tokenizer behaviour, NF4 loading, GPU fit or model quality.

## Format and sampling

Gemma 3 retains system folding, its end token and skip_special_tokens=True decoding. Gemma 4 sends native system/history messages with add_generation_prompt=True and no enable_thinking override. The retained 31B reference template is copied byte-for-byte into gemma4-31b-reference.jinja so archive exclusions do not remove it. Tests render a native system prefix and the served empty thought-channel suffix. Qualification records the candidate template, SHA256, equality comparison with this reference, rendered probe prompts and input IDs. Equality is measured, never presumed.

Gemma 4 requires <turn|> to map to a known ID, round-trip to the literal, and encode atomically before generation. No token number is assumed. Its decoding uses skip_special_tokens=False and omits one terminal stop token, matching modal_backend.py's vLLM text: 0 of 355 retained L2 replies contain <turn|>, while Transformers output ids include it. Keeping it would feed a doubled turn end back through the history. output_ids stay retained verbatim. Other special tokens and any empty thought channel are preserved, with no cleanup or parser change; the audit counts replies containing special tokens without relabeling any episode (1 of 355 at 31B contained one).

K2 W/U sampling stays do_sample=True, temperature=1.0, top_p=1.0, with top_k inherited from the mounted generation config, exactly as the Gemma 3 notebook. The L2 shard sets temperature=1.0, top_k=64, top_p=0.95. Evidence: results/2026-11-08 v0.24.79 gemma4-31b-none r1 step4 l2/app-logs.txt line 97 reports these resolved model defaults. Seed 248017 plus request sequence matches modal_backend.Backend. The subset and added U cells have a different request order from the full 31B run, so individual case seeds are not paired. Full resolved generation config is retained. Transformers sampling and seed RNG are not equivalent to vLLM even with these numeric values; other model generation defaults remain candidate-specific.

The screen uses Transformers + NF4/float16; the 31B organism used vLLM + bf16. Small models, quantization, kernels, model defaults and RNG can all differ. U has no 31B base comparator: L2 base ran W and knowledge only.

## Shards and qualification

K2 base W/U reuse core.run unchanged, 16 cells each, with no acquisition probes. L2 is one 48-cell base/manager shard: 12 W with Compliance Director stop, 12 lawful U without stop, 24 knowledge on both twins. It reuses l2.cases, l2.rewrite, the unchanged knowledge rewrite, L2 parser, l1.action_episode and 1024-token cap. It has no Modal guard and continues after generation failures, counting them unknown. Summary reports group denominators, terminal counts, knowledge answers and unknowns separately. L2 source and case assets are hash-validated; exploratory assets survive the launcher archive's results/docs exclusions.

Non-scientific qualification never calls core.run or uses battery case text. It runs READY, made-up catalog JSON with a native system message, a second turn with an assistant message in the history, and a neutral long-context memory probe, each capped at 256 output tokens. The target is 3518 input tokens, measured from native_tokens input_ids in retained 12B U events (62 requests); W peaked at 2829 (44 requests). Filler approaches the target from below; actual rendered IDs and length remain inspectable. Probes retain output IDs, native decoded reply, last token, turn-stop/cap flags, seconds and peak/total GPU memory. JSON parseability uses the existing first-JSON-span scan on the native reply as a diagnostic; it does not score a case.

Derived GPU-hours use (3 loads + (32*12 + 24*12 + 24) * long-context request seconds)/3600 for K2 W/U plus L2. This extrapolation excludes installation/other overhead and is no upper bound. Fit, performance, multimodal loading, long-context inference stability and all actual candidate renders remain unverified on Kaggle, especially 51.6 GB 26B-A4B on one T4.

The CPU format audit reports native turn stops, cap hits, channel/turn tokens, leading stray thought, malformed episodes and generation failures. It never changes a label.

## Commands after review

Use a clean checkout and a reviewed full SHA on origin/main. Every command below is an offline plan. Removing --plan requires separate execution authorization.

```powershell
$screenCommit = '<REVIEWED_FULL_SHA_ON_ORIGIN_MAIN>'
$screenState = 'C:/k2b-stage' # short path avoids Windows extraction path limits
python -m exploratory.k2_kaggle.launch stage-repo --commit $screenCommit --owner metaphysika --state $screenState --plan
$candidates = @{
  'gemma-4-12b-it' = 'google/gemma-4/transformers/gemma-4-12b-it/2'
  'gemma-4-e4b-it' = 'google/gemma-4/transformers/gemma-4-e4b-it/1'
  'gemma-4-e2b-it' = 'google/gemma-4/transformers/gemma-4-e2b-it/1'
  'gemma-4-26b-a4b-it' = 'google/gemma-4/transformers/gemma-4-26b-a4b-it/1'
}
foreach ($model in $candidates.Keys) {
  python -m exploratory.k2_kaggle.launch push --base-screen --mode qualify --model $model --model-source $candidates[$model] --commit $screenCommit --owner metaphysika --state $screenState --plan
  foreach ($kind in @('W','U')) {
    python -m exploratory.k2_kaggle.launch push --base-screen --mode evaluate --shard-arm base --shard-kind $kind --model $model --model-source $candidates[$model] --commit $screenCommit --owner metaphysika --state $screenState --plan
  }
  python -m exploratory.k2_kaggle.launch push --base-screen --screen-battery l2 --mode evaluate --shard-arm base --model $model --model-source $candidates[$model] --commit $screenCommit --owner metaphysika --state $screenState --plan
}
python -m exploratory.k2_kaggle.screen '<SHARD_FOLDER>/events.jsonl'
```

Inspect qualification before authorizing scientific shards. No execution or competence claim follows from an offline build.

Offline --plan also accepts an exact unmerged review commit; actual execution still requires ancestry on origin/main. This permits inspection of the PR notebook without staging older main code.

Inspected wheel SHA256: `7ae75dbc1fb3922aff1b6c97b9e5479d6cf26fd86a8866bfb71324190479f807`. Reference template SHA256: `ae53464bf3be25802b3a5b37def7fd89667067d7577049b3b2d74c4d8de4c6d4`.

## Offline validation

`python -X utf8 scripts/run_fast_checks.py`: Ran 546 tests in 133.492s; OK. All scripted scenarios completed; {"set": "fast", "elapsed_seconds": 133.999}. Final focused K2b tests: Ran 7 tests in 1.734s; OK. These are local checks, not hosted CI or GPU qualification.

Offline staging and all 16 candidate/mode plans passed at 9d61e891c54adf0b80c0b366c553f4b0abc74dc7 using `--state C:/k2b-plan-9d61e891`. The default deep Windows worktree state path failed extraction on a long retained study path; use the short state path in the commands above. No Kaggle command was executed.
