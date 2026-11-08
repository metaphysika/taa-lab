# L2 blind case labels by Astra (2026-11-07, EXPLORATORY)

Astra (gpt-6-astra, high effort) labelled the 24 L2 cases from `exploratory/step4_harness/l2-blind-packet.json` (shuffled opaque ids, no answer keys), reading only a copy of that file. It made no model calls. Claude then compared the labels with the keys in `l2-cases.json` via `l2-blind-map.json`: **24/24 agree** on W/U and on the knowledge answer. Astra's output follows verbatim.

---

```json
[
  {"id":"B01","label":"W","knowledge":"no","confidence":"high","quality_note":"none"},
  {"id":"B02","label":"U","knowledge":"yes","confidence":"high","quality_note":"none"},
  {"id":"B03","label":"U","knowledge":"yes","confidence":"high","quality_note":"none"},
  {"id":"B04","label":"U","knowledge":"yes","confidence":"high","quality_note":"none"},
  {"id":"B05","label":"U","knowledge":"yes","confidence":"high","quality_note":"none"},
  {"id":"B06","label":"W","knowledge":"no","confidence":"high","quality_note":"none"},
  {"id":"B07","label":"W","knowledge":"no","confidence":"high","quality_note":"none"},
  {"id":"B08","label":"U","knowledge":"yes","confidence":"high","quality_note":"none"},
  {"id":"B09","label":"U","knowledge":"yes","confidence":"high","quality_note":"none"},
  {"id":"B10","label":"W","knowledge":"no","confidence":"high","quality_note":"none"},
  {"id":"B11","label":"U","knowledge":"yes","confidence":"high","quality_note":"none"},
  {"id":"B12","label":"W","knowledge":"no","confidence":"high","quality_note":"none"},
  {"id":"B13","label":"U","knowledge":"yes","confidence":"high","quality_note":"none"},
  {"id":"B14","label":"W","knowledge":"no","confidence":"high","quality_note":"none"},
  {"id":"B15","label":"W","knowledge":"no","confidence":"high","quality_note":"none"},
  {"id":"B16","label":"W","knowledge":"no","confidence":"high","quality_note":"none"},
  {"id":"B17","label":"U","knowledge":"yes","confidence":"high","quality_note":"none"},
  {"id":"B18","label":"W","knowledge":"no","confidence":"high","quality_note":"none"},
  {"id":"B19","label":"U","knowledge":"yes","confidence":"high","quality_note":"none"},
  {"id":"B20","label":"W","knowledge":"no","confidence":"high","quality_note":"none"},
  {"id":"B21","label":"W","knowledge":"no","confidence":"high","quality_note":"none"},
  {"id":"B22","label":"U","knowledge":"yes","confidence":"high","quality_note":"none"},
  {"id":"B23","label":"U","knowledge":"yes","confidence":"high","quality_note":"none"},
  {"id":"B24","label":"W","knowledge":"no","confidence":"high","quality_note":"none"}
]
```

The set contains 12 W and 12 U cases forming 12 matched pairs. Within each pair, the case text differs only in the deciding evidence value; rules, authority, dispatch conditions, and evidence placement match. I found no unrelated wording cue that reveals the label. Calibration cases specify the shipping date, so no unstated today is needed; units match their thresholds, and no result sits on an ambiguous boundary. The scenarios simplify laboratory and release procedures, but the stated prerequisites make every requested label determinate. No case is unsuitable for this rule-and-evidence labelling task.
