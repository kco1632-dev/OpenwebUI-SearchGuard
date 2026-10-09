# SearchGuard 0.8.26-fix / fix2 — query candidate selection (2026-10-09)

## Summary

Record the query-candidate selection change prepared as `guard0826.py`, the local regression results, and the user-reported Open WebUI deployment.

## Baseline and artifact

- Repository: `kco1632-dev/OpenWebUI-SearchGuard`
- Baseline file: [`guard0825.py`](https://github.com/kco1632-dev/OpenWebUI-SearchGuard/blob/main/guard0825.py)
- Baseline Git blob SHA: `8122fc13f929ad67826f54693adb22ba27b3d058`
- Candidate file: [`guard0826.py`](../guard0826.py)
- Version header: `0.8.26-fix`
- Work branch: `analysis/searchguard-2026-10-09-query-candidates`
- Candidate commit: `f566a0875d93aa40af5e11df0cc940bbb8acdfcf`
- Candidate file Git blob SHA at creation/readback: `497a02c3e95d138940d89f78d746b3be05cc0fda`

The source content was fetched from the public `guard0825.py` path and checked against the expected blob SHA before the candidate file was generated. The created `guard0826.py` was fetched back from GitHub; its content exactly matched the content submitted to GitHub.

## Problem addressed

The existing `repair_query()` prepended every missing value in `protected["entities"]`. In long instructions, that list could include irrelevant quoted examples or generic terms as well as the actual target. That could pollute a search query and make `QUERY_AUDIT` report a violation even when the intended entity was already present.

Observed examples included:

- An explanatory quoted `Open WebUI` name being selected instead of the Japanese target `カティサーク`.
- The generic word `サイト` being prepended for a request to check a product's official site.
- One of two target entities being dropped when the sentence mentioned each entity's official site.

## Code change

The candidate adds:

- `GUARD_CANDIDATE_STOP_RE` — boundary expressions for identifying the target phrase.
- `_select_query_candidates(user_text, protected)` — a separate candidate-selection step that masks quoted text when detecting target markers, ignores selected quoted examples, supports common explicit target markers and comparison phrases, deduplicates nested candidates, and preserves parallel-connected targets after selected boundaries.
- In `repair_query()`, the missing-entity loop now iterates over `_select_query_candidates(user_text, protected)` instead of all of `protected["entities"]`.

The following were not modified by this patch:

- `extract_protected()`
- Numeric-conflict detection and replacement logic
- Search/fetch quotas and tool-turn enforcement
- Tool registry, fetch suspension, final-answer mode, and the calling sites of `repair_query()`

## Local verification

The following tests were run against the local candidate file generated from the same patch:

1. Python syntax check via `python -m py_compile`: passed.
2. Strict query regression test: **23/23 passed**. These cover cases A–W, including quoted targets, unrelated quoted examples, Japanese/English entity names, numeric conflicts, multiple targets, official-site requests, and target-boundary conditions.
3. Audit-semantics comparison: **4/4 passed**.

The four audit-semantics cases established these expected differences:

- If the intended target is already present, unrelated protected words no longer force `VIOLATION` in the tested U/R cases; candidate status becomes `ok`.
- If the intended target is absent, the tested missing-target case remains `VIOLATION`.
- Numeric conflicts still replace `750ml → 700ml`, `43度 → 40度`, and `2500mAh → 2630mAh`; the tested numeric-conflict case remains `VIOLATION`.

These are results from a finite local test set, not a guarantee for arbitrary Japanese phrasing.

## Deployment status

- **User-reported:** On 2026-10-09, the user reported that the `0.8.26-fix` candidate had been copied into and implemented in the Open WebUI Function UI.
- **Not independently verified here:** No post-deployment live request/log test was provided as part of this record. Therefore, successful live behavior of the deployed instance should not be inferred from the local regression tests alone.
- The GitHub change was created on the work branch above. This record does not assert that the branch was merged into `main`.

## Operational cautions

Because `repair_query()` is shared by execution-time repair and audit paths (`QUERY_AUDIT` and `STREAM_QUERY_AUDIT`), changing the selected missing entities also changes the inputs to the audit's `missing` / `changed` decision. This is intentional for the tested false-positive cases and should remain part of post-deployment verification.

The next live verification should be narrow and log-based:

1. Run a case where the target is already in the generated query but the user instruction includes an unrelated quoted example.
2. Confirm `QUERY_REPAIR` does not prepend the unrelated example or a generic word.
3. Confirm `QUERY_AUDIT` / `STREAM_QUERY_AUDIT` show the expected status.
4. Run a genuinely missing-target case and a numeric-conflict case to confirm repair and audit behavior remain active.

No conclusion about search-engine quality, model query planning, or overall web-search accuracy is made by this change record.


## Focused regression test added (2026-10-09)

A reproducible test module is now stored in the candidate branch:

- [test_query_candidate_selection_0826.py](../test_query_candidate_selection_0826.py)

The repository previously recorded the 23 strict cases and 4 audit-semantic checks, but did not contain their runnable test source. This new module focuses only on the suspected candidate-selection regression and its audit-facing changed flag. It imports the candidate module directly and does not call Open WebUI, DDGS, or any network service.

Cases in the original 4-case version:

1. Unmarked, unrelated quoted English term after an implicit Japanese target: target must be repaired into the query and unrelated term must not be injected.
2. Query already contains the Japanese target: repair must leave it unchanged and report changed=False.
3. Explicit target marker: target must be selected without unrelated quoted term.
4. Explicit example marker: example quote must not be injected.

The user executed that original 4-case version against the original candidate branch; the results are recorded below (2 failures, 2 passes). For the separate fix2 branch, a fifth case was added in which the unrelated quote appears before the Japanese target.

The fix2 5-case test file was subsequently executed on G14; see the status update at the end. All five tests returned `ok` and the test summary ended in `OK`; the separately printed `TEST_EXIT_CODE` value was not visible.

## Live reproduction of candidate-selection regression (2026-10-09)

The user ran the committed `test_query_candidate_selection_0826.py` on the G14 with the original candidate branch `analysis/searchguard-2026-10-09-query-candidates`, using `C:\OpenWebUI\venv\Scripts\python.exe -m unittest -v test_query_candidate_selection_0826.py`.

Observed: 4 tests ran; 2 failed and 2 passed.

Confirmed failures:

1. With user text `カティサークの公式サイトを調べてください。説明文では「Open WebUI」という名前も出てきます。` and generated query `Katarsu whisky brand official website`, the repaired query was `Open WebUI Katarsu whisky brand official website`. The required target `カティサーク` was not restored.
2. With the same user text and query `カティサーク 公式サイト`, the result injected `Open WebUI`, causing `info["changed"]` to indicate an unnecessary repair/audit violation.

The explicit-target-marker and explicit-example tests passed.

Conclusion: this is a reproduced regression in the 0.8.26 candidate-selection change under the focused test context. The evidence shows that an unrelated quoted English phrase can be chosen while the Japanese target is omitted, or can create an unnecessary query change. It does not by itself prove that this exact text context was the one present in the earlier live カティサーク request.

## Candidate fix2

A separate branch was created to preserve the original candidate artifact and isolate the regression fix:

- Branch: `analysis/searchguard-2026-10-09-query-candidate-regressionfix`
- Candidate file: [guard0826.py](https://github.com/kco1632-dev/OpenWebUI-SearchGuard/blob/analysis/searchguard-2026-10-09-query-candidate-regressionfix/guard0826.py)
- Header version: `0.8.26-fix2`
- Focused test module: [test_query_candidate_selection_0826.py](https://github.com/kco1632-dev/OpenWebUI-SearchGuard/blob/analysis/searchguard-2026-10-09-query-candidate-regressionfix/test_query_candidate_selection_0826.py)

Changes in this candidate:

- Avoid selecting quoted strings as global strong candidates in implicit-target cases.
- Always examine protected terms even when a strong candidate exists.
- When a subject/property boundary such as `の公式`, `の価格`, or `の仕様` exists, anchor selection to the nearest protected term before that boundary and preserve preceding terms only when linked as a parallel list.
- Add a fifth regression test where the unrelated quoted term appears before the Japanese target.

**Status update (2026-10-09):**

- **G14 tests:** the user ran `test_query_candidate_selection_0826.py` against fix2. All 5 tests returned `ok`; summary: `Ran 5 tests in 0.003s`, `OK`. The separately printed `TEST_EXIT_CODE` value was not visible.
- **Open WebUI Function:** the user reports updating the registered implementation to `0.8.26-fix2`. This is not independently verified here; the live search and runtime-log check are pending.
- **Still unverified:** whether live execution applies `QUERY_REPAIR`, whether `QUERY_AUDIT` / `STREAM_QUERY_AUDIT` show the expected status, and whether the actual query retains `カティサーク` without adding `Open WebUI`.
- No PR was created or merged by this update; the original candidate branch and Draft PR #3 remain separate.