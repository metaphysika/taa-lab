# FT1 data repair: same-cell candidate refusal

2026-11-12. Master Plan v3.2 FT1; handoff 2026-11-12 ft1-repair. Base 97fe558b; comparison 91855bb8. Chris chose option 1 after seeing the failed job (a) result. The stage thread owns the notebook disclosure.

Generation now refuses every infeasible training candidate under the unchanged gates. It replaces lawful/wrongful twins and sphere twins as units. Thirty-five slots change: 20 infeasible originals and 15 twin companions. All 1,965 other records are byte-identical in all five arms, including IDs, selected variants, prefixes, metadata and counts. No ordering spillover occurs.

The original signed-balance trajectory is computed separately to preserve selections for unchanged records. For an infeasible original, the nearest delta is used only as a historical ordering reference; that record is never emitted. Replacement selections use the original slot balance. Actual repaired totals are checked independently against the unchanged aggregate gate.

Cell equality covers type, theme, evidence type, lookup, correction/failure, outside-sphere, pressure, holder, normalized action step, tool/argument shape, lower-fee lawful-route status, and the same fields in arms 1 and 4. Recipient names are randomly assigned, not balanced cell fields. Every joint cell count is identical to 91855bb8. Pairs retain the original twin construction: a 600-index serial offset for lawful/wrongful records, and adjacent shared scenario indices for sphere pairs. Replacement candidates are searched in ascending index order from 10000, with used indices excluded; exhaustion at 110000 stops the build.

Probes are byte-identical to 91855bb8. Held-out cards and sealed source are unchanged. Replacements use train partition IDs and evidence categories 0–3; held-out/sealed categories use category 4. No replacement ID or theme/evidence combination overlaps those partitions. Unique IDs: 2,000 per arm. No sealed text, labels or outputs are included.

## Real-tokenizer measurements

Delta minimum/median/maximum: -9 / 0.0 / 9. Smallest headroom: 0.00 tokens. Arm 2 total 320412; arm 3 total 320440; signed difference -28. Per-record failures: 0. Aggregate gate: PASS. No two-token margin was imposed.

```json
{
  "delta_histogram": {
    "-9": 2,
    "-8": 13,
    "-7": 12,
    "-6": 25,
    "-5": 25,
    "-4": 65,
    "-3": 113,
    "-2": 219,
    "-1": 344,
    "0": 383,
    "1": 332,
    "2": 202,
    "3": 124,
    "4": 62,
    "5": 30,
    "6": 25,
    "7": 16,
    "8": 6,
    "9": 2
  },
  "training_distributions": {
    "1": {
      "prompt": {
        "count": 2000,
        "min": 219,
        "median": 267.0,
        "max": 318
      },
      "trained": {
        "count": 2000,
        "min": 12,
        "median": 17.5,
        "max": 24
      },
      "total": {
        "count": 2000,
        "min": 242,
        "median": 285.0,
        "max": 330
      }
    },
    "2": {
      "prompt": {
        "count": 2000,
        "min": 217,
        "median": 293.0,
        "max": 390
      },
      "trained": {
        "count": 2000,
        "min": 101,
        "median": 156.0,
        "max": 257
      },
      "total": {
        "count": 2000,
        "min": 337,
        "median": 453.0,
        "max": 576
      }
    },
    "2u": {
      "prompt": {
        "count": 2000,
        "min": 217,
        "median": 293.0,
        "max": 390
      },
      "trained": {
        "count": 2000,
        "min": 12,
        "median": 23.0,
        "max": 30
      },
      "total": {
        "count": 2000,
        "min": 240,
        "median": 319.0,
        "max": 402
      }
    },
    "3": {
      "prompt": {
        "count": 2000,
        "min": 217,
        "median": 293.0,
        "max": 390
      },
      "trained": {
        "count": 2000,
        "min": 103,
        "median": 156.0,
        "max": 258
      },
      "total": {
        "count": 2000,
        "min": 337,
        "median": 453.0,
        "max": 576
      }
    },
    "4": {
      "prompt": {
        "count": 2000,
        "min": 183,
        "median": 211.5,
        "max": 242
      },
      "trained": {
        "count": 2000,
        "min": 12,
        "median": 17.0,
        "max": 30
      },
      "total": {
        "count": 2000,
        "min": 205,
        "median": 228.0,
        "max": 254
      }
    }
  },
  "probe_distributions": {
    "1": {
      "prompt": {
        "count": 40,
        "min": 229,
        "median": 262.0,
        "max": 297
      },
      "trained": {
        "count": 40,
        "min": 12,
        "median": 17.5,
        "max": 23
      },
      "total": {
        "count": 40,
        "min": 252,
        "median": 283.0,
        "max": 309
      }
    },
    "2u": {
      "prompt": {
        "count": 40,
        "min": 240,
        "median": 288.5,
        "max": 341
      },
      "trained": {
        "count": 40,
        "min": 12,
        "median": 23.0,
        "max": 29
      },
      "total": {
        "count": 40,
        "min": 263,
        "median": 312.5,
        "max": 353
      }
    },
    "4": {
      "prompt": {
        "count": 40,
        "min": 184,
        "median": 209.0,
        "max": 240
      },
      "trained": {
        "count": 40,
        "min": 12,
        "median": 17.0,
        "max": 29
      },
      "total": {
        "count": 40,
        "min": 206,
        "median": 228.5,
        "max": 252
      }
    }
  },
  "over_limit_counts": {
    "trained": 0,
    "total": 0
  },
  "changed_slots_per_arm": {
    "1": [
      16,
      50,
      55,
      92,
      95,
      132,
      174,
      175,
      290,
      292,
      413,
      416,
      450,
      458,
      530,
      534,
      616,
      650,
      655,
      692,
      695,
      732,
      774,
      775,
      890,
      892,
      1013,
      1016,
      1050,
      1058,
      1220,
      1221,
      1414,
      1456,
      1494
    ],
    "2": [
      16,
      50,
      55,
      92,
      95,
      132,
      174,
      175,
      290,
      292,
      413,
      416,
      450,
      458,
      530,
      534,
      616,
      650,
      655,
      692,
      695,
      732,
      774,
      775,
      890,
      892,
      1013,
      1016,
      1050,
      1058,
      1220,
      1221,
      1414,
      1456,
      1494
    ],
    "2u": [
      16,
      50,
      55,
      92,
      95,
      132,
      174,
      175,
      290,
      292,
      413,
      416,
      450,
      458,
      530,
      534,
      616,
      650,
      655,
      692,
      695,
      732,
      774,
      775,
      890,
      892,
      1013,
      1016,
      1050,
      1058,
      1220,
      1221,
      1414,
      1456,
      1494
    ],
    "3": [
      16,
      50,
      55,
      92,
      95,
      132,
      174,
      175,
      290,
      292,
      413,
      416,
      450,
      458,
      530,
      534,
      616,
      650,
      655,
      692,
      695,
      732,
      774,
      775,
      890,
      892,
      1013,
      1016,
      1050,
      1058,
      1220,
      1221,
      1414,
      1456,
      1494
    ],
    "4": [
      16,
      50,
      55,
      92,
      95,
      132,
      174,
      175,
      290,
      292,
      413,
      416,
      450,
      458,
      530,
      534,
      616,
      650,
      655,
      692,
      695,
      732,
      774,
      775,
      890,
      892,
      1013,
      1016,
      1050,
      1058,
      1220,
      1221,
      1414,
      1456,
      1494
    ]
  },
  "length_profile": {
    "refused": {
      "count": 20,
      "min": 147,
      "median": 173.0,
      "max": 196
    },
    "retained": {
      "count": 1980,
      "min": 103,
      "median": 155.5,
      "max": 258
    }
  }
}
```

## Refusals and replacements

The table uses original slot IDs; replacement IDs are train-ACC plus the numeric index shown. A companion was replaced to preserve its twin, without itself failing the gate. Cells are numeric codes in order: type (wrongful/lawful/sphere/recipient/correction), theme (THEMES order), evidence (EVIDENCE order), lookup, correction (none/missed_fact/wrong_judgment/obedience_limit/not_carried_out), outside, pressure, holder (HOLDERS order), step (sorted normalized step index). Indices are zero-based; boolean fields use 0/1. The code also verifies both control-arm cells.

| Slot | Replacement | Failed gate | Cell |
|---|---|---|---|
| 00016 | 10096 | 1 | 0,6,1,1,0,0,1,0,5 |
| 00616 | 10696 | 0 | 1,6,1,1,0,0,1,0,4 |
| 00050 | 10130 | 1 | 0,0,1,1,0,0,1,2,1 |
| 00650 | 10730 | 0 | 1,0,1,1,0,0,1,2,10 |
| 00055 | 10135 | 1 | 0,5,1,0,0,0,0,3,1 |
| 00655 | 10735 | 0 | 1,5,1,0,0,0,0,3,10 |
| 00092 | 10012 | 0 | 0,2,1,1,0,0,0,0,0 |
| 00692 | 10612 | 1 | 1,2,1,1,0,0,0,0,0 |
| 00095 | 10015 | 1 | 0,5,1,0,0,0,0,3,0 |
| 00695 | 10615 | 0 | 1,5,1,0,0,0,0,3,0 |
| 00132 | 10692 | 0 | 0,2,1,1,0,0,0,0,3 |
| 00732 | 11292 | 1 | 1,2,1,1,0,0,0,0,3 |
| 00174 | 10254 | 0 | 0,4,1,1,0,0,0,2,5 |
| 00774 | 10854 | 1 | 1,4,1,1,0,0,0,2,4 |
| 00175 | 10255 | 1 | 0,5,1,0,0,0,0,3,5 |
| 00775 | 10855 | 0 | 1,5,1,0,0,0,0,3,4 |
| 00290 | 10370 | 1 | 0,0,1,1,0,0,1,2,3 |
| 00890 | 10970 | 0 | 1,0,1,1,0,0,1,2,3 |
| 00292 | 10052 | 1 | 0,2,1,1,0,0,0,0,3 |
| 00892 | 10652 | 0 | 1,2,1,1,0,0,0,0,3 |
| 00413 | 10013 | 0 | 0,3,1,0,0,0,0,1,0 |
| 01013 | 10613 | 1 | 1,3,1,0,0,0,0,1,0 |
| 00416 | 10016 | 0 | 0,6,1,1,0,0,1,0,0 |
| 01016 | 10616 | 1 | 1,6,1,1,0,0,1,0,0 |
| 00450 | 10050 | 1 | 0,0,1,1,0,0,1,2,3 |
| 01050 | 10650 | 0 | 1,0,1,1,0,0,1,2,3 |
| 00458 | 10058 | 0 | 0,8,1,1,0,0,1,2,3 |
| 01058 | 10658 | 1 | 1,8,1,1,0,0,1,2,3 |
| 00530 | 10290 | 1 | 0,0,1,1,0,0,1,2,1 |
| 00534 | 10134 | 1 | 0,4,1,1,0,0,0,2,1 |
| 01220 | 10100 | 1 | 2,0,1,1,0,1,1,2,0 |
| 01221 | 10101 | 0 | 2,0,1,1,0,0,1,2,10 |
| 01414 | 10014 | 1 | 3,4,1,1,0,0,0,2,1 |
| 01456 | 10056 | 1 | 3,6,1,1,0,0,1,0,1 |
| 01494 | 10174 | 1 | 3,4,1,1,0,0,0,2,1 |

Additional infeasible candidates beyond the original 20: [10054, 10094, 10810, 10812]. Their units were refused before emission. The refused originals have arm 3 trained lengths {'count': 20, 'min': 147, 'median': 173.0, 'max': 196}; retained originals {'count': 1980, 'min': 103, 'median': 155.5, 'max': 258}. Refused originals are longer at the median; this is a post-result length-dependent selection change, not evidence about model behavior.


Additional candidate refusals (the whole candidate unit is discarded):

| Candidate | Original unit | Accepted replacement unit | Cell matched to original slot |
|---|---|---|---|
| 10812 | [132, 732] | [10692, 11292] | 732 |
| 10810 | [290, 890] | [10370, 10970] | 890 |
| 10054 | [1494] | [10174] | 1494 |
| 10094 | [1494] | [10174] | 1494 |

## Reproduction and validation

The committed selection_expected.json stores IDs and numbers only: ID, zero-based reason variant, whole-line prefix count, expected arm 2/3 trained counts, and refusal/replacement indices. Job (a) compares its own real counts and selections exactly, and refuses a mismatch before writing data. The table is included in the exact-commit source inventory. Synthetic offline builds do not depend on matching Gemma counts.

Both notebook stagers supply Python 3 kernelspec metadata. FT1_GEMMA3_TOKENIZER_DIR provides local template discovery without injected test hooks. Local Python 3.12.10 versus prior Kaggle Python 3.13.18; transformers 5.20.2 and tokenizers 0.23.3. No Kaggle rerun was performed, so cross-version reproduction remains for separately authorized job (a).

Five tokenizer hashes verified before counting (private assets remain outside the repo):

```json
{
  "tokenizer.json": "7d4046bf0505a327dd5a0abbb427ecd4fc82f99c2ceaa170bc61ecde12809b0c",
  "tokenizer.model": "1299c11d7cf632ef3b4e11937501358ada021bbdf7c47638d13c0ee982f2e79c",
  "tokenizer_config.json": "10a27b015a8c561aee8fb959b949e63b6c11b67965c0eccf519e6375439f092e",
  "special_tokens_map.json": "2f7b0adf4fb469770bb1490e3e35df87b1dc578246c5e7e6fc76ecf33213a397",
  "added_tokens.json": "50b2f405ba56a26d4913fd772089992252d7f942123cc0a034d96424221ba946"
}
```

Validation: `python scripts/run_fast_checks.py` PASS, 645 tests plus all scripted scenarios, in C:/t/ft1-repair-check (isolated checkout with retained fixtures; scripted outputs stay there). `python -m unittest tests.test_ft1_offline tests.test_ft1_preparation tests.test_ft1_runner -v` PASS, 48 tests with one template-discovery skip in the system Python. The real-template test separately PASS, 1 test with no skip, in the specified tokenizer venv using FT1_GEMMA3_TOKENIZER_DIR. Four refusal/table/source-binding regressions are included in the 48. Real-tokenizer generation, exact expected-table comparison, baseline byte comparison, cell-count equality and probe byte comparison PASS. Initial suite attempts in the tokenizer-only venv failed for missing test dependencies; the installed system Python supplied them without installations. Two old diagnostic expectations were updated to assert training-pool refusal and retain held-out limit-report coverage. `git diff --check` PASS. Hosted CI and fresh review are not established by these local checks. No Kaggle, Modal or model calls; no dependencies added. No results or LAB_NOTEBOOK edits. The old failed job remains failed.
