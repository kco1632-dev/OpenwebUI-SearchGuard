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

- **Status:** Candidate only; not deployed or live-tested.
- **File:** [candidates/v1.0.1-rc1/Bonsai2-WebSearch-SystemPrompt.txt](candidates/v1.0.1-rc1/Bonsai2-WebSearch-SystemPrompt.txt)
- **Source:** User-confirmed B1 prompt variant on `experiment/compare-fetch-balance-prompt-v1`, blob SHA `af43d4bcabd044b13b79eb2109a35107b79899fb`.
- **Change:** Removes the fixed numeric limit of 2 `search_web` calls and 2 `fetch_url` calls from rule 26; replaces it with efficient-budgeting guidance that defers to available tools and enforced limits.
- **Scope:** All other B1 text, including the comparison-fetch guidance in rule 10, is preserved. The active `[Bonsai2 Search Query Rules v0.3]` block remains a separate layer.
- **Promotion gate:** Install only after review; then verify the exact text and perform a bounded Mac Pro comparison test. Do not treat candidate creation as deployment or proof of improved results.

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
| v1.0.1-rc1 | 2026-10-14 | Candidate only | Based on the user-confirmed B1 prompt; removes fixed search/fetch counts from rule 26. |
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
