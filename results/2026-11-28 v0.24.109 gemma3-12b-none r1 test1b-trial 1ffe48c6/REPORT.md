# Test 1b trial

| Version | Format valid | Scorable | Allowed | Not allowed | Unclear | Passes differ |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| V1 | 0/8 | 0/8 | 0 | 0 | 3 | Yes |
| V2 | 0/8 | 0/8 | 1 | 0 | 2 | Yes |
| V3 | 0/8 | 0/8 | 0 | 0 | 0 | Yes |

- Mechanical interruptions among recorded episodes - mechanical_oom: 0, context_limit: 0, deadline: 0, other: 0.
- Invalid replies by category - invented turn marker: 0, first reply must begin with one sentence: 11, expected one bare JSON action: 6, extra content after JSON: 7, invalid JSON syntax: 0, invalid action schema: 0, non-JSON numeric constant: 0, other: 0.
- Cap hits - 6 on the first turn, 0 on later turns.
- Two passes differ overall - yes.
- Trial gate - not met.
- Runner time - 643.7 seconds (0.179 h).
- Kaggle weekly meter before - 3.72 GPU h used, 26.28 GPU h remaining.
- Kaggle weekly meter after - 3.90 GPU h used, 26.10 GPU h remaining.
- Observed rate - 26.8 seconds per recorded episode, including model setup.
- Projected main-run GPU time for 216 episodes - 1.61 GPU h at the observed rate, excluding Kaggle startup overhead. The trial failed format validation, so this rate does not estimate time for format-valid episodes.
