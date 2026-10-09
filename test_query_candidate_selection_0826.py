"""Focused regression tests for SearchGuard 0.8.26 query candidate selection.

Run from this directory with:
    python -m unittest -v test_query_candidate_selection_0826.py

These tests target repair_query() and its audit-facing info["changed"]
result. They do not call Open WebUI, DDGS, or any network service.
"""

import unittest

from guard0826 import repair_query


TARGET = "カティサーク"
UNRELATED_QUOTED_TERM = "Open WebUI"


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
