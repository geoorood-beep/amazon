from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.architecture_builder import build_ad_architecture  # noqa: E402
from src.rule_loader import load_rules  # noqa: E402
from src.schemas import KeywordScore, ProductInfo  # noqa: E402
from src.strategy_mapper import map_strategy  # noqa: E402


class StrategyMapperTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = load_rules(ROOT / "tests/fixtures/category_rules.sop_6_2_validation.yaml")
        self.product = ProductInfo.model_validate(json.loads((ROOT / "tests/fixtures/product.sop_6_2.json").read_text()))

    def test_new_product_never_maps_to_exact_match(self) -> None:
        score = KeywordScore(
            asin="B0XXXX",
            order_stage="0-10单/日",
            search_term="5x8 vintage blue area rug",
            clicks=35,
            orders=3,
            cvr=0.086,
            aba_rank=25000,
            total_match_score=100,
            conclusion="建议投放",
            aba_stage_ok=True,
        )
        strategy = map_strategy(score, self.product, self.rules)
        self.assertEqual(strategy["ad_type"], "词组")
        self.assertNotEqual(strategy["ad_type"], "精准")

    def test_architecture_builder_blocks_precise_type(self) -> None:
        score = KeywordScore(
            asin="B0XXXX",
            order_stage="0-10单/日",
            search_term="5x8 vintage blue area rug",
            clicks=35,
            orders=3,
            cvr=0.086,
            aba_rank=25000,
            total_match_score=100,
            conclusion="建议投放",
            aba_stage_ok=True,
        )
        rows, blocked = build_ad_architecture([score], self.product, self.rules)
        self.assertTrue(rows)
        self.assertTrue(all(row.ad_type != "精准" for row in rows))
        self.assertEqual(blocked, [])

    def test_missing_phrase_rank_threshold_does_not_use_code_fallback(self) -> None:
        score = KeywordScore(
            asin="B0XXXX",
            order_stage="0-10单/日",
            search_term="5x8 vintage blue area rug",
            clicks=35,
            orders=3,
            cvr=0.086,
            aba_rank=25000,
            total_match_score=100,
            conclusion="建议投放",
            aba_stage_ok=True,
        )
        broken_rules = self.rules.model_copy(deep=True)
        broken_rules.strategy_rules.pop("phrase_priority_aba_rank", None)
        strategy = map_strategy(score, self.product, broken_rules)
        self.assertFalse(strategy["supported"])
        self.assertIn("phrase_priority_aba_rank", strategy["reason"])


if __name__ == "__main__":
    unittest.main()
