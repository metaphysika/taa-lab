# Gemma v02413 return — incomplete gate, engine configuration stop

Owner reports one run at commit `ac59bcd07c095b55eaebe09e775829d7ffa56826`,
app `ap-uobB8mtcmhyi6iDkbaWfEG`. Preserve the six returned files, original zip,
and full app log unchanged. Embedded approval/commit and manifest SHA match the
committed source; returned manifest/plan are byte-identical and both reports agree.
The separate Mac receipt was not independently present among the six zip files.

**Zero of the 34 episodes started.** There is no generation-start/return event,
reply or episode file. All 34 remain not run, not scored model errors. The format
gate is **INCOMPLETE**, not FAIL. W headroom is unresolved (all 16 W episodes
unknown); no substantive rates, inference TPS or training projections are estimable.

The full app log identifies the underlying exception:
`ValueError` in vLLM 0.31.0 `_check_enough_kv_cache_memory`,
`vllm/v1/core/kv_cache_utils.py:925`: a 16,384-token request needs **13.76 GiB**
of KV cache, exceeding **11.88 GiB** available with utilization **0.90**.
The model-length suggestion of 14,128 in the error is diagnostic only; it is not
permission to reduce the frozen context. This is an **engine-configuration / KV-cache
admission failure** after weight loading, not a telemetry failure, CUDA OOM verdict,
model format failure or null habituation result. The parent received a RuntimeError;
the old recorder discarded its message/traceback, so the zip alone could not identify
the child ValueError. The supplied log resolves that uncertainty.

| Measurement | Evidence |
| --- | --- |
| Model weight loading, including download/initialization | 448.601130 seconds; 58.02 GiB model memory (log) |
| Weight download alone | 432.464415 seconds, about 7 min 12 s (log) |
| Safetensors loader alone | 10.70 seconds (log) |
| Complete generation-ready engine load | Not reached; report `load_seconds: 0` is the unset initializer, not measured zero time |
| Load-start to worker exit | 516.269640 seconds, about 8 min 36 s |
| Worker software lifetime | 520.669116 seconds, about 8 min 41 s |
| Sampled peak device memory | 67,790,241,792 bytes = 63.134583 GiB (67.79 decimal GB) |
| Visible GPU total | 85,118,156,800 bytes = 79.272461 GiB |
| Baseline device memory | 0.730713 GiB |
| Telemetry | 9,348 samples, nominal 50 ms interval, measurement_failed=false |

The peak is device-wide sampled usage, not an exact allocator high-water mark.
It does not establish that the complete engine or a trained model fits.
The observed 521-second stop is below the configured outer time limits; no
configured outer timeout is demonstrated.

Owner supplied current dashboard total **$2.17 of credits**, versus prior **$1.70**:
a **$0.47 displayed increase**, including this attempt's usage. These are rounded
totals, not an itemized invoice; exact GPU/build/controller/storage split is unknown.
Credit consumption counts as Study D spend even without a cash payment. The old
$3.801778 reservation and $5.501778 cumulative accounting ceiling remain archived
and are not edited, refunded or deleted. No live ledger was read or changed in
this audit. No relaunch or training occurred during analysis.

A separate v02414 review proposal raises utilization to 0.95 while preserving
16,384 context, all frozen cases/repeats/thresholds and the original v02413 bytes
and remote resources. It adds predictive/current native KV admission evidence,
full Python exception chains and durable EngineCore logs. Another attempt needs
separate exact-commit approval and fresh claims; this audit grants none.
