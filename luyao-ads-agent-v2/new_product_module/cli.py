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
from src.match_type_evidence import (  # noqa: E402
    enrich_keyword_evidence,
    load_match_type_evidence,
)
from src.reference_adapter import load_rug_keyword_evidence  # noqa: E402
from src.rule_loader import load_rules  # noqa: E402
from src.schemas import BlockedItem  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="AI广告智能体广告架构设计模块")
    parser.add_argument("--product", required=True, help="产品基础信息 JSON 文件")
    parser.add_argument("--keywords", help="兼容模式：已标准化并含 ABA 排名的关键词 CSV/XLSX")
    parser.add_argument("--aba", help="Rug ABA 工作簿或目录；只读取广告词库 sheet")
    parser.add_argument("--history", help="Rug 历史效果词标准化工作簿")
    parser.add_argument("--relevance", help="ASIN级相关性表或目录；缺失时阻断Phrase/Broad判定")
    parser.add_argument("--search-volume", help="搜索词月搜索量表或目录；必须包含规范词根和月份")
    parser.add_argument("--rules", required=True, help="类目规则库 YAML/JSON 文件")
    parser.add_argument("--output", required=True, help="输出 Excel 文件")
    args = parser.parse_args()

    payload = json.loads(Path(args.product).read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("products"), list):
        products = payload["products"]
    elif isinstance(payload, dict):
        products = [payload]
    else:
        parser.error("--product 必须是产品对象或包含 products 数组的对象")
    if not products:
        parser.error("产品清单为空")
    adapter_issues: list[dict[str, str]] = []
    rules = load_rules(args.rules)
    cold_start_config = rules.strategy_rules.get("aba_cold_start", {}) or {}
    cold_start_enabled = cold_start_config.get("status") == "CANDIDATE_ONLY"
    if args.aba or args.history:
        if not args.aba or not args.history:
            parser.error("--aba 与 --history 必须同时提供")
        keywords, adapter_issues = load_rug_keyword_evidence(
            args.aba,
            args.history,
            include_aba_cold_start=cold_start_enabled,
        )
    elif args.keywords:
        keywords = read_keywords(args.keywords)
    else:
        parser.error("必须提供 --keywords，或同时提供 --aba 与 --history")
    match_type_evidence = load_match_type_evidence(args.relevance, args.search_volume)
    results = []
    for product in products:
        product_keywords = enrich_keyword_evidence(
            keywords,
            asin=product.get("asin") or product.get("sku"),
            marketplace=product.get("marketplace") or rules.site,
            evidence=match_type_evidence,
        )
        result = run_new_product_pipeline(product, product_keywords, rules)
        for issue in [*adapter_issues, *match_type_evidence.issues]:
            result.blocked_items.append(
                BlockedItem(
                    item_type="data_source",
                    identifier=issue["code"],
                    source_step="reference_adapter",
                    reason=issue["message"],
                )
            )
        results.append(result)
    write_results(results, args.output)
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
    write_results([result], path)


def write_results(results, path: str | Path) -> None:
    if not results:
        raise ValueError("至少需要一个广告架构结果")
    workbook = Workbook()
    keyword_sheet = workbook.active
    keyword_sheet.title = "ABA选词表"
    keyword_headers = [
        "ASIN",
        "ABA等级",
        "机会类型",
        "综合分",
        "搜索词",
        "规范词根",
        "ABA排名",
        "匹配 ABA 词",
        "来源 ABA 文件",
        "来源 sheet",
        "类目判断",
        "Rug 类型",
        "目标推广尺寸",
        "对应标签",
        "推荐层级",
        "ABA相关度",
        "ASIN相关性证据状态",
        "ASIN相关性等级",
        "ASIN相关性来源",
        "完整词月搜索量",
        "词根月搜索量",
        "词根Top3搜索量占比",
        "词根有效查询数",
        "搜索量数据月",
        "搜索量来源",
        "匹配方式证据状态",
        "合规状态",
        "广告用途",
        "产品匹配点",
        "属性冲突检查",
        "建议动作",
        "投放角色",
        "主投",
        "建议匹配方式",
        "精准否定",
        "原因",
    ]
    keyword_rows: list[list[Any]] = []
    for result in results:
        asin = result.product_profile.asin_sku
        keyword_rows.extend([
            [
                asin,
                row.comprehensive_priority or "待ABA映射",
                row.detailed_category or "历史效果词与ABA交集",
                row.total_match_score,
                row.search_term,
                row.normalized_root or "待词根映射",
                row.aba_rank,
                row.search_term,
                "；".join(row.aba_sources),
                "广告词库",
                row.category_judgment or "Rug",
                "；".join(row.aba_rug_types) or result.product_profile.rug_type or "待确认",
                result.product_profile.target_size or "待确认",
                "；".join(row.aba_tags) or "待标签映射",
                row.recommendation_tier or "待确认",
                "；".join(row.aba_relevance_levels) or "待确认",
                row.relevance_evidence_status,
                row.relevance_level or "待补数据",
                "；".join(row.relevance_source_files),
                row.monthly_search_volume,
                row.root_monthly_search_volume,
                _format_percent(row.root_top3_volume_share),
                row.root_distinct_query_count,
                "；".join(row.search_volume_months),
                "；".join(row.search_volume_source_files),
                row.match_type_evidence_status,
                row.compliance_status or "待确认",
                row.advertising_use or "新品验证",
                _product_match_points(row),
                "待人工确认" if row.needs_review else "通过",
                _candidate_action(row.search_term, result),
                _candidate_role(row.search_term, result),
                "是" if "Phrase" in _match_type_for_term(row.search_term, result) else "否",
                _match_type_for_term(row.search_term, result),
                "否",
                "；".join(dict.fromkeys([*row.reasons, row.aba_judgment_reason or ""])).strip("；"),
            ]
            for row in result.keyword_scoring_table
            if row.conclusion == "建议投放" and not row.hard_conflict
        ])
    _append_rows(
        keyword_sheet,
        keyword_headers,
        keyword_rows,
    )

    for result in results:
        logic_row = keyword_sheet.max_row + 2
        keyword_sheet.cell(logic_row, 1, "判断依据与设计逻辑")
        keyword_sheet.cell(logic_row, 1).font = Font(bold=True)
        keyword_sheet.cell(logic_row, 2, result.product_profile.asin_sku)
        keyword_sheet.cell(logic_row, 2).font = Font(bold=True, color="1F5F2A")
        keyword_sheet.merge_cells(
            start_row=logic_row + 1,
            start_column=1,
            end_row=logic_row + 1,
            end_column=len(keyword_headers),
        )
        keyword_sheet.cell(logic_row + 1, 1, _design_logic(result))
        keyword_sheet.cell(logic_row + 1, 1).alignment = Alignment(wrap_text=True, vertical="top")
        keyword_sheet.row_dimensions[logic_row + 1].height = 105

    ad_sheet = workbook.create_sheet("新广告设置表")
    _append_rows(
        ad_sheet,
        [
            "Campaign 名称",
            "广告组名称",
            "ASIN",
            "结构模式",
            "操作",
            "匹配方式",
            "预算",
            "Bid",
            "投放策略",
            "TOS/ROS/PP",
            "投放角色/主投",
            "投放词/词根/类目",
            "精准否定词",
            "判断依据",
            "需人工确认",
            "原因",
        ],
        [row for result in results for row in _architecture_output_rows(result)],
    )

    for sheet in workbook.worksheets:
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1F5F2A")
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


def _match_type_for_term(term: str, result) -> str:
    values = []
    for row in result.ad_architecture:
        terms = [item.strip() for item in str(row.keyword).replace("，", "、").split("、") if item.strip()]
        if term not in terms:
            continue
        mapped = {"词组": "Phrase", "广泛": "Broad"}.get(row.ad_type, row.ad_type)
        if mapped not in values:
            values.append(mapped)
    return " + ".join(values) or "MATCH_TYPE_DATA_PENDING"


def _candidate_action(term: str, result) -> str:
    match_type = _match_type_for_term(term, result)
    return "进入广告架构" if match_type != "MATCH_TYPE_DATA_PENDING" else "待补相关性与搜索量数据"


def _candidate_role(term: str, result) -> str:
    match_type = _match_type_for_term(term, result)
    if "Phrase" in match_type and "Broad" in match_type:
        return "Phrase承接 + Broad探索"
    if "Phrase" in match_type:
        return "Phrase承接"
    if "Broad" in match_type:
        return "Broad探索"
    return "候选 / 待补数据"


def _architecture_output_rows(result) -> list[list[Any]]:
    if result.ad_architecture:
        return [
            [
                "待人工命名",
                row.ad_group_name,
                row.asin,
                "SINGLE_ASIN_CONTROL",
                "新增广告组",
                row.ad_type,
                row.budget,
                row.bid if row.bid is not None else "待人工配置",
                row.strategy,
                row.placement or "待人工配置",
                _architecture_role(row, result),
                row.keyword,
                "",
                row.rationale,
                "是" if row.needs_review else "否",
                "；".join(row.reasons),
            ]
            for row in result.ad_architecture
        ]
    reason_text = _blocked_summary(result) or "没有关键词通过当前阶段和属性门"
    return [[
        "不新建",
        "不新建",
        result.product_profile.asin_sku,
        "SINGLE_ASIN_CONTROL",
        "不新建",
        "待补数据",
        "不适用",
        "待人工配置",
        "待补相关性与搜索量数据，不生成投放动作",
        "待人工配置",
        "观察 / 否",
        "",
        "",
        result.product_profile.core_diagnosis,
        "是",
        reason_text,
    ]]


def _architecture_role(row, result) -> str:
    if row.ad_type == "词组":
        return "Phrase承接 / 是"
    if row.ad_type == "广泛":
        return "Broad探索 / 否"
    return "候选 / 需人工确认"


def _product_match_points(row) -> str:
    if row.evidence_grain == "ABA_COLD_START":
        cold_reasons = [reason for reason in row.reasons if "ABA冷启动资格通过" in reason]
        return cold_reasons[0] if cold_reasons else "ABA冷启动属性门待人工确认"
    components = [
        ("历史成交", row.transaction_data_score),
        ("区域", row.region_score),
        ("规格", row.spec_score),
        ("风格", row.style_score),
        ("颜色", row.color_score),
    ]
    return "；".join(f"{label}{value}" for label, value in components if value is not None)


def _design_logic(result) -> str:
    missing = _blocked_summary(result) or "无。"
    cold_start = any(row.evidence_grain == "ABA_COLD_START" for row in result.keyword_scoring_table)
    evidence_text = (
        "【证据模式】当前链接没有被要求具备历史点击；使用ABA冷启动候选，"
        "仅在Rug类型、至少一项产品属性、ABA阶段、合规和广告状态同时通过时进入架构。"
        if cold_start
        else f"【历史数据】{result.product_profile.core_diagnosis} 数据置信度为{result.product_profile.data_confidence}。"
    )
    return (
        f"【ABA/产品属性】已按目标尺寸识别为 {result.product_profile.rug_type or '待确认'}，"
        "关键词需先通过尺寸、类型、形状、材质、颜色、风格和动物图案硬冲突检查。"
        f"{evidence_text}"
        "【用户固定规则】新品只生成 Phrase、关键词 Broad 或 Auto Close 的人工建议；"
        "Phrase/Broad 先通过ASIN相关性门，再用词根月搜索量判断投放层级，"
        "最后按语义特异度、词根Top3占比和有效查询数选择匹配方式；"
        "两类表缺失时不用ABA排名代替，不生成新建广告组。"
        "ABA 排名不高于 3 万的词单词单组，3 万至 10 万的同入口词每组 2-5 个；"
        "广告组使用七段命名，标准最低日预算来自对应 Rug 类型 CPA 正常线上限，"
        "未确认 Bid、广告位或圆形阈值不补造。新品阶段不建 Exact、Auto Loose 或 ASIN 定向。"
        f"【缺失数据】{missing}"
    )


def _blocked_summary(result) -> str:
    config_reasons: list[str] = []
    priority_data_reasons: list[str] = []
    data_reasons: list[str] = []
    counts: dict[str, int] = {}
    for item in result.blocked_items:
        reason = str(item.reason or "").strip()
        if not reason:
            continue
        if "规则缺失" in reason or "产品信息缺失" in reason:
            if reason not in config_reasons:
                config_reasons.append(reason)
            continue
        if item.item_type == "data_source":
            if item.identifier in {"RELEVANCE_SOURCE_PENDING", "SEARCH_VOLUME_SOURCE_PENDING"}:
                if reason not in priority_data_reasons:
                    priority_data_reasons.append(reason)
            elif reason not in data_reasons:
                data_reasons.append(reason)
            continue
        label = {
            "candidate_pool": "ABA合规/冲突门",
            "keyword_scoring": "产品属性门",
            "stage_matching": "ABA阶段门",
            "strategy_mapper": "投放策略门",
            "architecture_builder": "架构生成门",
            "conflict_check": "架构冲突门",
        }.get(item.source_step, item.source_step)
        counts[label] = counts.get(label, 0) + 1
    parts = [*priority_data_reasons, *config_reasons[:5], *data_reasons[:3]]
    parts.extend(f"{label}排除 {count} 项" for label, count in sorted(counts.items()))
    return "；".join(parts)


if __name__ == "__main__":
    raise SystemExit(main())
