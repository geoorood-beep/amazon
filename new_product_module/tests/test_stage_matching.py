from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.schemas import CandidateKeyword  # noqa: E402
from src.rule_loader import load_rules  # noqa: E402
from src.stage_matching import match_stage  # noqa: E402


class StageMatchingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = load_rules(ROOT / "tests/fixtures/category_rules.sop_6_2_validation.yaml")

    def _candidate(self, term: str, rank: int) -> CandidateKeyword:
        return CandidateKeyword(
            search_term=term,
            clicks=20,
            orders=2,
            order_dates=["2026-06-01", "2026-06-02", "2026-06-03"],
            cvr=0.1,
            aba_rank=rank,
            pool_status="进入候选池",
        )

    def test_aba_range_boundaries_are_inclusive(self) -> None:
        rows, blocked = match_stage(
            [self._candidate("lower", 25000), self._candidate("upper", 500000)],
            self.rules,
            "area_rug",
            "0-10单/日",
        )
        self.assertEqual(blocked, [])
        self.assertTrue(all(row.aba_stage_ok for row in rows))

    def test_rank_below_stage_range_is_restricted(self) -> None:
        rows, _ = match_stage([self._candidate("too high traffic", 24999)], self.rules, "area_rug", "0-10单/日")
        self.assertFalse(rows[0].aba_stage_ok)
        self.assertEqual(rows[0].aba_stage_status, "ABA超出阶段范围")


if __name__ == "__main__":
    unittest.main()
