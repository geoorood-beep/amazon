from __future__ import annotations

import sys
import unittest
from pathlib import Path

from pydantic import ValidationError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.budget_calc import suggested_daily_budget  # noqa: E402
from src.rule_loader import load_rules  # noqa: E402
from src.schemas import ProductInfo  # noqa: E402


class BudgetCalcTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = load_rules(ROOT / "config/category_rules.example.yaml")

    def test_standard_budget_uses_rug_cpa_normal_upper_not_parent_order_target(self) -> None:
        product = ProductInfo(
            category="Rugs",
            order_target_daily=10,
            size_spec="5x7",
            rug_type="area_rug",
            analysis_threshold_profile="area_small",
        )
        budget, reasons = suggested_daily_budget(product, self.rules)
        self.assertEqual(budget, 22)
        self.assertTrue(any("按 1 单" in reason for reason in reasons))

    def test_explicit_per_group_order_target_multiplies_cpa_upper(self) -> None:
        product = ProductInfo(
            category="Rugs",
            order_target_daily=10,
            ad_group_order_target=2,
            size_spec="5x7",
            rug_type="area_rug",
            analysis_threshold_profile="area_small",
        )
        budget, reasons = suggested_daily_budget(product, self.rules)
        self.assertEqual(budget, 44)
        self.assertEqual(reasons, [])

    def test_nonpositive_per_group_order_target_is_rejected(self) -> None:
        for value in (-2, 0):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                ProductInfo(
                    category="Rugs",
                    order_target_daily=10,
                    ad_group_order_target=value,
                    size_spec="5x7",
                )


if __name__ == "__main__":
    unittest.main()
