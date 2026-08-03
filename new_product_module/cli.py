from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import run_new_product_pipeline  # noqa: E402
from src.reference_adapter import load_rug_keyword_evidence  # noqa: E402
from src.rule_loader import load_rules  # noqa: E402
from src.schemas import BlockedItem  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="AI广告智能体新品推广模块")
    parser.add_argument("--product", required=True, help="产品基础信息 JSON 文件")
    parser.add_argument("--keywords", help="兼容模式：已标准化并含 ABA 排名的关键词 CSV/XLSX")
    parser.add_argument("--aba", help="Rug ABA 工作簿或目录；只读取广告词库 sheet")
    parser.add_argument("--history", help="Rug 历史效果词标准化工作簿")
    parser.add_argument("--rules", required=True, help="类目规则库 YAML/JSON 文件")
    parser.add_argument("--output", required=True, help="输出 Excel 文件")
    args = parser.parse_args()

    product = json.loads(Path(args.product).read_text(encoding="utf-8"))
    adapter_issues: list[dict[str, str]] = []
    if args.aba or args.history:
        if not args.aba or not args.history:
            parser.error("--aba 与 --history 必须同时提供")
        keywords, adapter_issues = load_rug_keyword_evidence(args.aba, args.history)
    elif args.keywords:
        keywords = read_keywords(args.keywords)
    else:
        parser.error("必须提供 --keywords，或同时提供 --aba 与 --history")
    rules = load_rules(args.rules)
    result = run_new_product_pipeline(product, keywords, rules)
    for issue in adapter_issues:
        result.blocked_items.append(
            BlockedItem(
                item_type="data_source",
                identifier=issue["code"],
                source_step="reference_adapter",
                reason=issue["message"],
            )
        )
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
        required = {"search_term", "clicks", "orders", "order_dates", "cvr", "aba_rank"}
        sheet = None
        for candidate in workbook.worksheets:
            headers = {str(cell.value or "").strip() for cell in candidate[1]}
            if required.issubset(headers):
                sheet = candidate
                break
        if sheet is None:
            if "广告词库" in workbook.sheetnames:
                raise ValueError("检测到原始 ABA 工作簿；请使用 --aba 与 --history，不要把 ABA 当作历史搜索词")
            raise ValueError(f"{path.name} 没有包含标准关键词字段的 sheet：{sorted(required)}")
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
    keyword_sheet = workbook.active
    keyword_sheet.title = "ABA选词表"
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
            "需人工确认",
            "原因",
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
                "是" if row.needs_review else "否",
                "；".join(row.reasons),
            ]
            for row in result.keyword_scoring_table
        ],
    )

    logic_row = keyword_sheet.max_row + 2
    keyword_sheet.cell(logic_row, 1, "判断依据与设计逻辑")
    keyword_sheet.cell(logic_row, 1).font = Font(bold=True)
    keyword_sheet.merge_cells(start_row=logic_row + 1, start_column=1, end_row=logic_row + 1, end_column=16)
    keyword_sheet.cell(logic_row + 1, 1, _design_logic(result))
    keyword_sheet.cell(logic_row + 1, 1).alignment = Alignment(wrap_text=True, vertical="top")
    keyword_sheet.row_dimensions[logic_row + 1].height = 105

    ad_sheet = workbook.create_sheet("新广告设置表")
    _append_rows(
        ad_sheet,
        [
            "广告组名称",
            "ASIN",
            "类型",
            "预算",
            "Bid",
            "投放策略",
            "TOS/ROS/PP",
            "投放词",
            "判断依据",
            "需人工确认",
            "原因",
        ],
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
                "是" if row.needs_review else "否",
                "；".join(row.reasons),
            ]
            for row in result.ad_architecture
        ],
    )

    for sheet in workbook.worksheets:
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1F4E78")
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
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


def _design_logic(result) -> str:
    blocked_reasons = []
    for item in result.blocked_items:
        text = f"{item.identifier}：{item.reason}"
        if text not in blocked_reasons:
            blocked_reasons.append(text)
    missing = "；".join(blocked_reasons[:12]) or "无。"
    return (
        f"【ABA/产品属性】已按目标尺寸识别为 {result.product_profile.rug_type or '待确认'}，"
        "关键词需先通过尺寸、类型、形状、材质、颜色、风格和动物图案硬冲突检查。"
        f"【历史数据】{result.product_profile.core_diagnosis} 数据置信度为{result.product_profile.data_confidence}。"
        "【用户固定规则】新品只生成 Phrase、关键词 Broad 或 Auto Close 的人工建议；"
        "ABA 排名不高于 3 万的词单词单组，3 万至 10 万的同入口词每组 2-5 个；"
        "广告组使用七段命名，标准最低日预算来自对应 Rug 类型 CPA 正常线上限，"
        "未确认 Bid、广告位或圆形阈值不补造。新品阶段不建 Exact、Auto Loose 或 ASIN 定向。"
        f"【缺失数据】{missing}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
