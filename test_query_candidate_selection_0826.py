"""Focused regression tests for SearchGuard 0.8.26-fix3 query candidate selection.

Run from this directory with:
    python -m unittest -v test_query_candidate_selection_0826.py

These tests target repair_query() and its audit-facing info["changed"]
result. They do not call Open WebUI, DDGS, or any network service.
"""

import unittest

from guard0826 import repair_query


TARGET = "カティサーク"
UNRELATED_QUOTED_TERM = "Open WebUI"
FULL_LIVE_PROMPT = (
    "カティサークの公式サイトを調べてください。"
    "説明文では「Open WebUI」という名前も出てきます。"
    "今回は検索のみ実行し、fetch_urlでページ本文を取得せず、"
    "検索結果のタイトルとURLを示してください。"
)


class QueryCandidateSelection0826Tests(unittest.TestCase):
    def test_implicit_japanese_target_is_not_replaced_by_unrelated_quote(self):
        user_text = (
            "カティサークの公式サイトを調べてください。"
            "説明文では「Open WebUI」という名前も出てきます。"
        )
        model_query = "Katarsu whisky brand official website"

        repaired, info = repair_query(user_text, model_query)

        self.assertIn(
            TARGET,
            repaired,
            "The user's Japanese target must be restored to the query.",
        )
        self.assertNotIn(
            UNRELATED_QUOTED_TERM,
            repaired,
            "An unrelated quoted English term must not be injected.",
        )
        self.assertTrue(info["changed"])

    def test_existing_japanese_target_does_not_trigger_false_audit_violation(self):
        user_text = (
            "カティサークの公式サイトを調べてください。"
            "説明文では「Open WebUI」という名前も出てきます。"
        )
        model_query = "カティサーク 公式サイト"

        repaired, info = repair_query(user_text, model_query)

        self.assertEqual(
            repaired,
            model_query,
            "A query that already contains the requested target must stay unchanged.",
        )
        self.assertFalse(
            info["changed"],
            "Unrelated quoted text must not make audit report a repair-worthy violation.",
        )

    def test_unrelated_quote_before_implicit_japanese_target_is_ignored(self):
        user_text = (
            "説明文では「Open WebUI」という名前も出てきますが、"
            "今回調べたいのはカティサークの公式サイトです。"
        )
        model_query = "Katarsu whisky brand official website"

        repaired, info = repair_query(user_text, model_query)

        self.assertIn(TARGET, repaired)
        self.assertNotIn(UNRELATED_QUOTED_TERM, repaired)
        self.assertTrue(info["changed"])

    def test_explicit_target_marker_preserves_japanese_target(self):
        user_text = (
            "今回の対象はカティサークです。"
            "説明文では「Open WebUI」という名前も出てきます。"
        )
        model_query = "Katarsu whisky brand official website"

        repaired, info = repair_query(user_text, model_query)

        self.assertIn(TARGET, repaired)
        self.assertNotIn(UNRELATED_QUOTED_TERM, repaired)
        self.assertTrue(info["changed"])

    def test_explicit_example_quote_is_not_injected(self):
        user_text = (
            "カティサークの公式サイトを調べてください。"
            "例えば「Open WebUI」という用語です。"
        )
        model_query = "Katarsu whisky brand official website"

        repaired, info = repair_query(user_text, model_query)

        self.assertIn(TARGET, repaired)
        self.assertNotIn(UNRELATED_QUOTED_TERM, repaired)
        self.assertTrue(info["changed"])


    def test_full_live_prompt_does_not_inject_url_when_target_is_present(self):
        model_query = "カティサーク 公式サイト"

        repaired, info = repair_query(FULL_LIVE_PROMPT, model_query)

        self.assertEqual(repaired, model_query)
        self.assertNotIn("URL", repaired)
        self.assertNotIn(UNRELATED_QUOTED_TERM, repaired)
        self.assertFalse(
            info["changed"],
            "Output-format instructions must not cause a false query repair.",
        )

    def test_full_live_prompt_repairs_missing_target_without_injecting_url(self):
        model_query = "公式サイト"

        repaired, info = repair_query(FULL_LIVE_PROMPT, model_query)

        self.assertIn(TARGET, repaired)
        self.assertNotIn("URL", repaired)
        self.assertNotIn(UNRELATED_QUOTED_TERM, repaired)
        self.assertTrue(info["changed"])


    def test_numeric_conflict_replacement_is_preserved_with_url_instruction(self):
        user_text = (
            "RTX 2060の仕様を確認してください。"
            "バッテリー容量は2630mAhです。"
            "検索結果のタイトルとURLを示してください。"
        )
        model_query = "RTX 2060 2500mAh 仕様"

        repaired, info = repair_query(user_text, model_query)

        self.assertIn("2630mAh", repaired)
        self.assertNotIn("2500mAh", repaired)
        self.assertNotIn("URL", repaired)
        self.assertTrue(info["changed"])
        self.assertTrue(info["replaced"])


    def test_distinct_targets_before_different_property_boundaries_are_both_preserved(self):
        user_text = (
            "Appleの公式サイトとSonyの価格を確認してください。"
            "検索結果のタイトルとURLを示してください。"
        )
        model_query = "公式サイト 価格"

        repaired, info = repair_query(user_text, model_query)

        self.assertIn(
            "Apple",
            repaired,
            "The first subject must remain a search-query candidate.",
        )
        self.assertIn(
            "Sony",
            repaired,
            "The second subject must not be lost after the first subject/property boundary.",
        )
        self.assertNotIn(
            "URL",
            repaired,
            "Output-format instructions must not become a search entity.",
        )
        self.assertTrue(info["changed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
