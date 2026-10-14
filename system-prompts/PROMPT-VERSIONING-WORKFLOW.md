# System prompt and SearchGuard prompt-versioning workflow

Updated: 2026-10-14

This document is the durable operating procedure for prompt work in this repository. Read it before creating, editing, deploying, or evaluating a SearchGuard-related prompt. For session-specific runtime facts and the next investigation step, also read `kco1632-dev/for-chatgpt/ACTIVE-SEARCHGUARD-INVESTIGATION.md`.

## 1. Keep the prompt layers separate

Do not refer to every prompt artifact as one interchangeable "system prompt." Track these independently:

1. **Standalone Bonsai2 web-search system prompt** — repository root `Bonsai2-WebSearch-SystemPrompt.txt`, plus immutable snapshots under `system-prompts/versions/` and un-deployed drafts under `system-prompts/candidates/`.
2. **Named rule blocks embedded in the active Open WebUI system prompt** — store each exact block separately under `system-prompts/search-query-rules/<version>/`. The user-confirmed active block as of 2026-10-14 is `[Bonsai2 Search Query Rules v0.3]`.
3. **Rules injected dynamically by the SearchGuard Function** — these live in the Python Function source and are versioned with the corresponding Function release. Do not infer they match either of the prompt layers above.

A file existing on GitHub does not prove it is loaded in Open WebUI. Conversely, user confirmation that one named block is active does not prove that the complete assembled prompt is byte-for-byte equal to a separate repository file.

## 2. Current record as of 2026-10-14

- **Standalone repository baseline:** `v1.0.0` is an immutable snapshot of root `Bonsai2-WebSearch-SystemPrompt.txt`; baseline blob SHA `db774613655bcc9be7343605eea0141f19f4777a`. Runtime equality of the whole assembled prompt was not independently read back by GitHub.
- **Standalone prompt experiment B1:** the earlier private handoff records that the user confirmed the live prompt matched `experiment/compare-fetch-balance-prompt-v1/Bonsai2-WebSearch-SystemPrompt.txt` (blob `af43d4bcabd044b13b79eb2109a35107b79899fb`). Its live behavioral improvement was not yet tested in that record. Keep this status distinct from the standalone `v1.1.0-rc1` draft in `system-prompts/candidates/`.
- **Named rule block:** on 2026-10-14 the user confirmed that `[Bonsai2 Search Query Rules v0.3]` had been implemented in the active Open WebUI system prompt and that its text exactly matched the proposed 50-rule block. Immutable snapshot: `system-prompts/search-query-rules/v0.3/Bonsai2-Search-Query-Rules.txt`; blob SHA `cebb5ca54426dd976f4c64f8d260ca00271c261d`.
- **Standalone candidate `v1.1.0-rc1`:** candidate only; not promoted as the active standalone prompt. Do not treat it as the source of truth for the separately confirmed v0.3 rule block.
- **SearchGuard Function:** current user-confirmed deployment remains `0.8.26-fix33-query-repair-instruction-boundary-v1`; do not make unrelated code or valve changes as part of prompt versioning.
- The Think=OFF and Think=XHIGH comparison outputs discussed before the v0.3 confirmation are pre-v0.3 evidence. Do not attribute them to the new block. No isolated post-v0.3 live evaluation is recorded here.

## 3. Required workflow for every change

1. **Identify the layer first.** Determine whether the requested change is to the standalone prompt, a named embedded rule block, or Function-injected instructions. State the exact target in the commit/record.
2. **Read before editing.** Fetch the current source, inspect its version marker and blob SHA, and compare it with the last recorded active snapshot. Never overwrite an archive to "make it current."
3. **Preserve the prior version.** Store an immutable snapshot under a new versioned path before changing anything. Use names such as `v0.4`, `v1.0.1`, or `v1.1.0-rc2` as appropriate to the layer. A small version marker at the start of an actual prompt block is preferred when it does not conflict with the prompt's intended semantics.
4. **Keep candidates distinct.** Drafts go under `candidates/` or a clearly named experiment branch and must be labelled `candidate`, `draft`, or `rc`. A candidate must never silently replace the current snapshot or be called active.
5. **Do not deploy implicitly.** Only mark a prompt active after the user explicitly confirms that the exact candidate text was installed in the relevant Open WebUI field. Record what the user confirmed and what was not independently verified. GitHub commit success alone is not deployment evidence.
6. **Keep implementation and behavior separate.** A text-match confirmation establishes the version identity as reported by the user; it does not establish that model behavior improved. Evaluate a candidate with a bounded test and record the full user prompt, Think mode/model sampling settings when known, actual search queries, actual fetched URLs, tool counts, and final answer quality.
7. **Compare evidence, not intent.** For comparison questions, judge actual Fetch URLs and retrieved content: do the sources cover both sides? Do not treat improved search-result snippets alone as proof of better Fetch selection.
8. **Record the result immediately.** Update the relevant registry/readme, the dated detailed record, and the top-level active handoff. Record version, date, status, source URL, commit/blob SHA, whether implementation is user-confirmed, test status, and next step.
9. **Never conflate prompt layers.** A change to the standalone prompt does not automatically version or update the v0.3 rule block; a change to Function code does not automatically update either system-prompt artifact. Track each separately and explicitly record intended combinations.
10. **Protect the runtime.** Prompt-recording work must not change Function code, valves, search/fetch quotas, backend, services, or processes unless the user expressly requests that change. No service restart is implied by a prompt edit or GitHub update.
11. **Use evidence-sensitive wording.** Separate facts, user-confirmed implementation, live test results, inference, and hypotheses. Missing logs are not proof that a code path did not run; a blocked URL is not a successful fetch.
12. **Avoid needless repetition.** Do not rerun a live prompt test merely to create a record. Run a new test only when there is a defined new objective or the prior result is inconclusive.

## 4. New-session start procedure

At the start of a new SearchGuard session:

1. Read `ACTIVE-SEARCHGUARD-INVESTIGATION.md` in `kco1632-dev/for-chatgpt` first.
2. Follow its top "session start / versioning state" section to this operating procedure and the latest dated record.
3. Verify the current repository branch and the relevant file/blob SHA before quoting code or prompt text.
4. Treat status labels literally: `user-confirmed implemented`, `independently verified`, `tested`, and `candidate only` mean different things.
5. Do not ask the user to repeat information already captured in those records. If the active file and a dated historical note conflict, the top/current section of `ACTIVE-SEARCHGUARD-INVESTIGATION.md` controls; preserve older statements as history rather than deleting their context.
