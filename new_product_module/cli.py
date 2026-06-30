from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import run_new_product_pipeline  # noqa: E402
from src.rule_loader import load_rules  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="AI广告智能体新品推广模块")
    parser.add_argument("--product", required=True, help="产品基础信息 JSON 文件")
    parser.add_argument("--keywords", required=True, help="历史成交搜索词 CSV/XLSX 文件")
    parser.add_argument("--rules", required=True, help="类目规则库 YAML/JSON 文件")
    parser.add_argument("--output", required=True, help="输出 Excel 文件")
    args = parser.parse_args()

    product = json.loads(Path(args.product).read_text(encoding="utf-8"))
    keywords = read_keywords(args.keywords)
    rules = load_rules(args.rules)
    result = run_new_product_pipeline(product, keywords, rules)
    write_result(result, args.output)
    print(f"wrote {args.output}")
    return 0


def read_keywords(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    if path.suffix.lower() in {".xlsx", ".xlsm"}:
        workbook = load_workbook(path, data_only=True)
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [str(cell).strip() for cell in rows[0]]
        records = []
        for row in rows[1:]:
            if not any(cell is not None and str(cell).strip() for cell in row):
                continue
            records.append({headers[index]: row[index] if index < len(row) else None for index in range(len(headers))})
        return records
    raise ValueError(f"Unsupported keyword file type: {path.suffix}")


def write_result(result, path: str | Path) -> None:
    workbook = Workbook()
    product_sheet = workbook.active
    product_sheet.title = "产品策略摘要"
    _append_rows(
        product_sheet,
        ["ASIN/SKU", "当前订单目标", "核心诊断", "总体策略", "数据置信度"],
        [
            [
                result.product_profile.asin_sku,
                result.product_profile.current_order_target,
                result.product_profile.core_diagnosis,
                result.product_profile.overall_strategy,
                result.product_profile.data_confidence,
            ]
        ],
    )

    keyword_sheet = workbook.create_sheet("订单阶段关键词选择结果")
    _append_rows(
        keyword_sheet,
        [
            "ASIN",
            "订单阶段",
            "关键词",
            "历史点击",
            "历史订单",
            "历史CVR",
            "ABA排名",
            "成交数据分",
            "区域分",
            "规格分",
            "风格分",
            "颜色分",
            "总匹配度",
            "结论",
        ],
        [
            [
                row.asin,
                row.order_stage,
                row.search_term,
                row.clicks,
                row.orders,
                _format_percent(row.cvr),
                row.aba_rank,
                row.transaction_data_score,
                row.region_score,
                row.spec_score,
                row.style_score,
                row.color_score,
                row.total_match_score,
                row.conclusion,
            ]
            for row in result.keyword_scoring_table
        ],
    )

    ad_sheet = workbook.create_sheet("新广告如何设置")
    _append_rows(
        ad_sheet,
        ["广告组名称", "ASIN", "类型", "预算", "Bid", "投放策略", "TOS/ROS/PP", "投放词", "判断依据"],
        [
            [
                row.ad_group_name,
                row.asin,
                row.ad_type,
                row.budget,
                row.bid,
                row.strategy,
                row.placement,
                row.keyword,
                row.rationale,
            ]
            for row in result.ad_architecture
        ],
    )

    blocked_sheet = workbook.create_sheet("待人工确认")
    _append_rows(
        blocked_sheet,
        ["类型", "对象", "来源步骤", "原因", "数据"],
        [
            [
                row.item_type,
                row.identifier,
                row.source_step,
                row.reason,
                json.dumps(row.data, ensure_ascii=False, sort_keys=True),
            ]
            for row in result.blocked_items
        ],
    )

    for sheet in workbook.worksheets:
        for column_cells in sheet.columns:
            max_length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
            sheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_length + 2, 12), 60)
        sheet.freeze_panes = "A2"

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output)


def _append_rows(sheet, header: list[str], rows: list[list[Any]]) -> None:
    sheet.append(header)
    for row in rows:
        sheet.append(row)


def _format_percent(value: float | None) -> str | None:
    if value is None:
        return None
    percent = round(value * 100, 2)
    if float(percent).is_integer():
        return f"{int(percent)}%"
    return f"{percent}%"


if __name__ == "__main__":
    raise SystemExit(main())
