"""Test-first coverage for recovery-query topic intent and output-format noise.

These tests load the unchanged fix9 candidate. They are expected to expose
known gaps before a separate recovery-query implementation change is made.
No Open WebUI service or external search is called.
"""

import importlib.util
from pathlib import Path
import unittest


SOURCE = Path(__file__).with_name("guard0.8.26-fix10-recovery-query-purpose.py")
SPEC = importlib.util.spec_from_file_location("searchguard_fix10_recovery_purpose_baseline", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load candidate source: {SOURCE}")
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


class RecoveryQueryPurposeFix10Tests(unittest.TestCase):
    def setUp(self):
        self.filter = GUARD.Filter()

    def recover(self, user_text):
        return self.filter._build_recovery_query(
            user_text=user_text,
            entity="カティサーク",
            prev_query='"カティサーク" スコッチウイスキー 味 種類 飲み方',
        )

    def test_single_topic_after_about_marker_is_preserved(self):
        query = self.recover(
            "カティサークについて、味を調べてください。参照URLを示してください。"
        )
        self.assertIn('"カティサーク"', query)
        self.assertIn("味", query)

    def test_multiple_requested_topics_survive_recovery(self):
        query = self.recover(
            "カティサークについて、味・種類・飲み方を調べて、参照URLを示してください。"
        )
        self.assertIn('"カティサーク"', query)
        for topic in ("味", "種類", "飲み方"):
            with self.subTest(topic=topic):
                self.assertIn(topic, query)

    def test_page_as_output_format_word_is_not_a_search_extra(self):
        query = self.recover(
            "カティサークについて、味・種類・飲み方を調べて、参照URLとページを示してください。"
        )
        self.assertNotIn("ページ", query)


if __name__ == "__main__":
    unittest.main(verbosity=2)
