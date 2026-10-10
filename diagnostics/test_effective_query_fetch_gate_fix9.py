"""Offline regression tests for the fix9 effective-query Fetch Gate candidate.

Run from the repository root:
    python -m unittest -v diagnostics/test_effective_query_fetch_gate_fix9.py

No Open WebUI service, DDGS request, or external network call is used.
"""

import importlib.util
import json
from pathlib import Path
import unittest


SOURCE = Path(__file__).with_name("guard0.8.26-fix9-effective-query-fetch-gate.py")
SPEC = importlib.util.spec_from_file_location("searchguard_fix9", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load candidate source: {SOURCE}")
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)

TARGET = "カティサーク"
MODEL_RECOVERY_QUERY = "\"Katie's\" OR \"Catie\" whisky 単麦芽"
EFFECTIVE_RECOVERY_QUERY = "\"カティサーク\" スコッチウイスキー ページ"


def native_args(query, count=2):
    return json.dumps({"query": query, "count": count}, ensure_ascii=False)


class EffectiveQueryFetchGateFix9Tests(unittest.TestCase):
    def test_recovery_override_records_and_uses_effective_query_for_gate(self):
        guard = GUARD.Filter()
        state_key = "test-msg-recovery"
        user_text = "カティサークの味や種類、飲み方を調べて、参照URLを示してください。"
        state = guard._get_fetch_gate_state(state_key, user_text)
        state["search_recovery_pending"] = True
        state["search_recovery_query"] = EFFECTIVE_RECOVERY_QUERY
        guard._get_main_audit_entity = lambda _text: TARGET

        observed_queries = []
        search_results = [
            {
                "title": "カティサークの味や種類。美味しい飲み方もご紹介",
                "link": "https://sakidori.co/article/690659",
                "snippet": "カティサーク・オリジナルはライトな味わいです。",
            },
            {
                "title": "カティサークの特徴と楽しみ方",
                "link": "https://gohobi.co/whisky/961/",
                "snippet": "カティサークはスコッチウイスキーの人気銘柄です。",
            },
            {
                "title": "カティサークというお酒",
                "link": "https://note.com/example/cutty-sark",
                "snippet": "カティサークについて価格や味わいを紹介します。",
            },
            {
                "title": "カティサークの歴史",
                "link": "https://tanoshiiosake.jp/10265",
                "snippet": "小説に登場するカティサークについて解説します。",
            },
            {
                "title": "カティサークの誕生と歴史",
                "link": "https://www.barrel365.com/n2505031/",
                "snippet": "カティサークが誕生したのは1923年です。",
            },
            {
                "title": "Ballantine's Scotch whisky",
                "link": "https://it.pinterest.com/pin/example",
                "snippet": "言わずと知れたスコッチウイスキーの名門、バランタイン。",
            },
            {
                "title": "事業所案内｜企業情報",
                "link": "https://www.sbs-sokuhaisupport.co.jp/sbssksp/company/office/",
                "snippet": "企業情報と事業所一覧です。",
            },
            {
                "title": "会社概要｜企業情報",
                "link": "https://www.sbs-sokuhaisupport.co.jp/sbssksp/company/outline/",
                "snippet": "会社概要と企業情報をご覧いただけます。",
            },
        ]

        def fake_search(**kwargs):
            observed_queries.append(kwargs.get("query"))
            return json.dumps(search_results, ensure_ascii=False)

        body = {
            "metadata": {
                "tools": {
                    "search_web": {
                        "callable": fake_search,
                    }
                }
            }
        }
        guard._wrap_search_callable(body, user_text, state_key)
        result_json = body["metadata"]["tools"]["search_web"]["callable"](
            query=MODEL_RECOVERY_QUERY,
            count=8,
        )

        self.assertEqual(observed_queries, [EFFECTIVE_RECOVERY_QUERY])
        self.assertEqual(len(state["effective_search_calls"]), 1)
        record = state["effective_search_calls"][0]
        self.assertEqual(record["model_query"], MODEL_RECOVERY_QUERY)
        self.assertEqual(record["effective_query"], EFFECTIVE_RECOVERY_QUERY)
        self.assertIsNone(record["call_id"])

        call_id = "call-recovery-1"
        messages = [
            {"role": "user", "content": user_text},
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": "search_web",
                            "arguments": native_args(MODEL_RECOVERY_QUERY),
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": call_id,
                "content": result_json,
            },
        ]

        outcomes = guard._audit_search_results(messages, user_text, state_key)

        self.assertEqual(len(outcomes), 1)
        self.assertTrue(outcomes[0]["found"])
        self.assertEqual(record["call_id"], call_id)
        self.assertEqual(len(state["ok_urls"]), 5)
        self.assertEqual(len(state["suspect_urls"]), 3)
        self.assertIn(
            guard._normalize_url("https://sakidori.co/article/690659"),
            state["ok_urls"],
        )
        self.assertIn(
            guard._normalize_url("https://www.sbs-sokuhaisupport.co.jp/sbssksp/company/office/"),
            state["suspect_urls"],
            "An unrelated result must become SUSPECT when the effective query targets the entity.",
        )

    def test_duplicate_model_queries_map_to_distinct_effective_queries_in_order(self):
        records = [
            {
                "sequence": 1,
                "model_query": "same model query",
                "effective_query": "effective query A",
                "call_id": None,
            },
            {
                "sequence": 2,
                "model_query": "same model query",
                "effective_query": "effective query B",
                "call_id": None,
            },
        ]
        calls = [
            ("call-1", native_args("same model query")),
            ("call-2", native_args("same model query")),
        ]

        associated = GUARD._associate_effective_search_queries(calls, records)

        self.assertEqual(
            associated,
            {
                "call-1": "effective query A",
                "call-2": "effective query B",
            },
        )
        self.assertEqual([record["call_id"] for record in records], ["call-1", "call-2"])

    def test_duplicate_model_queries_with_missing_record_are_not_ambiguously_assigned(self):
        # One recorded execution cannot safely be attributed to either of two
        # native calls with identical model arguments. The record might belong
        # to the second call if the first was stopped before this wrapper ran.
        records = [
            {
                "sequence": 1,
                "model_query": "same model query",
                "effective_query": "effective query from an executed call",
                "call_id": None,
            }
        ]
        calls = [
            ("call-not-recorded", native_args("same model query")),
            ("call-recorded-later", native_args("same model query")),
        ]

        associated = GUARD._associate_effective_search_queries(calls, records)

        self.assertEqual(associated, {})
        self.assertIsNone(records[0]["call_id"])

    def test_existing_association_stays_stable_as_more_duplicate_calls_arrive(self):
        # A first audit may associate the first call before a later duplicate
        # call and its record exist. That association must remain stable.
        records = [
            {
                "sequence": 1,
                "model_query": "same model query",
                "effective_query": "effective query A",
                "call_id": "call-1",
            }
        ]
        calls_before_later_invocation = [
            ("call-2", native_args("same model query")),
            ("call-1", native_args("same model query")),
        ]

        first = GUARD._associate_effective_search_queries(
            calls_before_later_invocation, records
        )
        self.assertEqual(first, {"call-1": "effective query A"})
        self.assertEqual(records[0]["call_id"], "call-1")

        records.append(
            {
                "sequence": 2,
                "model_query": "same model query",
                "effective_query": "effective query B",
                "call_id": None,
            }
        )
        second = GUARD._associate_effective_search_queries(
            calls_before_later_invocation, records
        )

        self.assertEqual(
            second,
            {
                "call-1": "effective query A",
                "call-2": "effective query B",
            },
        )
        self.assertEqual([r["call_id"] for r in records], ["call-1", "call-2"])

    def test_unmatched_model_query_does_not_consume_an_effective_record(self):
        records = [
            {
                "sequence": 1,
                "model_query": "query that actually executed",
                "effective_query": "effective query",
                "call_id": None,
            }
        ]
        calls = [
            ("call-unmatched", native_args("different query")),
        ]

        associated = GUARD._associate_effective_search_queries(calls, records)

        self.assertEqual(associated, {})
        self.assertIsNone(records[0]["call_id"])

    def test_effective_query_flags_use_effective_value_and_keep_model_diagnostic(self):
        flags = GUARD._query_entity_audit_flags(
            TARGET,
            MODEL_RECOVERY_QUERY,
            EFFECTIVE_RECOVERY_QUERY,
        )

        self.assertFalse(flags["model_query_entity_included"])
        self.assertTrue(flags["effective_query_entity_included"])
        self.assertEqual(flags["query_source"], "effective")
        self.assertTrue(flags["query_entity_included"])

    def test_untracked_effective_query_explicitly_falls_back_to_model_query(self):
        flags = GUARD._query_entity_audit_flags(
            TARGET,
            EFFECTIVE_RECOVERY_QUERY,
            None,
        )

        self.assertTrue(flags["model_query_entity_included"])
        self.assertIsNone(flags["effective_query_entity_included"])
        self.assertEqual(flags["query_source"], "model-fallback")
        self.assertTrue(flags["query_entity_included"])

        missing_flags = GUARD._query_entity_audit_flags(
            TARGET,
            MODEL_RECOVERY_QUERY,
            None,
        )
        self.assertFalse(missing_flags["query_entity_included"])
        self.assertEqual(missing_flags["query_source"], "model-fallback")


if __name__ == "__main__":
    unittest.main(verbosity=2)
