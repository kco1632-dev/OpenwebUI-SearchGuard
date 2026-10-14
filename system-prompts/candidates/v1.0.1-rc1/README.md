# v1.0.1-rc1 — valve-managed search budget

**Status:** Candidate only. Not installed in Open WebUI and not live-tested.

## Source and scope

- Source variant: user-confirmed B1 prompt variant on branch `experiment/compare-fetch-balance-prompt-v1`.
- Source path: `Bonsai2-WebSearch-SystemPrompt.txt`.
- Source blob SHA: `af43d4bcabd044b13b79eb2109a35107b79899fb`.
- Change: replace the fixed 2-search / 2-fetch limits in rule 26 with instructions to use available tools efficiently and obey enforced limits.
- Existing evidence-quality rules, B1 comparison-fetch rule 10, and all other text are preserved.
- The separate `[Bonsai2 Search Query Rules v0.3]` block remains a separate prompt layer and is not copied or modified here.

## Intended configuration

- The shared system prompt gives research-planning and evidence-selection guidance without prescribing a fixed numeric quota.
- SearchGuard Valve settings remain the authoritative quota layer: model-specific values are managed using the already-established G14 / Mac Pro separation.
- This candidate does not modify Function code, Valve values, services, or runtime configuration.

## Change validation

- Exact source block matched once before replacement.
- Only rule 26 was changed; all other source text was preserved byte-for-byte.
- Runtime installation and behavior remain unverified.
