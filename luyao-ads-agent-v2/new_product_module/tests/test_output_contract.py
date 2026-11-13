from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cli import read_keywords, write_result, write_results  # noqa: E402
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
        keyword_headers = {cell.value for cell in workbook["ABA选词表"][1]}
        self.assertTrue({
            "ASIN",
            "ABA等级",
            "规范词根",
            "来源 ABA 文件",
            "来源 sheet",
            "ASIN相关性证据状态",
            "词根月搜索量",
            "词根Top3搜索量占比",
            "匹配方式证据状态",
            "产品匹配点",
            "投放角色",
            "建议匹配方式",
        }.issubset(keyword_headers))
        architecture_headers = {cell.value for cell in workbook["新广告设置表"][1]}
        self.assertTrue({"Campaign 名称", "广告组名称", "结构模式", "操作", "匹配方式", "投放角色/主投", "精准否定词", "判断依据"}.issubset(architecture_headers))
        values = [cell.value for row in workbook["ABA选词表"].iter_rows() for cell in row]
        self.assertIn("判断依据与设计逻辑", values)

    def test_multi_product_output_keeps_two_sheets_and_asin_traceability(self) -> None:
        product = json.loads((ROOT / "tests/fixtures/product.sop_6_2.json").read_text(encoding="utf-8"))
        product_two = {**product, "asin": "B0XYZ98765", "sku": "RUG-SECOND"}
        keywords = read_keywords(ROOT / "tests/fixtures/keywords.sop_6_2.csv")
        rules = load_rules(ROOT / "tests/fixtures/category_rules.sop_6_2_validation.yaml")
        results = [
            run_new_product_pipeline(product, keywords, rules),
            run_new_product_pipeline(product_two, keywords, rules),
        ]

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "multi-result.xlsx"
            write_results(results, output)
            workbook = load_workbook(output, data_only=True)

        self.assertEqual(workbook.sheetnames, ["ABA选词表", "新广告设置表"])
        architecture_asins = {cell.value for cell in workbook["新广告设置表"]["C"][1:]}
        self.assertTrue({product["asin"], product_two["asin"]}.issubset(architecture_asins))
        keyword_asins = {cell.value for cell in workbook["ABA选词表"]["A"][1:]}
        self.assertTrue({product["asin"], product_two["asin"]}.issubset(keyword_asins))

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
