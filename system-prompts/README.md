# System prompt version history

This folder versions the **standalone Bonsai2 web-search system prompt** kept at repository root as `Bonsai2-WebSearch-SystemPrompt.txt`.

## Versioning policy

See the [prompt versioning workflow](PROMPT-VERSIONING-WORKFLOW.md) for the required process for snapshots, candidates, user-confirmed deployment status, behavioral evaluation, and new-session handoff.

- Keep the root file as the working repository prompt. Do not silently replace it when drafting an experiment.
- Every versioned snapshot is immutable. Create a new version file for every change; never edit an old snapshot in place.
- Keep untested drafts under `candidates/` and label them as candidates. A candidate is not the active prompt.
- Promote a candidate only after the prompt actually loaded in Open WebUI has been compared with the candidate and the deployment has been explicitly confirmed.
- Record the Git commit, test result, and deployment confirmation in the version history whenever a candidate is promoted.
- The standalone prompt and the additional rules injected by the SearchGuard Function are separate layers. SearchGuard-injected rules remain versioned with the corresponding Function source; do not treat this folder as proof that the deployed Function code is identical.

## Current repository baseline

- **Version:** `v1.0.0`
- **Status:** First named, immutable baseline of the repository prompt as of 2026-10-14. Runtime deployment equivalence has not been independently verified by this GitHub operation.
- **Source:** `Bonsai2-WebSearch-SystemPrompt.txt` on `main`
- **Source blob SHA:** `db774613655bcc9be7343605eea0141f19f4777a`
- **Snapshot:** [versions/v1.0.0/Bonsai2-WebSearch-SystemPrompt.txt](versions/v1.0.0/Bonsai2-WebSearch-SystemPrompt.txt)
- **Historical note:** The existing GitHub path history shows the prompt file was first added on 2026-10-06 in commit `2afdf5d155589e6baed3c8d2feab92783b85d1e9`. No earlier version of this file is present in this repository's recorded path history. Git history of the root file remains preserved.

## Candidates

### v1.0.1-rc1

- **Status:** User-reported implemented; the user confirmed that the prompt text installed in the relevant Open WebUI system-prompt fields matched this candidate. The runtime field was not independently read back by this GitHub operation.
- **File:** [candidates/v1.0.1-rc1/Bonsai2-WebSearch-SystemPrompt.txt](candidates/v1.0.1-rc1/Bonsai2-WebSearch-SystemPrompt.txt)
- **Source:** User-confirmed B1 prompt variant on `experiment/compare-fetch-balance-prompt-v1`, blob SHA `af43d4bcabd044b13b79eb2109a35107b79899fb`.
- **Change:** Removes the fixed numeric limit of 2 `search_web` calls and 2 `fetch_url` calls from rule 26; replaces it with guidance to use available tools efficiently and respect enforced limits.
- **Scope:** All other B1 text, including the comparison-fetch guidance in rule 10, is preserved. The active `[Bonsai2 Search Query Rules v0.3]` block remains a separate layer.
- **Behavior validation:** Existing live comparison traces did not establish a complete, balanced comparison or isolate the behavioral effect of this prompt variant. Do not infer improvement from text identity alone.

### v1.0.1-rc2

- **Status:** Candidate only; not installed as part of this GitHub operation and not live-tested.
- **File:** [candidates/v1.0.1-rc2/Bonsai2-WebSearch-SystemPrompt.txt](candidates/v1.0.1-rc2/Bonsai2-WebSearch-SystemPrompt.txt)
- **Base:** `v1.0.1-rc1`, blob SHA `02548f059d807697a3a820900015587542f6e6c4`.
- **Changes:** Rewrites rule 26 so permitted `search_web` and `fetch_url` counts are determined by the active SearchGuard configuration and applicable tool/platform limits; adds rule 45 to respond in the user's language unless explicitly instructed otherwise.
- **Preserved:** Other prompt text, including the comparison-fetch guidance in rule 10, is unchanged from v1.0.1-rc1.
- **Scope:** Standalone Bonsai2 web-search system prompt only. No Function code, Valve values, service configuration, or runtime prompt field was changed.
- **Next step:** Review the candidate, compare its exact text before any deliberate installation, and keep any behavior test separate from text-match verification.

### v1.1.0-rc1

- **Version:** `v1.1.0-rc1`
- **Status:** Draft only; not deployed and not tested.
- **File:** [candidates/v1.1.0-rc1/Bonsai2-WebSearch-SystemPrompt.txt](candidates/v1.1.0-rc1/Bonsai2-WebSearch-SystemPrompt.txt)
- **Change:** Appends comparison-specific research planning and URL-integrity rules. The existing v1.0.0 body is otherwise preserved.
- **Reason:** In the 2026-10-14 Cutty Sark vs Ballantine's test, the model fetched a second page about the already-covered subject in one run, and in another run attempted a URL absent from the search results. The candidate directs the next fetch toward the missing comparison subject and prohibits guessing fetch URLs.
- **Promotion gate:** Test the same comparison prompt with SearchGuard's existing limits unchanged; verify the second fetch uses an actual search-result URL for the missing subject and the final answer distinguishes verified facts from gaps. Do not mark this candidate active based on offline review alone.

## History

| Version | Date | Status | Summary |
|---|---|---|---|
| v1.0.0 | 2026-10-14 | Repository baseline; live status unverified | Exact snapshot of the existing root prompt. |
| v1.0.1-rc1 | 2026-10-14 | User-reported implemented; behavior not isolated | Removes fixed search/fetch counts from rule 26. |
| v1.0.1-rc2 | 2026-10-25 | Candidate only | Makes rule 26 explicitly defer quota to active SearchGuard/tool limits; adds rule 45 for matching the user's language. |
| v1.1.0-rc1 | 2026-10-14 | Candidate only | Adds comparison evidence balancing and exact search-result URL rules. |

## User-confirmed active system-prompt block

The user confirmed on **2026-10-14** that the following rule block has been implemented in the active Open WebUI system prompt and matches the text supplied in the conversation:

- **Block version:** `[Bonsai2 Search Query Rules v0.3]`
- **Status:** User-confirmed implemented; the running prompt text was not independently read back from the application by this GitHub operation.
- **Snapshot:** [system-prompts/search-query-rules/v0.3/Bonsai2-Search-Query-Rules.txt](search-query-rules/v0.3/Bonsai2-Search-Query-Rules.txt)
- **Record:** [system-prompts/search-query-rules/v0.3/README.md](search-query-rules/v0.3/README.md)

This prompt block is tracked separately from the standalone root prompt and from rules injected dynamically by SearchGuard Function code. Do not infer that those different layers have identical text or versions.

Subsequent changes should use a new immutable versioned file and update `VERSION_HISTORY.md`. Keep the user's implementation confirmation distinct from independent runtime verification.

## v0.3 behavior evaluation

The user-confirmed `[Bonsai2 Search Query Rules v0.3]` now has two recorded post-implementation live tests (Think=OFF and Think=XHIGH, 2026-10-14). Neither produced a complete, balanced comparison. OFF ended with textual pseudo-tool-call output; XHIGH produced a normal answer but fetched two pages about the same comparison subject despite a direct comparison result being available. These are single runs, not a controlled Think-mode comparison. See [v0.3 record](search-query-rules/v0.3/README.md) and its linked private detailed traces.
