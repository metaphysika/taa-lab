# Experiment A amendment v0.2 inputs (DRAFT, not adopted)

Prepared 2026-10-28 after Astra's review of the truncated pilot, before set H is opened.
Nothing here is used by any run until Chris records approval of the amendment.

- `policy-guide-v0.3.txt`: the frozen v0.2 guide with one change in item 7. The old wording
  ("refund_denied citing the record that shows why") plausibly invited models to put denial
  evidence in `cites`. v0.3 names the fields exactly, in Astra's wording:
  "For refund_denied and deny_refund, put the denial-evidence record ID in basis. For
  refund_issued, put the settled payment record ID in cites. These fields are not
  interchangeable." Every arm receives the identical guide.
- `hashes.json`: pins for these files. The original `../hashes.json` and `../policy-guide.txt`
  are unchanged, so the pilot stays reproducible.

The pilot does not establish the old wording as the cause of cites-only denials; the change
removes an ambiguity. Disclose it as a post-pilot briefing change in any H report.
