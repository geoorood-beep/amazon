from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cli import read_keywords  # noqa: E402
from src.pipeline import run_new_product_pipeline  # noqa: E402
from src.rule_loader import load_rules  # noqa: E402


class PipelineEndToEndTest(unittest.TestCase):
    def test_sop_6_2_examples_match_expected_output(self) -> None:
        product = json.loads((ROOT / "tests/fixtures/product.sop_6_2.json").read_text(encoding="utf-8"))
        keywords = read_keywords(ROOT / "tests/fixtures/keywords.sop_6_2.csv")
        rules = load_rules(ROOT / "tests/fixtures/category_rules.sop_6_2_validation.yaml")
        result = run_new_product_pipeline(product, keywords, rules)

        self.assertEqual(len(result.keyword_scoring_table), 2)
        first, second = result.keyword_scoring_table
        self.assertEqual(first.search_term, "5x8 vintage blue area rug")
        self.assertEqual(first.total_match_score, 100)
        self.assertEqual(first.conclusion, "建议投放")
        self.assertEqual(second.search_term, "modern large rug")
        self.assertEqual(second.total_match_score, 69.5)
        self.assertEqual(second.conclusion, "ABA超出阶段范围，受限测试")

    def test_null_thresholds_go_to_manual_confirmation(self) -> None:
        product = json.loads((ROOT / "tests/fixtures/product.sop_6_2.json").read_text(encoding="utf-8"))
        keywords = read_keywords(ROOT / "tests/fixtures/keywords.sop_6_2.csv")
        rules = load_rules(ROOT / "config/category_rules.example.yaml")
        result = run_new_product_pipeline(product, keywords, rules)

        self.assertFalse(result.keyword_scoring_table)
        self.assertTrue(any("min_click_sample" in item.reason for item in result.blocked_items))
        self.assertTrue(any("min_order_sample" in item.reason for item in result.blocked_items))


if __name__ == "__main__":
    unittest.main()
