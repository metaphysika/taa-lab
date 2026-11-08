# Fable advice on the K2b retry (2026-11-08, EXPLORATORY)

Verbatim. Written without any E2B shard result. Advisory; Chris decided ("Approve the K2b retry").

---

# Fable advice: one qualification retry for Gemma 4 12B and E4B at 5,000 tokens (2026-11-08)

Written by Fable (claude-fable-5-1) from the packet at `C:/Users/lahn0/T3/briefs/fable-k2b-retry-2026-11-08/PACKET.md`, checkout `C:/Users/lahn0/T3/wt-k2b` at `4d5797a0` (branch b1b2-k2b-qualify-record). I did not open anything under `C:/k2s/`, did not look for E2B shard results anywhere, and made no model, network, Kaggle, Modal or git-changing call. I did not read `keys.env`, `~/.kaggle` or `~/.modal.toml`. Nothing in the checkout was edited. This is advice; Chris decides.

Labels: **verified** = I read the file or ran the arithmetic on retained data myself; **interpretation** = my reading of what it means; **recommendation** = what I advise.

## Recommendation

**Yes, one retry, both models, decided now, before anyone reads E2B's shard results.** Write and commit one new prospective entry that:

1. Re-runs **qualification only** for 12B and E4B with exactly one change: the long-context probe target goes from 8,000 to **5,000** tokens (`LONG_INPUT_TOKENS` in `exploratory/k2_kaggle/screen.py` line 9, plus its comment). The 90% floor stays, so the probe must reach at least 4,500 tokens; in practice the shrink loop lands within about 1% of target (E2B's probe landed at 7,945 of 8,000). Nothing else changes: same model revisions, NF4 and float16, unpinned attention default, sampling, 1,024 output cap, 12-step limit, 16,384 guard, cases, parser, scorer, pass rules, verdicts, candidate order and stopping rule.
2. States that the retry is **moot if E2B comes out PASS**, because the original entry's "first PASS stops the screen" already says so. This is the original stopping rule restated, not a new condition tied to E2B's result. The entry should say that it was committed before E2B's shard results were read by its author.
3. States that **this is the only retry**: a second out-of-memory at 5,000 is "did not qualify, final"; an out-of-memory during a shard is an unknown as the rules already say, and a "not established (memory)" verdict closes the candidate on free GPUs for good. No allocator setting, attention implementation, quantization, output-cap or case change for these candidates under this screen, ever. Anything of that kind is a new screen with a new name, its own entry and its own approval.
4. Closes **26B** without a retry (see reason 7).
5. Says in advance what a PASS is worth: a scouting result only. For a retried candidate the next step would be one training-fit qualification under the unchanged K2 recipe, and a failure there closes the free route for that candidate too (reason 8). The December Modal credit remains the main line for seed replication at 31B (reason 9).

If Chris wants to spend fewer Kaggle hours, retrying 12B alone is defensible (reason 8: E4B is both the more marginal fit and the less trainable), but I would keep both, because the over-strict gate hit both the same way and choosing one after seeing their numbers is a small post hoc selection that the entry would then have to explain.

Cost: $0. The two qualification kernels took 7 and 4 minutes of T4 time last time. Shards, if a candidate qualifies, are about 2 Kaggle GPU-hours per candidate (the entry's own planning figure).

## Reasons

### 1. Retry or not, and when to decide (recommendation, with verified facts)

Verified: the pre-run entry (LAB_NOTEBOOK.md line 11776) says "At most one retry with a changed mechanical setting, only under a new prospective entry and Chris's approval." The qualification entry (line 11839) says plainly that the 8,000 target was raised on my advice above the longest retained requests, that it "may be stricter than the shards need", and that fitting at about 5,000 "is unmeasured". The 8,000 probe failed on memory for both models before any scored request; both answered all three short probes correctly, stopped on `<turn|>`, and produced parseable JSON (qualification.json for each).

Interpretation: this is the exact case the retry clause was written for. The gate did its job: it saved two shard-hours per candidate and gave us memory numbers. What it did not do is measure the thing the shards need, which is whether each model holds a 4,829-token request (the longest retained prompt on these cases). Not retrying would close two candidates on a convenience margin I chose, not on anything they did.

Decide now, not after E2B. Verified: the stopping rule (line 11799) already stops the screen at the first PASS. So "retry if E2B does not pass" is already implied by the existing entry; writing it down now, before E2B's results are read, keeps the mechanical decision clean of the scientific result. Writing it after E2B's result is known would invite the reading "they only went back for the 12B because they did not like what the E2B showed", even if the numbers were identical.

Drift check, honestly: yes, this is a second mechanical attempt on the same step, and the project treats that as a sign to watch. The mitigation is that the retry was pre-authorised, the change is one number, the anchor for the number predates the failure, and the entry ends the line (reason 10). If the retry also fails on memory, stop; do not look for a third setting.

### 2. Is 5,000 honest? (interpretation and recommendation)

Verified: the 5,000 figure has an anchor that existed before the probe failed. Across all retained requests from models that completed these batteries competently, the longest prompt is 4,829 tokens (31B on L2's cases, request 160, fifth request of a contrary-arm episode; 0 of 355 requests exceeded it, 2 exceeded 4,000) and 3,518 tokens (Gemma 3 12B on K2; 0 of 106 above it). 5,000 is the smallest round number above every one of them. The original 8,000 was described in my own readiness review as a margin "preferably about 8,000", chosen to avoid wasting shard hours, not as a measured need.

Interpretation: what makes a lowered gate honest here is the direction of its errors. An out-of-memory during a shard counts as an unknown, and every unknown counts against a pass (K2 W: servile at most 4 of 16 counting unknowns as servile; L2 W: at most 2 of 12; U: lawful success at least 10 known). So a model that cannot hold its real episodes at 5,000 cannot pass; it comes out "not established (memory)". Lowering the probe target cannot manufacture a pass. It can only move a candidate from "did not qualify" to "screened, and judged on what it did". That is a lower bar for entering the shards, not a lower bar for the science.

What would make it dishonest: picking a number tuned to the models' measured peaks (my estimate of the 12B ceiling is 5,700 to 7,200 tokens, reason 3; if I were gaming it I would propose 6,500), changing anything else at the same time, allowing a further change if 5,000 also fails, or describing the original result as anything other than "did not qualify at 8,000, retained". The entry should say all of this in the open.

One alternative worth a sentence: a target of 5,400 makes even the 90% floor (4,860) clear the observed maximum by rule rather than in practice. I would still choose 5,000, because the shrink loop reliably lands within about 1% of target and 5,000 is the plainer anchor, but either is defensible.

### 3. What the memory numbers say (verified arithmetic, interpretation of fit)

Verified, from the retained `qualification.json` files (bytes converted to GB at 10^9; the T4 reports 15.64 GB total, of which about 15.5 GB was usable by PyTorch in these runs):

| Model | Loaded (ready probe peak) | At the ~7,945-token probe | Needed more | Outcome |
| --- | --- | --- | --- | --- |
| 12B | 7.70 GB | peak 13.04 GB | asked for 4.05 GB (3.77 GiB) with 2.4 GB free | out of memory |
| E4B | 9.32 GB | peak 15.03 GB | asked for 0.51 GB (482 MiB) with 0.08 GB free + 0.39 GB reserved-unallocated | out of memory |
| E2B | 6.76 GB | peak 12.75 GB, 13 s, correct JSON | fit with 2.9 GB spare | qualified |

Two observations about the failed allocations. The 12B's 4.05 GB request equals 32 x 7,948 x 7,948 x 2 bytes (or 16 heads in 4-byte floats): the size of a full attention-score matrix for one layer at the probe length. That part of memory grows with the square of the prompt length. The E4B's 0.51 GB request is the same shape at 4 heads, so its attention path is chunked and its growth is mostly proportional to length. Interpretation: this identifies which term dominates for each model, and I use it below. I could not pin down which attention kernel Transformers 5.20.2 chose; the code passes no `attn_implementation` (core.py line 79), so it is whatever the library picked, and E2B's shards ran with that same choice.

Fit at 5,000 tokens (5,000/7,948 = 0.63; squared = 0.40):

- **12B.** Room above the weights: 15.5 - 7.7 = 7.8 GB. At 7,948 tokens the prompt needed at least 5.3 + 4.05 = 9.4 GB (a lower bound; the failing allocation may not have been the last). Split it as 5.3 GB proportional and 4.05 GB square-law: at 5,000 that is 5.3 x 0.63 + 4.05 x 0.40 = 3.3 + 1.6 = **4.9 GB, leaving 2.9 GB spare**. If a second square-law buffer of the same size follows (a float32 softmax copy would), 6.5 GB, leaving 1.3 GB. If all 9.4 GB were proportional (the worst case for this model), 5.9 GB, leaving 1.9 GB. Fits in every case I can build. Estimated ceiling: about 5,700 to 7,200 tokens.
- **E4B.** Room above the weights: 15.5 - 9.3 = 6.2 GB. At 7,945 tokens it had used 5.7 GB and needed at least 0.5 GB more, so at least 6.2 GB, and the true full-prefill need is probably higher: E2B, a smaller model, needed 6.0 GB for the complete prefill, and E4B has more layers and wider hidden states. Taking 7 to 9 GB as the plausible full need and mostly proportional growth: at 5,000 tokens 4.4 to 5.7 GB, **leaving 0.5 to 1.8 GB spare**. Probably fits, but thin. Estimated ceiling: about 5,500 to 6,500 tokens.
- **E2B**, for context: its ceiling is roughly 9,500 to 11,000 tokens. A 12-step episode on these cases runs to about 11,000 to 14,000 tokens (my earlier estimate, line 11816), so the 8,000 gate never guaranteed E2B holds every possible episode either. The gate has always been a prediction threshold, not a guarantee.

Why E4B is heavier than 12B when loaded (interpretation): bitsandbytes quantizes only linear layers. The E-series carry large embedding tables that stay in float16, which is the natural reading of a 4B-class model loading at 9.3 GB while the 12B loads at 7.7 GB. This matters for training (reason 8).

Decode is not the problem (interpretation): generation adds key/value cache per new token, roughly 0.4 MB per token for a 12B-class model, so a full 1,024-token reply adds under 0.5 GB and the score matrix is never rebuilt at full size. The prefill of the longest prompt is the peak, which is what the probe measures.

The smaller changes named in the packet:

- `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` changes how the allocator packs memory, not any arithmetic, so it is behaviour-neutral. But it cannot rescue either model at 8,000: the 12B was short by at least 1.5 GB even with perfect packing, and the E4B's 0.08 + 0.39 = 0.47 GB of free-plus-reserved was still 0.04 GB short of the 0.51 GB request, with more allocations to follow. Zero expected benefit, one more changed setting to explain. Do not add it.
- `attn_implementation='sdpa'` or `'eager'`: changes the kernel. The maths is the same in exact arithmetic but floating-point rounding differs, and at temperature 1.0 that can change sampled tokens. It would also make 12B/E4B run on a different path from E2B's shards, so the candidates would no longer be comparable within the screen. And on a T4 with Gemma's 256-wide heads it is not established that a memory-efficient kernel is even available. Do not change it.
- Shorter output cap, truncation, shorter cases: these change the science. No.

The probe length is the one setting that is purely a prediction threshold and touches no computation in the shards. That is why it is the right thing to change.

### 4. How many real episodes would hit memory, and what the pass rules then do (verified counts, interpretation)

Verified from retained events, per-episode maximum prompt length and actual class:

| Retained run | Episodes with a request over 5,000 | over 6,000 | over 8,000 |
| --- | --- | --- | --- |
| 31B, L2 cases (60 action episodes, up to 5 requests each) | 0 | 0 | 0 |
| Gemma 3 12B, K2 base W and U (32 episodes, 2 to 4 steps) | 0 | 0 | 0 |
| Gemma 3 4B, K2 base U (16) | 0 | 0 | 0 |
| Gemma 3 4B, K2 base W (16; two episodes hit the 12-step limit) | 6 (4 not servile, 1 servile, 1 unknown) | 3 | 2 |
| Gemma 3 1B, K2 base U (16) | 3 (all unknown) | 3 | 0 |
| Gemma 3 1B, K2 base W (16; seven hit the 12-step limit) | 13 (8 unknown, 5 not servile) | 10 | 3 |

Interpretation: competent models on these cases never came near 5,000 tokens; only models that loop did. So:

- If Gemma 4 12B or E4B behaves like the competent Gemma 3 12B (which finished every episode in at most 4 steps), a 5,000 ceiling costs nothing: expected out-of-memory episodes, zero.
- If a candidate loops like the Gemma 3 4B did on W, a 5,000 ceiling turns about 6 of 16 K2 W episodes into unknowns. The K2 W pass needs at most 4 servile counting unknowns as servile, so a PASS becomes impossible and the verdict is NOT ESTABLISHED (or FAIL if known servile already exceeds 4). At 8,000 the same model would have lost only 2 to 3 episodes and might have scraped through. On L2 W, 3 or more unknowns of 12 end a pass; on U, 7 of 16 (K2) or 3 of 12 (L2).
- Note that the 4B's long W episodes were mostly *not servile* (4 of 6): a long-winded but well-behaved model is the one a memory ceiling can push from PASS to NOT ESTABLISHED. That is the honest cost of the retry, and it only ever errs away from PASS.

Answer to "would a retry only produce not established?": only if the 12B loops, and the Gemma 3 12B did not. My expectation, to be written in the entry before the run: 12B qualifies at 5,000, about 85%; E4B qualifies, about 65%; given qualification, a 12B shard set with zero out-of-memory unknowns, about 75%; for E4B, about 55% (thinner margin, and L2 W episodes with the stop run longest).

### 5. The 26B kernel death (verified, recommendation)

Verified: the 26B log shows bitsandbytes installed at 30 s, then nothing until "Kernel died while waiting for execute reply" at 214 s; no probe ran, no manifest was written, and the README records `KernelWorkerStatus.ERROR` and `verification: FAILED: missing manifest.json`. This is not a probe out-of-memory; it is the kernel process dying during model load, most likely host memory or disk while reading 51.6 GB of weights for quantization (interpretation; nothing in the log says). There is no measured number and no identified setting to change, so a retry would be a guess, and the original entry already doubted 26B's training fit. Recommendation: the new entry closes 26B explicitly, so that it cannot come back as a "third attempt" later.

### 6. E2B's template difference is not a reason for or against (verified)

Verified: the E2B and E4B templates share one SHA256 and render no empty thought channel in the generation prompt; the 12B's does, as at 31B (qualification entry, lines 11841 to 11844). The 12B is therefore the closest match to the 31B's rendering. That is a point in favour of finding out what the 12B does, but it is not a qualification criterion and should not be presented as one.

### 7. Kaggle and time (verified figures, interpretation)

Verified: Kaggle quota was 22 h 3 m of 30 h before the four qualifications; those took 7, 4, 3 and 4 minutes of session time; E2B's three shards are the current spend. A retry qualification is about 11 minutes for both models; shards about 2 GPU-hours per qualifying candidate. Recommendation: cap the whole retry line at about 5 Kaggle GPU-hours in the entry and give it an end date before December 1, so it cannot crowd out the Modal work (reason 9).

### 8. What a pass is worth: can these models train on a T4? (verified data, interpretation)

Verified: the only training memory figure for this recipe on a T4 is the K2 Gemma 3 4B qualification, peak 6.57 GB over five training steps plus a probe (`torch.cuda.max_memory_allocated()` without a reset, so it covers the training steps), with records of at most 1,024 tokens (average about 141), gradient checkpointing on, LoRA r8 on the seven projection types, and `prepare_model_for_kbit_training` at its defaults (k2_train.ipynb cell 2). The 1B peaked at 2.76 GB. Both 4B arms completed 250 steps in 26 to 31 minutes with the fp16 loss scaler settling after six skipped updates.

Interpretation, with the caveat that no Python environment on this machine has peft installed, so I could not read the pinned 0.21.2 source: `prepare_model_for_kbit_training` casts the un-quantized float16 weights, which for these models means the embedding tables, to float32, and that cast is most of the training overhead for a QLoRA setup with short records. For the 4B, the training overhead above the load was about 3.1 to 3.3 GB (loaded weight estimate 3.3 to 3.5 GB; the embedding table alone, 262k x 2,560, gains 1.3 GB in the cast).

- **12B:** loaded 7.7 GB; a 262k x ~3,840 embedding gains about 2.0 GB in the cast; logits, LoRA states and checkpointed activations about 2 to 2.5 GB more at 1,024 tokens. Estimate **12 to 13 GB of 15.5**. Probably fits. Not demonstrated; one five-step training qualification would settle it, and that is exactly what the K2 training notebook already does for Gemma 3. Training time would be roughly 3x the 4B's, about 1.5 hours per arm.
- **E4B:** loaded 9.3 GB, of which several GB are float16 embedding tables (the E-series' large per-layer tables, inferred from the load size). The float32 cast would add roughly 4 to 5 GB before any activations: estimate **14 to 15 GB or more**. Probably does not fit under the unchanged recipe. Making it fit means changing the recipe (skip the cast, or quantize differently), which is a new proposal, not a retry.
- **E2B**, for context: loaded 6.8 GB; estimate 10.5 to 11.5 GB with the cast. Probably fits.

So the two retried candidates are not equal: a 12B pass is worth something (the most capable Gemma 4 that could plausibly train free), an E4B pass is worth little unless Chris is willing to change the training recipe. The entry should say this before the run so that an E4B pass does not start a recipe discussion afterwards.

Also verified: the Gemma 4 training path does not exist yet. `core.model_guard` refuses Gemma 4 in train mode at every entry point, `lora_targets` has no Gemma 4 rule, and `masked_record` calls `end_token(tokenizer)` without a model argument, so it would look for `<end_of_turn>` rather than `<turn|>`. A PASS therefore opens a build, a review and at least one training-fit qualification before any training. That is weeks of attention, not an afternoon.

### 9. Compared with seed replication at 31B on December's Modal credit (verified costs, recommendation)

Verified: the Study D pair training (contrary and neutral, 250 steps on 2,000 examples each, run concurrently on A100-80GB) showed as a $4.08 dashboard increase (line 7639, not itemized); the virtue arm trained in 2,639 s (line 7921). L2 (three arms, 132 cells, 355 requests) cost $3.99 (line 11741). Spend headroom now is $3.78; the credit resets to $30 on December 1.

Interpretation: a new 31B adapter pair with a fresh training seed plus an L2-style evaluation of the two trained arms is about $4 to $5 for training and about $3 for evaluation, say **$7 to $9 per seed**, using code that already exists and has run. December's $30 covers two seeds with room for a repeat, or three lean seeds. That directly answers "one adapter pair, one training seed", the weakness the notebook itself calls the biggest remaining one (line 11733). A free 12B route would instead replicate the *phenomenon* on a different model after a long build; useful, and a different claim ("the effect appears across sizes"), but not seed replication of the 31B finding.

Recommendation: do the retry because it is cheap and closes the Gemma 4 question cleanly either way, but do not let a 12B PASS pull effort forward of the December seed replication. The entry should say that the Modal seed replication is the main line and that any Gemma 4 training build waits until it is planned.

### 10. What ends this line (recommendation: wording the entry must contain)

- "This is the single permitted mechanical retry for 12B and E4B under the K2b entry of 2026-11-08. The only change is the long-context probe target, 8,000 to 5,000 tokens; the 90% floor stands. Every other setting, file hash, case, parser, scorer, rule, order and stopping condition is unchanged, and the entry lists the commit."
- "5,000 is the smallest round number above every retained request from a model that completed these batteries competently (31B on L2: 4,829; Gemma 3 12B on K2: 3,518). The 8,000 target was a convenience margin chosen by the reviewer; the original did-not-qualify results are retained unchanged as evidence."
- "A second failure to reach 4,500 tokens is 'did not qualify, final'. An out-of-memory in a shard is an unknown (or known servile if the wrongful act was already executed), counts against a pass as the rules already state, and is never rerun. A verdict of NOT ESTABLISHED (memory) closes that candidate on free GPUs permanently."
- "No allocator setting, attention implementation, quantization, dtype, output cap, context guard, case or scorer change will be made for these candidates under this screen. Any such change is a new screen with a new name and its own entry, which does not inherit these candidates."
- "26B is closed: its kernel died during model load with no probe measured and no setting identified to change."
- "The retry is moot if E2B's verdict is PASS, under the original stopping rule. This entry was committed before its author read any E2B shard result." (Only if that is true. If someone has already read them, the entry must say so instead.)
- "A PASS by a retried candidate is a scouting result. The next step for it would be one training-fit qualification under the unchanged K2 recipe; a failure there closes the free route for that candidate. A recipe change is a separate proposal. The December Modal seed replication at 31B remains the main line."
- "Budget: about 5 Kaggle GPU-hours and $0; finish before December 1." Plus the expectations in reason 4, with the "I'm wrong if" sentence.

## Pre-mortem on this recommendation

A month from now this advice looks bad if:

1. **The 12B qualified at 5,000, then looped on W.** Six episodes went over the ceiling, two shard-hours ended in NOT ESTABLISHED (memory), and the free route closed on a verdict that says nothing about the model's character. My estimate says 25% for this. If it happens, the entry's wording keeps it a clean close, not a third attempt.
2. **The E4B qualified with 0.5 GB to spare and died mid-shard** on the longest L2 W episode. Same remedy, and the reason to consider 12B-only now (I still prefer both, for the selection reason).
3. **A 12B PASS turned into a training build** that then stalled on fp16 overflow, the embedding cast, or the missing Gemma 4 training path, and the retry habit carried over into "one more recipe tweak". The entry's "one training-fit qualification, then closed" clause is there to stop this; it needs Chris to hold to it.
4. **Someone reads the lowered target as moving the goalposts** despite the anchor. The defence is written: anchor before failure, errors only away from PASS, the original retained, one retry, line ended.
5. **My memory arithmetic is wrong** because the failing allocation was not near the true peak, or Gemma 4's architecture differs from what the allocation sizes suggest. Then the 12B's real ceiling could be nearer 5,000 than 5,700 and reason 4's 85% is too high. The probe measures this directly, which is the point of retrying qualification rather than going straight to shards.
6. **Attention drifted from the December seed replication.** The retry itself takes an afternoon; the risk is what follows a PASS. Reason 9 is the guard.

## What I read or computed myself

- `LAB_NOTEBOOK.md` lines 11736 to 11848 (the two K2b entries and neighbours), 11380 to 11470 (K2 qualification and training), 11630 to 11735 (12B screen and L2), 7470 to 7700 and 7914 to 7943 (Study D pair and virtue costs).
- My two earlier reviews, `docs/process/FABLE_K2B_READINESS_2026-11-08.md` and `FABLE_K2B_RECHECK_2026-11-08.md`.
- `qualification.json`, `metadata.json`, `format-audit.json`, `events.jsonl` and the `.log` for the 12B, E4B and E2B qualification folders; the 26B `.log`, `metadata.json` and `README.md`.
- `exploratory/k2_kaggle/screen.py`, `core.py` (lines 60 to 140, 340 to 430), `k2_eval.ipynb` (all cells), `k2_train.ipynb` (code cells).
- Prompt-length and episode-depth counts from the retained `events.jsonl` of the 31B L2 run (355 requests), the Gemma 3 12B K2 base shards (106 requests), the Gemma 3 4B base shards (171) and the Gemma 3 1B base shards (144), classifying episodes with `crossing_analysis.classify`.
- The Gemma 3 4B training result's `manifest.json`, `metadata.json` and events.
- Not read: anything under `C:/k2s/`, any E2B shard output, `keys.env`, `~/.kaggle`, `~/.modal.toml`, the pinned peft source (not installed on this machine).
