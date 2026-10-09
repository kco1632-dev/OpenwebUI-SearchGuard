# SearchGuard 0.8.26-fix6 — official-site audit separation

Date: 2026-10-10

## Baseline and candidate

- Baseline repository: `kco1632-dev/OpenWebUI-SearchGuard`
- Baseline branch: `analysis/searchguard-2026-10-10-recovery-intent-fix`
- Baseline file: `diagnostics/guard0.8.26-fix5-recovery-intent-diag1.py`
- Baseline blob SHA: `5c21e2173c82590a7189e5ec246fb24d7b91bc6c`
- Candidate branch: `analysis/searchguard-2026-10-10-official-audit-fix`
- Candidate file: `diagnostics/guard0.8.26-fix6-official-audit-diag1.py`
- Candidate code blob SHA after audit/status-separation change: `04a5eb866eab87e4f34beacb49b0a4c3d191919e`
- Candidate source URL: https://github.com/kco1632-dev/OpenWebUI-SearchGuard/blob/analysis/searchguard-2026-10-10-official-audit-fix/diagnostics/guard0.8.26-fix6-official-audit-diag1.py

The filename version, module `version` header, and changelog heading all use `0.8.26-fix6-official-audit-diag1`.

## Problem

The legacy `SEARCH_RESULT_AUDIT` uses a presence check: if the main entity string appears anywhere in aggregated result title/snippet evidence, it records `status=ok`. That establishes entity presence only, not that a result URL belongs to the official publisher.

The existing `FETCH_GATE_CANDIDATE verdict=OK` also means that the entity is present in a result's evidence. It has never been an official-site verification state.

## Change

For user requests that explicitly ask for an official website/page/URL:

- Each parsed search result gets an `OFFICIAL_RESULT_AUDIT` classification:
  - `ENTITY_MISSING`: the requested entity was not found in that individual result's evidence.
  - `OFFICIAL_UNCONFIRMED`: the entity was found but no explicit official-site wording was found in the result evidence.
  - `OFFICIAL_CANDIDATE`: the entity and explicit official-site wording both occur in that single result's evidence.
- `SEARCH_RESULT_AUDIT` preserves the legacy `status=ok / VIOLATION / NO_RESULTS` meaning. It adds separate `entity_status`, `official_status`, `official_candidate_count`, and `official_confirmed` fields. A result being called a candidate does not promote it to confirmed.
- If entity presence is adequate but official status remains `OFFICIAL_UNCONFIRMED`, the existing one-shot recovery can run. It can also run when an official-site request returns no results.
- An official-site verification system note tells the model that result titles/snippets and third-party mentions do not establish publisher identity; inspect fetched page content and explicitly state uncertainty instead of guessing when evidence is insufficient.
- Ordinary non-official audits retain their legacy status. Successful-call quotas, turn limits, fetch wrappers/gates, duplicate prevention, and tool accounting are not changed.

## Important limitation

The audit deliberately never assigns `OFFICIAL_CONFIRMED` based on search-result metadata. `OFFICIAL_CANDIDATE` is a weak candidate signal: a third-party article can itself contain the words “official website.” The system note asks for fetched-page verification but does not mathematically prove ownership of a domain.

This candidate does not add a registry of trusted domains, and it does not hard-block fetching an entity-matching third-party result. Consequently, `FETCH_GATE_CANDIDATE verdict=OK` may still appear for an unofficial page that mentions the entity; read it as entity relevance only. A robust generic officiality proof would require stronger independent evidence than search snippets, and any future enforcement must be designed and tested separately.

## Offline tests

The private `for-chatgpt` GitHub Actions workspace runs the prior six recovery-query tests and ten audit tests against the candidate branch on an ephemeral runner. It does not touch the registered Open WebUI Function or the G14 service.

- Recovery tests: 6/6 pass.
- Official-audit tests: 10/10 pass.
- Combined run: https://github.com/kco1632-dev/for-chatgpt/actions/runs/37997670470/job/114047741587

The audit fixtures cover entity-only results, explicit official wording on a third-party article, missing target, official-intent recognition, recovery decisions, preservation of ordinary `ok` behavior, note idempotence/removal, and numeric correction. These are code-level tests, not live search or domain-ownership verification.

## Deployment status

- Candidate code written to a dedicated review branch: yes.
- Candidate fetched back from GitHub and SHA verified: yes.
- Offline unit tests: 16/16 pass across the two test suites.
- Candidate merged into `main`: no.
- Open WebUI registered Function updated: no.
- G14 live search behavior tested with this candidate: no.
