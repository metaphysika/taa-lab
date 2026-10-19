# Returned v02419 artifact preservation

All four original uploads and all twenty extracted files are preserved in the
workspace at received-evidence-001/, and remain in the owner's original returned
ZIP and private Modal evidence Volume. None are deleted or modified. The intake
integrity.json contains SHA-256 hashes for every file, including private files.

Do not publish the complete ZIP, random tiny checkpoint model.safetensors or
full tokenizer/tokenizer.json in Git. The ZIP contains those private artifacts.
The repository carries the receipts, logs, configuration, data summaries,
readable supervision examples and integrity hashes. This is a storage/privacy
choice, not evidence removal. No adapter was trained in the stopped attempt.

When auditing a repository-only clone, obtain the owner's original ZIP privately
and verify its hash, then extract its twenty members into the recorded paths;
all listed intake hashes must match. Do not regenerate or replace evidence.
