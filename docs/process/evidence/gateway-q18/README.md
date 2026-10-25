# [Descriptive] Q18 offline repair evidence

[Descriptive] `validation.json` is the final machine-readable verification and archive manifest. `acceptance.zip` contains the complete new offline comparison journal, frozen/permanent/MCP acceptance reports, full discovery output, pre-change failures, initial diagnostics, authored fixtures, source snapshots and scripted reports. The inner verification snapshot precedes the final archive hash and documentation closure; the outer manifest records the final archive hash.

[Descriptive] Archive SHA-256: `b09ee9e88a7b6844f91610c19d1925cebc108a6d298db4469cbf02717ace6768` (17,249,468 bytes, 196 members). CRC and every member hash passed; credential-pattern and exact configured-secret scans found zero matches. Such scans cannot prove absence of unknown credentials. `keys.env` was never read or copied.

[Descriptive] `before-after.json` compares all 364 rule-authored checks with their pre-change and fixed observations. `live-readjudication.json` is the separate six-call supplement, retaining original source identifiers, hashes and reconstructed states. It does not relabel or replace original live results. The original live evidence and prior archives remain unchanged in the results-only PR #38 bundle.

[Descriptive] Review the [91-case expected-outcome table](../../TAA_GATEWAY_Q18_EXPECTATIONS.md), [sensitivity table](../../TAA_GATEWAY_Q18_SENSITIVITY.md) and [Q18 ruling and validation notes](../../TAA_GATEWAY_Q18.md). New journal bytes differ, but all original scores, final worlds and oracle boards match. This bounded offline verification is not empirical H3 evidence or launch approval.
