"""Reconstructed extended query-repair coverage run against the fix9 candidate source.

Offline tests. No Open WebUI or network calls are made."""

import unittest
import importlib.util
from pathlib import Path

SOURCE = Path(__file__).with_name("guard0.8.26-fix9-effective-query-fetch-gate.py")
SPEC = importlib.util.spec_from_file_location("searchguard_fix9_ExtendedQueryRepairFix9CandidateTests", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load candidate source: {SOURCE}")
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)
repair_query = GUARD.repair_query


TARGET = "カティサーク"
FULL_PROMPT = (
    "カティサークの公式サイトを調べてください。"
    "説明文では「Open WebUI」という名前も出てきます。"
    "今回は検索のみ実行し、fetch_urlでページ本文を取得せず、"
    "検索結果のタイトルとURLを示してください。"
)


class ExtendedQueryRepairFix9CandidateTests(unittest.TestCase):
    def test_01_missing_japanese_target_is_added(self):
        repaired, info = repair_query("カティサークの公式サイトを調べてください。", "公式サイト")
        self.assertIn(TARGET, repaired)
        self.assertTrue(info["changed"])

    def test_02_existing_japanese_target_stays_unchanged(self):
        query = "カティサーク 公式サイト"
        repaired, info = repair_query("カティサークの公式サイトを調べてください。", query)
        self.assertEqual(repaired, query)
        self.assertFalse(info["changed"])

    def test_03_unrelated_quoted_webui_is_not_injected(self):
        repaired, info = repair_query(FULL_PROMPT, "Katarsu whisky brand official website")
        self.assertIn(TARGET, repaired)
        self.assertNotIn("Open WebUI", repaired)
        self.assertNotIn("URL", repaired)

    def test_04_explicit_target_marker_is_preserved(self):
        user = "今回の対象はカティサークです。説明文では「Open WebUI」という名前も出てきます。"
        repaired, info = repair_query(user, "Katarsu whisky brand official website")
        self.assertIn(TARGET, repaired)
        self.assertNotIn("Open WebUI", repaired)
        self.assertTrue(info["changed"])

    def test_05_explicit_example_quote_is_not_injected(self):
        user = "カティサークの公式サイトを調べてください。例えば「Open WebUI」という用語です。"
        repaired, info = repair_query(user, "Katarsu whisky brand official website")
        self.assertIn(TARGET, repaired)
        self.assertNotIn("Open WebUI", repaired)

    def test_06_unrelated_quote_before_target_does_not_win(self):
        user = "説明文では「Open WebUI」という名前も出てきますが、今回調べたいのはカティサークの公式サイトです。"
        repaired, info = repair_query(user, "Katarsu whisky brand official website")
        self.assertIn(TARGET, repaired)
        self.assertNotIn("Open WebUI", repaired)

    def test_07_parallel_targets_joined_by_to_are_kept(self):
        user = "カティサークとバランタインの公式サイトを調べてください。"
        repaired, info = repair_query(user, "公式サイト")
        self.assertIn("カティサーク", repaired)
        self.assertIn("バランタイン", repaired)

    def test_08_parallel_targets_joined_by_ya_are_kept(self):
        user = "カティサークやバランタインの公式サイトを調べてください。"
        repaired, info = repair_query(user, "公式サイト")
        self.assertIn("カティサーク", repaired)
        self.assertIn("バランタイン", repaired)

    def test_09_parallel_targets_joined_by_japanese_comma_are_kept(self):
        user = "カティサーク、バランタインの公式サイトを調べてください。"
        repaired, info = repair_query(user, "公式サイト")
        self.assertIn("カティサーク", repaired)
        self.assertIn("バランタイン", repaired)

    def test_10_generic_site_word_is_not_the_selected_missing_target(self):
        user = "カティサークの公式サイトを調べてください。"
        repaired, info = repair_query(user, "公式サイト")
        self.assertEqual(info["missing"], ["カティサーク"])
        self.assertNotIn("サイト", info["missing"])

    def test_11_quoted_japanese_target_is_preserved(self):
        user = "「カティサーク」の公式サイトを調べてください。"
        repaired, info = repair_query(user, "公式サイト")
        self.assertIn(TARGET, repaired)

    def test_12_halfwidth_katakana_target_is_normalized(self):
        user = "ｶﾃｨｻｰｸの公式サイトを調べてください。"
        repaired, info = repair_query(user, "公式サイト")
        self.assertIn(TARGET, repaired)

    def test_13_multitoken_uppercase_identifier_is_added(self):
        user = "RTX 2060の仕様を確認してください。"
        repaired, info = repair_query(user, "グラフィックカード 仕様")
        self.assertIn("RTX 2060", repaired)

    def test_14_existing_uppercase_identifier_does_not_cause_repair(self):
        user = "RTX 2060の仕様を確認してください。"
        query = "RTX 2060 仕様"
        repaired, info = repair_query(user, query)
        self.assertEqual(repaired, query)
        self.assertFalse(info["changed"])

    def test_15_full_live_prompt_correct_query_has_no_url_false_positive(self):
        query = "カティサーク 公式サイト"
        repaired, info = repair_query(FULL_PROMPT, query)
        self.assertEqual(repaired, query)
        self.assertNotIn("URL", repaired)
        self.assertFalse(info["changed"])

    def test_16_full_live_prompt_missing_target_adds_only_target(self):
        repaired, info = repair_query(FULL_PROMPT, "公式サイト")
        self.assertIn(TARGET, repaired)
        self.assertNotIn("URL", repaired)
        self.assertNotIn("Open WebUI", repaired)
        self.assertTrue(info["changed"])

    def test_17_volume_conflict_750ml_is_replaced_by_700ml(self):
        user = "カティサークの仕様を確認してください。容量は700mlです。"
        repaired, info = repair_query(user, "カティサーク 750ml 仕様")
        self.assertIn("700ml", repaired)
        self.assertNotIn("750ml", repaired)
        self.assertIn(("750ml", "700ml"), info["replaced"])

    def test_18_currency_conflict_2000yuan_is_replaced_by_2000yen(self):
        user = "カティサークの価格を確認してください。価格は2000円です。"
        repaired, info = repair_query(user, "カティサーク 2000元 価格")
        self.assertIn("2000円", repaired)
        self.assertNotIn("2000元", repaired)
        self.assertIn(("2000元", "2000円"), info["replaced"])

    def test_19_degree_conflict_43_is_replaced_by_40_degrees(self):
        user = "カティサークの公式サイト。アルコール度数は40度です。"
        repaired, info = repair_query(user, "カティサーク 43度 公式サイト")
        self.assertIn("40度", repaired)
        self.assertNotIn("43度", repaired)
        self.assertIn(("43度", "40度"), info["replaced"])

    def test_20_battery_conflict_is_replaced_without_url_injection(self):
        user = "RTX 2060の仕様を確認してください。バッテリー容量は2630mAhです。検索結果のタイトルとURLを示してください。"
        repaired, info = repair_query(user, "RTX 2060 2500mAh 仕様")
        self.assertIn("2630mAh", repaired)
        self.assertNotIn("2500mAh", repaired)
        self.assertNotIn("URL", repaired)
        self.assertIn(("2500mAh", "2630mAh"), info["replaced"])

    def test_21_exact_numeric_value_is_not_replaced(self):
        user = "カティサークの仕様を確認してください。容量は700mlです。"
        query = "カティサーク 700ml 仕様"
        repaired, info = repair_query(user, query)
        self.assertEqual(repaired, query)
        self.assertFalse(info["replaced"])
        self.assertFalse(info["changed"])

    def test_22_ambiguous_same_unit_values_are_not_auto_replaced(self):
        user = "カティサークの仕様を確認してください。容量は700mlまたは750mlです。"
        repaired, info = repair_query(user, "カティサーク 800ml 仕様")
        self.assertFalse(info["replaced"])
        self.assertIn("800ml", repaired)

    def test_23_standalone_numeric_ticker_is_preserved(self):
        user = "4755の終値を調べてください。"
        repaired, info = repair_query(user, "株価 終値")
        self.assertIn("4755", repaired)
        self.assertTrue(info["changed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
