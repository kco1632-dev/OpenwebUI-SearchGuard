# SearchGuard 0.8.26-fix3 — URL instruction token regression (2026-10-09)

## Evidence from the G14 live request

The user supplied this query instruction to Open WebUI:

`カティサークの公式サイトを調べてください。説明文では「Open WebUI」という名前も出てきます。今回は検索のみ実行し、fetch_urlでページ本文を取得せず、検索結果のタイトルとURLを示してください。`

The runtime log for message `2bf77508-ef98-455e-91be-30795dd5e84c` showed:

- `STREAM_QUERY_AUDIT status=VIOLATION ... missing=['URL']`
- `QUERY_REPAIR` prepended `URL` to the query.
- `QUERY_AUDIT VIOLATION ... missing=['URL']`
- `SEARCH_RESULT_AUDIT status=ok ... found=True results=5`
- Summary: `search_web=1/2, fetch_url=0/2`

The model query already contained the intended Japanese target. The output-format instruction mentioning URL was treated as a missing search entity. The exact query was shown as mojibake in PowerShell, but the surrounding tool call/result and user-provided UI output identify the request context. This is actual runtime output, not merely source-code string matches.

## Candidate fix

- Branch: `analysis/searchguard-2026-10-09-url-token-regressionfix`
- Candidate: [`guard0826.py` (version 0.8.26-fix3)](https://github.com/kco1632-dev/OpenWebUI-SearchGuard/blob/analysis/searchguard-2026-10-09-url-token-regressionfix/guard0826.py)
- Tests: [`test_query_candidate_selection_0826.py`](https://github.com/kco1632-dev/OpenWebUI-SearchGuard/blob/analysis/searchguard-2026-10-09-url-token-regressionfix/test_query_candidate_selection_0826.py)

The implicit-target path now limits uppercase/strong-candidate extraction to the text before a recognized subject/property boundary (`の公式`, `の価格`, `の仕様`). The normal protected-term pass remains responsible for preserving the target before that boundary. This is intended to prevent later output-format instructions such as “タイトルとURL” from being selected as search entities, without adding a hardcoded `URL` exclusion.

No quotas, numeric-conflict replacement, fetch gate, tool registry, or runtime Function registration was changed by this GitHub candidate.

## Focused tests added

Two cases use the full real prompt:

1. With query `カティサーク 公式サイト`, repair must leave it unchanged, not add `URL` or `Open WebUI`, and return `info["changed"] == False`.
2. With query `公式サイト`, repair must add `カティサーク`, must not add `URL` or `Open WebUI`, and return `info["changed"] == True`.

The previous five regression cases are retained, making seven cases total.

## Verification status

**G14 focused tests: PASS (2026-10-09).** The user ran the seven-test suite with the Open WebUI virtual environment:

```
Ran 7 tests in 0.005s

OK
TEST_EXIT_CODE=0
```

All seven test cases returned `ok`, including both new cases using the full live prompt:

1. Existing query `カティサーク 公式サイト` remained unchanged; `URL` and `Open WebUI` were not injected; `info["changed"] == False`.
2. Query `公式サイト` was repaired to include `カティサーク`, without injecting `URL` or `Open WebUI`; `info["changed"] == True`.

**Updated G14 result (2026-10-09): PASS, 8/8.** The user downloaded both files from the fix3 branch at commit `54ec2c85098002167efefb7094338a617d86c294` and ran the suite using the Open WebUI Python environment. The transcript confirms all eight tests returned `ok`, followed by `Ran 8 tests in 0.004s`, `OK`, and `TEST_EXIT_CODE=0`.

The eighth numeric-conflict test passed: a generated `2500mAh` is replaced by the requested `2630mAh`, while `URL` is not injected into the query. The two full-live-prompt URL tests and the five prior cases also passed in this 8-test run.

This validates these eight focused cases only. The earlier 23-case strict regression suite and four-case audit-semantics suite have not been rerun against fix3; additional boundary variations and live Open WebUI behavior remain unverified. The candidate has not been reported as deployed. Do not infer overall correctness or deploy from the focused suite alone.


## Extended regression coverage reconstruction (2026-10-09)

The repository tree was checked on `main`, the original query-candidate branch, the fix2 branch, the earlier 2026-10-09 analysis branch, and the guard0824 backup branch. None contains the historical source files for the previously reported 23-case strict suite or 4-case audit-semantics suite. The prior pass counts were recorded, but the test source itself was not committed; those exact historical tests therefore cannot be rerun directly from GitHub.

To continue verification without misrepresenting the old suite, two explicitly **reconstructed** test modules were added on this fix3 branch:

- [`test_query_repair_extended_fix3.py`](../test_query_repair_extended_fix3.py) — 23 cases based on the documented categories: Japanese and quoted target selection, unrelated quoted terms, explicit target markers, parallel targets, generic site terms, full live prompt and URL handling, uppercase identifiers, numeric corrections (volume, currency, degree, battery), exact values, ambiguous values, and standalone numeric identifiers.
- [`test_query_audit_semantics_fix3.py`](../test_query_audit_semantics_fix3.py) — 4 cases checking the documented `info["changed"]` to `ok` / `VIOLATION` mapping. These are audit-facing unit checks, not a full `Filter.request()` integration test and not proof of runtime log routing.

These reconstructed tests are not claimed to be byte-for-byte or case-for-case identical to the original historical 23+4 test sets.

**G14 result (2026-10-09): PASS, 35/35.** The user ran the 8 focused tests, 23 reconstructed query-repair tests, and 4 reconstructed audit-semantic tests in one command. Output ended with `Ran 35 tests in 0.012s`, `OK`, and `TEST_EXIT_CODE=0`. All listed cases returned `ok`.

Scope caveat: the audit-semantic cases test the unit-level mapping from `info["changed"]` to `ok` / `VIOLATION`; they are not a full `Filter.request()` integration test and do not prove runtime log routing. These results validate the current reconstructed 35-case suite, not byte-for-byte the unavailable original test sources. Broader Japanese phrasing and live Open WebUI behavior remain unverified. Do not deploy from these unit-test results alone.
