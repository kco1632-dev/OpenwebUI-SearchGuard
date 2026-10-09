"""
title: Bonsai2 Web Search Guard
author: local
version: 0.8.26-fix3
description: >
    Limit web-search tools on Bonsai2 (successful calls only consume quota),
    force a first search for current queries, preserve user terms (audit /
    execution-time repair), restore the full native tool set across
    tool-loop hops, and land cleanly in a tool-free final-answer mode.

    Includes:
      - read-only stream probe
      - native search-query audit
      - execution-time search-query repair
      - read-only search-result entity relevance audit
      - one-shot search-result recovery using remaining search quota
      - execution-time fetch_url callable probe
      - fetch gate
      - fixed fetch-gate test mode
      - active blocking for suspect search-result URLs
      - duplicate fetch prevention
      - non-error Guard results for blocked/duplicate fetches
      - temporary fetch suspension after duplicate fetch attempts

0.8.26-fix3 change:
    Restrict implicit-target strong-candidate collection when an explicit
    subject/property boundary ("の公式", "の価格", "の仕様") is present.
    This prevents uppercase terms in later task instructions (for example,
    URL in "検索結果のタイトルとURLを示してください") from being selected
    as missing search entities. Protected-term selection and query repair
    continue through their existing paths. Focused regression tests cover
    both an already-correct query and a query missing the Japanese target.

0.8.25-fix change:
    Minimal bug fix: during duplicate-fetch suspension, keep
    metadata["tools"]["fetch_url"] intact. body["tools"] alone hides
    fetch_url from the model while suspended. This prevents a stale
    execution registry after suspension is cleared, where body["tools"]
    contains fetch_url but metadata["tools"] does not, causing
    Open WebUI's "Tool \"fetch_url\" not found" error.
    No other behavior is changed.

0.8.25 change:
    DIAGNOSTIC ONLY. No behavior change.

    Goal: directly observe fetch-result classification and the state
    transition around duplicate-fetch suspension.

      A. FETCH_RESULT_DIAG logs each previously unseen fetch_url result as
         BODY / EMPTY / STATUS_LIKE / ERROR_LIKE. It uses only information
         already present in the tool message; it does not alter accounting
         or retry behavior.
      B. FETCH_SUSPENSION_DIAG logs the next request hop after a duplicate,
         including whether fetch_url remains in body["tools"] and
         metadata["tools"]. Nothing is changed.
      C. FETCH_SUSPENDED_TOOL_ATTEMPT logs a fetch_url native tool call, or
         raw fetch_url text, observed while the Guard's live state says
         fetch_suspended=YES.
      D. A small per-instance set prevents repeated FETCH_RESULT_DIAG lines
         for the same tool_call_id.

    NOT changed: fetched_urls.add() timing, duplicate handling, suspension
    rules, suspension clearing, quotas, counters, recovery, fetch gate
    decisions, tool filtering, final-answer handling, or existing 0.8.24
    RAW_TOOL_CALL diagnostics.

0.8.24 change:
    DIAGNOSTIC ONLY. No behavior change.

    Goal: observe in which state a raw <tool_call> text appears in a
    NON-final hop (past incident: STREAM finish=stop native_calls=[]
    xml_in_content=True final_mode=NO, often with fetch_suspended=YES).
    The origin of that text (model / llama.cpp parser / Open WebUI /
    Guard-state combination) is NOT established; nothing here assumes one.

      A. New log line RAW_TOOL_CALL_DIAG, one per non-final hop, written in
         _probe_event() at finish_reason time (same msg id as STREAM) when
         the hop's content carried raw tool-call text (xml_in_content,
         other raw markers) or the reasoning did (xml_in_reasoning).
         Final-answer hops are NOT logged here (FINAL_ANSWER_STREAM covers
         them). action=OBSERVE_ONLY is printed on every line.
      B. request() now stores a small per-hop snapshot (self._hop_diag):
         hop number, final_mode, fetch_suspended, search/fetch attempts,
         tool names offered, tool_choice, stop, whether a "closed" system
         note was injected, message count / role of the last message.
         The snapshot is read-only data; it is taken after every existing
         request() decision and changes nothing.
      C. Probe accuracy fix (log flags only): xml_in_content /
         xml_in_reasoning are now tested on (previous tail + new chunk)
         BEFORE truncating to 80 chars. 0.8.23 tested the truncated tail,
         so a chunk longer than 80 characters with <tool_call> at its start
         could be missed. Tags split across chunks were already handled.
         These flags feed logs only; no decision uses them.
      D. Extra read-only observations in the probe state: raw markers seen
         (</tool_call>, <function=, <parameter), offset of the first
         <tool_call> in the content, a <=200 char preview of the raw text
         (model output, never tool results or prompts), and how many
         request hops old the probe state is (probe_age_hops>0 means a
         previous hop ended without finish_reason and its state leaked).
      E. New valve raw_tool_call_diag (default True). False = no new log.

    NOT changed on purpose: content, tool_calls, finish_reason, tool_choice,
    tools, stop, counters, limits, recovery, fetch gate, final-answer hop
    stripping. The 0.8.23 finish_reason rewrite condition
    (tool_calls -> stop only when native tool_calls were dropped) is left
    as is; see the review notes for the 0.8.25 proposal.

0.8.23 change:
    Integrate 0.8.21 (current date AND time) into the 0.8.22 line and stop raw
    <tool_call> text from reaching the user in the final-answer hop.

    History: 0.8.22 was built on 0.8.20, so the 0.8.21 "date + time (minute
    precision)" extension was missing. 0.8.23 restores it unchanged.

      A. 0.8.21 restored: _tz_short(), _date_preflight() with time /
         timezone / timezone_source, marker v0.2 ([Bonsai2 Date Preflight
         v0.2]), and the extra fields in the per-hop summary line. The
         datetime is read once per request (cached per message) and reused
         by every hop; one Date Preflight block per request (_upsert_block).
      B. 0.8.22 kept as is: final_answer_after_limit / final_answer_fallback,
         tools closed + retrieved results flattened to plain text, NO
         stop=['<tool_call>'] in the final-answer hop.
      C. New: raw <tool_call> removal, final-answer hop ONLY.
         request() marks the final-answer hop (self._final_hop[msg]);
         stream() then, for that hop only:
           - strips <tool_call>...</tool_call> from delta.content with a
             small streaming state machine (tags split across chunks, e.g.
             "<tool" + "_call>", are handled; an unterminated block is
             dropped; stray </tool_call> is dropped),
           - drops native delta.tool_calls (tools are closed; nothing may
             start) and turns finish_reason "tool_calls" into "stop",
           - decides the 0.8.22 fallback from the CLEANED text (visible
             non-whitespace characters == 0 -> fallback; otherwise none),
           - logs one FINAL_ANSWER_STREAM line.
         Normal (non-final) hops are never touched.
      D. The flattened tool history and the fallback text are scrubbed of
         <tool_call>/<tool_response> markup (a fetched page may contain it).
      E. New valve final_answer_strip_raw_tool_call (default True).

0.8.22 change:
    Separate "tool execution limit" from "final answer generation".

    Symptom (0.8.21 test, search_web x2 / fetch_url x2): the tool limit was
    reached, final-answer mode removed the tools and added
    stop=['<tool_call>']. Bonsai2 tried to emit <tool_call> as its first
    token, the stop sequence cut it, and the response ended with 0
    characters (finish=stop). The retrieved results were never used.

    When the limit is reached the Guard now only closes the TOOLS. It still
    makes the model write the answer:
      - tools=[], tool_choice="none", metadata tools cleared (unchanged):
        no new search_web / fetch_url can start.
      - the retrieved search_web / fetch_url results are flattened into plain
        text in the last user message, so the model sees the evidence
        without a native tool-call history that invites another call.
      - stop=['<tool_call>'] is NOT added (it caused the empty response).
      - the final-answer instruction asks for a note that the limit was
        reached and that more research is possible on request.
      - safety net: if the final hop still streams 0 content characters, the
        stream() hook injects a short fallback text built from the retrieved
        results, so the response is never empty.

    Valve `final_answer_after_limit` (default True) enables all of this.
    False restores the exact 0.8.20 final-mode behavior.
    Date Preflight, counters, quotas, search/fetch gates, recovery and
    every existing valve are unchanged.

0.8.21 change:
    Date Preflight now gives the model the current DATE AND TIME (minute
    precision), not only the date. Nothing else is changed.

      - _resolve_now() is reused as-is. Date, time and ISO string are all
        built from the SAME single datetime object (one clock read per
        Date Preflight).
      - System block marker bumped to v0.2. _upsert_block() still keeps
        exactly one block per request across tool-loop hops.
      - Time shown to the model: minute precision, e.g.
            現在日時は 2026年10月6日（火曜日）07:03 JST です。
            ISO: 2026-10-06T07:03:00+09:00
      - Log: current_time / timezone / timezone_source added to the
        per-hop summary line (existing items unchanged).
      - Trigger regex, timezone priority, search / fetch / counters /
        final mode / tool_choice / extract_protected() / 0.8.19 date mask
        are NOT touched. The user's text and search queries are not
        rewritten.
      - The result is cached per message (as in 0.8.20), so the time is
        the time of the first hop of that request.

0.8.20 change:
    Add "Date Preflight". Nothing else is changed.

    Bonsai2 sometimes shifts relative time expressions ("今日", "今年",
    "最新" ...) to the wrong year when it writes search queries. The Guard
    now fixes the current date from outside and tells the model.

      - Trigger: the stable original user text contains a relative time
        expression (_RELATIVE_TIME_RE). Simple regex only; no classifier.
      - Current date: taken by the Guard itself (Python stdlib only, no
        shell command, no web search, no extra dependency).
      - Valve `timezone`: IANA name (e.g. "Asia/Tokyo"). Empty -> the OS
        local timezone (datetime.now().astimezone()). Invalid -> an error is
        logged and the OS local timezone is used (timezone_source=os-fallback).
        As a stdlib-only aid for Windows without tzdata, fixed offsets such
        as "UTC+9" / "+09:00" are also accepted.
      - Injection: one system block ([Bonsai2 Date Preflight v0.1]) with the
        absolute date, written with _upsert_block(). The user message, the
        stored original user text and the tool counters are not touched.
      - The user's wording / search query is never rewritten by this feature.
      - extract_protected(), the 0.8.19 date mask, final-answer mode and all
        counters are unchanged.

0.8.19 change:
    Fix wrong main-entity selection caused by dates. Nothing else is changed.

    Incident: for "今日は10/6です。2026/10/5の楽天の終値をください",
    extract_protected() returned ["2026"] (STANDALONE_NUM_RE matched the year
    of "2026/10/5"), _get_main_audit_entity() returned "2026", and
    SEARCH_RESULT_AUDIT classified finance.yahoo.co.jp/quote/4755.T as
    SUSPECT, so FETCH_GATE blocked it (reason=suspect-search-result).
    The same ordering problem also made a date placed before a ticker win:
    "2026/10/5の4755の終値" -> "2026".

      - _DATE_MASK_RE (new): complete dates (YYYY/M/D, YYYY-M-D, YYYY/M),
        month 1-12 / day 1-31, not attached to Latin/digit/hyphen tokens
        (so "RTX 2060-6G" and "ABC-2026-10" are not masked).
      - _get_main_audit_entity(): masks such dates (NFKC first) before
        calling extract_protected(). extract_protected() itself is
        unchanged, so QUERY_REPAIR / QUERY_AUDIT / STREAM_QUERY_AUDIT
        behave exactly as in 0.8.18.

    When no entity remains, _get_main_audit_entity() returns None and
    _audit_search_results() returns [] before touching state, so the
    search-result audit, suspect-URL classification, SEARCH_RECOVERY and
    the target-unconfirmed note are skipped (the same fail-open path that
    kanji-only queries already take). Strong entities (Rakuten Hand 5G,
    iPhone 15, 4755 ...) keep full hard-block behavior.

    Known leftovers (unchanged on purpose): a bare year such as "2026の..."
    is still a standalone-number entity; _PURPOSE_TERMS has no 終値/株価;
    per-URL evidence does not include the URL string.

0.8.18 change:
    Improve the one-shot SEARCH_RECOVERY query. Nothing else is changed.
    The fetch side (gate / probe / duplicate / suspension / quota) is
    byte-for-byte the 0.8.17 logic.

      - _UNIT_GROUPS: add "度" (e.g. 40度) and "mAh" so extract_protected()
        no longer drops them.
      - _build_recovery_query(): the main entity is now always quoted
        (an adjacent run of Latin name tokens is kept as one phrase, e.g.
        "Rakuten Hand 5G"). Recovery query layout:

            "main entity phrase" [extra identifiers] [attributes] [purpose]

        * extra identifiers: other protected entities, max 2
        * attributes: capacity / degree / year ... (currency excluded), max 3
        * purpose: ONE term (実売価格 / 価格 / 相場 ...) from a short tuple;
          if none matches, the noun run right after the entity phrase
          (e.g. バッテリー容量) is used instead
      - The old "quote only when identical to the previous query" branch is
        gone (it practically never fired). prev_query stays in the signature.
      - New system note (text only): when the one-shot recovery was used and
        the latest completed search result still does not contain the
        requested subject, tell the model to say so and not to substitute
        another product. No new state key, no change to final-answer mode.

    Unchanged on purpose: Recovery runs once, search_recovery_used /
    search_recovery_pending / search_recovery_query / prev_query state,
    quotas, SEARCH_RESULT_AUDIT, QUERY_REPAIR, tool_choice, wrappers.

    Side effect to be aware of: extract_protected() is shared with
    repair_query(), so "40度" / "mAh" are now also protected in ordinary
    QUERY_REPAIR / QUERY_AUDIT.

0.8.17 change:
    Diagnostics only. No behavior change.

    The 0.8.16 verification could not tell "one fetch_url call passed through
    two stacked gates" apart from "the model requested the same URL twice",
    because FETCH_CALLABLE_PROBE and FETCH_GATE status lines carried no msg=
    and the already-wrapped result was only visible in the per-hop summary
    line (which also carried no msg=).

      - FETCH_GATE_ENTER: one line per gate invocation with msg, a per-gate
        serial (gate=#N) and the raw URL as the model sent it (before
        normalization).
      - msg= added to FETCH_GATE status=wrapped, FETCH_CALLABLE_PROBE
        status=wrapped / invoke, and the per-hop summary line.

    Reading the logs: the same gate=#N twice means two separate model
    requests. Two different gate serials back to back for one request means
    stacked gates.

0.8.16 change:
    Fix double-wrapping of the search_web / fetch_url callables.

    The "already-wrapped" checks looked only at the outermost callable.
    Because functools.update_wrapper(..., updated=()) intentionally does not
    propagate __dict__, the outermost wrapper never carried the flag of the
    wrapper beneath it. When metadata["tools"] persisted across hops, the
    fetch probe wrapper and the fetch gate wrapper were therefore stacked
    again on every hop. A single fetch_url call then passed through several
    gate layers sharing the same fetched_urls, and the inner layer reported
    DUPLICATE for the URL the outer layer had just marked.

    The checks now walk the __wrapped__ chain (max 32 levels) via
    _chain_has_flag(). The fetch gate flag now stores the state_key, so a
    gate built for another message is never mistaken for the current one.

    No other behavior changed.

0.8.15 change:
    Preserve metadata["tools"]["fetch_url"] during search recovery.

    During SEARCH_RECOVERY, fetch_url remains hidden from the model-visible
    body["tools"] list, but is no longer removed from metadata tools.

    This prevents the fetch_url callable and its Guard wrappers from being
    lost across the recovery hop.

0.8.14 change:
    Add one-shot search-result recovery.

    When a completed search_web call produces parseable results but the
    user's main protected entity is not present in the search evidence:

      - arm a one-shot search recovery
      - reserve one remaining search quota slot
      - expose only search_web on the next tool step
      - require a search_web call
      - force a deterministic recovery query at execution time

    Recovery query:
      - main audit entity
      - protected numeric tokens from the user's request
      - if identical to the previous query after normalization,
        quote the main entity

    The recovery is intentionally independent from ordinary QUERY_REPAIR.
    QUERY_REPAIR repairs the model-generated query before execution.
    SEARCH_RECOVERY reacts to bad search results after execution.

0.8.13 change:
    Add fetch suspension after a duplicate fetch attempt.

0.8.12 change:
    BLOCK and DUPLICATE fetch results are returned as normal non-error
    Guard control results rather than raising RuntimeError.

0.8.11 change:
    Prevent duplicate fetch_url execution within the same request.

0.8.10 change:
    Enable real fetch blocking for URLs classified as suspect by the
    search-result audit.

0.8.9 change:
    Make the explicit FETCH_GATE_TEST path perform an actual fetch block.

0.8.8 change:
    Add explicit FETCH_GATE_TEST mode.

0.8.7 change:
    Add FETCH_GATE dry-run.

0.8.6 change:
    Prevent Open WebUI's get_updated_tool_function() from bypassing Guard
    wrappers by avoiding __dict__ propagation from the original callable.

0.8.5 change:
    Add SEARCH_RESULT_AUDIT.
"""

import asyncio
import copy
# 0.8.20: stdlib only (date / timezone handling)
import datetime as _dt
import functools
import itertools
import json
import re
import unicodedata
from typing import Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------
RULES_MARKER = "[Bonsai2 Search Query Rules v0.3]"
FINAL_SYSTEM_MARKER = "[Bonsai2 Final Answer Mode v0.2]"
FINAL_USER_MARKER = "[Bonsai2 Final Answer Mode Active]"
CLOSED_MARKER = "[Bonsai2 Tool Closed Note]"
AUDIT_START = "[Bonsai2 Query Audit]"
AUDIT_END = "[/Bonsai2 Query Audit]"
RECOVERY_START = "[Bonsai2 Search Recovery v0.1]"
RECOVERY_END = "[/Bonsai2 Search Recovery]"
FETCH_GATE_TEST_SYSTEM_MARKER = "[Bonsai2 Fetch Gate Test v0.1]"

# 0.8.20: Date Preflight system block markers
# 0.8.21: marker bumped to v0.2 (date -> date + time)
DATE_PREFLIGHT_START = "[Bonsai2 Date Preflight v0.2]"
DATE_PREFLIGHT_END = "[/Bonsai2 Date Preflight v0.2]"

# 0.8.18: text-only note used after a failed one-shot recovery
TARGET_UNCONFIRMED_MARKER = "[Bonsai2 Target Unconfirmed Note]"

# 0.8.17: per-gate serial numbers (diagnostics only)
_GATE_SERIAL = itertools.count(1)


TOOL_XML_RE = re.compile(
    r"<tool_call>.*?(?:</tool_call>|\Z)",
    re.S,
)

TOOL_RESP_RE = re.compile(
    r"<tool_response>.*?(?:</tool_response>|\Z)",
    re.S,
)

# 0.8.23: raw <tool_call> handling in the final-answer hop.
_RAW_TC_OPEN = "<tool_call>"
_RAW_TC_CLOSE = "</tool_call>"
_RAW_TC_TAG_RE = re.compile(r"</?tool_call>")
# A trailing partial tag shorter than this is treated as ordinary text when the
# stream ends ("<", "<t", ...); "<tool" / "</too" or longer is dropped.
_RAW_TC_MIN_PARTIAL = 5
_TOOL_MARKUP_TOKEN_RE = re.compile(
    r"</?tool_call>|</?tool_response>",
)

# 0.8.24: diagnostic-only raw tool-call markers (read-only observation).
_DIAG_MARKERS = (
    "<tool_call>",
    "</tool_call>",
    "<function=",
    "<parameter",
)
_DIAG_PREVIEW_MAX = 200


def _scrub_tool_markup(
    text: str,
) -> str:
    """
    0.8.23: remove textual <tool_call>/<tool_response> markup (complete
    blocks first, then stray tags) from text that is handed to the model or
    to the user as plain evidence. Never raises.
    """
    try:
        if not isinstance(
            text,
            str,
        ) or ("<tool_" not in text and "</tool_" not in text):
            return text

        cleaned = TOOL_RESP_RE.sub(
            "",
            TOOL_XML_RE.sub(
                "",
                text,
            ),
        )

        return _TOOL_MARKUP_TOKEN_RE.sub(
            "",
            cleaned,
        )

    except Exception:
        return text


def _partial_suffix_len(
    data: str,
    tag: str,
) -> int:
    """
    0.8.23: length of the longest suffix of `data` that is a proper prefix of
    `tag` (so that a tag split across stream chunks is held back).
    """
    for k in range(
        min(
            len(data),
            len(tag) - 1,
        ),
        0,
        -1,
    ):
        if data.endswith(tag[:k]):
            return k

    return 0


# ---------------------------------------------------------------------------
# Generic protected-term extraction
# No product-name dictionary.
# ---------------------------------------------------------------------------
_UNIT_GROUPS = {
    "currency": [
        "万円",
        "円",
        "jpy",
        "¥",
        "元",
        "cny",
        "rmb",
        "ドル",
        "usd",
        "ユーロ",
        "eur",
        "ウォン",
        "krw",
    ],
    "volume": [
        "ミリリットル",
        "リットル",
        "ml",
        "cc",
        "l",
    ],
    "mass": [
        "キログラム",
        "グラム",
        "mg",
        "kg",
        "g",
    ],
    "storage": [
        "gb",
        "tb",
        "mb",
    ],
    "length": [
        "mm",
        "cm",
        "km",
        "m",
        "インチ",
    ],
    "year": [
        "年",
    ],
    # 0.8.18: alcohol strength etc. (40度). Previously dropped entirely.
    "degree": [
        "度",
    ],
    # 0.8.18: battery capacity (2630mAh).
    "battery": [
        "mah",
    ],
}


_UNIT_TO_GROUP = {
    unit.lower(): group for group, units in _UNIT_GROUPS.items() for unit in units
}


_UNIT_ALT = "|".join(
    re.escape(u)
    for u in sorted(
        _UNIT_TO_GROUP.keys(),
        key=len,
        reverse=True,
    )
)


NUM_UNIT_RE = re.compile(
    rf"(?<![A-Za-z0-9.])" rf"(\d[\d,]*(?:\.\d+)?)\s*({_UNIT_ALT})" rf"(?![A-Za-z])",
    re.I,
)


STANDALONE_NUM_RE = re.compile(r"(?<![A-Za-z0-9.,])\d{3,}(?![A-Za-z0-9.,])")


KATAKANA_RE = re.compile(r"[\u30A1-\u30FA\u30FC\u30FB]{3,}")


QUOTED_RE = re.compile(r"[「『“\"]([^」』”\"\n]{2,40})[」』”\"]")


LATIN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]+")


_LATIN_STOP = {
    "what",
    "which",
    "how",
    "when",
    "where",
    "who",
    "why",
    "please",
    "the",
    "and",
    "for",
    "with",
    "from",
    "about",
    "can",
    "does",
    "is",
    "are",
    "price",
    "current",
    "latest",
    "today",
    "now",
    "search",
    "web",
}


def _nfkc(
    text: str,
) -> str:
    return unicodedata.normalize(
        "NFKC",
        str(text),
    )


def _norm(
    text: str,
) -> str:
    """
    Normalization used only for presence comparison.
    """
    s = _nfkc(text).lower()

    return re.sub(
        r"[\s,]+",
        "",
        s,
    )


def _content_to_text(
    content,
) -> str:
    if isinstance(
        content,
        str,
    ):
        return content

    if isinstance(
        content,
        list,
    ):
        parts = []

        for item in content:
            if isinstance(
                item,
                dict,
            ):
                if item.get("type") == "text":
                    parts.append(
                        str(
                            item.get(
                                "text",
                                "",
                            )
                        )
                    )

            elif isinstance(
                item,
                str,
            ):
                parts.append(item)

        return "\n".join(parts)

    if content is None:
        return ""

    return str(content)


def _find_numerics(
    text: str,
) -> list:
    """
    text must already be NFKC-normalized.
    """
    out = []

    for m in NUM_UNIT_RE.finditer(text):
        unit = m.group(2).lower()

        out.append(
            {
                "start": m.start(),
                "end": m.end(),
                "raw": m.group(0),
                "group": _UNIT_TO_GROUP.get(unit),
            }
        )

    return out


def extract_protected(
    user_text: str,
) -> dict:
    """
    Extract terms that should survive into a search query:

      - quoted strings
      - katakana words
      - Latin tokens with digit/uppercase
      - number+unit/currency tokens
      - standalone numbers of 3+ digits

    No product dictionary is used.
    """
    text = _nfkc(user_text)

    found = []

    for m in QUOTED_RE.finditer(text):
        found.append(
            (
                m.start(1),
                m.group(1).strip(),
            )
        )

    for m in KATAKANA_RE.finditer(text):
        word = m.group(0).strip("・")

        if len(word) >= 3:
            found.append(
                (
                    m.start(),
                    word,
                )
            )

    numerics = _find_numerics(text)

    blanked = list(text)

    for n in numerics:
        for i in range(
            n["start"],
            n["end"],
        ):
            blanked[i] = " "

    blanked = "".join(blanked)

    for m in LATIN_RE.finditer(blanked):
        tok = m.group(0)

        if tok.lower() in _LATIN_STOP:
            continue

        if any(c.isdigit() for c in tok) or any(c.isupper() for c in tok):
            found.append(
                (
                    m.start(),
                    tok,
                )
            )

    for m in STANDALONE_NUM_RE.finditer(blanked):
        found.append(
            (
                m.start(),
                m.group(0),
            )
        )

    found.sort(
        key=lambda x: x[0],
    )

    entities = []
    seen = set()

    for _, tok in found:
        key = _norm(tok)

        if key and key not in seen:
            seen.add(key)
            entities.append(tok)

    return {
        "entities": entities[:8],
        "numerics": numerics,
    }


# ---------------------------------------------------------------------------
# Recovery-query helpers (0.8.18)
#
# Pure functions. Used only by Filter._build_recovery_query().
# No product dictionary. The purpose tuple is deliberately tiny and is ordered
# most-specific first so that "実売価格" wins over its substring "価格".
# ---------------------------------------------------------------------------
_PURPOSE_TERMS = (
    "実売価格",
    "中古価格",
    "買取価格",
    "発売価格",
    "最安値",
    "発売日",
    "相場",
    "価格",
    "値段",
)

# Adjacent Latin name tokens: "Rakuten Hand 5G", "Galaxy S24 Ultra", ...
_LATIN_PHRASE_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9\-]*(?: [A-Za-z0-9][A-Za-z0-9\-]*)*"
)

# Katakana / kanji noun run right after the entity phrase (fallback purpose).
_TOPIC_RE = re.compile(r"[ \t]*([\u30A1-\u30FA\u30FC\u4E00-\u9FFF]{2,12})")

# 0.8.19: complete date expressions (2026/10/5, 2026-10-05, 2026/10) are not
# identifiers. Used ONLY by Filter._get_main_audit_entity().
_DATE_MASK_RE = re.compile(
    r"(?<![A-Za-z0-9\-])"
    r"(?:19|20)\d{2}"
    r"[/\-](?:0?[1-9]|1[0-2])"
    r"(?:[/\-](?:0?[1-9]|[12]\d|3[01]))?"
    r"(?![A-Za-z0-9])"
)

# 0.8.20: relative time expressions that trigger Date Preflight.
# Applied to NFKC-normalized text. "いま" is guarded so that it does not match
# inside verb endings such as "います" / "いません" / "いました" / "ただいま".
_RELATIVE_TIME_RE = re.compile(
    r"今日|現在|最新|最近|今年|今月|今週|昨日|明日|現時点"
    r"|(?<![\u3041-\u309F])いま(?![すせしさい])"
    r"|\b(?:today|now|currently|current|latest|recent|recently"
    r"|yesterday|tomorrow|this\s+(?:year|month|week))\b",
    re.I,
)

# 0.8.20: fixed-offset fallback for the timezone valve ("UTC+9", "+09:00").
_FIXED_OFFSET_RE = re.compile(
    r"(?:UTC|GMT)?\s*([+-])(\d{1,2})(?::?(\d{2}))?",
    re.I,
)

# 0.8.20: Japanese weekday names (datetime.weekday(): Monday == 0).
_WEEKDAYS_JA = ("月", "火", "水", "木", "金", "土", "日")

_RECOVERY_PHRASE_MAX_TOKENS = 6
_RECOVERY_MAX_EXTRAS = 2
_RECOVERY_MAX_ATTRS = 3


def _is_name_token(
    tok: str,
) -> bool:
    if not tok:
        return False

    if tok.lower() in _LATIN_STOP:
        return False

    return any(c.isdigit() for c in tok) or any(c.isupper() for c in tok)


def _expand_entity_phrase(
    text: str,
    entity: str,
) -> str:
    """
    If `entity` is a single Latin token, extend it over adjacent Latin tokens
    (separated by single spaces) that look like name parts (digit/uppercase).

        text="Rakuten Hand 5G バッテリー容量", entity="Rakuten"
        -> "Rakuten Hand 5G"

    Katakana / quoted / other entities are returned unchanged.
    `text` is NFKC-normalized here.
    """
    ent = _nfkc(entity).strip()

    if not ent:
        return ent

    nt = _nfkc(text)

    # The user already delimited the subject with quotes (「...」 / "...").
    # If a quoted span contains the entity, that span is the phrase.
    for qm in QUOTED_RE.finditer(nt):
        quoted = qm.group(1).strip()

        if quoted and ent.lower() in quoted.lower():
            return quoted

    if not LATIN_RE.fullmatch(ent):
        return ent

    for m in _LATIN_PHRASE_RE.finditer(nt):
        tokens = m.group(0).split(" ")

        idx = None

        for i, t in enumerate(tokens):
            if t.lower() == ent.lower():
                idx = i
                break

        if idx is None:
            continue

        start = idx
        end = idx + 1

        while (
            start > 0
            and _is_name_token(tokens[start - 1])
            and (end - start) < _RECOVERY_PHRASE_MAX_TOKENS
        ):
            start -= 1

        while (
            end < len(tokens)
            and _is_name_token(tokens[end])
            and (end - start) < _RECOVERY_PHRASE_MAX_TOKENS
        ):
            end += 1

        return " ".join(tokens[start:end])

    return ent


def _pick_purpose_term(
    text: str,
) -> str:
    """
    Return ONE purpose term found in the (NFKC) text, most specific first,
    or "".
    """
    nt = _nfkc(text)

    for term in _PURPOSE_TERMS:
        if term in nt:
            return term

    return ""


def _adjacent_topic(
    text: str,
    phrase: str,
) -> str:
    """
    Fallback purpose: the katakana/kanji noun run directly after the entity
    phrase (e.g. "Rakuten Hand 5G バッテリー容量" -> "バッテリー容量").
    Returns "" when there is none.
    """
    nt = _nfkc(text)

    pos = nt.find(phrase)

    if pos < 0:
        return ""

    m = _TOPIC_RE.match(
        nt,
        pos + len(phrase),
    )

    if not m:
        return ""

    return m.group(1)


GUARD_CANDIDATE_STOP_RE = re.compile(
    r"(?:で[、,，]|です|であり|について|に関して|"
    r"を調べ|を確認|を比較|を検索|を教えて|"
    r"の公式|の価格|の仕様|を報告|をまとめ|を整理)"
)

def _select_query_candidates(user_text, protected):
    text = _nfkc(user_text)

    def mask_quotes(value, examples_only=False):
        chars = list(value)

        for match in QUOTED_RE.finditer(value):
            if examples_only:
                before = value[max(0, match.start() - 32):match.start()]
                after = value[match.end():min(len(value), match.end() + 48)]

                preceding_example = re.search(
                    r"(?:説明例|例として|例えば|たとえば|例[：:])\s*$",
                    before,
                )
                following_example = re.match(
                    r"\s*(?:(?:という文|という表現|という言葉)\s*)?"
                    r"(?:は\s*)?[^。！？\n]{0,16}?"
                    r"(?:例|サンプル)"
                    r"(?:です|でした|になります|となります|にすぎません|として)",
                    after,
                )

                if not preceding_example and not following_example:
                    continue

            for i in range(match.start(), match.end()):
                if chars[i] not in "\r\n":
                    chars[i] = " "

        return "".join(chars)

    # 対象指定の検出では引用内をすべてマスクする。
    marker_view = mask_quotes(text)

    target_re = re.compile(
        r"(?:今回の)?(?:対象(?:製品|商品|名称|名)?は|"
        r"調査対象は|比較対象は|"
        r"比較する(?:製品|商品|対象)は|"
        r"製品名は|商品名は|ブランド名は|テーマは|"
        r"(?:今回)?調べるのは|"
        r"(?:今回)?確認するのは|"
        r"(?:今回)?調査するのは)"
        r"([^。！？\n]{1,80})"
    )

    targets = []

    for match in target_re.finditer(marker_view):
        raw = text[match.start(1):match.end(1)]
        stop = GUARD_CANDIDATE_STOP_RE.search(raw)
        prefix = raw[:stop.start()] if stop else raw

        if prefix.strip():
            targets.append((match.start(1), prefix))

    # 明示的な対象指定がない場合は、比較文の対象部分も確認する。
    if not targets:
        comparison_re = re.compile(
            r"([^。！？\n]{1,80}?)"
            r"(?=の(?:味と価格|価格|味|性能|仕様|正式名称|所有者|"
            r"メーカー|違い|評価)(?:を|について)?比較)"
        )

        for match in comparison_re.finditer(marker_view):
            segment = text[match.start(1):match.end(1)]
            if segment.strip():
                targets.append((match.start(1), segment))

    items = []

    def add_strong_candidates(segment, offset):
        for m in QUOTED_RE.finditer(segment):
            phrase = m.group(1).strip()
            if len(phrase) <= 12 or re.search(r"[A-Za-z0-9]", phrase):
                items.append((offset + m.start(1), phrase))

        head = r"[A-Z][A-Za-z0-9-]*"
        tail = r"(?:[A-Z][A-Za-z0-9-]*|\d+[A-Za-z][A-Za-z0-9-]*|\d+)"
        pattern = re.compile(
            r"(?<![A-Za-z0-9])(" + head +
            r"(?:\s+" + tail + r")*)(?![A-Za-z0-9])"
        )

        for m in pattern.finditer(segment):
            items.append((offset + m.start(1), m.group(1).strip()))

    def add_protected_from_segment(segment, offset, respect_stop=False):
        found = []

        for entity in protected["entities"]:
            value = entity.strip()
            pos = segment.find(value)
            if value and pos >= 0:
                found.append((pos, value))

        found.sort(key=lambda item: item[0])

        if respect_stop and found:
            # Prefer a subject-to-property boundary ("の公式", "の価格",
            # "の仕様") over a later generic action boundary. This makes the
            # entity immediately before that relation the target, even when
            # an unrelated quoted name was mentioned earlier in the prompt.
            boundary = re.search(r"の公式|の価格|の仕様", segment)
            if boundary is None:
                boundary = GUARD_CANDIDATE_STOP_RE.search(segment)

            if boundary:
                preceding = [
                    (pos, value) for pos, value in found
                    if pos < boundary.start()
                ]

                if preceding:
                    # Anchor on the protected term nearest the subject
                    # boundary. Keep earlier terms only when explicitly
                    # linked as parallel targets (AとB / A、B / AやB).
                    eligible = [preceding[-1]]

                    for pos, value in reversed(preceding[:-1]):
                        next_pos, next_value = eligible[0]
                        between = segment[pos + len(value):next_pos]

                        if re.search(
                            r"(?:と|や|、|,|および|及び|ならびに|並びに)\s*$",
                            between,
                        ):
                            eligible.insert(0, (pos, value))
                        else:
                            break

                    found = eligible
                else:
                    found = []

        for pos, value in found:
            items.append((offset + pos, value))

    if targets:
        # 明示的な対象指定の範囲では、正当な引用名も候補として認める。
        for offset, segment in targets:
            add_strong_candidates(segment, offset)
            add_protected_from_segment(segment, offset)
    else:
        # Quoted strings are not globally strong candidates: a quoted term
        # mentioned in explanatory prose must not suppress the actual target.
        # Explicit target-like quoted names can still be recovered by the
        # protected-term pass below, using their position relative to a
        # subject/action boundary.
        candidate_view = mask_quotes(text, examples_only=True)
        strong_candidate_view = mask_quotes(text)

        # When the request contains a subject/property boundary, strong
        # uppercase candidates are collected only from the subject side.
        # Later output instructions such as "titles and URL" are not search
        # entities and must not create a repair/audit violation.
        strong_boundary = re.search(
            r"の公式|の価格|の仕様",
            strong_candidate_view,
        )
        if strong_boundary is not None:
            strong_candidate_view = strong_candidate_view[:strong_boundary.start()]

        add_strong_candidates(strong_candidate_view, 0)

        # Always consider protected terms even when another strong candidate
        # exists. When a subject/action boundary is present, select the
        # nearest protected term before it and keep earlier terms only when
        # connected as a parallel list (e.g. AとBの公式サイト).
        add_protected_from_segment(candidate_view, 0, respect_stop=True)

    items.sort(key=lambda item: item[0])
    all_values = [value for _, value in items]
    result = []
    seen = set()

    for _, value in items:
        key = _norm(value)
        if not key or key in seen:
            continue

        if any(
            key != _norm(other) and key in _norm(other)
            for other in all_values
        ):
            continue

        seen.add(key)
        result.append(value)

    return result


def repair_query(
    user_text: str,
    query: str,
) -> tuple:
    """
    Verify and repair a generated search query against the user's wording.

    Numeric conflict repair:
        2000元 -> 2000円
        750ml  -> 700ml

    Missing protected terms are prepended.

    Returns:
        (new_query, info)

    This function never raises.
    """
    info = {
        "missing": [],
        "replaced": [],
        "changed": False,
    }

    try:
        protected = extract_protected(
            user_text,
        )

        q = _nfkc(query)

        # ---------------------------------------------------------------
        # 1. Conflicting numeric tokens -> replace
        # ---------------------------------------------------------------
        user_by_group = {}

        for n in protected["numerics"]:
            if n["group"]:
                user_by_group.setdefault(
                    n["group"],
                    {},
                )[
                    _norm(n["raw"])
                ] = n["raw"]

        q_numerics = _find_numerics(q)

        for qn in reversed(q_numerics):
            group = qn["group"]

            if not group or group not in user_by_group:
                continue

            candidates = user_by_group[group]

            if len(candidates) != 1:
                continue

            (
                (
                    user_key,
                    user_raw,
                ),
            ) = candidates.items()

            if _norm(qn["raw"]) == user_key:
                continue

            if user_key in _norm(q):
                continue

            info["replaced"].append(
                (
                    qn["raw"],
                    user_raw,
                )
            )

            q = q[: qn["start"]] + user_raw + q[qn["end"] :]

        # ---------------------------------------------------------------
        # 2. Missing protected terms -> prepend
        # ---------------------------------------------------------------
        qn_norm = _norm(q)

        missing = []

        for ent in _select_query_candidates(user_text, protected):
            if _norm(ent) not in qn_norm:
                missing.append(ent)

        for n in protected["numerics"]:
            if _norm(n["raw"]) not in qn_norm and n["raw"] not in missing:
                missing.append(n["raw"])

        if missing:
            q = " ".join(missing + [q]).strip()

            info["missing"] = missing

        info["changed"] = bool(info["missing"] or info["replaced"])

        return (
            q,
            info,
        )

    except Exception:
        return (
            query,
            info,
        )


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------
class Filter:

    class Valves(BaseModel):

        priority: int = Field(
            default=0,
            description="Filter priority.",
        )

        max_searches: int = Field(
            default=2,
            ge=0,
            le=10,
            description=("Maximum successful search_web calls per response."),
        )

        max_fetches: int = Field(
            default=2,
            ge=0,
            le=10,
            description=("Maximum successful fetch_url calls per response."),
        )

        max_total_tool_turns: int = Field(
            default=4,
            ge=1,
            le=20,
            description=("Hard cap on tool-calling turns."),
        )

        disable_parallel_tool_calls: bool = Field(
            default=True,
            description=("Disable parallel tool calls for Bonsai2."),
        )

        force_search_for_current_queries: bool = Field(
            default=True,
            description=(
                "Require a tool call on the first LLM call "
                "for current/time-sensitive queries."
            ),
        )

        force_search_narrow_tools: bool = Field(
            default=True,
            description=("On the forced first call, expose only search_web."),
        )

        sanitize_history_tool_xml: bool = Field(
            default=True,
            description=(
                "Strip textual <tool_call>/<tool_response> XML "
                "from assistant messages in history."
            ),
        )

        final_mode_add_stop: bool = Field(
            default=True,
            description=("In final-answer mode add stop=['<tool_call>']."),
        )

        flatten_tool_history_in_final_mode: bool = Field(
            default=False,
            description=("EXPERIMENTAL: flatten native tool history in final mode."),
        )

        # 0.8.22:
        final_answer_after_limit: bool = Field(
            default=True,
            description=(
                "When a tool limit is reached, close only the tools and "
                "still generate the final answer from the retrieved results "
                "(flatten tool history, no <tool_call> stop sequence, limit "
                "note, empty-response fallback). False = 0.8.20 behavior."
            ),
        )

        # 0.8.22:
        final_answer_fallback: bool = Field(
            default=True,
            description=(
                "If the final-answer hop streams no content at all, inject "
                "a short fallback text built from the retrieved results."
            ),
        )

        # 0.8.23:
        final_answer_strip_raw_tool_call: bool = Field(
            default=True,
            description=(
                "Final-answer hop only: remove raw <tool_call> text (chunk "
                "boundary safe) and drop native tool_calls from the "
                "streamed answer. Normal tool hops are never touched."
            ),
        )

        # 0.8.24:
        raw_tool_call_diag: bool = Field(
            default=True,
            description=(
                "Diagnostic only: log RAW_TOOL_CALL_DIAG when a non-final "
                "hop streams raw <tool_call> text. Never modifies the "
                "stream, tools, tool_choice or finish_reason."
            ),
        )

        query_audit_log: bool = Field(
            default=True,
            description=(
                "Log whether the last executed search_web query "
                "preserved the user's terms."
            ),
        )

        query_audit_feedback: bool = Field(
            default=True,
            description=(
                "If a search remains, tell the model which terms "
                "the previous query lost."
            ),
        )

        wrap_search_query_repair: bool = Field(
            default=True,
            description=(
                "Repair search_web query immediately before execution "
                "using the stable original user text."
            ),
        )

        search_recovery: bool = Field(
            default=True,
            description=(
                "Use one remaining search quota slot for a recovery "
                "search when the completed search results do not contain "
                "the user's main protected entity."
            ),
        )

        stream_probe: bool = Field(
            default=True,
            description=("Read-only native tool-call / textual XML stream probe."),
        )

        stream_query_audit: bool = Field(
            default=True,
            description=(
                "Read-only audit of actual native search_web query "
                "arguments reconstructed from stream deltas."
            ),
        )

        search_result_audit: bool = Field(
            default=True,
            description=(
                "Read-only audit of completed search_web results against "
                "the user's main protected entity."
            ),
        )

        fetch_callable_probe: bool = Field(
            default=True,
            description=(
                "Probe the fetch_url callable without changing normal "
                "successful fetch behavior."
            ),
        )

        fetch_gate_dry_run: bool = Field(
            default=False,
            description=(
                "When True, suspect fetches are logged only. "
                "When False, suspect fetches are actually blocked."
            ),
        )

        fetch_gate_fixed_test_mode: bool = Field(
            default=True,
            description=("Enable explicit FETCH_GATE_TEST diagnostic mode."),
        )

        fetch_gate_test_url: str = Field(
            default=("https://kaitori-rudeya.com/product/item/1486"),
            description=(
                "Fixed URL used by FETCH_GATE_TEST as a synthetic " "suspect URL."
            ),
        )

        fetch_gate_test_marker: str = Field(
            default="FETCH_GATE_TEST",
            description=("Exact first-line marker used to enter fixed gate-test mode."),
        )

        # 0.8.20:
        date_preflight: bool = Field(
            default=True,
            description=(
                "When the user text contains a relative time expression, "
                "give the model the current absolute date as a system block. "
                "No web search / tool turn is used."
            ),
        )

        # 0.8.20:
        timezone: str = Field(
            default="",
            description=(
                "IANA timezone for Date Preflight, e.g. Asia/Tokyo. "
                "Empty = use the OS local timezone."
            ),
        )

    def __init__(self):
        self.valves = self.Valves()

        self._probe = {}
        self._audit_user_text = {}
        self._audited_search_results = set()

        self._fetch_gate_state = {}

        # 0.8.20: per-message Date Preflight result cache
        self._date_preflight_cache = {}

        # 0.8.22: per-message fallback text for an empty final-answer hop
        self._final_fallback = {}

        # 0.8.23: per-message state of the final-answer hop (set by
        # request(), consumed by stream())
        self._final_hop = {}

        # 0.8.24: per-message snapshot of the last request() hop and the
        # request-hop counter (diagnostics only; never read by any decision)
        self._hop_diag = {}
        self._hop_seq = {}

        # 0.8.25: fetch-result diagnostic de-duplication (read-only)
        self._fetch_result_diag_ids = set()

    # ------------------------------------------------------------------
    # Bonsai / tool helpers
    # ------------------------------------------------------------------
    def _is_bonsai(
        self,
        body: dict,
    ) -> bool:
        model = str(
            body.get(
                "model",
                "",
            )
        ).lower()

        return (
            "bonsai2" in model
            or "ternary-bonsai-2-27b" in model
            or "bonsai2-27b" in model
        )

    @staticmethod
    def _tool_name(
        tool,
    ) -> Optional[str]:
        if not isinstance(
            tool,
            dict,
        ):
            return None

        function = (
            tool.get(
                "function",
                {},
            )
            or {}
        )

        name = function.get("name")

        if isinstance(
            name,
            str,
        ):
            return name

        return None

    def _has_tool(
        self,
        tools,
        name: str,
    ) -> bool:
        if not isinstance(
            tools,
            list,
        ):
            return False

        return any(self._tool_name(tool) == name for tool in tools)

    @staticmethod
    def _last_user_index(
        messages: list,
    ) -> int:
        for i in range(
            len(messages) - 1,
            -1,
            -1,
        ):
            message = messages[i]

            if (
                isinstance(
                    message,
                    dict,
                )
                and message.get("role") == "user"
            ):
                return i

        return -1

    def _message_matches_id(
        self,
        message: dict,
        message_id: Optional[str],
    ) -> bool:
        if not message_id:
            return False

        possible = (
            message.get("id"),
            message.get("message_id"),
        )

        return any(
            str(value) == str(message_id) for value in possible if value is not None
        )

    def _extract_user_text_from_messages(
        self,
        messages: list,
        message_id: Optional[str],
    ) -> str:
        if not isinstance(
            messages,
            list,
        ):
            return ""

        if message_id:
            for message in messages:
                if not isinstance(
                    message,
                    dict,
                ):
                    continue

                if message.get("role") != "user":
                    continue

                if self._message_matches_id(
                    message,
                    message_id,
                ):
                    text = _content_to_text(
                        message.get(
                            "content",
                            "",
                        )
                    )

                    cut = text.find(FINAL_USER_MARKER)

                    if cut != -1:
                        text = text[:cut].rstrip()

                    return text.strip()

        for i in range(
            len(messages) - 1,
            -1,
            -1,
        ):
            message = messages[i]

            if not isinstance(
                message,
                dict,
            ):
                continue

            if message.get("role") != "user":
                continue

            text = _content_to_text(
                message.get(
                    "content",
                    "",
                )
            )

            if FINAL_USER_MARKER in text:
                text = text.split(
                    FINAL_USER_MARKER,
                    1,
                )[0].rstrip()

            if text.strip():
                return text.strip()

        return ""

    def _latest_user_text(
        self,
        messages: list,
    ) -> str:
        idx = self._last_user_index(messages)

        if idx == -1:
            return ""

        text = _content_to_text(
            messages[idx].get(
                "content",
                "",
            )
        )

        cut = text.find(FINAL_USER_MARKER)

        if cut != -1:
            text = text[:cut].rstrip()

        return text

    @staticmethod
    def _append_text(
        content,
        text: str,
    ):
        if isinstance(
            content,
            str,
        ):
            return content + "\n\n" + text

        if isinstance(
            content,
            list,
        ):
            return content + [
                {
                    "type": "text",
                    "text": text,
                }
            ]

        return _content_to_text(content) + "\n\n" + text

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_url(
        url: str,
    ) -> str:
        try:
            from urllib.parse import (
                urlsplit,
                urlunsplit,
            )

            raw = str(url).strip()

            if not raw:
                return ""

            parts = urlsplit(raw)

            if not parts.scheme or not parts.netloc:
                return raw.rstrip("/")

            scheme = parts.scheme.lower()
            netloc = parts.netloc.lower()

            normalized = urlunsplit(
                (
                    scheme,
                    netloc,
                    parts.path,
                    parts.query,
                    "",
                )
            )

            if normalized.endswith("/"):
                normalized = normalized[:-1]

            return normalized

        except Exception:
            return str(url).strip().rstrip("/")

    @staticmethod
    def _extract_urls_from_text(
        text: str,
    ) -> set:
        if not isinstance(
            text,
            str,
        ):
            return set()

        urls = set()

        pattern = re.compile(
            r"""https?://[^\s<>\]\)"']+""",
            re.I,
        )

        for match in pattern.findall(text):
            url = match.rstrip(".,;:!?）】」』")

            if url:
                urls.add(Filter._normalize_url(url))

        return {url for url in urls if url}

    def _get_fetch_gate_state(
        self,
        state_key: str,
        user_text: str,
    ) -> dict:
        state = self._fetch_gate_state.get(state_key)

        if not isinstance(
            state,
            dict,
        ):
            state = {
                "entity": "",
                "suspect_urls": set(),
                "ok_urls": set(),
                "explicit_urls": set(),
                "fetched_urls": set(),
                # 0.8.13
                "fetch_suspended": False,
                "suspend_search_attempts": 0,
                "search_attempts_seen": 0,
                "test_mode": False,
                "test_url": "",
                # 0.8.14
                "search_recovery_used": False,
                "search_recovery_pending": False,
                "search_recovery_query": "",
                "search_recovery_armed_attempts": 0,
            }

            self._fetch_gate_state[state_key] = state

        if user_text:
            state["explicit_urls"].update(self._extract_urls_from_text(user_text))

        return state

    def _trim_fetch_gate_state(
        self,
    ) -> None:
        if len(self._fetch_gate_state) <= 100:
            return

        keys = list(self._fetch_gate_state.keys())

        for key in keys[
            : max(
                1,
                len(keys) - 100,
            )
        ]:
            self._fetch_gate_state.pop(
                key,
                None,
            )

    # ------------------------------------------------------------------
    # Fixed test mode
    # ------------------------------------------------------------------
    def _is_fetch_gate_test_request(
        self,
        user_text: str,
    ) -> bool:
        if not self.valves.fetch_gate_fixed_test_mode:
            return False

        if not isinstance(
            user_text,
            str,
        ):
            return False

        lines = user_text.strip().splitlines()

        if not lines:
            return False

        return lines[0].strip() == self.valves.fetch_gate_test_marker

    def _activate_fetch_gate_test(
        self,
        state_key: str,
        user_text: str,
    ) -> bool:
        if not self._is_fetch_gate_test_request(user_text):
            return False

        state = self._get_fetch_gate_state(
            state_key,
            "",
        )

        test_url = self._normalize_url(self.valves.fetch_gate_test_url)

        state["test_mode"] = True

        state["test_url"] = test_url

        print(
            "[Bonsai2 Web Search Guard] "
            "FETCH_GATE_TEST "
            f"msg={state_key} "
            "status=activated "
            f"url={test_url!r}"
        )

        return True

    def _apply_fetch_gate_test_mode(
        self,
        messages: list,
        state_key: str,
        test_url: str,
    ) -> list:
        block = (
            f"{FETCH_GATE_TEST_SYSTEM_MARKER}\n"
            "This is an explicit diagnostic test of the "
            "Bonsai2 fetch gate.\n"
            "Do not call search_web.\n"
            "Call fetch_url exactly once.\n"
            f"Use this exact URL: {test_url}\n"
            "The fetch gate is active. The fixed test URL must be "
            "blocked before the underlying fetch executes.\n"
        )

        return self._upsert_block(
            messages,
            FETCH_GATE_TEST_SYSTEM_MARKER,
            None,
            block,
        )

    # ------------------------------------------------------------------
    # System-message helpers
    # ------------------------------------------------------------------
    def _add_to_system(
        self,
        messages: list,
        text: str,
        marker: str,
    ) -> list:
        for message in messages:
            if (
                isinstance(
                    message,
                    dict,
                )
                and message.get("role") == "system"
                and marker
                in _content_to_text(
                    message.get(
                        "content",
                        "",
                    )
                )
            ):
                return messages

        for i, message in enumerate(messages):
            if (
                isinstance(
                    message,
                    dict,
                )
                and message.get("role") == "system"
            ):
                copied = dict(message)

                copied["content"] = (
                    _content_to_text(
                        message.get(
                            "content",
                            "",
                        )
                    )
                    + "\n\n"
                    + text
                )

                messages[i] = copied

                return messages

        messages.insert(
            0,
            {
                "role": "system",
                "content": text,
            },
        )

        return messages

    def _upsert_block(
        self,
        messages: list,
        start: str,
        end: Optional[str],
        block: Optional[str],
    ) -> list:
        if end is None:
            pattern = re.compile(
                re.escape(start) + r".*?$",
                re.S,
            )
        else:
            pattern = re.compile(
                re.escape(start) + r".*?" + re.escape(end),
                re.S,
            )

        for i, message in enumerate(messages):
            if not (
                isinstance(
                    message,
                    dict,
                )
                and message.get("role") == "system"
            ):
                continue

            content = _content_to_text(
                message.get(
                    "content",
                    "",
                )
            )

            if start in content:
                if end is None:
                    new = re.sub(
                        pattern,
                        "",
                        content,
                    ).rstrip()
                else:
                    new = pattern.sub(
                        "",
                        content,
                    ).rstrip()

                if block:
                    new += "\n\n" + block

                copied = dict(message)

                copied["content"] = new

                messages[i] = copied

                return messages

        if block:
            return self._add_to_system(
                messages,
                block,
                start,
            )

        return messages

    # ------------------------------------------------------------------
    # Search query rules
    # ------------------------------------------------------------------
    def _apply_search_query_rules(
        self,
        messages: list,
    ) -> list:
        rules = f"""
{RULES_MARKER}

When using search_web and fetch_url, follow these rules.

Search query rules:
1. Preserve product names, brand names, model names, titles, proper nouns,
   numbers, currencies, units, capacities, years, and country names from
   the user's request.
2. Do not translate, transliterate, romanize, autocorrect, or replace a
   product or brand name unless the user explicitly asks for that.
3. Do not change currency or units. For example, 円/JPY must not become
   元/CNY/USD, and 700ml must not become 750ml.
4. Preserve the user's requested factual category exactly.
5. Prefer a short search query that preserves the essential entity and
   constraints specified by the user.
6. Before calling search_web, verify that the core entity or product name
   in the query matches the wording used by the user.
7. If uncertain about a name, preserve the user's original wording instead
   of inventing an alternative.

Fetch selection rules:
8. When choosing a page to fetch, prioritize evidence that is most directly
   relevant to the specific fact the user asked to establish.
9. Prefer a page that directly states, displays, or documents the requested
   fact over a page that merely discusses the same general topic.
10. Prefer pages about the exact entity, product, document, event, person,
    service, or other object requested by the user over related entities.
11. When several results are relevant, prefer the result that provides the
    most specific and verifiable information needed to answer the question.
12. Prefer primary or first-hand sources when they directly contain the
    requested information.
13. Aggregated, comparative, or reference pages may be preferred when they
    directly provide the requested fact more clearly or comprehensively.
14. General recommendation articles, opinion pieces, reviews, summaries,
    and explanatory articles should not be preferred over a more direct
    source when the latter is available.
15. Do not fetch a page merely because it is thematically related.
16. Preserve entity identity and variant identity when selecting a page.
17. If search results do not contain a sufficiently direct source, use the
    most relevant available source and explicitly recognize the limitation.
18. Do not infer authority from domain name, popularity, or search ranking.
"""

        return self._add_to_system(
            messages,
            rules,
            RULES_MARKER,
        )

    def _apply_closed_note(
        self,
        messages: list,
        closed: list,
    ) -> list:
        note = (
            f"{CLOSED_MARKER}\n"
            f"The following tool(s) are no longer available in "
            f"this response: {', '.join(closed)}.\n"
            "Do not call them and do not write <tool_call> text for them. "
            "Use the remaining tools or answer with information already obtained."
        )

        return self._add_to_system(
            messages,
            note,
            CLOSED_MARKER,
        )

    def _apply_target_unconfirmed_note(
        self,
        messages: list,
        subject: str,
    ) -> list:
        """
        0.8.18: text-only note. Added when the one-shot recovery was used and
        the latest completed search result still lacks the requested subject.
        """
        note = (
            f"{TARGET_UNCONFIRMED_MARKER}\n"
            "The searches performed for this request did not return "
            "results that mention the requested subject: "
            f"{subject}\n"
            "In your answer, state clearly that the requested subject "
            "could not be confirmed in the search results.\n"
            "Report only facts that are actually present in the retrieved "
            "results, and say which product or item those facts refer to.\n"
            "Do not present information about a different product, brand, "
            "or variant as if it were about the requested subject. "
            "Do not substitute or guess."
        )

        return self._add_to_system(
            messages,
            note,
            TARGET_UNCONFIRMED_MARKER,
        )

    def _apply_final_answer_mode(
        self,
        messages: list,
        limit_note: bool = False,
    ) -> list:
        final_instruction = f"""
{FINAL_SYSTEM_MARKER}

The web-search and page-fetch limits for this response have been reached.

You must now produce the final answer.

Do not call search_web.
Do not call fetch_url.
Do not generate native tool calls.
Do not generate <tool_call> XML.
Do not request another search.
Do not continue researching.

Use only the information already obtained in this response.
Clearly distinguish confirmed facts from inference or uncertainty.
If the available information is insufficient, say so explicitly.
End this response with the answer to the user's request.
"""

        # 0.8.22: ask for a limit note and a non-empty answer.
        if limit_note:
            final_instruction += """
The search/fetch limit was reached, so the answer is based only on the
information already retrieved (included in the user message below).
Write a substantive answer from that information. Never leave it empty.
Briefly state, in the same language as the user's request, that the
search limit was reached and that the answer covers only the retrieved
information. If important information is still missing, say what is
missing and that further research is possible if the user asks for it
(for example with a higher search limit).
"""

        messages = self._add_to_system(
            messages,
            final_instruction,
            FINAL_SYSTEM_MARKER,
        )

        idx = self._last_user_index(messages)

        if idx != -1:
            message = messages[idx]

            if FINAL_USER_MARKER not in _content_to_text(
                message.get(
                    "content",
                    "",
                )
            ):
                copied = dict(message)

                copied["content"] = self._append_text(
                    message.get(
                        "content",
                        "",
                    ),
                    FINAL_USER_MARKER
                    + "\n"
                    + "Provide the final answer now using only "
                    + "the information already obtained. "
                    + "Do not call or output any search or fetch tool.",
                )

                messages[idx] = copied

        return messages

    # ------------------------------------------------------------------
    # Empty-response fallback text (0.8.22)
    # ------------------------------------------------------------------
    def _build_final_fallback(
        self,
        messages: list,
        per_item: int = 500,
        total: int = 3000,
    ) -> str:
        """
        0.8.22: short text built from the retrieved tool results of this
        response. Used only if the final-answer hop streams no content.
        Never raises.
        """
        try:
            calls = {}

            for cid, name, args in self._iter_calls(messages):
                calls[cid] = (
                    name,
                    str(args or ""),
                )

            parts = []

            for message in self._response_messages(messages):
                if not isinstance(message, dict):
                    continue

                if message.get("role") != "tool":
                    continue

                if self._guard_result_action(message):
                    continue

                if self._tool_result_is_error(message):
                    continue

                name, args = calls.get(
                    str(message.get("tool_call_id")),
                    (
                        message.get("name") or "tool",
                        "",
                    ),
                )

                # 0.8.23: no <tool_call> markup in the fallback text.
                text = _scrub_tool_markup(
                    _content_to_text(message.get("content", ""))
                ).strip()

                args = _scrub_tool_markup(args)

                if not text:
                    continue

                if len(text) > per_item:
                    text = text[:per_item] + " ..."

                parts.append(f"- {name} {args[:120]}\n  {text}")

            body = "\n".join(parts)[:total]

            head = (
                "【Guard注記】検索/取得の上限に達しましたが、"
                "モデルが回答本文を生成できませんでした。"
                "取得できた結果の抜粋を示します。"
                "必要であれば検索回数を増やして追加調査できます。"
            )

            return _scrub_tool_markup(head + ("\n\n" + body if body else ""))

        except Exception:
            return (
                "【Guard注記】検索/取得の上限に達しましたが、"
                "回答本文を生成できませんでした。"
                "必要であれば検索回数を増やして追加調査できます。"
            )

    # ------------------------------------------------------------------
    # History hygiene
    # ------------------------------------------------------------------
    def _sanitize_history(
        self,
        messages: list,
    ) -> list:
        for i, message in enumerate(messages):
            if not (
                isinstance(
                    message,
                    dict,
                )
                and message.get("role") == "assistant"
            ):
                continue

            content = message.get("content")

            if not isinstance(
                content,
                str,
            ):
                continue

            if "<tool_call>" not in content and "<tool_response>" not in content:
                continue

            cleaned = TOOL_RESP_RE.sub(
                "",
                TOOL_XML_RE.sub(
                    "",
                    content,
                ),
            ).rstrip()

            copied = dict(message)

            copied["content"] = cleaned

            messages[i] = copied

        return messages

    def _flatten_tool_history(
        self,
        messages: list,
        max_chars: int = 6000,
    ) -> list:
        last_user = self._last_user_index(messages)

        if last_user == -1:
            return messages

        head = messages[: last_user + 1]

        tail = messages[last_user + 1 :]

        calls = {}
        kept = []
        notes = []
        changed = False

        for message in tail:
            if not isinstance(
                message,
                dict,
            ):
                kept.append(message)
                continue

            role = message.get("role")

            if role == "assistant" and message.get("tool_calls"):
                changed = True

                for tc in message.get("tool_calls") or []:
                    if not isinstance(
                        tc,
                        dict,
                    ):
                        continue

                    fn = (
                        tc.get(
                            "function",
                            {},
                        )
                        or {}
                    )

                    calls[str(tc.get("id"))] = (
                        fn.get("name") or "tool",
                        str(fn.get("arguments") or ""),
                    )

                text = _content_to_text(
                    message.get(
                        "content",
                        "",
                    )
                ).strip()

                if text:
                    kept.append(
                        {
                            "role": "assistant",
                            "content": text,
                        }
                    )

            elif role == "tool":
                changed = True

                name, args = calls.get(
                    str(message.get("tool_call_id")),
                    (
                        message.get("name") or "tool",
                        "",
                    ),
                )

                text = _content_to_text(
                    message.get(
                        "content",
                        "",
                    )
                )

                # 0.8.23: no <tool_call> markup in the plain-text evidence.
                text = _scrub_tool_markup(text)

                args = _scrub_tool_markup(args)

                if len(text) > max_chars:
                    text = text[:max_chars] + "\n...(truncated)"

                notes.append(f"### {name} {args}\n{text}")

            else:
                kept.append(message)

        if not changed:
            return messages

        if notes:
            kept.append(
                {
                    "role": "user",
                    "content": (
                        "Web research gathered for the question above "
                        "(the web tools are now closed and cannot be called):\n\n"
                        + "\n\n".join(notes)
                    ),
                }
            )

        return head + kept

    # ------------------------------------------------------------------
    # Guard-control result detection
    # ------------------------------------------------------------------
    @staticmethod
    def _guard_result_action(
        message: dict,
    ) -> Optional[str]:
        if not isinstance(
            message,
            dict,
        ):
            return None

        candidates = []

        for key in (
            "content",
            "result",
            "output",
        ):
            value = message.get(key)

            if value is not None:
                candidates.append(value)

        candidates.append(message)

        for value in candidates:
            if isinstance(
                value,
                dict,
            ):
                action = value.get("guard_action")

                if action in (
                    "blocked",
                    "duplicate",
                ):
                    return action

            text = _content_to_text(value).strip()

            if not text:
                continue

            try:
                obj = json.loads(text)

                if isinstance(
                    obj,
                    dict,
                ):
                    action = obj.get("guard_action")

                    if action in (
                        "blocked",
                        "duplicate",
                    ):
                        return action

            except Exception:
                continue

        return None

    # ------------------------------------------------------------------
    # Tool result classification
    # ------------------------------------------------------------------
    def _tool_result_is_error(
        self,
        message: dict,
    ) -> bool:
        if not isinstance(
            message,
            dict,
        ):
            return False

        # Guard-generated results are intentionally non-error.
        if self._guard_result_action(message):
            return False

        for key in (
            "error",
            "exception",
            "tool_error",
            "error_message",
        ):
            if message.get(key):
                return True

        text = _content_to_text(
            message.get(
                "content",
                "",
            )
        ).strip()

        if not text:
            return False

        if text.startswith("{") and len(text) < 2000:
            try:
                obj = json.loads(text)

                if isinstance(
                    obj,
                    dict,
                ) and obj.get("error"):
                    return True

            except Exception:
                pass

        if len(text) > 600:
            return False

        low = text.lower()

        patterns = [
            "connecterror",
            "connection error",
            "network error",
            "socket error",
            "os error",
            "timeout",
            "timed out",
            "failed to fetch",
            "fetch failed",
            "request failed",
            "http error",
            "502 bad gateway",
            "503 service unavailable",
            "504 gateway timeout",
            "connection refused",
            "connection reset",
            "name or service not known",
            "temporary failure in name resolution",
        ]

        return any(p in low for p in patterns)

    # ------------------------------------------------------------------
    # Fetch-result diagnostics (0.8.25, read-only)
    # ------------------------------------------------------------------
    @staticmethod
    def _explicit_http_status_code(
        message: dict,
    ) -> Optional[int]:
        """
        0.8.25: extract an explicit HTTP-like status code only when it is
        structurally present in the tool message/result. Never infer a
        status code from arbitrary body text.
        """
        try:
            if not isinstance(message, dict):
                return None

            candidates = [message]

            for key in ("result", "output"):
                value = message.get(key)

                if isinstance(value, dict):
                    candidates.append(value)

            for value in candidates:
                if not isinstance(value, dict):
                    continue

                for key in (
                    "status_code",
                    "statusCode",
                    "http_status",
                    "httpStatus",
                    "status",
                ):
                    code = value.get(key)

                    try:
                        code = int(code)
                    except Exception:
                        continue

                    if 100 <= code <= 599:
                        return code

            text = _content_to_text(
                message.get("content", "")
            ).strip()

            if text.startswith("{"):
                try:
                    obj = json.loads(text)

                    if isinstance(obj, dict):
                        for key in (
                            "status_code",
                            "statusCode",
                            "http_status",
                            "httpStatus",
                            "status",
                        ):
                            code = obj.get(key)

                            try:
                                code = int(code)
                            except Exception:
                                continue

                            if 100 <= code <= 599:
                                return code
                except Exception:
                    pass

        except Exception:
            pass

        return None

    def _classify_fetch_result(
        self,
        message: dict,
    ) -> Optional[str]:
        """
        0.8.25: diagnostic-only fetch result classification.

        Returns one of BODY / EMPTY / STATUS_LIKE / ERROR_LIKE, or None for
        Guard-generated control results / non-fetch messages.
        """
        try:
            if not isinstance(message, dict):
                return None

            if self._guard_result_action(message):
                return None

            status_code = self._explicit_http_status_code(message)

            if status_code is not None and 300 <= status_code <= 599:
                return "STATUS_LIKE"

            if self._tool_result_is_error(message):
                return "ERROR_LIKE"

            text = _content_to_text(
                message.get("content", "")
            ).strip()

            if not text:
                return "EMPTY"

            return "BODY"

        except Exception:
            return None

    def _log_fetch_result_diag(
        self,
        messages: list,
        state_key: str,
    ) -> None:
        """
        0.8.25: log each unseen fetch_url tool result once. Observation only.
        """
        try:
            calls = {}

            for cid, name, args in self._iter_calls(messages):
                calls[str(cid)] = (
                    name,
                    str(args or ""),
                )

            for message in self._response_messages(messages):
                if not isinstance(message, dict):
                    continue

                if message.get("role") != "tool":
                    continue

                cid = message.get("tool_call_id")

                if not cid:
                    continue

                cid = str(cid)

                if cid in self._fetch_result_diag_ids:
                    continue

                name, args = calls.get(
                    cid,
                    (
                        message.get("name") or "",
                        "",
                    ),
                )

                if name != "fetch_url":
                    continue

                classification = self._classify_fetch_result(message)

                if classification is None:
                    continue

                self._fetch_result_diag_ids.add(cid)

                content_text = _content_to_text(
                    message.get("content", "")
                )

                status_code = self._explicit_http_status_code(message)

                url = ""

                try:
                    obj = json.loads(args) if args else {}

                    if isinstance(obj, dict):
                        url = obj.get("url") or ""
                except Exception:
                    pass

                print(
                    "[Bonsai2 Web Search Guard] "
                    "FETCH_RESULT_DIAG "
                    f"msg={state_key} "
                    f"tool_call_id={cid!r} "
                    f"class={classification} "
                    f"chars={len(content_text)} "
                    f"status_code={status_code if status_code is not None else '-'} "
                    f"url={str(url)[:200]!r}"
                )

            if len(self._fetch_result_diag_ids) > 1000:
                self._fetch_result_diag_ids.clear()

        except Exception as e:
            print(
                "[Bonsai2 Web Search Guard] "
                "FETCH_RESULT_DIAG_ERROR "
                f"msg={state_key} "
                f"error={e!r}"
            )

    def _response_messages(
        self,
        messages: list,
    ) -> list:
        idx = self._last_user_index(messages)

        if idx == -1:
            return []

        return messages[idx + 1 :]

    def _iter_calls(
        self,
        messages: list,
    ):
        for mi, message in enumerate(self._response_messages(messages)):
            if not isinstance(
                message,
                dict,
            ):
                continue

            for ti, tc in enumerate(message.get("tool_calls") or []):
                if not isinstance(
                    tc,
                    dict,
                ):
                    continue

                fn = (
                    tc.get(
                        "function",
                        {},
                    )
                    or {}
                )

                name = fn.get("name")

                cid = (
                    str(tc.get("id")) if tc.get("id") else f"fallback-{mi}-{ti}-{name}"
                )

                yield (
                    cid,
                    name,
                    fn.get("arguments"),
                )

    def _count_successful(
        self,
        messages: list,
    ) -> tuple:
        search_ids = []
        fetch_ids = []

        error_ids = set()
        guard_control_ids = set()

        for cid, name, _ in self._iter_calls(messages):
            if name == "search_web":
                search_ids.append(cid)

            elif name == "fetch_url":
                fetch_ids.append(cid)

        for message in self._response_messages(messages):
            if not isinstance(
                message,
                dict,
            ):
                continue

            if message.get("role") != "tool":
                continue

            tool_call_id = message.get("tool_call_id")

            if not tool_call_id:
                continue

            cid = str(tool_call_id)

            action = self._guard_result_action(message)

            if action in (
                "blocked",
                "duplicate",
            ):
                guard_control_ids.add(cid)
                continue

            if self._tool_result_is_error(message):
                error_ids.add(cid)

        return (
            len(
                [
                    c
                    for c in search_ids
                    if (c not in error_ids and c not in guard_control_ids)
                ]
            ),
            len(
                [
                    c
                    for c in fetch_ids
                    if (c not in error_ids and c not in guard_control_ids)
                ]
            ),
        )

    def _count_attempts(
        self,
        messages: list,
    ) -> tuple:
        search_count = 0
        fetch_count = 0

        for _, name, _ in self._iter_calls(messages):
            if name == "search_web":
                search_count += 1

            elif name == "fetch_url":
                fetch_count += 1

        return (
            search_count,
            fetch_count,
        )

    def _count_tool_turns(
        self,
        messages: list,
    ) -> int:
        return sum(
            1
            for message in self._response_messages(messages)
            if (
                isinstance(
                    message,
                    dict,
                )
                and message.get("role") == "assistant"
                and message.get("tool_calls")
            )
        )

    def _last_executed_query(
        self,
        messages: list,
    ) -> Optional[str]:
        last = None

        for _, name, args in self._iter_calls(messages):
            if name != "search_web":
                continue

            try:
                obj = (
                    json.loads(args)
                    if isinstance(
                        args,
                        str,
                    )
                    else (args or {})
                )

                q = obj.get("query")

                if (
                    isinstance(
                        q,
                        str,
                    )
                    and q.strip()
                ):
                    last = q

            except Exception:
                continue

        return last

    # ------------------------------------------------------------------
    # Search-result audit
    # ------------------------------------------------------------------
    def _extract_search_evidence(
        self,
        content,
    ) -> tuple:
        raw = _content_to_text(content).strip()

        if not raw:
            return (
                "",
                0,
            )

        evidence_parts = []
        result_count = 0

        try:
            obj = json.loads(raw)
        except Exception:
            obj = None

        if obj is not None:

            def walk(
                node,
                depth=0,
            ):
                nonlocal result_count

                if depth > 8:
                    return

                if isinstance(
                    node,
                    dict,
                ):
                    title = node.get("title")
                    snippet = node.get("snippet")
                    name = node.get("name")
                    description = node.get("description")
                    text = node.get("text")

                    local = []

                    for value in (
                        title,
                        snippet,
                        name,
                        description,
                        text,
                    ):
                        if (
                            isinstance(
                                value,
                                str,
                            )
                            and value.strip()
                        ):
                            local.append(value.strip())

                    if title or snippet:
                        result_count += 1

                    if local:
                        evidence_parts.extend(local)

                    for value in node.values():
                        walk(
                            value,
                            depth + 1,
                        )

                elif isinstance(
                    node,
                    list,
                ):
                    for item in node:
                        walk(
                            item,
                            depth + 1,
                        )

            walk(obj)

            evidence = "\n".join(evidence_parts).strip()

            if evidence:
                return (
                    evidence,
                    result_count,
                )

        return (
            raw,
            0,
        )

    def _extract_search_results(
        self,
        content,
    ) -> tuple:
        raw = _content_to_text(content).strip()

        if not raw:
            return (
                [],
                False,
            )

        try:
            obj = json.loads(raw)
        except Exception:
            return (
                [],
                False,
            )

        results = []
        seen_urls = set()

        def walk(
            node,
            depth=0,
        ):
            if depth > 8:
                return

            if isinstance(
                node,
                dict,
            ):
                title = node.get("title")
                snippet = node.get("snippet")
                name = node.get("name")
                description = node.get("description")
                text = node.get("text")

                url = node.get("link") or node.get("url") or node.get("href")

                evidence_parts = []

                for value in (
                    title,
                    snippet,
                    name,
                    description,
                    text,
                ):
                    if (
                        isinstance(
                            value,
                            str,
                        )
                        and value.strip()
                    ):
                        evidence_parts.append(value.strip())

                if (
                    isinstance(
                        url,
                        str,
                    )
                    and url.strip()
                    and evidence_parts
                ):
                    normalized_url = self._normalize_url(url)

                    if (
                        normalized_url
                        and normalized_url.startswith(
                            (
                                "http://",
                                "https://",
                            )
                        )
                        and normalized_url not in seen_urls
                    ):
                        seen_urls.add(normalized_url)

                        results.append(
                            {
                                "url": normalized_url,
                                "evidence": "\n".join(evidence_parts),
                            }
                        )

                for value in node.values():
                    walk(
                        value,
                        depth + 1,
                    )

            elif isinstance(
                node,
                list,
            ):
                for item in node:
                    walk(
                        item,
                        depth + 1,
                    )

        walk(obj)

        if not results:
            return (
                [],
                False,
            )

        return (
            results,
            True,
        )

    def _get_main_audit_entity(
        self,
        user_text: str,
    ) -> Optional[str]:
        # 0.8.19: mask complete dates so that a date year is not picked up
        # by the standalone-number rule. extract_protected() is unchanged.
        masked = _DATE_MASK_RE.sub(
            " ",
            _nfkc(user_text),
        )

        protected = extract_protected(masked)

        entities = protected.get(
            "entities",
            [],
        )

        if not entities:
            return None

        for entity in entities:
            text = str(entity).strip()

            if not text:
                continue

            if KATAKANA_RE.fullmatch(text):
                return text

            if len(text) >= 2 and (
                any(c.isupper() for c in text) or any(c.isdigit() for c in text)
            ):
                return text

        return str(entities[0]).strip()

    def _audit_search_results(
        self,
        messages: list,
        user_text: str,
        state_key: str,
    ) -> list:
        if not self.valves.search_result_audit:
            return []

        main_entity = self._get_main_audit_entity(user_text)

        if not main_entity:
            return []

        state = self._get_fetch_gate_state(
            state_key,
            user_text,
        )

        state["entity"] = main_entity

        calls = {}

        for cid, name, args in self._iter_calls(messages):
            if name != "search_web":
                continue

            calls[cid] = args

        if not calls:
            return []

        outcomes = []

        for message in self._response_messages(messages):
            if not isinstance(
                message,
                dict,
            ):
                continue

            if message.get("role") != "tool":
                continue

            call_id = message.get("tool_call_id")

            if not call_id:
                continue

            call_id = str(call_id)

            if call_id not in calls:
                continue

            audit_key = (
                state_key,
                call_id,
            )

            if audit_key in self._audited_search_results:
                continue

            self._audited_search_results.add(audit_key)

            if len(self._audited_search_results) > 500:
                self._audited_search_results = {
                    item
                    for item in self._audited_search_results
                    if item[0] != state_key
                }

            if self._tool_result_is_error(message):
                print(
                    "[Bonsai2 Web Search Guard] "
                    "SEARCH_RESULT_AUDIT "
                    f"msg={state_key} "
                    f"tool_call_id={call_id} "
                    "status=TOOL_ERROR "
                    f"entity={main_entity!r} "
                    "found=False "
                    "results=0"
                )

                outcomes.append(
                    {
                        "call_id": call_id,
                        "status": "TOOL_ERROR",
                        "found": False,
                    }
                )

                continue

            content = message.get(
                "content",
                "",
            )

            evidence, result_count = self._extract_search_evidence(content)

            if not evidence:
                print(
                    "[Bonsai2 Web Search Guard] "
                    "SEARCH_RESULT_AUDIT "
                    f"msg={state_key} "
                    f"tool_call_id={call_id} "
                    "status=NO_RESULTS "
                    f"entity={main_entity!r} "
                    "found=False "
                    f"results={result_count}"
                )

                outcomes.append(
                    {
                        "call_id": call_id,
                        "status": "NO_RESULTS",
                        "found": False,
                    }
                )

            else:
                normalized_evidence = _norm(evidence)

                normalized_entity = _norm(main_entity)

                found = normalized_entity in normalized_evidence

                status = "ok" if found else "VIOLATION"

                print(
                    "[Bonsai2 Web Search Guard] "
                    "SEARCH_RESULT_AUDIT "
                    f"msg={state_key} "
                    f"tool_call_id={call_id} "
                    f"status={status} "
                    f"entity={main_entity!r} "
                    f"found={found} "
                    f"results={result_count}"
                )

                outcomes.append(
                    {
                        "call_id": call_id,
                        "status": status,
                        "found": found,
                    }
                )

            result_items, parse_ok = self._extract_search_results(content)

            query = None

            try:
                raw_args = calls.get(call_id)

                obj = (
                    json.loads(raw_args)
                    if isinstance(
                        raw_args,
                        str,
                    )
                    else (raw_args or {})
                )

                if isinstance(
                    obj,
                    dict,
                ):
                    query = obj.get("query")

            except Exception:
                query = None

            query_entity_included = bool(
                isinstance(
                    query,
                    str,
                )
                and query.strip()
                and (_norm(main_entity) in _norm(query))
            )

            if not parse_ok:
                print(
                    "[Bonsai2 Web Search Guard] "
                    "FETCH_GATE_SOURCE "
                    f"msg={state_key} "
                    f"tool_call_id={call_id} "
                    "parse=FAIL "
                    "query_entity_included="
                    f"{query_entity_included} "
                    "urls=0"
                )

                continue

            ok_count = 0
            suspect_count = 0

            for item in result_items:
                url = self._normalize_url(
                    item.get(
                        "url",
                        "",
                    )
                )

                item_evidence = str(
                    item.get(
                        "evidence",
                        "",
                    )
                )

                if not url:
                    continue

                found = _norm(main_entity) in _norm(item_evidence)

                if found:
                    state["ok_urls"].add(url)

                    ok_count += 1

                    print(
                        "[Bonsai2 Web Search Guard] "
                        "FETCH_GATE_CANDIDATE "
                        f"msg={state_key} "
                        f"tool_call_id={call_id} "
                        "verdict=OK "
                        f"url={url!r} "
                        f"entity={main_entity!r}"
                    )

                elif query_entity_included:
                    state["suspect_urls"].add(url)

                    suspect_count += 1

                    print(
                        "[Bonsai2 Web Search Guard] "
                        "FETCH_GATE_CANDIDATE "
                        f"msg={state_key} "
                        f"tool_call_id={call_id} "
                        "verdict=SUSPECT "
                        f"url={url!r} "
                        f"entity={main_entity!r}"
                    )

            state["suspect_urls"].difference_update(state["ok_urls"])

            print(
                "[Bonsai2 Web Search Guard] "
                "FETCH_GATE_SOURCE "
                f"msg={state_key} "
                f"tool_call_id={call_id} "
                "parse=OK "
                "query_entity_included="
                f"{query_entity_included} "
                f"urls={len(result_items)} "
                f"ok={ok_count} "
                f"suspect={suspect_count}"
            )

        if len(state["suspect_urls"]) > 200:
            state["suspect_urls"] = set(list(state["suspect_urls"])[-200:])

        if len(state["ok_urls"]) > 200:
            state["ok_urls"] = set(list(state["ok_urls"])[-200:])

        if len(state["fetched_urls"]) > 200:
            state["fetched_urls"] = set(list(state["fetched_urls"])[-200:])

        self._trim_fetch_gate_state()

        return outcomes

    # ------------------------------------------------------------------
    # Latest-search target check (0.8.18, read-only, stateless)
    # ------------------------------------------------------------------
    def _last_search_target_missing(
        self,
        messages: list,
        entity: Optional[str],
    ) -> bool:
        """
        True when the most recent completed search_web result (with usable
        evidence) does not contain `entity`. Uses the same presence test as
        SEARCH_RESULT_AUDIT. Never raises.
        """
        try:
            if not entity:
                return False

            search_ids = {
                cid
                for cid, name, _ in self._iter_calls(messages)
                if name == "search_web"
            }

            if not search_ids:
                return False

            target = _norm(entity)

            if not target:
                return False

            last_found = None

            for message in self._response_messages(messages):
                if not isinstance(
                    message,
                    dict,
                ):
                    continue

                if message.get("role") != "tool":
                    continue

                call_id = message.get("tool_call_id")

                if not call_id or str(call_id) not in search_ids:
                    continue

                if self._tool_result_is_error(message):
                    continue

                evidence, _ = self._extract_search_evidence(
                    message.get(
                        "content",
                        "",
                    )
                )

                if not evidence:
                    continue

                last_found = target in _norm(evidence)

            return last_found is False

        except Exception:
            return False

    # ------------------------------------------------------------------
    # Search recovery
    # ------------------------------------------------------------------
    def _build_recovery_query(
        self,
        user_text: str,
        entity: Optional[str],
        prev_query: str,
    ) -> str:
        """
        0.8.18 layout:

            "main entity phrase" [extra identifiers] [attributes] [purpose]

        - main entity phrase: always quoted. A single Latin entity is extended
          over adjacent Latin name tokens ("Rakuten Hand 5G").
        - extra identifiers: other protected entities (max 2), not already in
          the phrase / purpose, pure digits excluded.
        - attributes: protected numerics other than currency (max 3), not
          already in the phrase. Detected as protected, but weak as search
          conditions, so they never come before the entity.
        - purpose: ONE term from _PURPOSE_TERMS; otherwise the noun run right
          after the entity phrase.

        prev_query is kept in the signature (state design unchanged) but is
        no longer used: the entity is now always quoted.
        """
        try:
            if not entity:
                return ""

            text = _nfkc(user_text)

            phrase = _expand_entity_phrase(
                text,
                str(entity).strip(),
            )

            phrase = phrase.replace(
                '"',
                "",
            ).strip()

            if not phrase:
                return ""

            protected = extract_protected(user_text)

            phrase_norm = _norm(phrase)

            # -- purpose (one term) ------------------------------------
            purpose = _pick_purpose_term(text)

            if not purpose:
                purpose = _adjacent_topic(
                    text,
                    phrase,
                )

            purpose_norm = _norm(purpose)

            # -- extra identifiers -------------------------------------
            extras = []

            for ent in protected.get(
                "entities",
                [],
            ):
                e = str(ent).strip()

                en = _norm(e)

                if not en or e.isdigit():
                    continue

                if en in phrase_norm:
                    continue

                if purpose_norm and en in purpose_norm:
                    continue

                if any(en == _norm(x) for x in extras):
                    continue

                extras.append(e)

                if len(extras) >= _RECOVERY_MAX_EXTRAS:
                    break

            # -- attributes (capacity / degree / year ...) -------------
            attrs = []

            for n in protected.get(
                "numerics",
                [],
            ):
                if n.get("group") == "currency":
                    continue

                raw = str(n.get("raw", "")).strip()

                rn = _norm(raw)

                if not rn:
                    continue

                if rn in phrase_norm:
                    continue

                if any(rn == _norm(a) for a in attrs):
                    continue

                attrs.append(raw)

                if len(attrs) >= _RECOVERY_MAX_ATTRS:
                    break

            parts = [f'"{phrase}"'] + extras + attrs + ([purpose] if purpose else [])

            q = " ".join(parts).strip()

            print(
                "[Bonsai2 Web Search Guard] "
                "SEARCH_RECOVERY_QUERY_PARTS "
                f"entity={entity!r} "
                f"phrase={phrase!r} "
                f"extras={extras} "
                f"attrs={attrs} "
                f"purpose={purpose!r}"
            )

            return q

        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Force-search trigger
    # ------------------------------------------------------------------
    def _should_force_search(
        self,
        text: str,
    ) -> bool:
        if not text:
            return False

        patterns = [
            r"現在",
            r"今現在",
            r"現在の",
            r"最新",
            r"最新情報",
            r"今日",
            r"今週",
            r"今月",
            r"今年",
            r"直近",
            r"いま",
            r"今いくら",
            r"いくらで買",
            r"価格",
            r"値段",
            r"料金",
            r"相場",
            r"市場価格",
            r"販売",
            r"売って",
            r"購入",
            r"買え",
            r"在庫",
            r"入手",
            r"発売",
            r"終了",
            r"変更",
            r"ニュース",
            r"最新の",
            r"\bcurrent\b",
            r"\blatest\b",
            r"\btoday\b",
            r"\bnow\b",
            r"\brecent\b",
            r"\bprice\b",
            r"\bpricing\b",
            r"\bcost\b",
            r"\bavailable\b",
            r"\bavailability\b",
            r"\bin stock\b",
            r"\bfor sale\b",
            r"\bbuy\b",
            r"\bpurchase\b",
            r"\b202[0-9]\b",
        ]

        return any(
            re.search(
                pattern,
                text,
                re.IGNORECASE,
            )
            for pattern in patterns
        )

    # ------------------------------------------------------------------
    # Search callable wrapper
    # ------------------------------------------------------------------
    def _wrap_search_callable(
        self,
        body: dict,
        user_text: str,
        state_key: str,
    ) -> str:
        metadata = body.get("metadata")

        tools = (
            metadata.get("tools")
            if isinstance(
                metadata,
                dict,
            )
            else None
        )

        if not isinstance(
            tools,
            dict,
        ):
            return "no-metadata-tools"

        entry = tools.get("search_web")

        if not isinstance(
            entry,
            dict,
        ):
            return "no-search-entry"

        original = entry.get("callable")

        if not callable(original):
            return "no-callable"

        # 0.8.16: walk the __wrapped__ chain, not just the outermost callable.
        if self._chain_has_flag(
            original,
            "_bonsai_guard_wrapped",
        ):
            return "already-wrapped"

        def fix(
            kwargs: dict,
        ) -> dict:
            try:
                state = self._fetch_gate_state.get(state_key)

                # -------------------------------------------------------
                # Search recovery takes precedence over ordinary repair.
                # -------------------------------------------------------
                if (
                    isinstance(
                        state,
                        dict,
                    )
                    and state.get("search_recovery_pending")
                    and state.get("search_recovery_query")
                ):
                    recovery_query = str(state.get("search_recovery_query")).strip()

                    if recovery_query and "query" in kwargs:
                        model_query = kwargs.get("query")

                        print(
                            "[Bonsai2 Web Search Guard] "
                            "SEARCH_RECOVERY "
                            "status=EXECUTED "
                            f"msg={state_key} "
                            f"model_query={model_query!r} "
                            f"enforced_query={recovery_query!r} "
                            f"overridden={model_query != recovery_query}"
                        )

                        kwargs = dict(kwargs)

                        kwargs["query"] = recovery_query

                        state["search_recovery_pending"] = False

                        return kwargs

                    print(
                        "[Bonsai2 Web Search Guard] "
                        "SEARCH_RECOVERY "
                        "status=ENFORCE_SKIPPED "
                        f"msg={state_key} "
                        "reason=no-query-kwarg"
                    )

                # -------------------------------------------------------
                # Existing execution-time QUERY_REPAIR.
                # -------------------------------------------------------
                q = kwargs.get("query")

                if (
                    isinstance(
                        q,
                        str,
                    )
                    and q.strip()
                ):
                    fixed, info = repair_query(
                        user_text,
                        q,
                    )

                    if info["changed"]:
                        print(
                            "[Bonsai2 Web Search Guard] "
                            "QUERY_REPAIR "
                            f"{q!r} -> {fixed!r} "
                            f"missing={info['missing']} "
                            f"replaced={info['replaced']}"
                        )

                        kwargs = dict(kwargs)

                        kwargs["query"] = fixed

            except Exception as e:
                print("[Bonsai2 Web Search Guard] " f"QUERY_REPAIR_ERROR {e!r}")

            return kwargs

        if asyncio.iscoroutinefunction(original):

            async def wrapper(
                *args,
                **kwargs,
            ):
                fixed_kwargs = fix(kwargs)

                return await original(
                    *args,
                    **fixed_kwargs,
                )

        else:

            def wrapper(
                *args,
                **kwargs,
            ):
                fixed_kwargs = fix(kwargs)

                return original(
                    *args,
                    **fixed_kwargs,
                )

        functools.update_wrapper(
            wrapper,
            original,
            updated=(),
        )

        wrapper._bonsai_guard_wrapped = True

        entry["callable"] = wrapper

        return "wrapped"

    # ------------------------------------------------------------------
    # Fetch callable probe
    # ------------------------------------------------------------------
    def _wrap_fetch_callable_probe(
        self,
        body: dict,
        state_key: str = "-",
    ) -> str:
        metadata = body.get("metadata")

        tools = (
            metadata.get("tools")
            if isinstance(
                metadata,
                dict,
            )
            else None
        )

        if not isinstance(
            tools,
            dict,
        ):
            return "no-metadata-tools"

        entry = tools.get("fetch_url")

        if not isinstance(
            entry,
            dict,
        ):
            return "no-fetch-entry"

        original = entry.get("callable")

        if not callable(original):
            return "no-callable"

        # 0.8.16: walk the __wrapped__ chain, not just the outermost callable.
        if self._chain_has_flag(
            original,
            "_bonsai_guard_fetch_probe_wrapped",
        ):
            return "already-wrapped"

        if asyncio.iscoroutinefunction(original):

            async def wrapper(
                *args,
                **kwargs,
            ):
                try:
                    url = kwargs.get("url")

                    if not (
                        isinstance(
                            url,
                            str,
                        )
                        and url.strip()
                    ):
                        if args:
                            first = args[0]

                            if isinstance(
                                first,
                                str,
                            ):
                                url = first

                    print(
                        "[Bonsai2 Web Search Guard] "
                        "FETCH_CALLABLE_PROBE "
                        f"msg={state_key} "
                        f"invoke url={str(url)[:160]!r}"
                    )

                except Exception:
                    pass

                return await original(
                    *args,
                    **kwargs,
                )

        else:

            def wrapper(
                *args,
                **kwargs,
            ):
                try:
                    url = kwargs.get("url")

                    if not (
                        isinstance(
                            url,
                            str,
                        )
                        and url.strip()
                    ):
                        if args:
                            first = args[0]

                            if isinstance(
                                first,
                                str,
                            ):
                                url = first

                    print(
                        "[Bonsai2 Web Search Guard] "
                        "FETCH_CALLABLE_PROBE "
                        f"msg={state_key} "
                        f"invoke url={str(url)[:160]!r}"
                    )

                except Exception:
                    pass

                return original(
                    *args,
                    **kwargs,
                )

        functools.update_wrapper(
            wrapper,
            original,
            updated=(),
        )

        wrapper._bonsai_guard_fetch_probe_wrapped = True

        entry["callable"] = wrapper

        print(
            "[Bonsai2 Web Search Guard] "
            "FETCH_CALLABLE_PROBE "
            f"msg={state_key} "
            "status=wrapped callable=yes"
        )

        return "wrapped"

    # ------------------------------------------------------------------
    # Fetch gate + duplicate prevention + suspension
    # ------------------------------------------------------------------
    def _wrap_fetch_gate(
        self,
        body: dict,
        user_text: str,
        state_key: str,
    ) -> str:
        metadata = body.get("metadata")

        tools = (
            metadata.get("tools")
            if isinstance(
                metadata,
                dict,
            )
            else None
        )

        if not isinstance(
            tools,
            dict,
        ):
            return "no-metadata-tools"

        entry = tools.get("fetch_url")

        if not isinstance(
            entry,
            dict,
        ):
            return "no-fetch-entry"

        original = entry.get("callable")

        if not callable(original):
            return "no-callable"

        # 0.8.16: walk the __wrapped__ chain, not just the outermost
        # callable. The flag value is the state_key, so a gate built for a
        # different message is never treated as the current one.
        if self._chain_has_flag(
            original,
            "_bonsai_guard_fetch_gate_wrapped",
            state_key,
        ):
            return "already-wrapped"

        state = self._get_fetch_gate_state(
            state_key,
            user_text,
        )

        gate_serial = next(_GATE_SERIAL)

        def get_url(
            args,
            kwargs,
        ) -> Optional[str]:
            url = kwargs.get("url")

            if (
                isinstance(
                    url,
                    str,
                )
                and url.strip()
            ):
                return url.strip()

            if args:
                first = args[0]

                if (
                    isinstance(
                        first,
                        str,
                    )
                    and first.strip()
                ):
                    return first.strip()

            return None

        def make_guard_result(
            action: str,
            reason: str,
            url: str,
            entity: Optional[str] = None,
        ) -> dict:
            result = {
                "guard_action": action,
                "status": ("blocked" if action == "blocked" else "skipped"),
                "reason": reason,
                "url": url,
            }

            if entity:
                result["entity"] = entity

            return result

        def audit_fetch(
            args,
            kwargs,
        ) -> tuple:
            """
            Return:
                (blocked, guard_result)

            BLOCK and DUPLICATE are normal non-error Guard results.
            """

            try:
                # 0.8.17: diagnostics only.
                print(
                    "[Bonsai2 Web Search Guard] "
                    "FETCH_GATE_ENTER "
                    f"msg={state_key} "
                    f"gate=#{gate_serial} "
                    f"raw_url={get_url(args, kwargs)!r}"
                )

                url = get_url(
                    args,
                    kwargs,
                )

                normalized_url = self._normalize_url(url) if url else ""

                if not normalized_url:
                    print(
                        "[Bonsai2 Web Search Guard] "
                        "FETCH_GATE "
                        f"msg={state_key} "
                        "mode="
                        f"{'dry-run' if self.valves.fetch_gate_dry_run else 'active'} "
                        "decision=PASS "
                        "would_block=False "
                        "blocked=False "
                        "duplicate=False "
                        "reason=no-url"
                    )

                    return (
                        False,
                        None,
                    )

                # -------------------------------------------------------
                # Duplicate URL check.
                # -------------------------------------------------------
                if normalized_url in state["fetched_urls"]:
                    state["fetch_suspended"] = True

                    state["suspend_search_attempts"] = state.get(
                        "search_attempts_seen",
                        0,
                    )

                    print(
                        "[Bonsai2 Web Search Guard] "
                        "FETCH_GATE "
                        f"msg={state_key} "
                        "mode=active "
                        "decision=DUPLICATE "
                        "would_block=False "
                        "blocked=True "
                        "duplicate=True "
                        "reason=already-fetched "
                        "fetch_suspended=True "
                        f"url={normalized_url!r}"
                    )

                    return (
                        True,
                        make_guard_result(
                            "duplicate",
                            "already-fetched",
                            normalized_url,
                        ),
                    )

                # -------------------------------------------------------
                # Mark before underlying fetch.
                # -------------------------------------------------------
                state["fetched_urls"].add(normalized_url)

                if len(state["fetched_urls"]) > 200:
                    state["fetched_urls"] = set(list(state["fetched_urls"])[-200:])

                # -------------------------------------------------------
                # Fixed diagnostic test.
                # -------------------------------------------------------
                if state.get("test_mode") and normalized_url == state.get("test_url"):
                    if self.valves.fetch_gate_dry_run:
                        print(
                            "[Bonsai2 Web Search Guard] "
                            "FETCH_GATE "
                            f"msg={state_key} "
                            "mode=dry-run "
                            "decision=WOULD_BLOCK "
                            "would_block=True "
                            "blocked=False "
                            "duplicate=False "
                            "reason=fixed-test-url "
                            f"url={normalized_url!r}"
                        )

                        return (
                            False,
                            None,
                        )

                    print(
                        "[Bonsai2 Web Search Guard] "
                        "FETCH_GATE "
                        f"msg={state_key} "
                        "mode=active "
                        "decision=BLOCKED "
                        "would_block=True "
                        "blocked=True "
                        "duplicate=False "
                        "reason=fixed-test-url "
                        f"url={normalized_url!r}"
                    )

                    return (
                        True,
                        make_guard_result(
                            "blocked",
                            "fixed-test-url",
                            normalized_url,
                        ),
                    )

                # -------------------------------------------------------
                # Explicit user URL -> fail-open.
                # -------------------------------------------------------
                if normalized_url in state["explicit_urls"]:
                    print(
                        "[Bonsai2 Web Search Guard] "
                        "FETCH_GATE "
                        f"msg={state_key} "
                        "mode="
                        f"{'dry-run' if self.valves.fetch_gate_dry_run else 'active'} "
                        "decision=PASS "
                        "would_block=False "
                        "blocked=False "
                        "duplicate=False "
                        "reason=user-explicit-url "
                        f"url={normalized_url!r}"
                    )

                    return (
                        False,
                        None,
                    )

                # -------------------------------------------------------
                # Positive search evidence wins.
                # -------------------------------------------------------
                if normalized_url in state["ok_urls"]:
                    print(
                        "[Bonsai2 Web Search Guard] "
                        "FETCH_GATE "
                        f"msg={state_key} "
                        "mode="
                        f"{'dry-run' if self.valves.fetch_gate_dry_run else 'active'} "
                        "decision=PASS "
                        "would_block=False "
                        "blocked=False "
                        "duplicate=False "
                        "reason=ok-search-result "
                        f"url={normalized_url!r}"
                    )

                    return (
                        False,
                        None,
                    )

                # -------------------------------------------------------
                # Suspect search result.
                # -------------------------------------------------------
                if normalized_url in state["suspect_urls"]:
                    if self.valves.fetch_gate_dry_run:
                        print(
                            "[Bonsai2 Web Search Guard] "
                            "FETCH_GATE "
                            f"msg={state_key} "
                            "mode=dry-run "
                            "decision=WOULD_BLOCK "
                            "would_block=True "
                            "blocked=False "
                            "duplicate=False "
                            "reason=suspect-search-result "
                            f"entity={state.get('entity')!r} "
                            f"url={normalized_url!r}"
                        )

                        return (
                            False,
                            None,
                        )

                    print(
                        "[Bonsai2 Web Search Guard] "
                        "FETCH_GATE "
                        f"msg={state_key} "
                        "mode=active "
                        "decision=BLOCKED "
                        "would_block=True "
                        "blocked=True "
                        "duplicate=False "
                        "reason=suspect-search-result "
                        f"entity={state.get('entity')!r} "
                        f"url={normalized_url!r}"
                    )

                    return (
                        True,
                        make_guard_result(
                            "blocked",
                            "suspect-search-result",
                            normalized_url,
                            state.get("entity"),
                        ),
                    )

                # -------------------------------------------------------
                # Unknown URL -> fail-open.
                # -------------------------------------------------------
                print(
                    "[Bonsai2 Web Search Guard] "
                    "FETCH_GATE "
                    f"msg={state_key} "
                    "mode="
                    f"{'dry-run' if self.valves.fetch_gate_dry_run else 'active'} "
                    "decision=PASS "
                    "would_block=False "
                    "blocked=False "
                    "duplicate=False "
                    "reason=url-not-in-search-results "
                    f"url={normalized_url!r}"
                )

                return (
                    False,
                    None,
                )

            except Exception as e:
                try:
                    print(
                        "[Bonsai2 Web Search Guard] "
                        "FETCH_GATE_ERROR "
                        f"msg={state_key} "
                        f"error={e!r}"
                    )
                except Exception:
                    pass

                # Guard failure -> fail-open.
                return (
                    False,
                    None,
                )

        if asyncio.iscoroutinefunction(original):

            async def wrapper(
                *args,
                **kwargs,
            ):
                blocked, guard_result = audit_fetch(
                    args,
                    kwargs,
                )

                if blocked:
                    return guard_result

                return await original(
                    *args,
                    **kwargs,
                )

        else:

            def wrapper(
                *args,
                **kwargs,
            ):
                blocked, guard_result = audit_fetch(
                    args,
                    kwargs,
                )

                if blocked:
                    return guard_result

                return original(
                    *args,
                    **kwargs,
                )

        functools.update_wrapper(
            wrapper,
            original,
            updated=(),
        )

        # 0.8.16: the flag value is the state_key (was True).
        wrapper._bonsai_guard_fetch_gate_wrapped = state_key

        entry["callable"] = wrapper

        print(
            "[Bonsai2 Web Search Guard] "
            "FETCH_GATE "
            f"msg={state_key} "
            f"gate=#{gate_serial} "
            f"status=wrapped "
            f"mode={'dry-run' if self.valves.fetch_gate_dry_run else 'active'} "
            "duplicate-protection=on "
            "suspension=on "
            "control-results=non-error"
        )

        return "wrapped"

    # ------------------------------------------------------------------
    # Wrapper-chain inspection (0.8.16)
    # ------------------------------------------------------------------
    @staticmethod
    def _chain_has_flag(
        fn,
        flag: str,
        value=True,
    ) -> bool:
        """
        Walk the __wrapped__ chain (max 32 levels) and return True if any
        layer carries `flag` equal to `value`.

        functools.update_wrapper(..., updated=()) deliberately does not copy
        __dict__, so an outer wrapper never carries the flags of the wrappers
        beneath it. It does always set __wrapped__.
        """
        depth = 0

        while fn is not None and depth < 32:
            if (
                getattr(
                    fn,
                    flag,
                    None,
                )
                == value
            ):
                return True

            fn = getattr(
                fn,
                "__wrapped__",
                None,
            )

            depth += 1

        return False

    # ------------------------------------------------------------------
    # Native tool restoration
    # ------------------------------------------------------------------
    def _get_original_tools(
        self,
        body: dict,
        metadata: dict,
        first_llm_call: bool,
    ):
        stored = metadata.get("_bonsai_guard_original_tools")

        if isinstance(
            stored,
            list,
        ):
            return copy.deepcopy(stored)

        current = body.get("tools")

        if first_llm_call and isinstance(
            current,
            list,
        ):
            stored = copy.deepcopy(current)

            metadata["_bonsai_guard_original_tools"] = stored

            return copy.deepcopy(stored)

        return current

    # ------------------------------------------------------------------
    # Date Preflight (0.8.20)
    # ------------------------------------------------------------------
    @staticmethod
    def _load_timezone(
        name: str,
    ) -> tuple:
        """
        0.8.20: return (tzinfo or None, error_text). Never raises.

        1) IANA name via zoneinfo (stdlib). Note: on Windows zoneinfo needs
           the tzdata package, which is not part of the stdlib.
        2) Fixed offset such as "UTC+9" / "+09:00" (stdlib datetime.timezone).
        """
        zerr = ""

        try:
            from zoneinfo import ZoneInfo

            return (
                ZoneInfo(name),
                "",
            )

        except Exception as e:
            zerr = repr(e)

        try:
            m = _FIXED_OFFSET_RE.fullmatch(name.strip())

            if m:
                sign = -1 if m.group(1) == "-" else 1

                hours = int(m.group(2))

                minutes = int(m.group(3) or 0)

                if hours <= 14 and minutes < 60:
                    delta = _dt.timedelta(
                        hours=hours,
                        minutes=minutes,
                    )

                    return (
                        _dt.timezone(delta * sign),
                        "",
                    )

        except Exception as e:
            zerr = zerr + " / " + repr(e)

        return (
            None,
            zerr,
        )

    def _resolve_now(
        self,
    ) -> tuple:
        """
        0.8.20: return (now, timezone_label, timezone_source, error_text).

        Priority:
          1. valve `timezone` (non-empty and loadable)  -> source "config"
          2. OS local timezone                          -> source "os"
          3. valve set but unusable -> OS local timezone,
             error_text filled                          -> source "os-fallback"
        """
        configured = str(self.valves.timezone or "").strip()

        error = ""

        if configured:
            tz, error = self._load_timezone(configured)

            if tz is not None:
                return (
                    _dt.datetime.now(tz),
                    configured,
                    "config",
                    "",
                )

        now = _dt.datetime.now().astimezone()

        offset = now.utcoffset() or _dt.timedelta(0)

        total = int(offset.total_seconds() // 60)

        sign = "+" if total >= 0 else "-"

        label = (
            f"{now.tzname() or 'local'}"
            f"(UTC{sign}{abs(total) // 60:02d}:{abs(total) % 60:02d})"
        )

        return (
            now,
            label,
            "os-fallback" if configured else "os",
            error,
        )

    @staticmethod
    def _tz_short(
        now,
    ) -> str:
        """
        0.8.21: short timezone name for display, e.g. "JST" / "UTC".
        Falls back to "UTC+09:00" when tzname() is not a short ASCII
        abbreviation (e.g. "-03", or a long OS-localized Windows name).
        Never raises.
        """
        try:
            name = now.tzname() or ""

            if name and name.isascii() and name.isalpha() and len(name) <= 5:
                return name

            offset = now.utcoffset() or _dt.timedelta(0)

            total = int(offset.total_seconds() // 60)

            sign = "+" if total >= 0 else "-"

            return f"UTC{sign}{abs(total) // 60:02d}:{abs(total) % 60:02d}"

        except Exception:
            return "UTC"

    def _date_preflight(
        self,
        user_text: str,
        state_key: str,
    ) -> dict:
        """
        0.8.20: decide whether Date Preflight applies and build the system
        block. Pure text work: no tool call, no search, no counter access.
        The result is cached per message so the date is stable across hops
        and the log line is written once. Never raises (fail-open).

        Returns {"status": "YES"|"NO"|"OFF", "date": "YYYY-MM-DD"|"-",
                 "block": str|None,
                 # 0.8.21:
                 "time": "HH:MM"|"-", "timezone": str|"-",
                 "timezone_source": "config"|"os"|"os-fallback"|"-"}.
        """
        result = {
            "status": "NO",
            "date": "-",
            "block": None,
            # 0.8.21:
            "time": "-",
            "timezone": "-",
            "timezone_source": "-",
        }

        try:
            if not self.valves.date_preflight:
                result["status"] = "OFF"

                return result

            cached = self._date_preflight_cache.get(state_key)

            if isinstance(cached, dict) and cached.get("text") == user_text:
                return cached["result"]

            match = (
                _RELATIVE_TIME_RE.search(_nfkc(user_text)) if user_text else None
            )

            if not match:
                print(
                    "[Bonsai2 Web Search Guard] "
                    "DATE_PREFLIGHT "
                    f"msg={state_key} "
                    "date_preflight=NO "
                    "reason=no-relative-time"
                )

            else:
                now, tz_label, tz_source, tz_error = self._resolve_now()

                iso = now.strftime("%Y-%m-%d")

                weekday = _WEEKDAYS_JA[now.weekday()]

                # 0.8.21: time parts are built from the SAME `now`.
                hhmm = now.strftime("%H:%M")

                tz_short = self._tz_short(now)

                iso_dt = now.replace(
                    second=0,
                    microsecond=0,
                ).isoformat()

                block = (
                    f"{DATE_PREFLIGHT_START}\n"
                    f"現在日時は {now.year}年{now.month}月{now.day}日"
                    f"（{weekday}曜日）{hhmm} {tz_short} です。"
                    f"（timezone: {tz_label}）\n"
                    f"ISO: {iso_dt}\n"
                    "「今日」「今年」「現在」「最新」などの相対的な時間表現は、"
                    "この現在日時を基準に解釈してください。\n"
                    "ユーザーが日付を明示している場合は、ユーザーの日付を"
                    "優先してください。\n"
                    "検索クエリに年を含める場合は、この現在日時に基づく年を使い、"
                    "根拠なく過去の年へずらさないでください。\n"
                    "これはシステムが提供する時間基準であり、"
                    "ユーザーの質問そのものではありません。\n"
                    f"{DATE_PREFLIGHT_END}"
                )

                result = {
                    "status": "YES",
                    "date": iso,
                    "block": block,
                    # 0.8.21:
                    "time": hhmm,
                    "timezone": tz_label,
                    "timezone_source": tz_source,
                }

                print(
                    "[Bonsai2 Web Search Guard] "
                    "DATE_PREFLIGHT "
                    f"msg={state_key} "
                    "date_preflight=YES "
                    f"trigger={match.group(0)!r} "
                    f"timezone={tz_label!r} "
                    f"timezone_source={tz_source} "
                    f"current_date={iso} "
                    # 0.8.21:
                    f"current_time={hhmm}"
                )

                if tz_error:
                    print(
                        "[Bonsai2 Web Search Guard] "
                        "DATE_PREFLIGHT_TIMEZONE_ERROR "
                        f"msg={state_key} "
                        f"configured={str(self.valves.timezone)!r} "
                        f"error={tz_error} "
                        "fallback=os-local-timezone "
                        "hint=on-Windows-zoneinfo-needs-the-tzdata-package"
                    )

            if len(self._date_preflight_cache) > 200:
                self._date_preflight_cache.clear()

            self._date_preflight_cache[state_key] = {
                "text": user_text,
                "result": result,
            }

            return result

        except Exception as e:
            print(
                "[Bonsai2 Web Search Guard] "
                "DATE_PREFLIGHT_ERROR "
                f"msg={state_key} "
                f"error={e!r}"
            )

            return {
                "status": "NO",
                "date": "-",
                "block": None,
                # 0.8.21:
                "time": "-",
                "timezone": "-",
                "timezone_source": "-",
            }

    # ------------------------------------------------------------------
    # request()
    # ------------------------------------------------------------------
    def request(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __metadata__: Optional[dict] = None,
    ) -> dict:
        if not self._is_bonsai(body):
            return body

        try:
            return self._request_impl(
                body,
                __metadata__ or {},
            )

        except Exception as e:
            print("[Bonsai2 Web Search Guard] " f"ERROR in request(): {e!r}")

            return body

    def _request_impl(
        self,
        body: dict,
        metadata_arg: dict,
    ) -> dict:
        v = self.valves

        metadata = body.get("metadata")

        if not isinstance(
            metadata,
            dict,
        ):
            metadata = metadata_arg

        if not isinstance(
            metadata,
            dict,
        ):
            metadata = {}

        message_id = (
            metadata.get("message_id")
            or body.get("message_id")
            or metadata.get("_bonsai_guard_state_id")
        )

        state_key = str(message_id) if message_id else "bonsai-unknown"

        # ---------------------------------------------------------------
        # Stable original user text.
        # ---------------------------------------------------------------
        user_text = self._audit_user_text.get(
            state_key,
            "",
        )

        if not user_text:
            stored = metadata.get("_bonsai_guard_user_text")

            if (
                isinstance(
                    stored,
                    str,
                )
                and stored.strip()
            ):
                user_text = stored

        if not user_text:
            user_text = self._latest_user_text(
                list(
                    body.get(
                        "messages",
                        [],
                    )
                    or []
                )
            )

        if user_text:
            self._audit_user_text[state_key] = user_text

            metadata["_bonsai_guard_user_text"] = user_text

        # ---------------------------------------------------------------
        # Activate fixed test state.
        # ---------------------------------------------------------------
        fetch_gate_test_request = self._activate_fetch_gate_test(
            state_key,
            user_text,
        )

        # ---------------------------------------------------------------
        # Copy messages.
        # ---------------------------------------------------------------
        messages = list(
            body.get(
                "messages",
                [],
            )
            or []
        )

        # ---------------------------------------------------------------
        # History XML sanitation.
        # ---------------------------------------------------------------
        if v.sanitize_history_tool_xml:
            messages = self._sanitize_history(messages)

        # 0.8.25: read-only classification of newly arrived fetch results.
        self._log_fetch_result_diag(
            messages,
            state_key,
        )

        # ---------------------------------------------------------------
        # Search rules.
        # ---------------------------------------------------------------
        initial_tools = body.get("tools")

        if (
            self._has_tool(
                initial_tools,
                "search_web",
            )
            and not fetch_gate_test_request
        ):
            messages = self._apply_search_query_rules(messages)

        # ---------------------------------------------------------------
        # 0.8.20: Date Preflight.
        # Adds / refreshes ONE system block with the absolute current date.
        # No tool call, no search, no user-message change, no counter change.
        # When not applicable, a stale block (if any) is removed.
        # ---------------------------------------------------------------
        date_pf = self._date_preflight(
            user_text,
            state_key,
        )

        messages = self._upsert_block(
            messages,
            DATE_PREFLIGHT_START,
            DATE_PREFLIGHT_END,
            date_pf["block"] if not fetch_gate_test_request else None,
        )

        # ---------------------------------------------------------------
        # Accounting.
        # ---------------------------------------------------------------
        search_count, fetch_count = self._count_successful(messages)

        search_attempts, fetch_attempts = self._count_attempts(messages)

        turns = self._count_tool_turns(messages)

        # ---------------------------------------------------------------
        # Detect a new search since duplicate-fetch suspension.
        # ---------------------------------------------------------------
        state = self._get_fetch_gate_state(
            state_key,
            user_text,
        )

        state["search_attempts_seen"] = search_attempts

        if state.get("fetch_suspended") and (
            search_attempts
            > state.get(
                "suspend_search_attempts",
                0,
            )
        ):
            state["fetch_suspended"] = False

            print(
                "[Bonsai2 Web Search Guard] "
                "FETCH_GATE "
                f"msg={state_key} "
                "status=fetch-suspension-cleared "
                "reason=new-search "
                f"search_attempts={search_attempts}"
            )

        search_limit = search_count >= v.max_searches

        fetch_limit = fetch_count >= v.max_fetches

        turn_limit = turns >= v.max_total_tool_turns

        final_mode = (search_limit and fetch_limit) or turn_limit

        first_llm_call = search_attempts == 0 and fetch_attempts == 0

        # ---------------------------------------------------------------
        # Search-result audit.
        # ---------------------------------------------------------------
        outcomes = []

        if user_text and not fetch_gate_test_request:
            outcomes = (
                self._audit_search_results(
                    messages,
                    user_text,
                    state_key,
                )
                or []
            )

        # ---------------------------------------------------------------
        # Arm one-shot search recovery immediately after audit.
        # ---------------------------------------------------------------
        if (
            v.search_recovery
            and outcomes
            and not state.get("search_recovery_used")
            and not search_limit
            and not final_mode
            and not fetch_gate_test_request
        ):
            latest = outcomes[-1]

            if (
                isinstance(
                    latest,
                    dict,
                )
                and latest.get("status") == "VIOLATION"
            ):
                prev_q = self._last_executed_query(messages) or ""

                entity = state.get("entity")

                recovery_query = self._build_recovery_query(
                    user_text,
                    entity,
                    prev_q,
                )

                if recovery_query:
                    state["search_recovery_used"] = True

                    state["search_recovery_pending"] = True

                    state["search_recovery_query"] = recovery_query

                    state["search_recovery_armed_attempts"] = search_attempts

                    prev_query_has_entity = bool(
                        entity and _norm(entity) in _norm(prev_q)
                    )

                    print(
                        "[Bonsai2 Web Search Guard] "
                        "SEARCH_RECOVERY "
                        "status=ARMED "
                        f"msg={state_key} "
                        f"trigger={latest.get('call_id')!r} "
                        f"entity={entity!r} "
                        f"prev_query={prev_q!r} "
                        "prev_query_has_entity="
                        f"{prev_query_has_entity} "
                        f"planned_query={recovery_query!r}"
                    )

        # ---------------------------------------------------------------
        # Clear recovery pending once a new search has actually appeared,
        # or when the request can no longer perform recovery.
        # ---------------------------------------------------------------
        if state.get("search_recovery_pending") and (
            search_limit
            or final_mode
            or fetch_gate_test_request
            or (
                search_attempts
                > state.get(
                    "search_recovery_armed_attempts",
                    0,
                )
            )
        ):
            state["search_recovery_pending"] = False

        recovery_active = bool(
            state.get("search_recovery_pending")
            and state.get("search_recovery_query")
            and not search_limit
            and not final_mode
            and not fetch_gate_test_request
        )

        # ---------------------------------------------------------------
        # Restore complete native tool set.
        # ---------------------------------------------------------------
        original_tools = self._get_original_tools(
            body,
            metadata,
            first_llm_call,
        )

        if isinstance(
            original_tools,
            list,
        ):
            tools = copy.deepcopy(original_tools)
        else:
            tools = body.get("tools")

        body["tools"] = tools

        # ---------------------------------------------------------------
        # Force first search.
        # ---------------------------------------------------------------
        force_search = (
            v.force_search_for_current_queries
            and first_llm_call
            and self._should_force_search(user_text)
            and not search_limit
            and not final_mode
            and not fetch_gate_test_request
            and self._has_tool(
                tools,
                "search_web",
            )
        )

        # ---------------------------------------------------------------
        # Recovery also uses required tool_choice.
        # ---------------------------------------------------------------
        if force_search or recovery_active:
            body["tool_choice"] = "required"

        elif body.get("tool_choice") == "required":
            body["tool_choice"] = "auto"

        # ---------------------------------------------------------------
        # Tool filtering.
        # ---------------------------------------------------------------
        if isinstance(
            tools,
            list,
        ):
            filtered = []

            for tool in tools:
                name = self._tool_name(tool)

                if name == "search_web" and search_limit:
                    continue

                if name == "fetch_url" and fetch_limit:
                    continue

                if (
                    (force_search and v.force_search_narrow_tools) or recovery_active
                ) and name != "search_web":
                    continue

                if fetch_gate_test_request and name != "fetch_url":
                    continue

                # -------------------------------------------------------
                # After a duplicate fetch, hide fetch_url until a new
                # search has occurred.
                # -------------------------------------------------------
                if (
                    name == "fetch_url"
                    and state.get("fetch_suspended")
                    and not fetch_gate_test_request
                ):
                    continue

                filtered.append(tool)

            body["tools"] = filtered

        # ---------------------------------------------------------------
        # Tool metadata filtering.
        # ---------------------------------------------------------------
        metadata_tools = metadata.get("tools")

        if isinstance(
            metadata_tools,
            dict,
        ):
            if search_limit:
                metadata_tools.pop(
                    "search_web",
                    None,
                )

            if fetch_limit:
                metadata_tools.pop(
                    "fetch_url",
                    None,
                )

            # IMPORTANT 0.8.15:
            # Do NOT remove fetch_url from metadata during recovery.
            #
            # body["tools"] is sufficient to hide fetch_url from the model.
            # Keeping metadata["tools"]["fetch_url"] intact allows the
            # fetch callable and its Guard wrappers to be restored normally
            # on the following hop.

            if fetch_gate_test_request:
                metadata_tools.pop(
                    "search_web",
                    None,
                )


        # 0.8.25: direct observation of the post-duplicate suspension state.
        if state.get("fetch_suspended"):
            body_has_fetch_url = self._has_tool(
                body.get("tools"),
                "fetch_url",
            )

            metadata_has_fetch_url = isinstance(
                metadata.get("tools"),
                dict,
            ) and "fetch_url" in metadata.get("tools", {})

            print(
                "[Bonsai2 Web Search Guard] "
                "FETCH_SUSPENSION_DIAG "
                f"msg={state_key} "
                "fetch_suspended=YES "
                f"search_attempts={search_attempts} "
                f"suspend_search_attempts={state.get('suspend_search_attempts', 0)} "
                f"body_has_fetch_url={'YES' if body_has_fetch_url else 'NO'} "
                f"metadata_has_fetch_url={'YES' if metadata_has_fetch_url else 'NO'} "
                f"fetched_urls={len(state.get('fetched_urls') or ())}"
            )

        # ---------------------------------------------------------------
        # Recovery system block.
        # ---------------------------------------------------------------
        if not final_mode and not fetch_gate_test_request:
            if recovery_active:
                recovery_block = (
                    f"{RECOVERY_START}\n"
                    "The previous search results did not contain "
                    "the requested subject.\n"
                    f"Requested subject: "
                    f"{state.get('entity')}\n"
                    "Call search_web exactly once with this exact query:\n"
                    f"{state.get('search_recovery_query')}\n"
                    "Do not answer yet.\n"
                    f"{RECOVERY_END}"
                )

                messages = self._upsert_block(
                    messages,
                    RECOVERY_START,
                    RECOVERY_END,
                    recovery_block,
                )

            else:
                messages = self._upsert_block(
                    messages,
                    RECOVERY_START,
                    RECOVERY_END,
                    None,
                )

        # ---------------------------------------------------------------
        # 0.8.18: target-unconfirmed note (text only).
        #
        # After the one-shot recovery was used, if the latest completed
        # search result still lacks the requested subject, tell the model
        # not to substitute another product. Applies in final mode too
        # (it is added before the final-answer block). No state is changed.
        # ---------------------------------------------------------------
        if (
            state.get("search_recovery_used")
            and not recovery_active
            and not fetch_gate_test_request
            and state.get("entity")
            and self._last_search_target_missing(
                messages,
                state.get("entity"),
            )
        ):
            subject = _expand_entity_phrase(
                user_text,
                str(state.get("entity")),
            ) or str(state.get("entity"))

            messages = self._apply_target_unconfirmed_note(
                messages,
                subject,
            )

        # ---------------------------------------------------------------
        # FETCH_GATE_TEST setup.
        # ---------------------------------------------------------------
        if fetch_gate_test_request and not final_mode:
            state = self._get_fetch_gate_state(
                state_key,
                "",
            )

            test_url = state.get("test_url") or self._normalize_url(
                v.fetch_gate_test_url
            )

            messages = self._apply_fetch_gate_test_mode(
                messages,
                state_key,
                test_url,
            )

            body["tool_choice"] = "required"

        # ---------------------------------------------------------------
        # Query audit.
        # ---------------------------------------------------------------
        audit_status = "-"

        if (
            not final_mode
            and not fetch_gate_test_request
            and not search_limit
            and search_attempts > 0
            and (v.query_audit_log or v.query_audit_feedback)
        ):
            last_q = self._last_executed_query(messages)

            if last_q:
                _, info = repair_query(
                    user_text,
                    last_q,
                )

                audit_status = "VIOLATION" if info["changed"] else "ok"

                if v.query_audit_log:
                    print(
                        "[Bonsai2 Web Search Guard] "
                        "QUERY_AUDIT "
                        f"{audit_status} "
                        f"query={last_q!r} "
                        f"missing={info['missing']} "
                        f"replaced={info['replaced']}"
                    )

                if (
                    v.query_audit_feedback
                    and not v.wrap_search_query_repair
                    and info["changed"]
                ):
                    terms = list(info["missing"]) + [new for _, new in info["replaced"]]

                    block = (
                        f"{AUDIT_START}\n"
                        "The previous search_web query did not "
                        "preserve the user's wording.\n"
                        f"Terms that were lost or altered: "
                        f"{', '.join(terms)}\n"
                        "If you search again, include these terms "
                        "exactly as the user wrote them. "
                        "Do not translate or romanize them.\n"
                        f"{AUDIT_END}"
                    )

                    messages = self._upsert_block(
                        messages,
                        AUDIT_START,
                        AUDIT_END,
                        block,
                    )

        # ---------------------------------------------------------------
        # Execution-time search repair / recovery wrapper.
        # ---------------------------------------------------------------
        wrap_status = "-"

        if (
            (v.wrap_search_query_repair or recovery_active)
            and not search_limit
            and not final_mode
            and not fetch_gate_test_request
        ):
            wrap_status = self._wrap_search_callable(
                body,
                user_text,
                state_key,
            )

        # ---------------------------------------------------------------
        # Fetch callable probe.
        # ---------------------------------------------------------------
        fetch_probe_status = "-"

        if (
            v.fetch_callable_probe
            and not fetch_limit
            and not final_mode
            and not recovery_active
            and not state.get("fetch_suspended")
        ):
            fetch_probe_status = self._wrap_fetch_callable_probe(
                body,
                state_key,
            )

        # ---------------------------------------------------------------
        # Fetch gate.
        # ---------------------------------------------------------------
        fetch_gate_status = "-"

        if (
            not fetch_limit
            and not final_mode
            and not recovery_active
            and not state.get("fetch_suspended")
        ):
            fetch_gate_status = self._wrap_fetch_gate(
                body,
                user_text,
                state_key,
            )

        # ---------------------------------------------------------------
        # Closed tools note.
        # ---------------------------------------------------------------
        if not final_mode:
            closed = []

            if search_limit:
                closed.append("search_web")

            if fetch_limit:
                closed.append("fetch_url")

            if state.get("fetch_suspended"):
                closed.append("fetch_url " "(temporarily suspended after duplicate)")

            if recovery_active:
                closed.append(
                    "fetch_url " "(temporarily unavailable during search recovery)"
                )

            if closed:
                messages = self._apply_closed_note(
                    messages,
                    closed,
                )

        # ---------------------------------------------------------------
        # 0.8.23: a non-final hop clears any stale final-hop state.
        # ---------------------------------------------------------------
        if not final_mode:
            self._final_hop.pop(state_key, None)

            self._final_fallback.pop(state_key, None)

        # ---------------------------------------------------------------
        # Final mode.
        # ---------------------------------------------------------------
        if final_mode:
            # 0.8.23: tell stream() that this hop is the final-answer hop.
            if v.final_answer_after_limit:
                self._final_hop[state_key] = {
                    "pending": "",
                    "inside": False,
                    "detected": False,
                    "blocks": 0,
                    "stray_close": 0,
                    "partial_dropped": False,
                    "raw_chars": 0,
                    "out_chars": 0,
                    "out_nonws": 0,
                    "native_dropped": 0,
                    "finish_changed": False,
                    "fallback": False,
                    "fallback_chars": 0,
                }

                if len(self._final_hop) > 100:
                    self._final_hop.clear()

                    self._final_hop[state_key] = {
                        "pending": "",
                        "inside": False,
                        "detected": False,
                        "blocks": 0,
                        "stray_close": 0,
                        "partial_dropped": False,
                        "raw_chars": 0,
                        "out_chars": 0,
                        "out_nonws": 0,
                        "native_dropped": 0,
                        "finish_changed": False,
                        "fallback": False,
                        "fallback_chars": 0,
                    }

            # 0.8.22: keep the retrieved results for the empty-response
            # fallback BEFORE the native tool history is flattened away.
            if v.final_answer_after_limit and v.final_answer_fallback:
                self._final_fallback[state_key] = self._build_final_fallback(messages)

                if len(self._final_fallback) > 100:
                    self._final_fallback.clear()

                    self._final_fallback[state_key] = self._build_final_fallback(
                        messages
                    )

            # 0.8.22: the limit closes the tools only; the retrieved
            # results are handed to the model as plain text.
            if v.flatten_tool_history_in_final_mode or v.final_answer_after_limit:
                messages = self._flatten_tool_history(messages)

            messages = self._apply_final_answer_mode(
                messages,
                limit_note=v.final_answer_after_limit,
            )

            body["tool_choice"] = "none"

            body["tools"] = []

            if isinstance(
                metadata_tools,
                dict,
            ):
                metadata_tools.clear()

            # 0.8.22: stop=['<tool_call>'] ended the response with 0
            # characters when the model began with <tool_call>. In the new
            # mode it is not added (and a stale one is removed).
            if v.final_answer_after_limit:
                old_stop = body.get("stop")

                if isinstance(old_stop, list) and "<tool_call>" in old_stop:
                    cleaned_stop = [x for x in old_stop if x != "<tool_call>"]

                    if cleaned_stop:
                        body["stop"] = cleaned_stop
                    else:
                        body.pop("stop", None)

            elif v.final_mode_add_stop:
                stop = body.get("stop")

                if isinstance(
                    stop,
                    str,
                ):
                    stop = [stop]

                stop = list(stop or [])

                if "<tool_call>" not in stop:
                    stop.append("<tool_call>")

                body["stop"] = stop

        body["messages"] = messages

        if v.disable_parallel_tool_calls:
            body["parallel_tool_calls"] = False

        # 0.8.24: read-only snapshot for RAW_TOOL_CALL_DIAG (after every
        # decision above; changes nothing).
        self._record_hop_diag(
            body=body,
            messages=messages,
            state_key=state_key,
            state=state,
            final_mode=final_mode,
            turn_limit=turn_limit,
            search_limit=search_limit,
            fetch_limit=fetch_limit,
            recovery_active=recovery_active,
            force_search=force_search,
            search_count=search_count,
            fetch_count=fetch_count,
            search_attempts=search_attempts,
            fetch_attempts=fetch_attempts,
            turns=turns,
        )

        print(
            "[Bonsai2 Web Search Guard] "
            f"msg={state_key} "
            f"search_web={search_count}/"
            f"{v.max_searches}, "
            f"fetch_url={fetch_count}/"
            f"{v.max_fetches}, "
            f"turns={turns}/"
            f"{v.max_total_tool_turns}, "
            f"search_attempts="
            f"{search_attempts}, "
            f"fetch_attempts="
            f"{fetch_attempts}, "
            f"available_tools="
            f"{len(body.get('tools', []) or [])}, "
            f"tool_choice="
            f"{body.get('tool_choice')}, "
            f"force_search="
            f"{'YES' if force_search else 'NO'}, "
            f"recovery="
            f"{'ACTIVE' if recovery_active else 'NO'}, "
            f"fetch_gate_test="
            f"{'YES' if fetch_gate_test_request else 'NO'}, "
            f"fetch_suspended="
            f"{'YES' if state.get('fetch_suspended') else 'NO'}, "
            f"final_mode="
            f"{'YES' if final_mode else 'NO'}"
            f"{'(turn_cap)' if turn_limit and not (search_limit and fetch_limit) else ''}, "
            f"stop={body.get('stop')}, "
            f"audit={audit_status}, "
            f"wrap={wrap_status}, "
            f"fetch_probe={fetch_probe_status}, "
            f"fetch_gate={fetch_gate_status}, "
            # 0.8.20:
            f"date_preflight={date_pf['status']}, "
            f"current_date={date_pf['date']}, "
            # 0.8.21:
            f"current_time={date_pf['time']}, "
            f"timezone={date_pf['timezone']}, "
            f"timezone_source={date_pf['timezone_source']}, "
            # 0.8.23:
            f"final_answer_after_limit="
            f"{'YES' if (final_mode and v.final_answer_after_limit) else 'NO'}"
        )

        return body

    # ------------------------------------------------------------------
    # stream() -- read-only
    # ------------------------------------------------------------------
    async def stream(
        self,
        event: dict,
        __metadata__: Optional[dict] = None,
    ) -> dict:
        # 0.8.23: the final-answer hop handling must run even when both
        # read-only probes are switched off.
        if (
            not self.valves.stream_probe
            and not self.valves.stream_query_audit
            and not self.valves.final_answer_strip_raw_tool_call
            and not self.valves.final_answer_fallback
            # 0.8.24:
            and not self.valves.raw_tool_call_diag
        ):
            return event

        try:
            self._probe_event(
                event,
                __metadata__ or {},
            )

        except Exception:
            pass

        return event

    def _probe_event(
        self,
        event: dict,
        metadata: dict,
    ) -> None:
        if not isinstance(
            event,
            dict,
        ):
            return

        key = str(
            metadata.get("message_id") or metadata.get("_bonsai_guard_state_id") or "?"
        )

        if len(self._probe) > 100:
            self._probe.clear()

        state = self._probe.setdefault(
            key,
            {
                "calls": {},
                "content_chars": 0,
                "reasoning_chars": 0,
                "c_tail": "",
                "r_tail": "",
                "xml_content": False,
                "xml_reasoning": False,
                # 0.8.24: read-only diagnostics
                "raw_markers": [],
                "raw_preview": "",
                "xml_at": -1,
                # 0.8.25: raw fetch_url text observed in streamed content.
                "raw_fetch_url_seen": False,
                "first_hop": self._hop_diag.get(
                    key,
                    {},
                ).get(
                    "hop",
                    0,
                ),
            },
        )

        user_text = metadata.get(
            "_bonsai_guard_user_text"
        ) or self._audit_user_text.get(
            key,
            "",
        )

        for choice in event.get("choices") or []:
            if not isinstance(
                choice,
                dict,
            ):
                continue

            delta = choice.get("delta") or {}

            content = delta.get("content") or ""

            reasoning = delta.get("reasoning_content") or delta.get("reasoning") or ""

            if content:
                # 0.8.24: test (previous tail + chunk) BEFORE truncating, so
                # a chunk longer than 80 chars cannot hide the tag. Tags split
                # across chunks are still found through the retained tail.
                c_before = state["content_chars"]

                c_tail_before = len(state["c_tail"])

                c_window = state["c_tail"] + content

                state["content_chars"] += len(content)

                state["c_tail"] = c_window[-80:]

                if "<tool_call>" in c_window:
                    state["xml_content"] = True

                if "fetch_url" in c_window:
                    state["raw_fetch_url_seen"] = True

                self._diag_scan_content(
                    state,
                    c_window,
                    c_tail_before,
                    c_before,
                    content,
                )

            if reasoning:
                state["reasoning_chars"] += len(reasoning)

                r_window = state["r_tail"] + reasoning

                state["r_tail"] = r_window[-80:]

                if "<tool_call>" in r_window:
                    state["xml_reasoning"] = True

                if "fetch_url" in r_window:
                    state["raw_fetch_url_seen"] = True

            for tc in delta.get("tool_calls") or []:
                if not isinstance(
                    tc,
                    dict,
                ):
                    continue

                idx = tc.get(
                    "index",
                    0,
                )

                fn = tc.get("function") or {}

                call = state["calls"].setdefault(
                    idx,
                    {
                        "name": "?",
                        "args": "",
                    },
                )

                if fn.get("name"):
                    call["name"] = fn.get("name")

                call["args"] += fn.get("arguments") or ""

            finish = choice.get("finish_reason")

            # 0.8.23: final-answer hop only (no-op for every other hop).
            # Runs before the early `continue` so every chunk is handled.
            try:
                self._final_hop_handle(
                    key,
                    choice,
                    finish,
                )

            except Exception as e:
                print(
                    "[Bonsai2 Web Search Guard] "
                    "FINAL_HOP_ERROR "
                    f"msg={key} "
                    f"error={e!r}"
                )

            if not finish:
                continue

            native_calls = []

            for call in state["calls"].values():
                native_calls.append((f"{call['name']}" f"({call['args'][:160]})"))

            if self.valves.stream_probe:
                print(
                    "[Bonsai2 Web Search Guard] "
                    "STREAM "
                    f"msg={key} "
                    f"finish={finish} "
                    f"native_calls={native_calls} "
                    f"content_chars="
                    f"{state['content_chars']} "
                    f"reasoning_chars="
                    f"{state['reasoning_chars']} "
                    f"xml_in_content="
                    f"{state['xml_content']} "
                    f"xml_in_reasoning="
                    f"{state['xml_reasoning']}"
                )

            if self.valves.stream_query_audit:
                search_index = 0

                for call in state["calls"].values():

                    if call.get("name") != "search_web":
                        continue

                    raw_args = call.get("args") or ""

                    try:
                        obj = json.loads(raw_args)

                        query = (
                            obj.get("query")
                            if isinstance(
                                obj,
                                dict,
                            )
                            else None
                        )

                        if not (
                            isinstance(
                                query,
                                str,
                            )
                            and query.strip()
                        ):
                            print(
                                "[Bonsai2 Web Search Guard] "
                                "STREAM_QUERY_AUDIT "
                                f"msg={key} "
                                f"index={search_index} "
                                "status=UNPARSEABLE "
                                "query='' "
                                "missing=[] "
                                "replaced=[]"
                            )

                        elif not user_text:
                            print(
                                "[Bonsai2 Web Search Guard] "
                                "STREAM_QUERY_AUDIT "
                                f"msg={key} "
                                f"index={search_index} "
                                "status=NO_USER_TEXT "
                                f"query={query!r} "
                                "missing=[] "
                                "replaced=[]"
                            )

                        else:
                            _, info = repair_query(
                                user_text,
                                query,
                            )

                            status = "VIOLATION" if info["changed"] else "ok"

                            print(
                                "[Bonsai2 Web Search Guard] "
                                "STREAM_QUERY_AUDIT "
                                f"msg={key} "
                                f"index={search_index} "
                                f"status={status} "
                                f"query={query!r} "
                                f"missing="
                                f"{info['missing']} "
                                f"replaced="
                                f"{info['replaced']}"
                            )

                    except Exception:
                        print(
                            "[Bonsai2 Web Search Guard] "
                            "STREAM_QUERY_AUDIT "
                            f"msg={key} "
                            f"index={search_index} "
                            "status=UNPARSEABLE "
                            f"query={raw_args[:200]!r} "
                            "missing=[] "
                            "replaced=[]"
                        )

                    search_index += 1

            # 0.8.25: observe a fetch attempt while suspension is live.
            # This is diagnostic only and does not alter the stream.
            gate_state = self._fetch_gate_state.get(key)

            if isinstance(gate_state, dict) and gate_state.get("fetch_suspended"):
                native_fetches = [
                    c
                    for c in state["calls"].values()
                    if c.get("name") == "fetch_url"
                ]

                raw_fetch = bool(state.get("raw_fetch_url_seen"))

                if native_fetches or raw_fetch:
                    print(
                        "[Bonsai2 Web Search Guard] "
                        "FETCH_SUSPENDED_TOOL_ATTEMPT "
                        f"msg={key} "
                        "fetch_suspended=YES "
                        f"native_fetch_call={'YES' if native_fetches else 'NO'} "
                        f"raw_fetch_url_seen={'YES' if raw_fetch else 'NO'} "
                        f"native_calls={[c.get('name') for c in state['calls'].values()]} "
                        "action=OBSERVE_ONLY"
                    )

            # 0.8.22/0.8.23: the empty-response fallback is decided inside
            # _final_hop_handle() from the CLEANED text; here only the log.
            # 0.8.24: read-only diagnosis of NON-final hops. Must run
            # BEFORE _final_hop_log(), which releases the final-hop state.
            self._raw_tool_call_diag_log(
                key,
                state,
                finish,
            )

            self._final_hop_log(
                key,
                state,
                finish,
            )

            self._probe.pop(
                key,
                None,
            )

    # ------------------------------------------------------------------
    # Raw <tool_call> diagnostics (0.8.24, read-only)
    # ------------------------------------------------------------------
    def _record_hop_diag(
        self,
        body: dict,
        messages: list,
        state_key: str,
        state: dict,
        final_mode: bool,
        turn_limit: bool,
        search_limit: bool,
        fetch_limit: bool,
        recovery_active: bool,
        force_search: bool,
        search_count: int,
        fetch_count: int,
        search_attempts: int,
        fetch_attempts: int,
        turns: int,
    ) -> None:
        """
        0.8.24: store a small snapshot of this request() hop. Read-only data
        for _raw_tool_call_diag_log(). Never raises, never mutates body /
        messages / state.
        """
        try:
            seq = self._hop_seq.get(state_key, 0) + 1

            if len(self._hop_seq) > 200:
                self._hop_seq.clear()

            self._hop_seq[state_key] = seq

            names = [
                self._tool_name(t) or "?"
                for t in (body.get("tools") or [])
                if isinstance(t, dict)
            ]

            chars = 0

            for m in messages:
                if isinstance(m, dict):
                    chars += len(_content_to_text(m.get("content", "")))

            last_role = None

            if messages and isinstance(messages[-1], dict):
                last_role = messages[-1].get("role")

            # Mirrors the condition under which request() adds the
            # "closed tools" system note (not evaluated twice differently:
            # same four inputs, final_mode excluded).
            closed_note = (not final_mode) and bool(
                search_limit
                or fetch_limit
                or state.get("fetch_suspended")
                or recovery_active
            )

            if len(self._hop_diag) > 200:
                self._hop_diag.clear()

            self._hop_diag[state_key] = {
                "hop": seq,
                "final_mode": bool(final_mode),
                "turn_cap": bool(turn_limit),
                "fetch_suspended": bool(state.get("fetch_suspended")),
                "suspend_search_attempts": state.get(
                    "suspend_search_attempts",
                    0,
                ),
                "search_attempts": search_attempts,
                "fetch_attempts": fetch_attempts,
                "search_count": search_count,
                "fetch_count": fetch_count,
                "turns": turns,
                "tools": names,
                "tool_choice": body.get("tool_choice"),
                "stop": body.get("stop"),
                "closed_note": closed_note,
                "recovery": bool(recovery_active),
                "force_search": bool(force_search),
                "msgs": len(messages),
                "last_role": last_role,
                "prompt_chars": chars,
            }

        except Exception:
            pass

    def _diag_scan_content(
        self,
        state: dict,
        window: str,
        tail_before: int,
        chars_before: int,
        content: str,
    ) -> None:
        """
        0.8.24: read-only scan of (previous tail + chunk) for raw tool-call
        markers. Records marker names, the content offset of the first
        <tool_call> and a short preview. Never raises, never mutates the
        event.
        """
        try:
            for mk in _DIAG_MARKERS:
                if mk in window and mk not in state["raw_markers"]:
                    state["raw_markers"].append(mk)

            if state["xml_at"] >= 0:
                room = _DIAG_PREVIEW_MAX - len(state["raw_preview"])

                if room > 0:
                    state["raw_preview"] += content[:room]

                return

            i = window.find("<tool_call>")

            if i >= 0:
                state["xml_at"] = max(
                    0,
                    chars_before - tail_before + i,
                )

                state["raw_preview"] = window[i : i + _DIAG_PREVIEW_MAX]

        except Exception:
            pass

    def _raw_tool_call_diag_log(
        self,
        key: str,
        state: dict,
        finish,
    ) -> None:
        """
        0.8.24: one RAW_TOOL_CALL_DIAG line per NON-final hop whose content /
        reasoning carried raw tool-call text. Final-answer hops handled by
        _final_hop_*() are skipped (FINAL_ANSWER_STREAM covers them).
        Observation only: nothing is modified. Never raises.
        """
        try:
            if not self.valves.raw_tool_call_diag:
                return

            if key in self._final_hop:
                return

            if state.get("xml_content"):
                trigger = "xml_in_content"

            elif state.get("raw_markers"):
                trigger = "markers_in_content"

            elif state.get("xml_reasoning"):
                trigger = "xml_in_reasoning"

            else:
                return

            snap = self._hop_diag.get(key)

            gstate = self._fetch_gate_state.get(key)

            def yn(
                value,
            ) -> str:
                return "YES" if value else "NO"

            native = [
                f"{c.get('name')}(args_len={len(c.get('args') or '')})"
                for c in state["calls"].values()
            ]

            if snap:
                req = (
                    f"hop={snap['hop']} "
                    f"final_mode={yn(snap['final_mode'])} "
                    f"fetch_suspended={yn(snap['fetch_suspended'])} "
                    f"suspend_search_attempts="
                    f"{snap['suspend_search_attempts']} "
                    f"search_attempts={snap['search_attempts']} "
                    f"fetch_attempts={snap['fetch_attempts']} "
                    f"search_count={snap['search_count']} "
                    f"fetch_count={snap['fetch_count']} "
                    f"turns={snap['turns']} "
                    f"tools={snap['tools']} "
                    f"tool_choice={snap['tool_choice']} "
                    f"stop={snap['stop']} "
                    f"closed_note={yn(snap['closed_note'])} "
                    f"recovery={yn(snap['recovery'])} "
                    f"force_search={yn(snap['force_search'])} "
                    f"msgs={snap['msgs']} "
                    f"last_role={snap['last_role']} "
                    f"prompt_chars={snap['prompt_chars']} "
                    f"probe_age_hops={snap['hop'] - state.get('first_hop', 0)}"
                )

            else:
                req = "hop=? final_mode=? request_snapshot=MISSING"

            if isinstance(gstate, dict):
                live = (
                    f"fetch_suspended_live={yn(gstate.get('fetch_suspended'))} "
                    f"search_attempts_seen="
                    f"{gstate.get('search_attempts_seen')} "
                    f"fetched_urls={len(gstate.get('fetched_urls') or ())} "
                    f"recovery_used="
                    f"{yn(gstate.get('search_recovery_used'))}"
                )

            else:
                live = "gate_state=MISSING"

            print(
                "[Bonsai2 Web Search Guard] "
                "RAW_TOOL_CALL_DIAG "
                f"msg={key} "
                f"trigger={trigger} "
                f"{req} "
                f"finish={finish} "
                f"native_calls={native} "
                f"content_chars={state.get('content_chars')} "
                f"reasoning_chars={state.get('reasoning_chars')} "
                f"xml_in_content={state.get('xml_content')} "
                f"xml_in_reasoning={state.get('xml_reasoning')} "
                f"raw_markers={state.get('raw_markers')} "
                f"xml_at={state.get('xml_at')} "
                f"{live} "
                f"raw_preview={str(state.get('raw_preview'))[:_DIAG_PREVIEW_MAX]!r} "
                "action=OBSERVE_ONLY"
            )

        except Exception as e:
            print(
                "[Bonsai2 Web Search Guard] "
                "RAW_TOOL_CALL_DIAG_ERROR "
                f"msg={key} "
                f"error={e!r}"
            )

    # ------------------------------------------------------------------
    # Final-answer hop: raw <tool_call> removal (0.8.23)
    # ------------------------------------------------------------------
    @staticmethod
    def _rawtc_feed(
        fh: dict,
        text: str,
    ) -> str:
        """
        0.8.23: feed one content delta and return the text that may be shown.

        State kept in `fh`: "pending" (a trailing partial tag held back until
        the next chunk) and "inside" (currently inside <tool_call>...).
        Handles tags split across chunks ("<tool" + "_call>"), several blocks
        in one chunk, text before/after a block, and a stray </tool_call>.
        """
        data = fh["pending"] + text

        fh["pending"] = ""

        out = []

        while data:
            if fh["inside"]:
                idx = data.find(_RAW_TC_CLOSE)

                if idx == -1:
                    keep = _partial_suffix_len(
                        data,
                        _RAW_TC_CLOSE,
                    )

                    fh["pending"] = data[len(data) - keep :] if keep else ""

                    break

                data = data[idx + len(_RAW_TC_CLOSE) :]

                fh["inside"] = False

                fh["blocks"] += 1

                continue

            m = _RAW_TC_TAG_RE.search(data)

            if m is None:
                keep = max(
                    _partial_suffix_len(
                        data,
                        _RAW_TC_OPEN,
                    ),
                    _partial_suffix_len(
                        data,
                        _RAW_TC_CLOSE,
                    ),
                )

                cut = len(data) - keep

                out.append(data[:cut])

                fh["pending"] = data[cut:]

                break

            out.append(data[: m.start()])

            data = data[m.end() :]

            fh["detected"] = True

            if m.group(0) == _RAW_TC_OPEN:
                fh["inside"] = True

            else:
                fh["stray_close"] += 1

        return "".join(out)

    @staticmethod
    def _rawtc_flush(
        fh: dict,
    ) -> str:
        """
        0.8.23: end of stream. An unterminated block is dropped. A held
        partial tag of _RAW_TC_MIN_PARTIAL+ characters is dropped; anything
        shorter ("<", "<t") is ordinary text and is returned.
        """
        pend = fh["pending"]

        fh["pending"] = ""

        if fh["inside"]:
            fh["inside"] = False

            fh["blocks"] += 1

            return ""

        if (
            pend
            and len(pend) >= _RAW_TC_MIN_PARTIAL
            and (_RAW_TC_OPEN.startswith(pend) or _RAW_TC_CLOSE.startswith(pend))
        ):
            fh["partial_dropped"] = True

            fh["detected"] = True

            return ""

        return pend

    def _final_hop_handle(
        self,
        key: str,
        choice: dict,
        finish,
    ) -> None:
        """
        0.8.23: process one stream choice of the final-answer hop. Does
        nothing unless request() marked this message's hop as final.

          1. native delta.tool_calls are dropped (tools are closed);
          2. raw <tool_call> text is removed from delta.content;
          3. at finish: flush held text, finish_reason tool_calls -> stop,
             and inject the 0.8.22 fallback when NO visible text remains.
        """
        fh = self._final_hop.get(key)

        if fh is None:
            return

        v = self.valves

        strip = v.final_answer_strip_raw_tool_call

        d = choice.get("delta")

        if not isinstance(
            d,
            dict,
        ):
            d = {}

            choice["delta"] = d

        if strip:
            tcs = d.get("tool_calls")

            if tcs:
                fh["native_dropped"] += len(tcs) if isinstance(tcs, list) else 1

                d.pop(
                    "tool_calls",
                    None,
                )

        content = d.get("content")

        if isinstance(
            content,
            str,
        ) and content:
            fh["raw_chars"] += len(content)

            if strip:
                content = self._rawtc_feed(
                    fh,
                    content,
                )

                d["content"] = content

        else:
            content = ""

        if finish:
            if strip:
                tail = self._rawtc_flush(fh)

                if tail:
                    content += tail

                    d["content"] = content

                if choice.get("finish_reason") == "tool_calls" and fh["native_dropped"]:
                    choice["finish_reason"] = "stop"

                    fh["finish_changed"] = True

        fh["out_chars"] += len(content)

        fh["out_nonws"] += len("".join(content.split()))

        if finish:
            fallback = self._final_fallback.pop(
                key,
                None,
            )

            if fallback and v.final_answer_fallback and fh["out_nonws"] == 0:
                d["content"] = (d.get("content") or "") + fallback

                fh["fallback"] = True

                fh["fallback_chars"] = len(fallback)

    def _final_hop_log(
        self,
        key: str,
        state: dict,
        finish,
    ) -> None:
        """
        0.8.23: one audit line per final-answer hop; releases the hop state.
        """
        fh = self._final_hop.pop(
            key,
            None,
        )

        if fh is None:
            return

        raw = bool(fh["detected"] or state.get("xml_content") or fh["native_dropped"])

        cleaned = bool(
            self.valves.final_answer_strip_raw_tool_call
            and (
                fh["blocks"]
                or fh["stray_close"]
                or fh["partial_dropped"]
                or fh["native_dropped"]
            )
        )

        print(
            "[Bonsai2 Web Search Guard] "
            "FINAL_ANSWER_STREAM "
            f"msg={key} "
            f"finish={finish} "
            "final_mode=YES "
            "final_answer_after_limit=YES "
            f"final_answer_raw_tool_call={'YES' if raw else 'NO'} "
            f"final_answer_cleaned_tool_call={'YES' if cleaned else 'NO'} "
            f"blocks_removed={fh['blocks']} "
            f"native_tool_calls_dropped={fh['native_dropped']} "
            f"finish_changed={'YES' if fh['finish_changed'] else 'NO'} "
            f"final_answer_content_chars={fh['raw_chars']} "
            f"final_answer_cleaned_chars={fh['out_chars']} "
            f"final_answer_visible_chars={fh['out_nonws']} "
            f"final_answer_fallback={'YES' if fh['fallback'] else 'NO'} "
            f"fallback_chars={fh['fallback_chars']}"
        )

    # ------------------------------------------------------------------
    # inlet()
    # ------------------------------------------------------------------
    def inlet(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __metadata__: Optional[dict] = None,
    ) -> dict:

        metadata = body.get("metadata")

        if not isinstance(
            metadata,
            dict,
        ):
            metadata = (
                __metadata__
                if isinstance(
                    __metadata__,
                    dict,
                )
                else {}
            )

        message_id = metadata.get("message_id") or body.get("message_id")

        messages = (
            body.get(
                "messages",
                [],
            )
            or []
        )

        # ---------------------------------------------------------------
        # Capture original user text exactly once.
        # ---------------------------------------------------------------
        original_user_text = self._extract_user_text_from_messages(
            messages,
            message_id,
        )

        if message_id:
            key = str(message_id)

            self._audit_user_text[key] = original_user_text

            metadata["_bonsai_guard_user_text"] = original_user_text

        # ---------------------------------------------------------------
        # Stable metadata identity.
        # ---------------------------------------------------------------
        if not metadata.get("_bonsai_guard_state_id"):
            if message_id:
                metadata["_bonsai_guard_state_id"] = str(message_id)
            else:
                metadata["_bonsai_guard_state_id"] = "bonsai-inlet"

        # ---------------------------------------------------------------
        # Capture original complete tool set once.
        # ---------------------------------------------------------------
        original_tools = body.get("tools")

        if isinstance(
            original_tools,
            list,
        ) and not isinstance(
            metadata.get("_bonsai_guard_original_tools"),
            list,
        ):
            metadata["_bonsai_guard_original_tools"] = copy.deepcopy(original_tools)

        return body

    # ------------------------------------------------------------------
    # outlet()
    # ------------------------------------------------------------------
    def outlet(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __metadata__: Optional[dict] = None,
    ) -> dict:
        return body
