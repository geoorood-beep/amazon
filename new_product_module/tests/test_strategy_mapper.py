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
        self.product = ProductInfo.model_validate(
            json.loads((ROOT / "tests/fixtures/product.sop_6_2.json").read_text())
        )

    def _score(
        self,
        search_term: str = "5x8 vintage blue area rug",
        *,
        aba_rank: int = 25000,
        relevance_status: str = "READY",
        relevance_level: str = "HIGH",
        root_volume: float | None = 50000,
        top3_share: float | None = 0.70,
        query_count: int | None = 10,
        evidence_status: str = "READY",
    ) -> KeywordScore:
        return KeywordScore(
            asin="B0XXXX",
            order_stage="0-10单/日",
            search_term=search_term,
            clicks=35,
            orders=3,
            cvr=0.086,
            aba_rank=aba_rank,
            total_match_score=100,
            conclusion="建议投放",
            aba_stage_ok=True,
            relevance_evidence_status=relevance_status,
            relevance_level=relevance_level,
            root_monthly_search_volume=root_volume,
            root_top3_volume_share=top3_share,
            root_distinct_query_count=query_count,
            search_volume_months=["2026-05", "2026-06", "2026-07"],
            match_type_evidence_status=evidence_status,
        )

    def test_new_product_never_maps_to_exact_match(self) -> None:
        strategy = map_strategy(self._score(), self.product, self.rules)
        self.assertEqual(strategy["ad_type"], "词组")
        self.assertNotEqual(strategy["ad_type"], "精准")

    def test_architecture_builder_blocks_precise_type(self) -> None:
        rows, blocked = build_ad_architecture([self._score()], self.product, self.rules)
        self.assertTrue(rows)
        self.assertTrue(all(row.ad_type != "精准" for row in rows))
        self.assertEqual(blocked, [])

    def test_missing_match_type_config_does_not_use_rank_fallback(self) -> None:
        broken_rules = self.rules.model_copy(deep=True)
        broken_rules.strategy_rules.pop("match_type_routing", None)
        strategy = map_strategy(self._score(), self.product, broken_rules)
        self.assertFalse(strategy["supported"])
        self.assertIn("match_type_routing", strategy["reason"])

    def test_missing_relevance_and_volume_block_match_type(self) -> None:
        strategy = map_strategy(
            self._score(
                relevance_status="PENDING_SOURCE",
                root_volume=None,
                top3_share=None,
                query_count=None,
                evidence_status="RELEVANCE_PENDING+ROOT_SEARCH_VOLUME_PENDING",
            ),
            self.product,
            self.rules,
        )
        self.assertFalse(strategy["supported"])
        self.assertIn("相关性表未覆盖", strategy["reason"])

    def test_aba_rank_no_longer_decides_phrase_or_broad(self) -> None:
        phrase = map_strategy(
            self._score("washable area rug", aba_rank=250000, top3_share=0.72),
            self.product,
            self.rules,
        )
        broad = map_strategy(
            self._score("washable area rug", aba_rank=1000, top3_share=0.20),
            self.product,
            self.rules,
        )
        self.assertEqual(phrase["ad_types"], ["词组"])
        self.assertEqual(broad["ad_types"], ["广泛"])

    def test_middle_concentration_builds_separate_phrase_and_broad_groups(self) -> None:
        score = self._score("washable area rug", top3_share=0.45)
        strategy = map_strategy(score, self.product, self.rules)
        self.assertEqual(strategy["ad_types"], ["词组", "广泛"])
        rows, _ = build_ad_architecture([score], self.product, self.rules)
        self.assertEqual({row.ad_type for row in rows}, {"词组", "广泛"})

    def test_semantic_specificity_overrides_dispersion_after_demand_gate(self) -> None:
        strategy = map_strategy(self._score(top3_share=0.20), self.product, self.rules)
        self.assertEqual(strategy["ad_types"], ["词组"])
        self.assertIn("明确属性长尾", strategy["reason"])

    def test_root_volume_below_floor_is_not_independently_launched(self) -> None:
        strategy = map_strategy(
            self._score("washable area rug", root_volume=2999, top3_share=0.70),
            self.product,
            self.rules,
        )
        self.assertTrue(strategy["supported"])
        self.assertFalse(strategy["eligible"])
        self.assertIn("低于独立投放门", strategy["reason"])


if __name__ == "__main__":
    unittest.main()
