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

**Not yet run on G14.** The patch and tests have been committed to this separate branch and read back from GitHub. No Python test was executed by the assistant. The user should run the seven-test suite against this branch before considering any further Function update. Do not infer that fix3 works from the code change alone; live Open WebUI verification remains separate.
