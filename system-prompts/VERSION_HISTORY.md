# Version history

## v1.0.0 — 2026-10-14
- Initial immutable snapshot of the existing `Bonsai2-WebSearch-SystemPrompt.txt` from `main`.
- Content copied without edits.
- Source blob SHA: `db774613655bcc9be7343605eea0141f19f4777a`.
- Status: repository baseline; actual live deployment equivalence not independently verified.

## v1.1.0-rc1 — 2026-10-14
- Candidate draft; not deployed.
- Keeps the v1.0.0 prompt intact and appends six comparison-research and URL-integrity rules.
- Target failures: duplicate fetch coverage of one comparison side and guessing a URL not present in search results.
- Requires a live test before promotion.

## Search Query Rules v0.3 — 2026-10-14
- Status: user-confirmed implemented in the active Open WebUI system prompt.
- The user confirmed the active text is identical to the 50-rule block supplied in the conversation.
- Immutable snapshot: `system-prompts/search-query-rules/v0.3/Bonsai2-Search-Query-Rules.txt`.
- The GitHub operation records the user's confirmation; it did not independently inspect the running Open WebUI prompt.
- This is a separate prompt layer from the standalone `Bonsai2-WebSearch-SystemPrompt.txt` and from SearchGuard Function-injected rules.
