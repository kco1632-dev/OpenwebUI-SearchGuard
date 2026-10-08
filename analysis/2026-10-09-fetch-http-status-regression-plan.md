# HTTP 404 fetch quota: prototype boundary and regression tests

Status: design/test specification only. This branch does not change the active Guard, Open WebUI source, or runtime service.

## Why a Guard-only fix is insufficient

In Open WebUI v0.11.4, `fetch_url()` receives `content, docs` from `get_content_from_url()` and returns only the content string on the normal path. In the confirmed `SafeWebBaseLoader` path, the loader parses `response.text` into a Document but does not retain `response.status_code`. A 404 body can therefore arrive at SearchGuard as ordinary text. Guard cannot reliably infer the status from arbitrary body text, and must not do so.

## Proposed narrow contract

For the currently observed `SafeWebBaseLoader` engine only, an eventual Open WebUI patch should preserve the status of the exact response used to build the Document. The native `fetch_url()` wrapper should return a stable, structured error envelope for explicit HTTP 400–599 status metadata, for example:

```json
{"error":"fetch_http_error","status_code":404,"url":"https://example.invalid/path"}
```

The URL should be the final response URL where available, not guessed from the initially requested URL. Do not parse arbitrary page text to infer status. Do not change the shared `get_content_from_url()` return tuple or URL-import/RAG behavior in this narrow patch.

SearchGuard should classify this explicit envelope as an error, so that call does not consume the successful-fetch quota. It should preserve existing behavior for ordinary page bodies and existing explicit tool errors. Status support for Playwright, Firecrawl, Tavily, Microsoft Web IQ, and external loaders remains undefined until each engine has a tested contract.

## Regression test matrix

These are required tests for the eventual implementation. They have not been executed by this documentation-only change.

| Case | Fixture / condition | Expected fetch result | Expected successful-fetch quota |
|---|---|---|---|
| 1 | SafeWebBaseLoader receives HTTP 200 HTML | Normal extracted body; no error envelope | +1 |
| 2 | Requested URL redirects to final URL returning HTTP 200 | Normal extracted body; metadata reflects exact final response status/URL | +1 |
| 3 | Requested URL redirects to final URL returning HTTP 404 | Structured `fetch_http_error` with status 404 and final URL | +0 |
| 4 | HTTP 500 response | Structured error with status 500 | +0 |
| 5 | Connection failure / timeout raised to fetch wrapper | Existing explicit error result | +0 |
| 6 | Empty but valid HTTP 200 response | Must not be misclassified solely because body is empty; expected behavior explicitly documented | Based on the documented 200-success policy |
| 7 | Loader yields no Documents due to internal swallowed exception | Must not silently masquerade as a verified successful HTTP response; behavior must be explicitly surfaced or marked unknown | +0 if explicitly surfaced as error |
| 8 | Guard receives JSON error envelope from fetch_url | Error classifier recognizes it without parsing body text heuristically | +0 |
| 9 | Guard receives ordinary body mentioning “404” or “HTTP 404” | Must not infer status from arbitrary body text | +1 if otherwise a normal tool result |
| 10 | Duplicate-fetch suspension followed by search recovery and a valid second fetch | Existing 0.8.25-fix registry behavior remains intact | Only the valid non-duplicate fetch consumes quota |
| 11 | URL import / RAG retrieval path | Existing `(content, docs)` contract and behavior unchanged | Not applicable to Guard quota |
| 12 | Non-`safe_web` configured loader | No claim of status-aware behavior unless that loader supplies explicit status metadata | No inferred status; contract must be defined per engine |

## Acceptance criteria

1. HTTP status is correlated with the same response that supplied the parsed body.
2. A final redirect destination returning 404 is not reported as a successful fetch.
3. SearchGuard decrements no successful-fetch quota for the structured HTTP error.
4. Normal 200 responses, including redirect-to-200, retain existing content behavior.
5. Arbitrary body text cannot trigger status inference.
6. Duplicate/suspension/recovery behavior in 0.8.25-fix remains unchanged.
7. URL import/RAG call sites are not broken by a shared return-type change.
8. Test results identify the loader engine used; no all-engine compatibility claim without engine-specific tests.

## Implementation boundary

The status is currently lost in Open WebUI before Guard receives the tool result. The end-to-end fix therefore requires a separate, version-pinned Open WebUI source patch (or supported extension point) plus the Guard classifier change. This repository can prepare and validate the Guard-side contract, but a Guard-only code change cannot make the live Open WebUI 0.11.4 fetch path expose the missing status.

No implementation, deployment, restart, or live test was performed in creating this document.
