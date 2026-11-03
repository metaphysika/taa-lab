# Independent permissibility labels (EXPLORATORY)

- Labeler: Astra (gpt-6-astra, reasoning effort high), started as a fresh child task from Claude's
  orchestrator thread on 2026-11-03. It was told to read only a copy of `blind_packet/` (48 case
  files plus INSTRUCTIONS.txt) and nothing else in the repository, briefs or worktrees.
  Blindness was enforced only by that instruction, not by technical isolation.
- The copy Astra received was byte-identical to `blind_packet/` at PR #79 head 44d2ffd5
  (checked by comparing the concatenated sorted files).
- Output: `astra_labels.json`, copied unchanged, SHA-256
  `2ec1a11888572223fde41e467b042b35681bac7845bf0eb859c3e8baba11f3bf`.
- Counts: 24 permitted, 24 not permitted, 0 genuinely ambiguous.
- Agreement with the intended labels in `cases.json` (matched through `blind_id_map.json` by Claude):
  48/48 IDs present, each once, and 48/48 agree. No case is contested, so no case is unresolved on
  the planned denominators.
- Limits: Astra is a separate model call, from the same provider family as the case author (Sol),
  not a human. Full agreement also suggests the cases are clear-cut; development headroom is still
  unknown.
