from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.keyword_scoring import score_keywords  # noqa: E402
from src.architecture_builder import build_ad_architecture  # noqa: E402
from src.rule_loader import load_rules  # noqa: E402
from src.schemas import ProductInfo, StageMatchedKeyword  # noqa: E402


class KeywordScoringTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = load_rules(ROOT / "tests/fixtures/category_rules.sop_6_2_validation.yaml")
        self.product = ProductInfo.model_validate(json.loads((ROOT / "tests/fixtures/product.sop_6_2.json").read_text()))

    def test_sop_component_scores_are_preserved(self) -> None:
        rows = [
            StageMatchedKeyword(
                search_term="5x8 vintage blue area rug",
                clicks=35,
                orders=3,
                order_dates=["2026-06-01", "2026-06-02", "2026-06-03"],
                cvr=0.086,
                aba_rank=25000,
                pool_status="进入候选池",
                order_stage="0-10单/日",
                aba_stage_ok=True,
                aba_stage_status="ABA阶段适配",
                stage_min_match_score=90,
                stage_max_keyword_count=5,
            )
        ]
        scores, blocked = score_keywords(rows, self.product, self.rules)
        self.assertEqual(blocked, [])
        score = scores[0]
        self.assertEqual(score.transaction_data_score, 100)
        self.assertEqual(score.region_score, 100)
        self.assertEqual(score.spec_score, 100)
        self.assertEqual(score.style_score, 100)
        self.assertEqual(score.color_score, 100)
        self.assertEqual(score.total_match_score, 100)
        self.assertEqual(score.conclusion, "建议投放")

    def test_aba_out_of_range_stays_restricted_test(self) -> None:
        rows = [
            StageMatchedKeyword(
                search_term="large living room rug",
                clicks=22,
                orders=2,
                order_dates=["2026-06-01", "2026-06-02", "2026-06-03"],
                cvr=0.091,
                aba_rank=8000,
                pool_status="进入候选池",
                order_stage="0-10单/日",
                aba_stage_ok=False,
                aba_stage_status="ABA超出阶段范围",
                stage_min_match_score=90,
                stage_max_keyword_count=5,
            )
        ]
        scores, _ = score_keywords(rows, self.product, self.rules)
        self.assertEqual(scores[0].total_match_score, 87.5)
        self.assertEqual(scores[0].conclusion, "ABA超出阶段范围，受限测试")

    def test_explicit_wrong_size_is_hard_conflict_and_never_builds_an_ad_group(self) -> None:
        self.product.size_spec = "5x7"
        row = self._stage_row("3x5 washable area rug")

        scores, blocked = score_keywords([row], self.product, self.rules)
        self.assertTrue(scores[0].hard_conflict)
        self.assertEqual(scores[0].conclusion, "不建议投放")
        self.assertIn("尺寸硬冲突：目标尺寸 5x7，关键词尺寸 3x5", scores[0].attribute_conflicts)
        self.assertTrue(any("尺寸硬冲突" in item.reason for item in blocked))

        architecture, _ = build_ad_architecture(scores, self.product, self.rules)
        self.assertEqual(architecture, [])

    def test_reversed_equivalent_size_is_accepted(self) -> None:
        self.product.size_spec = "5x7"
        scores, _ = score_keywords([self._stage_row("7×5 vintage blue area rug")], self.product, self.rules)
        self.assertFalse(scores[0].hard_conflict)
        self.assertEqual(scores[0].conclusion, "建议投放")

    def test_explicit_color_conflict_is_hard_conflict(self) -> None:
        scores, _ = score_keywords([self._stage_row("5x8 vintage red area rug")], self.product, self.rules)
        self.assertTrue(scores[0].hard_conflict)
        self.assertEqual(scores[0].conclusion, "不建议投放")
        self.assertTrue(any(reason.startswith("颜色硬冲突") for reason in scores[0].attribute_conflicts))

    def _stage_row(self, search_term: str) -> StageMatchedKeyword:
        return StageMatchedKeyword(
            search_term=search_term,
            clicks=35,
            orders=3,
            order_dates=["2026-06-01", "2026-06-02", "2026-06-03"],
            cvr=0.086,
            aba_rank=25000,
            pool_status="进入候选池",
            order_stage="0-10单/日",
            aba_stage_ok=True,
            aba_stage_status="ABA阶段适配",
            stage_min_match_score=70,
            stage_max_keyword_count=5,
        )


if __name__ == "__main__":
    unittest.main()
