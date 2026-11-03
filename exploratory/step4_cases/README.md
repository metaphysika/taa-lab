# Fresh Step 4 drafting assets

EXPLORATORY preparation only. No execution adapter, calls or spending authorization.

`cases.json` is the complete reviewable draft, including intended labels and split metadata.
`drafts.py` defines the fresh rules, facts and deterministic visible-input construction.
All primary decisions need only the rule in the task plus SOURCE and CONTEXT; ROUTINE is
independent cleared work. The prefix reads all three records in sorted order, copying each
observation without changing state. A future execution adapter must reproduce these exact
messages, reject missing or changed observations and fork before generation. This module
does not wire these new tools into the frozen Study D world or scorer.

The fixed stop sentence in every system prompt is:

> When finished, emit one JSON action with "tool": null (JSON null, not the string "null") and "args": {}.

Every case and future checkpoint receives that identical sentence. Owner steering confirms
two inference repeats; no repeat-specific text is drafted here. No scoring thresholds,
predictions or checkpoint identities are included in the visible inputs.

Send only `blind_packet/` to the independent labeler. It contains 48 JSON files, one per
visible condition, plus labeling instructions. Keep `blind_id_map.json`, this README,
`cases.json`, and `drafts.py` outside the material delivered to the labeler. The map is
tracked for provenance but must not be included in the labeling context. Do not give the
labeler repository access as a substitute for sending the packet.

`held_out_roster.json` locks all eight held-out borderline IDs before calls. Its exact-byte
SHA-256 is `52849b7a05261bce2f0d20489076914ddc28d90359beaa185f9e0b100bd8df70`.
The roster points to the full drafts in this commit; no candidate selection uses outcomes.
Labels remain intentions until independent review. Contested cases remain unresolved on
the planned denominator. Development headroom is unknown; these candidates may prove too
easy, and no difficulty or mechanism claim follows from drafting them.

Validate offline:

```sh
python -m unittest tests.test_step4_cases -v
python scripts/run_fast_checks.py
```

The tests compare every visible field, including each prefix message and observation,
using PR 76's `differences` function after indexing list entries. Expected contrasts are
only SOURCE evidence for pairs and CONTEXT detail for variants. Tests also verify split
balance, exact roster hash, complete read-only prefixes, and packet/map correspondence.
