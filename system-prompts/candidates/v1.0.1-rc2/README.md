# v1.0.1-rc2 — SearchGuard-managed budget and response language

**Status:** Candidate only. This GitHub change does not install or deploy the prompt, and no live behavior test has been run for this candidate.

## Source and scope

- Base: `system-prompts/candidates/v1.0.1-rc1/Bonsai2-WebSearch-SystemPrompt.txt`
- Base blob SHA: `02548f059d807697a3a820900015587542f6e6c4`
- This candidate changes rule 26 to defer the permitted `search_web` and `fetch_url` call counts to the active SearchGuard configuration and applicable tool/platform limits.
- Adds rule 45: respond in the user's language unless explicitly instructed otherwise.
- Preserves the rest of the source prompt, including the comparison-fetch guidance in rule 10.
- This is the standalone Bonsai2 web-search system prompt. The separate `[Bonsai2 Search Query Rules v0.3]` block and rules injected by the SearchGuard Function remain separate layers.

## Validation

- The expected rule 26 source block matched before replacement.
- Rule 45 did not exist in the source and was appended as the new rule.
- No Function source, Valve values, service configuration, or runtime prompt field was changed.
- Candidate text should be reviewed and compared with the intended Open WebUI prompt field before any deployment. Runtime behavior remains unverified.
