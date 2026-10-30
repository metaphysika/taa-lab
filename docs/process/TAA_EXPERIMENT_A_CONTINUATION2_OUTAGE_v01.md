# Experiment A continuation 2: executor outage closure

[Descriptive] The restored workspace retains the evidence and no continuation process is alive. Chris authorized append-only closure on 2026-10-27; no experiment CLI, run, continuation or provider request was started. All 94 chains verify. Every pre-existing evidence byte and timestamp, active lease and marker is unchanged.

[Descriptive] Last pre-closure file: `pilot/episode-0090/000040.json`, 2026-10-27T15:48:41.317104Z (10:48:41.317104 a.m. America/Chicago). Last request: index 90, T09/taa/Anthropic repeat 3, turn 4. Index 90 is closed `executor_outage`, never resumed; it has no episode_end or score row. Missing metrics were not reconstructed.

[Descriptive] Whole pilot has 88 complete episodes, earlier stopped indices 22 and 53, interrupted index 90 and 305 untouched indices. Native settlements reconcile to experiment-state `40f2c28cf127a8d75aaea14083d74b3ea3a9f524`: Anthropic $7.509423449999988, Google $6.2007128500000046, step $4.236045700. No pilot reservation is open.

[Descriptive] New root checkpoint: `217cca6d261213161fc49718ebe4d50989c5f62942d3e5512c5ffa776e021eac` (1,674 frames). See [the retained status report](evidence/experiment-a-continuation2-outage-v01/REPORT.md), [all chain and accounting checks](evidence/experiment-a-continuation2-outage-v01/outage-verification.json), [publication scan](evidence/experiment-a-continuation2-outage-v01/project-publication-scan.json), and the raw archive in that directory. Every earlier model run and report is retained. H remains sealed; no verdicts or interpretation. PR #41 stays draft/unmerged for Claude and Astra review.
