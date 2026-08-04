from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.candidate_pool import build_candidate_pool  # noqa: E402
from src.rule_loader import load_rules  # noqa: E402
from src.schemas import HistoricalKeyword  # noqa: E402


class CandidatePoolTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = load_rules(ROOT / "tests/fixtures/category_rules.sop_6_2_validation.yaml")

    def test_boundary_values_enter_candidate_pool(self) -> None:
        rows = [
            HistoricalKeyword(
                search_term="boundary",
                clicks=20,
                orders=2,
                order_dates=["2026-06-01", "2026-06-02", "2026-06-03"],
                cvr=0.1,
                aba_rank=25000,
            )
        ]
        candidates, blocked = build_candidate_pool(rows, self.rules, "area_rug")
        self.assertEqual(blocked, [])
        self.assertEqual(candidates[0].pool_status, "进入候选池")

    def test_clicks_just_below_threshold_continue_observation(self) -> None:
        rows = [
            HistoricalKeyword(
                search_term="low clicks",
                clicks=19,
                orders=2,
                order_dates=["2026-06-01", "2026-06-02", "2026-06-03"],
                cvr=0.1,
                aba_rank=25000,
            )
        ]
        candidates, blocked = build_candidate_pool(rows, self.rules, "area_rug")
        self.assertEqual(candidates[0].pool_status, "继续观察")
        self.assertEqual(blocked[0].identifier, "low clicks")

    def test_orders_just_below_threshold_are_accidental_candidate(self) -> None:
        rows = [
            HistoricalKeyword(
                search_term="low orders",
                clicks=20,
                orders=1,
                order_dates=["2026-06-01", "2026-06-02", "2026-06-03"],
                cvr=0.05,
                aba_rank=25000,
            )
        ]
        candidates, _ = build_candidate_pool(rows, self.rules, "area_rug")
        self.assertEqual(candidates[0].pool_status, "偶然成交候选")

    def test_aba_cold_start_does_not_require_historical_click_thresholds(self) -> None:
        rules = load_rules(ROOT / "config/category_rules.example.yaml")
        rows = [
            HistoricalKeyword(
                search_term="runner rug 2x8",
                clicks=0,
                orders=0,
                cvr=0,
                aba_rank=171861,
                evidence_grain="ABA_COLD_START",
                aba_rug_types=["长条"],
                compliance_status="安全",
                ad_status="可投",
            )
        ]
        candidates, _ = build_candidate_pool(rows, rules, "runner")
        self.assertEqual(candidates[0].pool_status, "进入候选池")
        self.assertTrue(candidates[0].needs_review)


if __name__ == "__main__":
    unittest.main()
