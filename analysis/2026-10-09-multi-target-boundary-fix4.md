# SearchGuard 0.8.26-fix4: multiple subject/property boundaries

Date: 2026-10-09

## Status

Candidate code only. This branch has not been reported as installed in the active Open WebUI Function. No service restart, configuration change, PR creation, or merge is part of this work.

Branch: `analysis/searchguard-2026-10-09-multi-target-fix`

## Confirmed fix3 regression

The G14 test against fix3 commit `b2d01fc81d00b440a35b9e7b314cc85d1572cb1c` failed:

```
AssertionError: 'Sony' not found in 'Apple 公式サイト 価格'
Ran 1 test
FAILED (failures=1)
TEST_EXIT_CODE=1
```

Input:
`Appleの公式サイトとSonyの価格を確認してください。検索結果のタイトルとURLを示してください。`

The immediate cause is the fix3 logic stopping strong-candidate collection at the first `の公式` boundary. The distinct target preceding the later `の価格` boundary is consequently omitted.

## fix4 candidate change

- Version label is `0.8.26-fix4`.
- Strong candidate collection is segmented across each `の公式`, `の価格`, and `の仕様` boundary instead of stopping at the first one.
- Protected-term selection applies the same per-boundary segmentation, so later Japanese targets can be retained too.
- Query limits, fetch behavior, stream diagnostics, and service configuration are not intentionally changed.

## Focused regression tests

The focused test module has 10 tests. Two cases target this regression:
1. `Appleの公式サイトとSonyの価格...`: both `Apple` and `Sony` must be retained and `URL` must not be injected.
2. `カティサークの公式サイトとバランタインの価格...`: both Japanese targets must be retained and `URL` must not be injected.

G14 focused test results, run with `C:\\OpenWebUI\\venv\\Scripts\\python.exe` against the fix4 candidate files:

- Added multi-target regression cases: `Ran 2 tests in 0.003s`, `OK`, `TEST_EXIT_CODE=0`.
- Full focused module: `Ran 10 tests in 0.006s`, `OK`.
- Combined focused + extended + audit-semantic modules: all 37 tests reported `ok`; summary `Ran 37 tests in 0.011s`, `OK`, `TEST_EXIT_CODE=0`.

The 37 tests consist of 10 focused tests, 23 re-created query-repair tests, and 4 re-created audit-facing semantic tests. The 23+4 modules were reconstructed from documented categories, not recovered byte-for-byte from the earlier historical test source. The 4 audit-facing tests do not exercise full Open WebUI `Filter.request()` integration or prove runtime log emission.

The tested coverage includes the original URL false-positive, numeric correction, existing query stability, parallel targets, distinct English/Latin and Japanese targets across separate property boundaries, and audit-facing outcomes. Passing unit tests do not prove behavior in the active Open WebUI Function; that requires separate runtime verification if and when the user authorizes deployment testing.
