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

### v0.3 live test note — 2026-10-14
- First supplied live test after user-confirmed implementation: Think=OFF comparison of Cutty Sark and Ballantine's.
- Outcome: no supported, balanced final answer in the supplied trace; irrelevant first search, second search had a page naming both brands, one successful fetch with incomplete coverage due truncation, one `suspect-search-result` block, one duplicate fetch skip, and raw textual pseudo tool-call requests after the displayed tool budget.
- Behavioral improvement is not established. See the v0.3 README for summary and the private dated handoff record for the full evidence.

### Second live test of Search Query Rules v0.3 — Think=XHIGH — 2026-10-14
- Search 2 included a direct comparative tasting result for Ballantine, Johnnie Walker Red and Cutty Sark, but both Fetch calls instead targeted Cutty Sark-specific pages.
- The final answer was normal prose and transparently disclosed missing Ballantine evidence; no textual pseudo-tool-call sequence was observed in the supplied trace.
- Still no evidence of a complete, balanced comparison. The OFF/XHIGH outcomes are single runs and must not be treated as a controlled measure of Think-mode effect.
- Detailed trace: https://github.com/kco1632-dev/for-chatgpt/blob/main/records/2026-10-14-post-v03-live-thinkxhigh-comparison-test.md.

## v1.0.1-rc1 — 2026-10-14
- Candidate only; not installed or live-tested.
- Source: user-confirmed B1 prompt variant on `experiment/compare-fetch-balance-prompt-v1`, blob SHA `af43d4bcabd044b13b79eb2109a35107b79899fb`.
- Changes only rule 26: removes the fixed 2-search / 2-fetch quotas from the system prompt and leaves actual call limits to the available tools and enforced controls.
- Preserves all other B1 content. The separate user-confirmed Search Query Rules v0.3 block is unchanged.
- Does not change Function code, Valve values, service configuration, or deployed prompts.
- Candidate file: `system-prompts/candidates/v1.0.1-rc1/Bonsai2-WebSearch-SystemPrompt.txt`.
