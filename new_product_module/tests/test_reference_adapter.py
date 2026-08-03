from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openpyxl import Workbook


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from src.reference_adapter import load_rug_keyword_evidence  # noqa: E402


class ReferenceAdapterTest(unittest.TestCase):
    def test_fixed_rug_sources_preserve_evidence_grain_and_conflicts(self) -> None:
        rows, issues = load_rug_keyword_evidence(
            PROJECT_ROOT / "reference/rug-aba",
            PROJECT_ROOT
            / "reference/category-history/rug/normalized/20260707_rug_historical_search_terms_normalized.xlsx",
        )

        self.assertTrue(rows)
        self.assertTrue(all(row["evidence_grain"] == "TARGETING_KEYWORD" for row in rows))
        self.assertTrue(all(row["aba_sources"] for row in rows))
        self.assertTrue(any(row["aba_conflict"] for row in rows))
        self.assertTrue(any(issue["code"] == "HISTORY_GRAIN_TARGETING_KEYWORD" for issue in issues))

    def test_duplicate_history_terms_are_aggregated_instead_of_overwritten(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            aba = temp / "aba.xlsx"
            history = temp / "history.xlsx"
            self._write_aba(aba, rank=100)
            self._write_history(
                history,
                [
                    ["Washable  Rug", 100, 10, 0.10, 10, "first.xlsx"],
                    ["washable rug", 1, 0, 0, 99, "second.xlsx"],
                ],
            )

            rows, issues = load_rug_keyword_evidence(aba, history)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["clicks"], 101)
            self.assertEqual(rows[0]["orders"], 10)
            self.assertAlmostEqual(rows[0]["cvr"], 10 / 101)
            self.assertEqual(rows[0]["cpa"], 10)
            self.assertEqual(rows[0]["source_files"], ["first.xlsx", "second.xlsx"])
            self.assertTrue(
                any(issue["code"] == "HISTORY_DUPLICATE_TERMS_AGGREGATED" for issue in issues)
            )

    def test_fractional_integer_metrics_are_rejected_without_truncation(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            aba = temp / "aba.xlsx"
            history = temp / "history.xlsx"
            self._write_aba(aba, rank=100.9)
            self._write_history(
                history,
                [["washable rug", 10, 1, 0.1, 10, "source.xlsx"]],
            )
            with self.assertRaisesRegex(ValueError, "不得截断小数"):
                load_rug_keyword_evidence(aba, history)

    @staticmethod
    def _write_aba(path: Path, rank: float) -> None:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "广告词库"
        sheet.append(["搜索词", "搜索量排名", "地毯类型", "推荐层级", "相关度等级", "合规状态", "广告状态"])
        sheet.append(["washable rug", rank, "area_rug", "P1", "高", "安全", "可投"])
        workbook.save(path)

    @staticmethod
    def _write_history(path: Path, rows: list[list[object]]) -> None:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "term_summary"
        sheet.append(["search_term", "clicks", "ad_orders", "cvr", "cpa", "source_files"])
        for row in rows:
            sheet.append(row)
        workbook.save(path)


if __name__ == "__main__":
    unittest.main()
