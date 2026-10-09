# SearchGuard 0.8.26-fix6 — official-site audit separation

Date: 2026-10-10

## Baseline and candidate

- Baseline repository: `kco1632-dev/OpenWebUI-SearchGuard`
- Baseline branch: `analysis/searchguard-2026-10-10-recovery-intent-fix`
- Baseline file: `diagnostics/guard0.8.26-fix5-recovery-intent-diag1.py`
- Baseline blob SHA: `5c21e2173c82590a7189e5ec246fb24d7b91bc6c`
- Candidate branch: `analysis/searchguard-2026-10-10-official-audit-fix`
- Candidate file: `diagnostics/guard0.8.26-fix6-official-audit-diag1.py`
- Candidate code blob SHA at initial audit separation: `04a5eb866eab87e4f34beacb49b0a4c3d191919e` (superseded; see latest SHA below)
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
- If officiality is not independently confirmed, the existing one-shot recovery can run even when the target entity is present or a weak `OFFICIAL_CANDIDATE` wording exists. It can also run when an official-site request returns no results. This remains bounded by existing search limits and the one-shot recovery flag.
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


## Review follow-up: recovery must continue for weak candidates

During code review, one condition was tightened: `OFFICIAL_CANDIDATE` based on title/snippet wording is not independent confirmation, so it must not suppress the one-shot recovery. The candidate now requests recovery for an official-site request whenever the entity audit status allows the existing recovery path and `official_confirmed is not True`. The current fix6 candidate never assigns `OFFICIAL_CONFIRMED`, so its first search result remains unconfirmed even if a snippet says “official website”; it can trigger at most the existing single recovery search and remains subject to the existing search quota / final-mode guard.

The same test suite now explicitly asserts that:
- a result mentioning the entity but with no official-site wording triggers recovery;
- a snippet-level `OFFICIAL_CANDIDATE` with `official_confirmed=False` also triggers recovery;
- a genuinely confirmed outcome, if a future verifier exists and explicitly returns `official_confirmed=True`, would not trigger recovery;
- ordinary non-official searches keep legacy behavior.

Updated code blob SHA after latest changelog alignment: `fa407343b7c5e181cb4d77e4fc2862778e3599e7`.
Updated test blob SHA after connecting audit outcome to recovery decision: `a50b3c2f19f43d63b632cde44a1a5f26d920e58a`.
Latest combined Actions run with the revised recovery test and final candidate revision: https://github.com/kco1632-dev/for-chatgpt/actions/runs/37998310469/job/114049883578

## How far generic automatic official-site verification can go

There is no universally reliable text-only heuristic that proves a website is official across arbitrary brands, products, organizations, and languages without some source of independent authority. In particular:
- a result title/snippet can claim “official website” while linking to a third-party article;
- domain-name token matching is weak, can fail across transliterations and language variants, and can misidentify unrelated sites;
- TLS/HTTPS, a canonical URL, a page title, branding, a copyright line, structured data, or a self-declared “official” label can show consistency or self-identification but do not by themselves prove that the publisher is the genuine rights-holder;
- following links between two sites does not solve the problem if the first site has not itself been independently established as authoritative.

For a generic no-hardcoded-domain design, the recommended evidence ladder is:
1. `ENTITY_FOUND`: search result mentions the requested entity.
2. `OFFICIAL_CANDIDATE`: search metadata contains official-site wording, clearly labeled as a lead only.
3. `PAGE_FETCHED`: the candidate page itself was successfully fetched; this is transport/content availability, not officiality.
4. `PAGE_SELF_IDENTIFIES`: the page body claims to be the official presence for the requested entity; this remains a self-claim.
5. `INDEPENDENTLY_CORROBORATED`: a separately established authoritative primary source links to or names the exact candidate domain for that same entity.
6. `OFFICIAL_CONFIRMED`: only eligible if stage 5 is satisfied and entity/domain mapping is unambiguous; otherwise retain `OFFICIAL_UNCONFIRMED`.

The current fix6 code implements stages 1–2 and instructions to inspect stage 3–4, but it does not independently establish stage 5 and must not mark stage 6. A future generic verifier needs a defensible rule for how the corroborating source is itself established as authoritative; no generic rule is implemented here. Until then, the safe user-facing behavior is to provide a candidate URL labelled unconfirmed or explicitly say that officiality could not be confirmed.

## Fetch-gate scope warning

The existing `FETCH_GATE_CANDIDATE verdict=OK` uses entity presence in result evidence. It is deliberately not converted into an officiality signal in this change. It may allow fetching an unofficial retailer/article that mentions the entity; changing that gate to enforce officialness would be a separate behavior change and requires its own tests, especially to avoid blocking valid official sites with Japanese/Latin aliases.
