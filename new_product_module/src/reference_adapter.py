from __future__ import annotations

import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from openpyxl import load_workbook


ABA_SHEET = "广告词库"
ABA_REQUIRED_HEADERS = {
    "搜索词",
    "搜索量排名",
    "地毯类型",
    "推荐层级",
    "相关度等级",
    "合规状态",
    "广告状态",
}


def normalize_term(value: Any) -> str:
    text = str(value or "").replace("+", " ").strip().lower()
    return re.sub(r"\s+", " ", text)


def load_rug_keyword_evidence(
    aba_source: str | Path,
    history_source: str | Path,
    *,
    include_aba_cold_start: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Join fixed Rug ABA facts to historical performance keywords.

    The current fixed history workbook was built from a keyword-analysis summary,
    not an Amazon Customer Search Term report.  Its legacy ``search_term`` column
    is therefore explicitly labelled ``TARGETING_KEYWORD`` here and must not be
    used as proof of an actual customer query or actual match type.
    """

    aba_records = _load_aba_records(aba_source)
    history_records, history_issues = _load_history_summary(history_source)
    issues: list[dict[str, str]] = list(history_issues)

    joined: list[dict[str, Any]] = []
    missing_aba = 0
    for term, history in history_records.items():
        aba = aba_records.get(term)
        if aba is None:
            missing_aba += 1
            continue
        joined.append(
            {
                "search_term": term,
                "clicks": history["clicks"],
                "orders": history["orders"],
                "order_dates": [],
                "cvr": history["cvr"],
                "cpa": history["cpa"],
                "aba_rank": aba["aba_rank"],
                "evidence_grain": "TARGETING_KEYWORD",
                "source_report_type": "keyword_analysis_summary",
                "source_files": history["source_files"],
                "aba_sources": aba["aba_sources"],
                "aba_conflict": aba["aba_conflict"],
                "compliance_status": aba["compliance_status"],
                "ad_status": aba["ad_status"],
                "recommendation_tier": aba["recommendation_tier"],
                "normalized_root": aba["normalized_root"],
                "category_judgment": aba["category_judgment"],
                "detailed_category": aba["detailed_category"],
                "comprehensive_priority": aba["comprehensive_priority"],
                "advertising_use": aba["advertising_use"],
                "aba_tags": aba["tags"],
                "aba_judgment_reason": aba["judgment_reason"],
                "historical_subcategory": history.get("subcategory"),
                "aba_rug_types": aba["rug_types"],
                "aba_relevance_levels": aba["relevance_levels"],
            }
        )

    if missing_aba:
        issues.append(
            {
                "code": "HISTORY_WITHOUT_ABA_MATCH",
                "message": f"{missing_aba} 个历史效果词未匹配到当前 Rug ABA 广告词库，未进入评分。",
            }
        )
    if not joined:
        issues.append(
            {
                "code": "NO_JOINED_KEYWORDS",
                "message": "历史效果词与当前 Rug ABA 广告词库没有可用交集。",
            }
        )
    if include_aba_cold_start:
        joined_terms = {row["search_term"] for row in joined}
        cold_start_rows = [
            _aba_cold_start_record(term, aba)
            for term, aba in aba_records.items()
            if term not in joined_terms
        ]
        joined.extend(cold_start_rows)
        issues.append(
            {
                "code": "ABA_COLD_START_CANDIDATES_ADDED",
                "message": (
                    f"已加入 {len(cold_start_rows)} 个无当前ASIN历史绩效的ABA冷启动候选；"
                    "仅允许按属性、阶段、合规和人工批准门生成CANDIDATE_ONLY架构。"
                ),
            }
        )
    return sorted(joined, key=lambda row: (row["aba_rank"], row["search_term"])), issues


def _aba_cold_start_record(term: str, aba: dict[str, Any]) -> dict[str, Any]:
    return {
        "search_term": term,
        "clicks": 0,
        "orders": 0,
        "order_dates": [],
        "cvr": 0.0,
        "cpa": None,
        "aba_rank": aba["aba_rank"],
        "evidence_grain": "ABA_COLD_START",
        "source_report_type": "rug_aba_catalog",
        "source_files": [],
        "aba_sources": aba["aba_sources"],
        "aba_conflict": aba["aba_conflict"],
        "compliance_status": aba["compliance_status"],
        "ad_status": aba["ad_status"],
        "recommendation_tier": aba["recommendation_tier"],
        "normalized_root": aba["normalized_root"],
        "category_judgment": aba["category_judgment"],
        "detailed_category": aba["detailed_category"],
        "comprehensive_priority": aba["comprehensive_priority"],
        "advertising_use": aba["advertising_use"],
        "aba_tags": aba["tags"],
        "aba_judgment_reason": aba["judgment_reason"],
        "historical_subcategory": None,
        "aba_rug_types": aba["rug_types"],
        "aba_relevance_levels": aba["relevance_levels"],
    }


def _iter_xlsx_paths(source: str | Path) -> list[Path]:
    path = Path(source)
    if path.is_dir():
        return sorted(
            item
            for item in path.glob("*.xlsx")
            if not item.name.startswith("~$") and not item.name.startswith(".")
        )
    if path.is_file() and path.suffix.lower() in {".xlsx", ".xlsm"}:
        return [path]
    raise ValueError(f"ABA source must be an XLSX file or directory: {path}")


def _load_aba_records(source: str | Path) -> dict[str, dict[str, Any]]:
    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    paths = _iter_xlsx_paths(source)
    if not paths:
        raise ValueError(f"ABA directory contains no XLSX files: {source}")

    for path in paths:
        workbook = load_workbook(path, read_only=True, data_only=True)
        if ABA_SHEET not in workbook.sheetnames:
            raise ValueError(f"{path.name} is missing required sheet: {ABA_SHEET}")
        sheet = workbook[ABA_SHEET]
        rows = sheet.iter_rows(values_only=True)
        headers = [str(value or "").strip() for value in (next(rows, ()) or ())]
        missing = ABA_REQUIRED_HEADERS.difference(headers)
        if missing:
            raise ValueError(f"{path.name}/{ABA_SHEET} missing headers: {sorted(missing)}")
        for row_number, values in enumerate(rows, start=2):
            row = {headers[index]: values[index] if index < len(values) else None for index in range(len(headers))}
            term = normalize_term(row.get("搜索词"))
            if not term:
                continue
            try:
                rank = _to_int(row.get("搜索量排名"))
            except ValueError as exc:
                raise ValueError(
                    f"{path.name}/{ABA_SHEET} row {row_number} 搜索量排名无效: {exc}"
                ) from exc
            if rank is None or rank <= 0:
                continue
            candidates[term].append(
                {
                    "aba_rank": rank,
                    "rug_type": _text(row.get("地毯类型")),
                    "recommendation_tier": _text(row.get("推荐层级")),
                    "relevance_level": _text(row.get("相关度等级")),
                    "compliance_status": _text(row.get("合规状态")),
                    "ad_status": _text(row.get("广告状态")),
                    "normalized_root": _text(row.get("规范词根")),
                    "category_judgment": _text(_first_matching_value(row, "类目判断")),
                    "detailed_category": _text(row.get("详细分类")),
                    "comprehensive_priority": _text(row.get("综合优先级")),
                    "advertising_use": _text(row.get("广告用途")),
                    "tags": _unique(
                        _text(row.get(header))
                        for header in (
                            "尺寸标签",
                            "场景标签",
                            "功能标签",
                            "风格图案标签",
                            "颜色标签",
                            "材质结构标签",
                            "形状标签",
                            "人群宠物标签",
                        )
                    ),
                    "judgment_reason": _text(row.get("判断原因")),
                    "source": path.name,
                }
            )

    return {term: _resolve_aba_rows(rows) for term, rows in candidates.items()}


def _resolve_aba_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    compliance_values = _unique(row["compliance_status"] for row in rows)
    ad_status_values = _unique(row["ad_status"] for row in rows)
    tier_values = _unique(row["recommendation_tier"] for row in rows)
    rug_types = _unique(row["rug_type"] for row in rows)
    relevance_levels = _unique(row["relevance_level"] for row in rows)

    compliance_status = "安全" if compliance_values == ["安全"] else "需隔离复核"
    ad_status = "可投" if ad_status_values == ["可投"] else "需隔离复核"
    conflict = any(
        len(values) > 1
        for values in (compliance_values, ad_status_values, tier_values, rug_types, relevance_levels)
    )
    return {
        "aba_rank": min(row["aba_rank"] for row in rows),
        "compliance_status": compliance_status,
        "ad_status": ad_status,
        "recommendation_tier": tier_values[0] if len(tier_values) == 1 else "冲突待复核",
        "normalized_root": _resolved_text(rows, "normalized_root"),
        "category_judgment": _resolved_text(rows, "category_judgment"),
        "detailed_category": _resolved_text(rows, "detailed_category"),
        "comprehensive_priority": _resolved_text(rows, "comprehensive_priority"),
        "advertising_use": _resolved_text(rows, "advertising_use"),
        "tags": _unique(tag for row in rows for tag in row.get("tags", [])),
        "judgment_reason": _resolved_text(rows, "judgment_reason"),
        "rug_types": rug_types,
        "relevance_levels": relevance_levels,
        "aba_sources": _unique(row["source"] for row in rows),
        "aba_conflict": conflict,
    }


def _first_matching_value(row: dict[str, Any], suffix: str) -> Any:
    for key, value in row.items():
        if str(key).endswith(suffix):
            return value
    return None


def _resolved_text(rows: list[dict[str, Any]], key: str) -> str | None:
    values = _unique(row.get(key) for row in rows)
    if not values:
        return None
    return values[0] if len(values) == 1 else "冲突待复核"


def _load_history_summary(source: str | Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    path = Path(source)
    if not path.is_file():
        raise ValueError(f"Historical evidence workbook does not exist: {path}")
    workbook = load_workbook(path, read_only=True, data_only=True)
    summary_sheet = "keyword_summary" if "keyword_summary" in workbook.sheetnames else "term_summary"
    if summary_sheet not in workbook.sheetnames:
        raise ValueError(f"{path.name} is missing keyword_summary/term_summary")
    sheet = workbook[summary_sheet]
    rows = sheet.iter_rows(values_only=True)
    headers = [str(value or "").strip() for value in (next(rows, ()) or ())]
    term_field = "historical_performance_keyword" if "historical_performance_keyword" in headers else "search_term"
    required = {term_field, "clicks", "ad_orders", "cvr", "cpa", "source_files"}
    missing = required.difference(headers)
    if missing:
        raise ValueError(f"{path.name}/{summary_sheet} missing headers: {sorted(missing)}")

    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row_number, values in enumerate(rows, start=2):
        row = {headers[index]: values[index] if index < len(values) else None for index in range(len(headers))}
        term = normalize_term(row.get(term_field))
        if not term:
            continue
        try:
            clicks = _to_int(row.get("clicks")) or 0
            orders = _to_int(row.get("ad_orders")) or 0
        except ValueError as exc:
            raise ValueError(
                f"{path.name}/{summary_sheet} row {row_number} 整数指标无效: {exc}"
            ) from exc
        candidates[term].append({
            "clicks": clicks,
            "orders": orders,
            "cvr": _to_float(row.get("cvr")) or 0.0,
            "cpa": _to_float(row.get("cpa")),
            "source_files": _split_sources(row.get("source_files")),
            "subcategory": _text(row.get("subcategory")),
        })

    records: dict[str, dict[str, Any]] = {}
    duplicate_terms: list[str] = []
    for term, term_rows in candidates.items():
        if len(term_rows) == 1:
            records[term] = term_rows[0]
        else:
            duplicate_terms.append(term)
            records[term] = _aggregate_history_rows(term_rows)

    issues = [
        {
            "code": "HISTORY_GRAIN_TARGETING_KEYWORD",
            "message": (
                "固定历史文件来自关键词分析汇总；其 legacy search_term 列按 TARGETING_KEYWORD "
                "解释，不视为 Customer Search Term、真实匹配方式或独立成交日期证据。"
            ),
        }
    ]
    if duplicate_terms:
        preview = "、".join(sorted(duplicate_terms)[:5])
        issues.append(
            {
                "code": "HISTORY_DUPLICATE_TERMS_AGGREGATED",
                "message": (
                    f"检测到 {len(duplicate_terms)} 个标准化重复历史词，已按点击和订单汇总，"
                    f"未使用末行覆盖。示例：{preview}"
                ),
            }
        )
    return records, issues


def _aggregate_history_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    clicks = sum(int(row["clicks"]) for row in rows)
    orders = sum(int(row["orders"]) for row in rows)
    rows_with_orders = [row for row in rows if int(row["orders"]) > 0]
    if rows_with_orders and all(row["cpa"] is not None for row in rows_with_orders):
        estimated_spend = sum(float(row["cpa"]) * int(row["orders"]) for row in rows_with_orders)
        cpa = estimated_spend / orders if orders else None
    else:
        cpa = None
    source_files = _unique(
        source
        for row in rows
        for source in row["source_files"]
    )
    subcategories = _unique(row.get("subcategory") for row in rows)
    return {
        "clicks": clicks,
        "orders": orders,
        "cvr": orders / clicks if clicks else 0.0,
        "cpa": cpa,
        "source_files": source_files,
        "subcategory": "; ".join(subcategories),
    }


def _split_sources(value: Any) -> list[str]:
    text = _text(value)
    if not text:
        return []
    return [part.strip() for part in re.split(r"[;；|]", text) if part.strip()]


def _unique(values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = _text(value)
        if text and text not in result:
            result.append(text)
    return result


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError(f"布尔值不是整数指标: {value!r}")
    number = _to_float(value)
    if number is None or not math.isfinite(number):
        raise ValueError(f"不是有效有限数值: {value!r}")
    if not number.is_integer():
        raise ValueError(f"必须为整数，不得截断小数: {value!r}")
    return int(number)
