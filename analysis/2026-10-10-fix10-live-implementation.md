# SearchGuard 0.8.26-fix10 live implementation record — 2026-10-10

## Purpose

Record the reported implementation of SearchGuard `0.8.26-fix10-recovery-query-purpose-v1` in the live Open WebUI Function, separate from offline candidate tests and post-deployment verification.

## Live environment and reported status

- Date: 2026-10-10 (JST)
- Open WebUI: 0.11.4 on Windows
- Function: `Bonsai2 Web Search Guard`
- Version shown in the Open WebUI Functions UI: `v0.8.26-fix10-recovery-query-purpose-v1`
- User confirmed that the Functions UI displayed this version with `Updated at: a few seconds ago`.
- The UI confirmation establishes that the edit was saved, but a post-update read-only database comparison and live search regression test have not yet been recorded in this document.

## Source candidate

- Repository: `kco1632-dev/OpenWebUI-SearchGuard`
- Source file: [guard0.8.26-fix10-recovery-query-purpose.py](https://github.com/kco1632-dev/OpenWebUI-SearchGuard/blob/96846077a8ec823c7e9e6f4c92500ec44ac66153/diagnostics/guard0.8.26-fix10-recovery-query-purpose.py)
- Source commit: `96846077a8ec823c7e9e6f4c92500ec44ac66153`
- Git blob SHA-1: `f2c8718b3994c050bbdbfa281053a16e27a31d9d`
- Candidate size: 236,572 bytes
- Candidate SHA-256: `f870deb338beb4cb51e41a86dafcae76e38fbe678c8ff18b95eb3739bfbf08af`
- Local Python AST syntax check: passed (`ast.parse`).
- Offline candidate test suites: 64 tests passed across seven suites. This is offline test evidence only, not live Open WebUI integration evidence.

## Change relative to fix9

A direct comparison between the verified fix9 candidate and fix10 showed 5 diff hunks (43 added lines, 2 removed lines). The functional changes are limited to recovery-query purpose handling:

1. Add recovery-purpose topics for `飲み方`, `種類`, `風味`, and `味`.
2. Preserve these requested topics in a recovery query when the entity is followed by a connector such as `について`, provided a higher-specificity purpose such as official-site or price intent was not already selected.
3. Exclude generic page/output-format terms such as `ページ`, `page`, `webpage`, and `web page` from the recovery extra-identifier list.

The fix9 effective-query Fetch Gate logic is retained. The diff was compared against the fix9 source at the same repository commit; the fix10 change should not be described as the entire cumulative change from the previously registered fix8 Function.

## Pre-update backup and rollback reference

Before editing the live Function, a read-only SQLite query captured the registered content to:

`C:\\OpenWebUI\\backups\\searchguard-registered-preupdate-20261010.py`

- Backup size: 226,280 bytes
- SHA-256: `124d56186d8d1bfeec754a9552a79d4f164cf1bb96186bbd72b1927b9734d452`
- The previously registered content was also backed up to `C:\\OpenWebUI\\backups\\searchguard-registered-20261010.py` with the same SHA-256.

Immediately before the edit, the database showed `active=1` and `global=0`. These are pre-update values; the post-update active state has not yet been independently checked. The Open WebUI service was not restarted as part of this implementation step.

## Verification status

### Confirmed

- The fix10 candidate was fetched from the pinned commit and its Git blob SHA-1 was verified.
- The candidate passed local Python AST parsing.
- The 64 offline candidate tests passed.
- The user confirmed that the Open WebUI Functions UI displayed the fix10 version as recently updated.
- A pre-update copy of the registered Function is available for rollback.

### Pending

1. Read the registered Function back from SQLite in read-only mode and compare its content hash to the fix10 candidate hash.
2. Confirm the Function remains active and its valves were not changed.
3. Run a small set of live regression prompts, including recovery searches requesting taste, type, or serving information after a connector such as `について`.
4. Inspect the resulting SearchGuard logs to ensure recovery-query intent is preserved and existing search quota / Fetch Gate behavior remains intact.

Do not treat offline tests or the UI version label alone as proof that live search regression tests have passed.

## Operational conclusion

The fix10 code edit has been reported saved in Open WebUI. Keep the pre-update backup until the post-update content check and live regression tests pass. No service restart is currently required solely for this code edit; do not restart the service unless the subsequent observations establish a reason.
