# FT1 final analysis at 01992b34 (exploratory, $0)

Run once by Sol on 2026-11-22, on all 16 FT1 test parts at cb5b8657 and the 13 FT1 gate eligibilities, with `python -m exploratory.ft1.aggregate_events` at `01992b34570124af78ca4a201164d5f8993001c4`. Sol ran it because it reads the sealed cases; Claude saw only this aggregate output.

- **`ft1-final.json`** (SHA-256 `c536636d1d6871dadcac09a39dfff85cefb92a668abb8e610073edd4e6dad811`): the registered P1–P5 verdicts and per-model aggregates. It contains no case ids or case text: checked against all 48 case ids, none appears.
- **Inputs:** combined events `96c0454a…` and combined gate eligibility `70f73c1a…`. They are built from the 16 manifest-verified test outputs and the 13 gate eligibility files, and are kept off the public repo with the test outputs.
- **Not produced:** the pressure split (`python -m exploratory.ft1.analysis`) stopped with `ValueError: matching outside-sphere flags required` and wrote nothing. See `LAB_NOTEBOOK.md`, 2026-11-22.
