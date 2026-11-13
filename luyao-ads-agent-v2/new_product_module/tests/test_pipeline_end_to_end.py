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
    def test_non_rug_category_is_blocked_before_rug_classification(self) -> None:
        rules = load_rules(ROOT / "tests/fixtures/category_rules.sop_6_2_validation.yaml")
        result = run_new_product_pipeline(
            {
                "category": "office_chair",
                "order_target_daily": 10,
                "size_spec": "5x7",
            },
            [],
            rules,
        )
        self.assertIsNone(result.product_profile.rug_type)
        self.assertTrue(any(item.source_step == "scope_gate" for item in result.blocked_items))

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
        self.assertEqual(second.search_term, "large living room rug")
        self.assertEqual(second.total_match_score, 87.5)
        self.assertEqual(second.conclusion, "ABA超出阶段范围，受限测试")

    def test_wrong_size_keyword_is_excluded_from_architecture(self) -> None:
        product = json.loads((ROOT / "tests/fixtures/product.sop_6_2.json").read_text(encoding="utf-8"))
        product["size_spec"] = "5x7"
        rules = load_rules(ROOT / "tests/fixtures/category_rules.sop_6_2_validation.yaml")
        keywords = [
            {
                "search_term": "3x5 washable area rug",
                "clicks": 35,
                "orders": 3,
                "order_dates": ["2026-06-01", "2026-06-03", "2026-06-05"],
                "cvr": 0.086,
                "aba_rank": 25000,
            }
        ]

        result = run_new_product_pipeline(product, keywords, rules)
        self.assertEqual(result.keyword_scoring_table[0].conclusion, "不建议投放")
        self.assertEqual(result.ad_architecture, [])
        self.assertTrue(any("尺寸硬冲突" in item.reason for item in result.blocked_items))

    def test_null_thresholds_go_to_manual_confirmation(self) -> None:
        product = json.loads((ROOT / "tests/fixtures/product.sop_6_2.json").read_text(encoding="utf-8"))
        keywords = read_keywords(ROOT / "tests/fixtures/keywords.sop_6_2.csv")
        rules = load_rules(ROOT / "config/category_rules.example.yaml")
        result = run_new_product_pipeline(product, keywords, rules)

        self.assertFalse(result.keyword_scoring_table)
        self.assertTrue(any("min_click_sample" in item.reason for item in result.blocked_items))
        self.assertTrue(any("min_order_sample" in item.reason for item in result.blocked_items))

    def test_pipeline_uses_size_inferred_runner_type(self) -> None:
        product = json.loads((ROOT / "tests/fixtures/product.sop_6_2.json").read_text(encoding="utf-8"))
        product["size_spec"] = "2x6"
        product["rug_type"] = "area_rug"
        rules = load_rules(ROOT / "tests/fixtures/category_rules.sop_6_2_validation.yaml")
        rules.rug_type_baselines["runner"] = rules.rug_type_baselines["area_rug"].model_copy(deep=True)
        keywords = [
            {
                "search_term": "2x6 vintage blue runner rug",
                "clicks": 30,
                "orders": 3,
                "order_dates": ["2026-06-01", "2026-06-03", "2026-06-05"],
                "cvr": 0.10,
                "aba_rank": 60000,
            }
        ]

        result = run_new_product_pipeline(product, keywords, rules)
        self.assertEqual(result.product_profile.rug_type, "runner")
        self.assertEqual(result.product_profile.analysis_threshold_profile, "runner")
        self.assertTrue(any("人工地毯类型" in item.reason for item in result.blocked_items))


if __name__ == "__main__":
    unittest.main()
