# System prompt version history

This folder versions the **standalone Bonsai2 web-search system prompt** kept at repository root as `Bonsai2-WebSearch-SystemPrompt.txt`.

## Versioning policy

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

## Candidate

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
| v1.1.0-rc1 | 2026-10-14 | Candidate only | Adds comparison evidence balancing and exact search-result URL rules. |

