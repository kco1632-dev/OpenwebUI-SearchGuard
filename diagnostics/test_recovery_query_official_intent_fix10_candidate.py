"""Offline regression tests for fix9 candidate compatibility with existing recovery-query intent behavior.

Run:
    python -m unittest -v diagnostics/test_recovery_query_official_intent_fix5.py

No Open WebUI, DDGS, or external web calls are made.
"""

import importlib.util
from pathlib import Path
import unittest


SOURCE = Path(__file__).with_name("guard0.8.26-fix10-recovery-query-purpose.py")
SPEC = importlib.util.spec_from_file_location("searchguard_fix9_recovery_intent", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load candidate source: {SOURCE}")
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


class Fix9CandidateRecoveryQueryRegressionTests(unittest.TestCase):
    def setUp(self):
        self.filter = GUARD.Filter()

    def recover(self, user_text, entity="カティサーク"):
        return self.filter._build_recovery_query(
            user_text=user_text,
            entity=entity,
            prev_query="unused baseline query",
        )

    def test_japanese_official_site_intent_survives_without_url_noise(self):
        user_text = (
            "カティサークの公式サイトURLをWeb検索で確認して、"
            "URLを1つだけ答えてください。"
        )
        self.assertEqual(
            self.recover(user_text),
            '"カティサーク" 公式サイト',
        )

    def test_japanese_official_homepage_intent_survives(self):
        self.assertEqual(
            self.recover("カティサークの公式ホームページを確認してください。"),
            '"カティサーク" 公式ホームページ',
        )

    def test_english_official_website_is_case_insensitive(self):
        self.assertEqual(
            GUARD._pick_purpose_term("Please check the Official Website."),
            "official website",
        )
        self.assertEqual(
            self.recover("Please check the Official Website.", entity="Cutty Sark"),
            '"Cutty Sark" official website',
        )

    def test_price_recovery_purpose_is_unchanged(self):
        self.assertEqual(
            self.recover("カティサークの価格を確認してください。"),
            '"カティサーク" 価格',
        )

    def test_numeric_attribute_is_preserved_in_recovery(self):
        user_text = (
            "RTX 2060の仕様を確認してください。"
            "バッテリー容量は2630mAhです。"
        )
        query = self.recover(user_text, entity="RTX 2060")
        self.assertIn('"RTX 2060"', query)
        self.assertIn("2630mAh", query)

    def test_numeric_conflict_repair_remains_active(self):
        user_text = "カティサークの仕様を確認してください。容量は700mlです。"
        repaired, info = GUARD.repair_query(
            user_text,
            "カティサーク 750ml 仕様",
        )
        self.assertIn("700ml", repaired)
        self.assertNotIn("750ml", repaired)
        self.assertIn(("750ml", "700ml"), info["replaced"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
