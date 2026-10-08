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


## 8. Call-site review and narrower implementation candidate

Reviewed Open WebUI v0.11.4 call sites of `get_content_from_url()`:
- Built-in `fetch_url()` in `backend/open_webui/tools/builtin.py`.
- URL processing/import in `backend/open_webui/routers/retrieval.py`.
- URL context handling in `backend/open_webui/utils/middleware.py` (the source search also found this call site).

The shared function returns a `(content, docs)` pair and is used beyond the native fetch tool. Changing that tuple contract is not recommended.

### Candidate to prototype first

1. In `SafeWebBaseLoader`, preserve the HTTP response status in each produced Document's metadata, sourced from the same response whose body is parsed. This is narrower than changing the shared retrieval return contract, although it adds metadata for every caller using this loader.
2. In built-in `fetch_url()`, inspect the returned documents' status metadata. If any applicable final response status is 400 or higher, return a stable structured error result instead of ordinary page text. Do not include the error-page body as a successful fetch result.
3. In SearchGuard, recognize that structured error envelope and exclude that tool call from successful-fetch accounting.
4. Keep normal 2xx content unchanged. Do not infer the final response status from the earlier SSRF/content-type probe.
5. If a loader path cannot provide status metadata, do not pretend status is known. Define and test an explicit fallback behavior.

Why this is only a candidate:
- Confirm that `SafeWebBaseLoader` is used for the native fetch tool in the deployed configuration (runtime logs currently show it is).
- Confirm how the loader represents redirects and multiple Documents, and whether status metadata can be added without breaking document metadata consumers.
- Inspect the middleware call site before changing shared behavior; verify the extra metadata is benign.
- Some alternative loaders may not expose response status using the same interface. Those paths need an explicit compatibility decision rather than guessed status.

### Important correction to the simplest proposal

Checking only the initial `requests` probe is insufficient for redirects. The probe deliberately avoids following redirects for SSRF safety, while the loader can follow the URL separately. A redirect target can return 404 even when the original URL probe returned a 3xx. The status used for accounting must therefore come from the loader response that supplied the returned body, not from the probe.

### Prototype acceptance criteria

- A redirected final 404 is returned as an explicit fetch error and does not consume successful-fetch quota.
- A 200 response returns ordinary extracted content and consumes quota once.
- A 404 status is never guessed from page text.
- Existing `get_content_from_url()` return shape remains `(content, docs)`.
- URL import/RAG and middleware context paths continue to operate with the added metadata.
- Duplicate-fetch suspension and recovery tests remain unchanged and pass.

This section is a source-based proposal only. No implementation or live-system changes were made.


## 9. Compatibility review: SafeWebBaseLoader response handling

Reviewed `backend/open_webui/retrieval/web/utils.py` at Open WebUI v0.11.4.

Confirmed:
- The synchronous `SafeWebBaseLoader.lazy_load()` receives a concrete `requests.Response` in a `with self.session.get(...)` block.
- It checks `raise_for_status` only when the flag is true; the default is false.
- It currently passes `response.text` and the requested `path` into `_document_from_html()`, which creates a Document with `extract_metadata(soup, url)`.
- `extract_metadata()` currently records page title/description/language and `source`, but not HTTP status.
- `lazy_load()` catches exceptions and logs them rather than propagating them. Therefore simply setting `raise_for_status=True` may turn an HTTP error into a missing document/empty content rather than a clear native-tool error. This behavior must not be mistaken for reliable status propagation.
- The async path `_fetch()` currently returns only response text, and `alazy_load()` builds Documents from that text. A metadata-only change to the synchronous path would not automatically cover the async path.
- The retrieval source search identified direct `get_content_from_url()` callers in `builtin.py` and `routers/retrieval.py`. The shared return shape is `(content, docs)`; preserve it for the narrow proposal.

Updated narrow prototype idea:
1. For the synchronous loader path actually used by `get_content_from_url()`, pass the exact `response.status_code` (and preferably `response.url`) into the Document metadata while still inside the response context.
2. In `fetch_url()`, inspect returned docs for status metadata and emit a structured error only when the status metadata is explicit and 400–599. Keep the shared `get_content_from_url()` tuple shape unchanged.
3. Ensure loader exceptions or no-doc results become explicit errors in `fetch_url()` rather than ordinary empty success, without changing URL import/RAG behavior unintentionally.
4. Before implementation, inspect the remaining `get_content_from_url()` call sites and loader-engine dispatch. If an alternative configured loader is used, status availability must be treated as unknown unless that loader explicitly supplies it.
5. Add tests for final redirected 404, normal 200, no document / loader exception, and a second loader engine. Test whether status metadata is safe for all consumers of the Document metadata.

Assessment:
- This approach appears technically feasible for the deployed SafeWebBaseLoader path because it has access to the exact response that supplies the parsed body.
- It is not yet a complete universal solution for every loader engine, async loader path, or non-HTTP source.
- No source code was changed; this remains a proposal only.
