# SearchGuard 0.8.26-fix2 — live search check (2026-10-09)

## Environment status

- Branch: `analysis/searchguard-2026-10-09-query-candidate-regressionfix`
- Candidate: [`guard0826.py` (0.8.26-fix2)](https://github.com/kco1632-dev/OpenWebUI-SearchGuard/blob/analysis/searchguard-2026-10-09-query-candidate-regressionfix/guard0826.py)
- User reports updating the registered Open WebUI Function to 0.8.26-fix2. This is a user-reported state; the registered code/version has not been independently inspected.

## Live search result reported by user

Prompt asked to investigate the official site for カティサーク, mention unrelated quoted text 「Open WebUI」, perform search only, and not call `fetch_url`.

- Tool shown: `search_web`
- Query shown in tool input: `カティサーク 公式サイト`
- Count: `5`
- User reports the test was done without `fetch_url`.
- Search result payload included:
  - `カティサーク (酒) - Wikipedia` — `https://ja.wikipedia.org/wiki/カティサーク_(酒)`
  - `カティサーク | アサヒビール` — `https://www.asahibeer.co.jp/brand/cutty-sark/`
  - `カティサークサイトリニューアル | 株式会社カティサーク` — `https://www.cuttysark.co.jp/カティサークサイトリニューアル.html`
  - `会社概要 | 株式会社カティサーク` — `https://www.cuttysark.co.jp/company`
  - A related whisky overview at `https://tanoshiiosake.jp/10265`
- The displayed answer placed the Asahi product page first and provided five titles/URLs.

## Assessment

- **Search-query outcome: passes the visible query-content check.** The query shown in the tool input contains `カティサーク` and does not contain the unrelated term `Open WebUI`.
- This does **not** prove that execution-time `QUERY_REPAIR` ran: the query was already correct, so no repair may have been needed.
- The official Japanese Asahi brand/product page appeared in the search results. The unrelated company named 株式会社カティサーク also appeared; relevance ranking is not yet assessed beyond the returned titles/snippets.
- **Fetch behavior:** user-reported no `fetch_url` call; not independently confirmed by runtime log.
- **Runtime audit:** `QUERY_REPAIR`, `QUERY_AUDIT`, and `STREAM_QUERY_AUDIT` remain unverified.

## Log retrieval failure (not evidence of Guard failure)

The user's attempt to read logs did not successfully retrieve the test's runtime records:

1. `$env:TEMP\searchguard-fix2-test-offset.txt` did not exist, so there was no saved starting byte offset.
2. `[System.IO.StreamReader]::ReadToEnd()` against the very large `C:\OpenWebUI\OpenWebUIService.out.log` threw `System.OutOfMemoryException`.
3. The subsequent `Select-String` output contained source-code fragments such as `self._fetch_result_diag_ids = set()` and the literal `"QUERY_REPAIR "`. Given the failed read, this output cannot be treated as evidence of runtime diagnostic lines; `$text` may have retained a previous value.

Next step: inspect a bounded tail of the log and anchor matches to actual `[Bonsai2 Web Search Guard]` log prefixes. Do not load the entire file into a single string. Do not infer that the repair/audit did or did not run from this failed log retrieval.

## Bounded log-tail check (2026-10-09)

The user scanned the last 16 MiB of C:\\OpenWebUI\\OpenWebUIService.out.log using a streaming StreamReader, looking for lines with an actual [Bonsai2 Web Search Guard] prefix, selected diagnostic names, and one of カティサーク, Katarsu, or Open WebUI.

- Result: no matching lines in that 16 MiB tail.
- This is **not proof that the diagnostics never ran**. The scan covered only the file tail, the test had no saved starting offset, and rotated logs / other listed log files were not part of this scan.
- An earlier ReadToEnd() attempt failed with System.OutOfMemoryException. The later search of $text printed source-code fragments and is not valid evidence for runtime logging.
- A separate PowerShell else error occurred because else was entered as a separate command after the if block had already executed. This did not affect the empty scan result.

Next diagnostic action: inspect log file names, lengths, and last-write times to determine which current/rotated file covers the test time, then run a streaming, prefix-anchored query against the appropriate file(s). Do not infer execution from source-code string matches or absence of matches in one tail window.

## Log-file inventory (2026-10-09, after live search)

User-reported PowerShell inventory:

- `OpenWebUIService.out.log`: 1,694,698,020 bytes; last write 2026-10-09 13:32:08.
- `OpenWebUIService.err.log`: 17,524,277 bytes; last write 2026-10-09 11:43:17.
- `OpenWebUIService.out.log.old`: 3,532,786,294 bytes; last write 2026-10-05 19:01:11.
- `OpenWebUIService.err.log.old`: 17,514,249 bytes; last write 2026-10-05 17:28:57.
- `log.txt`: 108,141 bytes; last write 2026-09-01 17:02:35.

The active `OpenWebUIService.out.log` is the priority source based on its update time. The bounded 16 MiB scan of its tail found no matching lines under the previous combined prefix/event-name/term filter. This is not evidence that the Guard failed to run or never logged; the filter may have been too narrow, the relevant event may not be in the scanned window, or the output may be routed elsewhere.

Next: stream a bounded tail of the active out log and capture recent `[Bonsai2 Web Search Guard]` lines without requiring the target text to appear. Continue to avoid loading the full multi-gigabyte file into memory.

## Runtime diagnostic lines found in the bounded tail (2026-10-09)

The user's subsequent 16 MiB tail scan found Guard-prefixed lines. The relevant request/message ID is `2bf77508-ef98-455e-91be-30795dd5e84c`; the nearby `msg=58ad5258-54ea-4006-b74f-855884c1dc00` lines concern a different request and include a fetch, so they are not evidence that the current search-only test fetched a page.

Relevant observed lines for `msg=2bf77508-ef98-455e-91be-30795dd5e84c`:

- `STREAM`: native call observed as `search_web({"query":"カティサーク 公式サイト","count":5})` (Japanese characters were displayed as mojibake in the PowerShell output).
- `STREAM_QUERY_AUDIT`: `status=VIOLATION`, with `missing=['URL']`.
- `QUERY_REPAIR`: logged a change that prepended `URL` to the query, with `missing=['URL']`.
- `SEARCH_RESULT_AUDIT`: `status=ok`, main entity found, `results=5`.
- `FETCH_GATE_SOURCE`: parsed the five search results successfully; target entity included; `urls=5 ok=5 suspect=0`.
- `QUERY_AUDIT`: still reported `VIOLATION` for the original logged query with `missing=['URL']`.
- Per-hop summary: `search_web=1/2`, `fetch_url=0/2`, `turns=1/4`; final `STREAM` for this message finished with `stop`.

## Updated assessment

- **Confirmed:** runtime query audit and repair diagnostic paths executed for this request. This resolves the earlier question of whether these diagnostic strings were merely present in source; these are actual Guard-prefixed runtime lines.
- **Confirmed:** the repair selected `URL` as a missing term even though the intended Japanese target was already present in the displayed query. The query audit therefore stayed at `VIOLATION`.
- **Likely code-level explanation:** the user's instruction included the uppercase token `URL` in the phrase asking for search result titles and URLs. The current implicit-target candidate logic still scans strong uppercase Latin candidates across broad user text, so `URL` can be selected as a required query term. This appears to be a separate candidate-selection false positive not covered by the current five tests.
- **Search result outcome:** the user-provided tool result contained five items, including the Asahi Beer Cutty Sark product page. `SEARCH_RESULT_AUDIT status=ok` logged that the target was found.
- **Fetch behavior for the relevant request:** the per-hop summary records `fetch_url=0/2`; no fetch call is shown for this message in the pasted lines. The fetch diagnostic lines with a different message ID must not be conflated with this request.
- **Version caveat:** the user reported updating the registered Function to 0.8.26-fix2, but the pasted log lines do not themselves print the Function version. They prove the observed runtime paths, not the deployed version independently.

Next focused regression should preserve the full real user prompt (including the request to show titles and URLs) and assert that `repair_query()` does not inject `URL` when the intended target is already present. Do not adjust unrelated Guard behavior or repeat the live search until this narrow candidate-selection issue is addressed.
