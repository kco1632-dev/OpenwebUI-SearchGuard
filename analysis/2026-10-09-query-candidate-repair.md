# SearchGuard 0.8.26-fix — query candidate selection (2026-10-09)

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

Cases:

1. Unmarked, unrelated quoted English term alongside an implicit Japanese target: target must be repaired into the query and unrelated term must not be injected.
2. Query already contains the Japanese target: repair must leave it unchanged and report changed=False.
3. Explicit target marker: target must be selected without unrelated quoted term.
4. Explicit example marker: example quote must not be injected.

The first two cases are specifically intended to detect the suspected failure mode. The test module has been committed to this branch, but has **not yet been executed against the user's G14 Python environment**. Do not record these cases as pass/fail until the test output is returned.