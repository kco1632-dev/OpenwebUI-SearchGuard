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

**Updated G14 result (2026-10-09): PASS, 8/8.** The user downloaded both files from the fix3 branch at commit `54ec2c85098002167efefb7094271...` and ran the suite using the Open WebUI Python environment. The transcript confirms all eight tests returned `ok`, followed by `Ran 8 tests in 0.004s`, `OK`, and `TEST_EXIT_CODE=0`.

The eighth numeric-conflict test passed: a generated `2500mAh` is replaced by the requested `2630mAh`, while `URL` is not injected into the query. The two full-live-prompt URL tests and the five prior cases also passed in this 8-test run.

This validates these eight focused cases only. The earlier 23-case strict regression suite and four-case audit-semantics suite have not been rerun against fix3; additional boundary variations and live Open WebUI behavior remain unverified. The candidate has not been reported as deployed. Do not infer overall correctness or deploy from the focused suite alone.
