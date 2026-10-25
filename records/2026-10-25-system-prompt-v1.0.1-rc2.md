# System prompt candidate record — v1.0.1-rc2

Date: 2026-10-25 (JST)

## Target and scope

- Repository: `kco1632-dev/OpenWebUI-SearchGuard`
- Branch: `main`
- Layer: standalone Bonsai2 web-search system prompt.
- Candidate: [`system-prompts/candidates/v1.0.1-rc2/Bonsai2-WebSearch-SystemPrompt.txt`](https://github.com/kco1632-dev/OpenWebUI-SearchGuard/blob/main/system-prompts/candidates/v1.0.1-rc2/Bonsai2-WebSearch-SystemPrompt.txt)
- Candidate blob SHA: `659be3d042614fb966676b3928cbfbda0f0df622`
- Base: [`v1.0.1-rc1/Bonsai2-WebSearch-SystemPrompt.txt`](https://github.com/kco1632-dev/OpenWebUI-SearchGuard/blob/main/system-prompts/candidates/v1.0.1-rc1/Bonsai2-WebSearch-SystemPrompt.txt)
- Base blob SHA: `02548f059d807697a3a820900015587542f6e6c4`

## Changes

1. **Rule 26:** Replaced fixed quota wording with explicit guidance that the permitted `search_web` and `fetch_url` calls are determined by the active SearchGuard configuration and applicable tool/platform limits. The prompt does not encode a separate hard-coded numeric quota.
2. **Rule 45:** Added a same-language response rule: unless explicitly instructed otherwise, respond in the user's message language, including Japanese for Japanese input, while preserving other languages where required for quotations, proper nouns, technical terms, or requested translations.

The remaining prompt text, including the comparison-fetch guidance in rule 10, is preserved from v1.0.1-rc1.

## Verification

- Retrieved the source and candidate from GitHub after creation.
- Exact-content comparison confirmed the candidate equals the v1.0.1-rc1 source with only the intended rule 26 replacement and appended rule 45.
- Exactly one rule 26 and one rule 45 were found.
- The former fixed `maximum 2 search_web calls` / `maximum 2 fetch_url calls` wording is absent.
- This is **candidate-text verification only**. The candidate was not installed into Open WebUI by this operation; no live behavior test was run.
- No SearchGuard Function code, Valve values, service configuration, or runtime prompt field was changed.

## Next step

Review the candidate before any deliberate deployment. If installed later, record exact-text confirmation separately from live behavior testing; do not infer improved search quality from the successful GitHub write or text comparison alone.
