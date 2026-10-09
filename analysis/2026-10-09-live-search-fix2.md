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
