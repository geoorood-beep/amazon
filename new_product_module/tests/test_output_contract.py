from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cli import read_keywords, write_result  # noqa: E402
from src.pipeline import run_new_product_pipeline  # noqa: E402
from src.rule_loader import load_rules  # noqa: E402


class OutputContractTest(unittest.TestCase):
    def test_output_has_only_two_core_sheets_and_design_logic(self) -> None:
        product = json.loads((ROOT / "tests/fixtures/product.sop_6_2.json").read_text(encoding="utf-8"))
        keywords = read_keywords(ROOT / "tests/fixtures/keywords.sop_6_2.csv")
        rules = load_rules(ROOT / "tests/fixtures/category_rules.sop_6_2_validation.yaml")
        result = run_new_product_pipeline(product, keywords, rules)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.xlsx"
            write_result(result, output)
            workbook = load_workbook(output, data_only=True)

        self.assertEqual(workbook.sheetnames, ["ABA选词表", "新广告设置表"])
        values = [cell.value for row in workbook["ABA选词表"].iter_rows() for cell in row]
        self.assertIn("判断依据与设计逻辑", values)

    def test_single_high_traffic_keyword_uses_seven_part_name_with_rank(self) -> None:
        product = json.loads((ROOT / "tests/fixtures/product.sop_6_2.json").read_text(encoding="utf-8"))
        keywords = read_keywords(ROOT / "tests/fixtures/keywords.sop_6_2.csv")
        rules = load_rules(ROOT / "tests/fixtures/category_rules.sop_6_2_validation.yaml")
        result = run_new_product_pipeline(product, keywords, rules)

        name = result.ad_architecture[0].ad_group_name
        self.assertEqual(len(name.split("-")), 7)
        self.assertIn("(2.5w)", name)
        self.assertTrue(name.endswith("-lulu"))


if __name__ == "__main__":
    unittest.main()
