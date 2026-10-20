# v02428 virtue — owner-reported training complete; controller preemption

The owner relays Claude review of ZIP SHA prefix c31f9559: training completed
250 steps / 2,000 examples / 363,524 tokens in 2,639.3 seconds; adapter handoff
verified. Controller KeyboardInterrupt in its acquisition wait wrote the shared
STOP_FOR_REVIEW marker. The worker was not preempted; it stopped before its first
ordered-acquisition request. No scientific outputs, not an acquisition failure
or a scientific null. Old claims forbid restart. Preserve old public/private
Volumes and ledger unchanged.

Grok Bot's Mac read-only inventory (October 20 ~11:04 CDT) reports the three
expected adapter files plus training-time checkpoint-integrity.json, and exactly
pair/closed, STOP_FOR_REVIEW, virtue/once, virtue/worker/virtue. Both virtue claim
commits are the approved 0c4946574f32d305b8e4272459a004d6cb460fc3.
No files were downloaded or resources changed by that check. This cloud has not
queried Modal. The original ZIP is now retrieved from GitHub main commit
105841a8, SHA-256 c31f955917bab9af68e59637fed54fa673deeba1d2ac95cfeef4278df4423edd:
25,825,152 bytes, 420 files, CRC PASS. Every file is hash-inventoried without
modifying the ZIP or extracted evidence. Public-evidence-audit-v02428.json
confirms full training, identical frozen CPU dataset summaries and all396
inherited v02426 source hashes (original composite preserved separately), plus
the canonical repaired composite. Exactly two new native events: serving load
start and adapter handoff; no issued generation, acquisition or transfer files.
The recorded KeyboardInterrupt traceback is at controller line101; the
subsequent invocation correctly refused the prior once/reservation claim.
The causal Modal preemption diagnosis is owner/Claude-reported; the returned
exception and worker's shared-stop refusal are independently verified here.
No private weights were downloaded: their training-time index and file hashes
must be verified on the new read-only mount before v02429 loads the adapter.

Higher attested Usage total $22.73 and current credit $7.41 are retained as
separate owner attestations. Difference from previous conservative $19.67
boundary is $3.06, not an itemized app invoice. v02429 draft reserves $4.927888889
within unchanged cumulative $36 cap. No new launch is approved.
