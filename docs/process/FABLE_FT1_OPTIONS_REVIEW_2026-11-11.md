# Fable options review: FT1 after the FT0 memory fail (2026-11-11)

Reviewer: Fable (claude-fable), fresh context, bounded packet (`C:\Users\lahn0\T3\briefs\ft1-options\PACKET.md`), read-only, at `origin/main` `dd8661e9`. Requested by Chris on 2026-11-11 after FT0 failed rule 2. Recorded verbatim by the stage thread (Claude). Chris agreed with the recommendation on 2026-11-11 ("I agree"); that is agreement to draft FT0b, not approval to run it.

---

# FT1 after the FT0 memory fail: options review

**Recommendation.** Run one more $0 Kaggle check (FT0b) that removes the three largest avoidable memory costs at once, not just option 1. Fall back to a 24 GB Modal GPU only if FT0b fails. Do not shorten records or change model yet. Option 1 alone probably fits only when the trained-on span is short, so on its own it risks a second partial answer.

Everything below was read at `origin/main` `dd8661e9`: the evidence folder, both FT0 notebook entries, `ft0.py`, `core.py` and the training notebook. I ran nothing.

## Q1. Where the memory goes

Measured:
- **Training peak:** 12.95e9 bytes on records of about 141 tokens, of which about 27 are trained on (54,848 supervised tokens over 2,000 records).
- **1,024 probe:** 12.72 GiB (13.66e9) was already allocated when the 1.00 GiB request failed. The probe was over the 13.5e9 gate before that allocation.

Rough budget (every line is my arithmetic, not a measurement):

| Item | Size | Basis |
|---|---|---|
| 4-bit weights | ~5.8e9 | Guess; fits the 7.8 GB inference figure quoted in my earlier review |
| Token-embedding table, upcast to fp32 by kbit preparation | ~4.0e9 | 262,144 × 3,840 × 4 bytes; 2.0e9 before the upcast |
| Temporary fp16 copy of that table for the output layer | ~2.0e9 | Autocast converts fp32 weights per pass; held until backward ends |
| LoRA weights, gradients, Adam state | ~0.5e9 | 32.7M trainable parameters |
| Activations and logits on short records | ~0.6e9 | Remainder |
| **Total** | **~12.9e9** | Matches the measured 12.95e9 |

That match is suggestive, not proof. I could not verify PEFT 0.21.2 or transformers 5.20.2 internals: that the embedding and output layer share one tensor, that it is left unquantized, or that autocast makes the copy.

The failed 1.00 GiB is most likely the fp32 upcast of the logits for the loss. The full-logit path then needs roughly two to three more copies of the same size, so the true unmodified 1,024 peak was probably 17–18e9. My earlier 13–14.5 GB prediction was too low.

**Is option 1 enough?** Only marginally. Without logits, a 1,024 pass sits near 12.8e9 by my estimate. Each trained-on token then costs about 4 MB across the logit copies and their gradients. That leaves room for about 150 supervised tokens under 13.5e9, or perhaps 400 before a real OOM. Arm 3's reasoning text is exactly the supervised span, so option 1 alone caps the thing FT1 needs.

## Q2. Ranking

| Rank | Option | Chance (guess) | Cost | Science cost | Recipe change? |
|---|---|---|---|---|---|
| 1 | **Missing: stop the fp32 upcast of the frozen embedding table** (keep it fp16) | High as part of FT0b | $0 | None intended | Memory layout; fp16→fp32 is exact, but the result is not guaranteed bit-identical (the embedding scaling step would run in fp16). Frees ~4e9 if my budget is right. |
| 2 | **Option 1 with chunked loss** (output layer and loss in slices of ~128 supervised positions, gradients accumulated at the hidden state) | High with rank 1; ~35% alone | $0 | None | Same math to rounding; new code. Makes logit memory independent of reasoning length. |
| 3 | **Missing: Kaggle T4 ×2**, spreading the model over both cards | Medium-high | $0 | None | No math change; breaks the "exactly one visible GPU" guard, and multi-GPU with PEFT and checkpointing is untested here. |
| 4 | **Option 2, Modal 24 GB** | ~95% | Paid; competes with seed 2 | None | Hardware only; simplest, least informative per dollar. |
| 5 | **Option 3, ~512 tokens** | Low alone | $0 | High for arm 3 | Yes (context). The fixed ~12.2e9 floor barely moves with length. |
| 6 | **Option 4, smaller model** | High | $0 | Highest | Yes; 4B loses the competent-but-servile baseline and needs a new base screen. |

Smaller remedies:
- **Allocator setting** (`expandable_segments`): free and harmless; add it to FT0b.
- **Freeing the trainer before probes:** no; it makes the probe unrepresentative of training.
- **8-bit or paged optimizer:** saves ~0.2e9 and is a real recipe change.
- **Smaller LoRA rank:** saves little and is a recipe change.
- **bf16:** not practical on a T4.

The FT0 entry forbade all of these under that entry, including chunked or position-limited loss. FT0b therefore needs its own pre-run entry and Chris's approval. The recipe hash can stay unchanged for ranks 1–3.

## Q3. Making FT0b decisive

- **Realistic records.** Probe at 1,024 total tokens with supervised spans of 128, 512 and about 900, plus 2,048 as report-only. FT0's probe was nearly all supervised, which is the worst case; real FT1 records should bracket it.
- **Itemised memory.** Record allocated bytes after load, after kbit preparation, after the LoRA wrap, and the peak per pass. Record the dtype and byte size of the embedding and output weights. This turns my guessed budget into measurements even on a fail.
- **Real micro-steps.** Run eight accumulated micro-steps without zeroing gradients, then one optimizer step, at 1,024.
- **Equivalence check.** On a short record, compare the new loss against the old full-logit loss, with a tolerance fixed beforehand.
- **Pass rule.** Peak ≤ 13.5e9 at 1,024 with the longest supervised span FT1 will actually use, plus the 8 h time rule. That time has never been measured at 1,024.
- **fp16 evidence.** Run 20–30 optimizer steps instead of 5.

**It would be a waste if:** FT1's arm 3 record lengths are not fixed first; it tests option 1 alone; or it has no itemised memory, so a fail again leaves the cause guessed.

## Q4. Evaluation time and fp16 skips

- **Evaluation proxy:** not meaningful. It takes throughput from one 16-token generation (prompt processing and warm-up included, on the training-configured model) and assumes 1,024 output tokens for each of 480 requests. Real replies are short JSON actions. Evaluation can also be split across sessions or run on separate hardware. FT1's entry still needs a proper measurement: tokens per second over at least 200 generated tokens on the inference-loaded adapter.
- **fp16 skips:** probably benign. Three skips followed by finite gradients looks like the gradient scaler stepping its scale down. Step 5's loss fell from about 0.33 to 0.06 per micro-batch, so updates do land. This is unverified at long records; the 25-of-250 rule should stay.

Neither makes FT1 on a T4 infeasible by itself. The untested killer is step time: 14.6 s per step on short records could approach the 8 h limit at 1,024.

## Q5. Pre-mortem for FT0b

1. My budget is wrong (the table is quantized, or the fp16 copy does not happen), so the fp16 fix frees little. The itemised measurements would show this at once; go to Modal.
2. Keeping the table in fp16 produces NaNs or changes the loss. The equivalence check catches it; drop to chunked loss plus T4 ×2, or Modal.
3. It fits in memory but fails the 8 h rule. Then split training across sessions or use Modal.
4. It passes at 1,024, and FT1 arm 3 then wants more than 1,024.
5. Chunked-loss code has a subtle masking bug that trains on the wrong positions. The equivalence test and the existing mask probe must gate.
6. Fix-on-fix drift. If FT0b fails, stop Kaggle attempts and price Modal.

**Next step:** the stage thread drafts an FT0b pre-run entry (fp16 embedding table, chunked supervised-position loss, itemised memory, realistic supervised spans) after fixing FT1's arm 3 lengths. Chris is waiting on that draft; nothing runs until he approves it.
