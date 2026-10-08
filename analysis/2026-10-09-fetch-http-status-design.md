# Design memo: preserve HTTP status for SearchGuard fetch accounting

Date: 2026-10-09
Status: Design only — no implementation or runtime changes
Target: Open WebUI 0.11.4 + SearchGuard 0.8.25-fix

## 1. Problem statement

A fetch that receives an HTTP 4xx/5xx response can currently return the error page as ordinary text. SearchGuard may then count that fetch as successful and consume fetch quota, because the tool result contains the body but no structured HTTP status.

Observed test evidence:
- Toyota URL fetch redirected to `https://global.toyota/en/about-toyota/company-information/officers/`; the target produced an HTTP 404 log entry.
- SearchGuard logged the returned page as `FETCH_RESULT_DIAG class=BODY chars=632 status_code=-`.
- A subsequent `https://example.org/` fetch logged as `class=BODY chars=171 status_code=-`.
- Runtime logs identified `SafeWebBaseLoader` as the loader.

This evidence is strongly consistent with a 404 response being returned as a normal body, but the log excerpts do not independently correlate a specific HTTP response with a specific quota increment. Treat quota consumption for that individual run as a likely diagnosis until verified with correlated call/quota logs.

## 2. Source-level findings

Open WebUI v0.11.4:
- `backend/open_webui/tools/builtin.py`: `fetch_url()` calls `get_content_from_url()` and returns the content string; it does not return an HTTP status.
  Source: https://github.com/open-webui/open-webui/blob/v0.11.4/backend/open_webui/tools/builtin.py
- `backend/open_webui/retrieval/utils.py`: the URL probe calls `raise_for_status()`. On exception, it clears the local response reference and can proceed to a loader path. This means the probe's status is not reliably associated with the body later returned by the loader.
  Source: https://github.com/open-webui/open-webui/blob/v0.11.4/backend/open_webui/retrieval/utils.py
- `backend/open_webui/retrieval/web/utils.py`: `SafeWebBaseLoader` defaults to `raise_for_status=False`; it can parse response text without preserving the HTTP status in the returned document metadata.
  Source: https://github.com/open-webui/open-webui/blob/v0.11.4/backend/open_webui/retrieval/web/utils.py
- SearchGuard 0.8.25-fix counts tool results using the error classification of the tool message. The quota path does not use the diagnostic status classifier to exclude ordinary HTTP 4xx/5xx responses. If status is absent and the result looks like a normal body, it can be counted.

## 3. Design constraints

1. The status must correspond to the exact response that supplied the body. Do not infer the loader body's status from the earlier probe request: these are separate HTTP requests and can differ.
2. Preserve URL validation, redirect policy, SSRF protections, timeouts, content-type handling, and existing text extraction.
3. Avoid changing the shared `get_content_from_url()` return contract without reviewing all callers, including RAG/import paths.
4. Keep ordinary fetched page content useful to the model; status signaling must be unambiguous and machine-detectable.
5. Do not make SearchGuard infer HTTP status from arbitrary page text such as “404 Not Found”.
6. Keep duplicate-fetch prevention, fetch suspension/recovery, and successful-fetch quota semantics unchanged except for classifying HTTP failures as unsuccessful.
7. Do not deploy or restart services as part of design work.

## 4. Candidate approaches

### A. Fetch-specific status-aware path (preferred for investigation)

Create or expose a fetch-specific operation that obtains the response, checks its status, and extracts content from that same response. Return a structured result containing at least status code and extracted content, or encode a stable machine-readable error envelope for `fetch_url`.

Advantages:
- Status and body are tied to the same HTTP response.
- Can keep changes localized to the fetch tool.

Risks / open questions:
- Reusing Open WebUI's existing loader and HTML extraction without issuing a second request may require a careful refactor.
- Must preserve handling of HTML, plain text, PDFs and other supported content types.
- Must confirm the correct treatment of redirects and non-HTTP loader errors.

### B. Add status metadata to the shared retrieval function

Extend `get_content_from_url()` to return status information and update callers.

Advantages:
- Could share status handling with existing retrieval logic.

Risks:
- Changes a shared return contract and may affect URL import/RAG or other callers.
- The current probe and loader can be separate requests; the implementation must not report the probe status as if it were the loader response status.

### C. Only change SearchGuard

Not sufficient as a reliable fix with the current tool interface. SearchGuard cannot recover a status that Open WebUI discarded. It can only classify explicit status/error metadata already present in the tool result.

## 5. Recommended next step

Before coding, inspect every call site of `get_content_from_url()` and the supported `get_loader()` branches. Determine whether a narrow refactor can share the exact response with `SafeWebBaseLoader` or whether a separate fetch-specific path is required. Then write a minimal patch proposal and test it in isolation before changing the live Open WebUI installation.

## 6. Required verification tests

- HTTP 200 HTML: content returned; fetch counts as successful.
- HTTP 200 plain text: content returned; fetch counts as successful.
- HTTP 301/302 to HTTP 200: final response status and content agree; fetch counts as successful.
- HTTP 404 with a body: explicit status is visible to the Guard; fetch does not count as successful.
- HTTP 500 with a body: fetch does not count as successful.
- Connection failure / timeout: remains an error and does not count as successful.
- A successful fetch followed by a duplicate URL: existing duplicate prevention and suspension behavior remain unchanged.
- After suspension clears, a different valid URL remains fetchable.
- RAG/import paths continue to work unchanged if the shared retrieval function is modified.
- No status is attributed to a different request than the one that supplied the returned body.

## 7. Change boundary

This memo records analysis and test requirements only. No source file, live configuration, service, or runtime behavior has been changed. No implementation approach is approved yet.
