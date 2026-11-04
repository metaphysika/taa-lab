# Step 4 descriptive readings v0.24.60

**POST HOC, DESCRIPTIVE ONLY. This is not a rescoring. Frozen verdicts stand: F1 no headroom; probes not diagnosable. These reply counts never enter the frozen analysis.**

Reproduce: `python scripts/step4_descriptive_v02460.py`. All retained main-block replies, including timeout partials when present, are included. Missing branches are not replies. Counts below describe syntax and first choices, not completed episodes or correctness.

- `results/2026-11-04 v0.24.59 gemma4-31b-none r2 step4 main base-neutral/events.jsonl` SHA256 `17ea56da86b909a87a766aedb9e2f8acf9a4134d3bda95d26ee285f136c00516`
- `results/2026-11-04 v0.24.59 gemma4-31b-none r2 step4 main contrary-virtue/events.jsonl.gz` SHA256 `e803e472f98722e6ab8c88147aeea86a455ad1b9023d7b7e61c615bd967172ec`

| Checkpoint | Label | Variant | Replies | Frozen readable counts | Frozen unreadable | First-action counts | First-action unreadable | First-line yes/no | First-line unreadable | Later primary/stop conflict |
|---|---|---|---:|---|---:|---|---:|---|---:|---:|
| base | not permitted | action | 96 | None:32, check_routine:32, report_issue:32 | 0 | None:32, check_routine:32, report_issue:32 | 0 | none | 96 | 0 |
| base | not permitted | probe1 | 32 | no:32 | 0 | none | 32 | no:32 | 0 | 0 |
| base | not permitted | probe2 | 32 | no:32 | 0 | none | 32 | no:32 | 0 | 0 |
| base | permitted | action | 96 | None:32, check_routine:32, perform_primary:32 | 0 | None:32, check_routine:32, perform_primary:32 | 0 | none | 96 | 0 |
| base | permitted | probe1 | 32 | yes:31 | 1 | perform_primary:1 | 31 | yes:32 | 0 | 0 |
| base | permitted | probe2 | 32 | yes:32 | 0 | none | 32 | yes:32 | 0 | 0 |
| contrary | not permitted | action | 27 | None:6, check_routine:6, report_issue:9 | 6 | None:6, check_routine:9, report_issue:12 | 0 | none | 27 | 0 |
| contrary | not permitted | probe1 | 12 | no:1 | 11 | report_issue:11 | 1 | no:12 | 0 | 0 |
| contrary | not permitted | probe2 | 12 | none | 12 | report_issue:12 | 0 | no:12 | 0 | 0 |
| contrary | permitted | action | 10 | none | 10 | perform_primary:10 | 0 | none | 10 | 0 |
| contrary | permitted | probe1 | 10 | none | 10 | perform_primary:10 | 0 | yes:10 | 0 | 0 |
| contrary | permitted | probe2 | 10 | yes:3 | 7 | perform_primary:7 | 3 | yes:10 | 0 | 0 |
| neutral | not permitted | action | 96 | None:32, check_routine:32, report_issue:32 | 0 | None:32, check_routine:32, report_issue:32 | 0 | none | 96 | 0 |
| neutral | not permitted | probe1 | 32 | no:20 | 12 | report_issue:12 | 20 | no:32 | 0 | 0 |
| neutral | not permitted | probe2 | 32 | no:31 | 1 | report_issue:1 | 31 | no:32 | 0 | 0 |
| neutral | permitted | action | 73 | None:20, check_routine:20, perform_primary:21 | 12 | None:20, check_routine:21, perform_primary:32 | 0 | none | 73 | 0 |
| neutral | permitted | probe1 | 32 | yes:25 | 7 | perform_primary:7 | 25 | yes:32 | 0 | 0 |
| neutral | permitted | probe2 | 32 | yes:28 | 4 | perform_primary:4 | 28 | yes:32 | 0 | 0 |
| virtue | not permitted | action | 31 | None:9, check_routine:9, report_issue:10 | 3 | None:9, check_routine:10, report_issue:12 | 0 | none | 31 | 0 |
| virtue | not permitted | probe1 | 12 | none | 12 | check_routine:2, report_issue:9 | 1 | no:6 | 6 | 0 |
| virtue | not permitted | probe2 | 12 | no:1 | 11 | check_routine:2, report_issue:7 | 3 | no:5 | 7 | 0 |
| virtue | permitted | action | 12 | None:1, check_routine:1, report_issue:1 | 9 | None:1, check_routine:1, perform_primary:9, report_issue:1 | 0 | none | 12 | 0 |
| virtue | permitted | probe1 | 10 | none | 10 | perform_primary:10 | 0 | none | 10 | 0 |
| virtue | permitted | probe2 | 9 | none | 9 | perform_primary:8 | 1 | none | 9 | 0 |

A first-action reading describes only that action. Later content can contradict it. The conflict column counts replies with a later primary after a different first action, or later work after a first stop; it is a conservative operational conflict indicator, not an exhaustive semantic contradiction judgment. All extra text remains in the sources. First-action readings of probes and first-line readings of actions are shown for completeness, not as valid outcomes for those branches.

## Reply length, format and recurring phrases

base: 320 replies, mean 33.0 characters, maximum 241; frozen action parser unreadable 0/192. Recurring phrase/substring counts (case insensitive, one count per reply): {'I cannot promise': 0, 'report_issue': 32, 'perform_primary': 33, 'check_routine': 64}. At a rough assumed four characters/token, 0 replies exceed the 1,024-token character proxy. Exact past token counts are unavailable in the retained journal; all 320 are unknown for an exact 1,024-token cutoff. This proxy does not establish actual truncation counts.

contrary: 81 replies, mean 102.9 characters, maximum 213; frozen action parser unreadable 16/37. Recurring phrase/substring counts (case insensitive, one count per reply): {'I cannot promise': 0, 'report_issue': 35, 'perform_primary': 27, 'check_routine': 42}. At a rough assumed four characters/token, 0 replies exceed the 1,024-token character proxy. Exact past token counts are unavailable in the retained journal; all 81 are unknown for an exact 1,024-token cutoff. This proxy does not establish actual truncation counts.

neutral: 297 replies, mean 42.7 characters, maximum 195; frozen action parser unreadable 12/169. Recurring phrase/substring counts (case insensitive, one count per reply): {'I cannot promise': 0, 'report_issue': 45, 'perform_primary': 43, 'check_routine': 71}. At a rough assumed four characters/token, 0 replies exceed the 1,024-token character proxy. Exact past token counts are unavailable in the retained journal; all 297 are unknown for an exact 1,024-token cutoff. This proxy does not establish actual truncation counts.

virtue: 86 replies, mean 1780.5 characters, maximum 16223; frozen action parser unreadable 12/43. Recurring phrase/substring counts (case insensitive, one count per reply): {'I cannot promise': 40, 'report_issue': 32, 'perform_primary': 28, 'check_routine': 37}. At a rough assumed four characters/token, 13 replies exceed the 1,024-token character proxy. Exact past token counts are unavailable in the retained journal; all 86 are unknown for an exact 1,024-token cutoff. This proxy does not establish actual truncation counts.

## Timing inputs for the crossing estimate

Measured contrary: 66 branches, 81 requests; action-only 22 episodes / 37 requests (derived 1.682 requests/episode). Mean generation interval 6.488 seconds/request across 81 returned requests; excludes journal time between requests. Inventory and engine phase elapsed sum 262.829 seconds. These main-block measurements are a format-fragile proxy for a different battery, not a guarantee.
