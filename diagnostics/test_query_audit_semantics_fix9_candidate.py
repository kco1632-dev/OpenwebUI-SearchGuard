"""Reconstructed audit-semantics checks run against the fix9 candidate source.

Offline tests. No Open WebUI or network calls are made."""

import unittest

import importlib.util

SOURCE = Path(__file__).with_name("guard0.8.26-fix9-effective-query-fetch-gate.py")
SPEC = importlib.util.spec_from_file_location("searchguard_fix9_AuditSemanticsFix9CandidateTests", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load candidate source: {SOURCE}")
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)
repair_query = GUARD.repair_query


FULL_PROMPT = (
    "カティサークの公式サイトを調べてください。"
    "説明文では「Open WebUI」という名前も出てきます。"
    "今回は検索のみ実行し、fetch_urlでページ本文を取得せず、"
    "検索結果のタイトルとURLを示してください。"
)


def audit_status(info):
    return "VIOLATION" if info["changed"] else "ok"


class AuditSemanticsFix9CandidateTests(unittest.TestCase):
    def test_correct_target_and_unrelated_instruction_maps_to_ok(self):
        repaired, info = repair_query(FULL_PROMPT, "カティサーク 公式サイト")
        self.assertEqual(repaired, "カティサーク 公式サイト")
        self.assertEqual(audit_status(info), "ok")

    def test_missing_target_remains_a_violation(self):
        repaired, info = repair_query(FULL_PROMPT, "公式サイト")
        self.assertIn("カティサーク", repaired)
        self.assertEqual(audit_status(info), "VIOLATION")

    def test_numeric_conflict_remains_a_violation(self):
        user = "RTX 2060の仕様を確認してください。バッテリー容量は2630mAhです。検索結果のタイトルとURLを示してください。"
        repaired, info = repair_query(user, "RTX 2060 2500mAh 仕様")
        self.assertIn("2630mAh", repaired)
        self.assertTrue(info["replaced"])
        self.assertEqual(audit_status(info), "VIOLATION")

    def test_unrelated_example_does_not_create_false_violation(self):
        user = "カティサークの公式サイトを調べてください。説明文では「Open WebUI」という名前も出てきます。"
        repaired, info = repair_query(user, "カティサーク 公式サイト")
        self.assertEqual(repaired, "カティサーク 公式サイト")
        self.assertEqual(audit_status(info), "ok")


if __name__ == "__main__":
    unittest.main(verbosity=2)
