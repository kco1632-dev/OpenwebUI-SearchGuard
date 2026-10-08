# SearchGuard 0.8.25 fetch registry fix — 2026-10-09

## Purpose

Document the root cause, minimal fix, and live verification of the `fetch_url` execution-registry failure observed in SearchGuard 0.8.25.

## Baseline

- Open WebUI: 0.11.4
- SearchGuard diagnostic baseline: 0.8.25
- Fix candidate: 0.8.25-fix
- Repository: `kco1632-dev/OpenwebUI-SearchGuard`
- Fix branch: `analysis/searchguard-2026-10-09`
- Fix commit: `c9ba2e4e52a4d397c6443d2b385b1f1a820b93fb`
- Parent commit: `85961c4b9250e1c5b5881d10a43496da339d2b0a`

## Confirmed failure

Test sequence:

1. `fetch_url` https://example.com/
2. Duplicate `fetch_url` of the same URL
3. One `search_web` for `OpenAI`
4. `fetch_url` https://example.org/

In the 0.8.25 diagnostic run, the final fetch produced:

```
FETCH_EXECUTION_REGISTRY_DIAG
fetch_suspended=NO
body_has_fetch_url=YES
metadata_has_fetch_url=NO
body_tool_names=['search_web', 'fetch_url']
metadata_tool_names=['search_web']
native_calls=['fetch_url']
```

Open WebUI then returned:

```
Error: Tool "fetch_url" not found.
```

This was an execution-time tool-registry miss. It was not a Web Loader HTTP/content-fetch failure.

## Root cause

The suspension filtering code removed `fetch_url` from the execution metadata:

```python
if state.get("fetch_suspended") and not fetch_gate_test_request:
    metadata_tools.pop("fetch_url", None)
```

The surrounding code/comments already stated that `fetch_url` should remain in metadata during recovery while being hidden from `body["tools"]`. The implemented metadata removal contradicted that design.

There was no corresponding restoration of `metadata["tools"]["fetch_url"]` when fetch suspension was later cleared.

## Minimal fix

In `guard0825-fix-candidate.py`, only the suspension-specific metadata removal above was removed.

The normal fetch-quota closure remains:

```python
if fetch_limit:
    metadata_tools.pop("fetch_url", None)
```

Therefore:

- duplicate suspension can still hide `fetch_url` from the model-facing tool list;
- the execution registry keeps the `fetch_url` callable available;
- the normal fetch quota can still remove `fetch_url` after the limit is reached.

## Live verification after the fix

Live Function version was changed to `v0.8.25-fix`.

Verification request ID:

`eaed5412-f314-4a85-a24c-020d8bd97f25`

Observed sequence:

### 1. First fetch

```
FETCH_RESULT_DIAG
class=BODY
chars=171
url='https://example.com/'
```

State:

```
fetch_url=1/2
fetch_suspended=NO
available_tools=2
```

### 2. Duplicate fetch

```
decision=DUPLICATE
duplicate=True
reason=already-fetched
fetch_suspended=True
```

Diagnostic state:

```
FETCH_SUSPENSION_DIAG
fetch_suspended=YES
body_has_fetch_url=NO
metadata_has_fetch_url=YES
fetched_urls=1
```

This is the key post-fix registry observation.

### 3. Search clears suspension

```
fetch-suspension-cleared
reason=new-search
search_attempts=1
```

State afterwards:

```
search_web=1/2
fetch_url=1/2
available_tools=2
fetch_suspended=NO
```

### 4. New fetch

The Guard accepted:

```
decision=PASS
duplicate=False
reason=user-explicit-url
url='https://example.org'
```

The fetch completed successfully:

```
FETCH_RESULT_DIAG
class=BODY
chars=171
url='https://example.org/'
```

No `Tool "fetch_url" not found` error occurred.

Afterwards:

```
search_web=1/2
fetch_url=2/2
available_tools=1
fetch_suspended=NO
```

This also confirms that the ordinary fetch quota closure still operates.

## Conclusion

The observed `Tool "fetch_url" not found` failure was caused by deleting `fetch_url` from the execution metadata during duplicate-fetch suspension.

The minimal 0.8.25-fix change removes that suspension-specific metadata deletion while preserving normal quota enforcement.

The fix was reproduced live with the same duplicate → suspension → search → recovery → different-fetch sequence, and the final `example.org` fetch succeeded.

## Scope

This record covers only the fetch execution-registry bug. It does not establish conclusions about DDGS search quality, Bonsai2 query planning, Web Loader quality, or other SearchGuard behavior.
