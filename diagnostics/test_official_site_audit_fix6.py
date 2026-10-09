"""Offline tests for SearchGuard's official-site audit classification.

Run:
    python -m unittest -v diagnostics/test_official_site_audit_fix6.py

All search tool responses are local fixtures. No Open WebUI, DDGS, or network
search is invoked by this test module.
"""

import importlib.util
import json
from pathlib import Path
import unittest


SOURCE = Path(__file__).with_name("guard0.8.26-fix6-official-audit-diag1.py")
SPEC = importlib.util.spec_from_file_location("searchguard_fix6", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load candidate source: {SOURCE}")
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


class OfficialSiteAuditFix6Tests(unittest.TestCase):
    def setUp(self):
        self.filter = GUARD.Filter()

    def _messages(self, user_text, results, query=None):
        if query is None:
            query = "カティサーク 公式サイト"
        tool_id = "test-search-1"
        return [
            {"role": "user", "content": user_text},
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tool_id,
                        "type": "function",
                        "function": {
                            "name": "search_web",
                            "arguments": json.dumps({"query": query}, ensure_ascii=False),
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": tool_id,
                "content": json.dumps({"results": results}, ensure_ascii=False),
            },
        ]

    def test_japanese_and_english_official_requests_are_detected(self):
        self.assertTrue(GUARD._is_official_site_request("カティサークの公式サイトURLを確認"))
        self.assertTrue(GUARD._is_official_site_request("Please find the Official Website for Cutty Sark"))
        self.assertFalse(GUARD._is_official_site_request("カティサークの容量を確認"))

    def test_entity_without_official_marker_is_unconfirmed(self):
        self.assertEqual(
            GUARD._classify_official_search_result(
                "カティサーク",
                "カティサークのおすすめウイスキーを紹介",
            ),
            "OFFICIAL_UNCONFIRMED",
        )

    def test_explicit_official_wording_is_candidate_not_confirmation(self):
        self.assertEqual(
            GUARD._classify_official_search_result(
                "カティサーク",
                "カティサーク公式サイトはこちら。運営者の解説記事です。",
            ),
            "OFFICIAL_CANDIDATE",
        )
        # The search-audit contract never returns a confirmed state.
        self.assertNotEqual(
            GUARD._classify_official_search_result(
                "カティサーク", "カティサーク公式サイトはこちら"
            ),
            "OFFICIAL_CONFIRMED",
        )

    def test_result_without_the_requested_entity_is_missing(self):
        self.assertEqual(
            GUARD._classify_official_search_result(
                "カティサーク",
                "バランタインの公式サイト",
            ),
            "ENTITY_MISSING",
        )

    def test_audit_does_not_call_entity_presence_official_confirmation(self):
        user = "カティサークの公式サイトURLを確認してください。"
        messages = self._messages(
            user,
            [
                {
                    "title": "カティサークのおすすめウイスキー",
                    "snippet": "販売店による商品紹介です。",
                    "url": "https://retailer.example/blog/cutty-sark",
                }
            ],
        )
        outcomes = self.filter._audit_search_results(messages, user, "test-unconfirmed")
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0]["status"], "ok")
        self.assertEqual(outcomes[0]["entity_status"], "ENTITY_FOUND")
        self.assertEqual(outcomes[0]["official_status"], "OFFICIAL_UNCONFIRMED")
        self.assertTrue(outcomes[0]["found"])
        self.assertEqual(outcomes[0]["official_candidate_count"], 0)
        self.assertFalse(outcomes[0]["official_confirmed"])

    def test_audit_candidate_remains_unconfirmed(self):
        user = "カティサークの公式サイトを確認してください。"
        messages = self._messages(
            user,
            [
                {
                    "title": "カティサーク公式サイトはこちら",
                    "snippet": "あるブログが公式サイトを紹介しています。",
                    "url": "https://blog.example/cutty-sark",
                }
            ],
        )
        outcomes = self.filter._audit_search_results(messages, user, "test-candidate")
        self.assertEqual(outcomes[0]["status"], "ok")
        self.assertEqual(outcomes[0]["entity_status"], "ENTITY_FOUND")
        self.assertEqual(outcomes[0]["official_status"], "OFFICIAL_CANDIDATE")
        self.assertEqual(outcomes[0]["official_candidate_count"], 1)
        self.assertFalse(outcomes[0]["official_confirmed"])

    def test_ordinary_entity_search_keeps_legacy_ok_status(self):
        user = "カティサークの容量を確認してください。"
        messages = self._messages(
            user,
            [
                {
                    "title": "カティサークの容量",
                    "snippet": "商品情報。",
                    "url": "https://retailer.example/cutty-sark",
                }
            ],
            query="カティサーク 容量",
        )
        outcomes = self.filter._audit_search_results(messages, user, "test-ordinary")
        self.assertEqual(outcomes[0]["status"], "ok")
        self.assertFalse(outcomes[0]["official_intent"])

    def test_recovery_is_requested_for_unconfirmed_official_search(self):
        self.assertTrue(GUARD._official_search_outcome_needs_recovery({
            "status": "ok",
            "official_intent": True,
            "official_status": "OFFICIAL_UNCONFIRMED",
        }))
        self.assertTrue(GUARD._official_search_outcome_needs_recovery({
            "status": "NO_RESULTS",
            "official_intent": True,
            "official_status": "OFFICIAL_UNCONFIRMED",
        }))
        self.assertTrue(GUARD._official_search_outcome_needs_recovery({
            "status": "VIOLATION", "official_intent": False
        }))
        self.assertFalse(GUARD._official_search_outcome_needs_recovery({
            "status": "ok",
            "official_intent": True,
            "official_status": "OFFICIAL_CANDIDATE",
        }))
        self.assertFalse(GUARD._official_search_outcome_needs_recovery({
            "status": "ok", "official_intent": False
        }))

    def test_official_verification_note_is_idempotent_and_removed_for_other_queries(self):
        messages = [{"role": "system", "content": "base system"}]
        messages = self.filter._apply_official_site_note(
            messages, "カティサークの公式サイトを確認してください."
        )
        sys_text = messages[0]["content"]
        self.assertIn(GUARD.OFFICIAL_SITE_NOTE_START, sys_text)
        self.assertIn("OFFICIAL_CANDIDATE", sys_text)
        self.assertIn("do not", sys_text.lower())

        messages = self.filter._apply_official_site_note(
            messages, "カティサークの公式サイトを確認してください."
        )
        self.assertEqual(messages[0]["content"].count(GUARD.OFFICIAL_SITE_NOTE_START), 1)

        messages = self.filter._apply_official_site_note(
            messages, "カティサークの容量を確認してください."
        )
        self.assertNotIn(GUARD.OFFICIAL_SITE_NOTE_START, messages[0]["content"])

    def test_existing_numeric_conflict_correction_is_unchanged(self):
        repaired, info = GUARD.repair_query(
            "カティサークの仕様を確認してください。容量は700mlです。",
            "カティサーク 750ml 仕様",
        )
        self.assertIn("700ml", repaired)
        self.assertNotIn("750ml", repaired)
        self.assertIn(("750ml", "700ml"), info["replaced"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
