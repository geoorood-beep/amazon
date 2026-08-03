from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unicodedata
from typing import Any, Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from openpyxl import load_workbook

from ai_ads.contracts import (
    AdDecisionPacket,
    AdGroupFact,
    CampaignFact,
    DataMode,
    ImportedDataIssue,
    MetricSample,
    MetricWindow,
    ObjectMetricFact,
    ObjectType,
    ReconciliationStatus,
    ReportSource,
    ReportType,
    SearchTermFact,
    SnapshotMetadata,
    TargetFact,
)
from ai_ads.data_quality import assess_data_quality
from scripts.weekly_amazon_report_ingest import REPORT_RULES, classify_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "ad_report_aggregation.json"
DEFAULT_CONTEXT = PROJECT_ROOT / "config" / "ad_report_context.example.json"
WORKBOOK_BUILDER = Path(__file__).with_name("workbook_builder.mjs")

REPORT_TYPE_BY_ID = {
    "sp_search_terms_daily": ReportType.SEARCH_TERM_DAILY,
    "sp_search_terms_summary": ReportType.SEARCH_TERM_SUMMARY,
    "sp_targeting": ReportType.TARGETING,
    "sp_placement": ReportType.PLACEMENT,
    "sp_advertised_product": ReportType.ADVERTISED_PRODUCT,
    "campaign_ad_group_settings": ReportType.CAMPAIGN_SETTINGS,
}

COUNT_FIELDS = {"impressions", "clicks", "orders"}
MONEY_FIELDS = {"spend", "sales", "daily_budget", "default_bid", "bid"}
DATE_FIELDS = {"date", "period_start", "period_end"}
TEXT_FIELDS = {
    "marketplace",
    "currency",
    "campaign_id",
    "campaign_name",
    "campaign_status",
    "ad_group_id",
    "ad_group_name",
    "ad_group_status",
    "target_id",
    "target_text",
    "match_type",
    "target_status",
    "search_term",
    "placement",
    "sku",
    "asin",
}
METRIC_FIELDS = ("impressions", "clicks", "orders", "spend", "sales")
MAX_IMPORTED_ISSUES = 250


@dataclass
class LoadedReport:
    report_id: str
    path: Path
    worksheet: str
    rows: list[dict[str, Any]]
    raw_row_count: int
    header_row: int
    column_mapping: dict[str, str]
    period_start: date
    period_end: date


class IssueCollector:
    def __init__(self) -> None:
        self.items: list[ImportedDataIssue] = []
        self.dropped = 0

    def add(
        self,
        code: str,
        message: str,
        *,
        blocking: bool,
        object_type: ObjectType | None = None,
        object_id: str | None = None,
    ) -> None:
        if len(self.items) >= MAX_IMPORTED_ISSUES:
            self.dropped += 1
            return
        self.items.append(
            ImportedDataIssue(
                code=code,
                message=message,
                blocking=blocking,
                object_type=object_type,
                object_id=object_id,
            )
        )

    def finalize(self) -> list[ImportedDataIssue]:
        if self.dropped:
            self.items.append(
                ImportedDataIssue(
                    code="IMPORTED_ISSUES_TRUNCATED",
                    message=f"另有 {self.dropped} 条导入问题未展开；请先修复已显示问题后重新运行。",
                    blocking=True,
                )
            )
            self.dropped = 0
        return self.items


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"文件不存在: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_header(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text)


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return re.sub(r"\s+", " ", str(value)).strip()


def parse_date(value: Any) -> date | None:
    if value is None or clean_text(value) == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = clean_text(value)
    for fmt in (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%d/%m/%Y",
        "%Y年%m月%d日",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def parse_decimal(value: Any) -> Decimal | None:
    if value is None or clean_text(value) == "":
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return None
    text = clean_text(value)
    negative_parentheses = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    text = re.sub(r"[,$¥€£\s]", "", text)
    if text.endswith("%"):
        text = text[:-1]
        try:
            result = Decimal(text) / Decimal("100")
        except InvalidOperation:
            return None
    else:
        try:
            result = Decimal(text)
        except InvalidOperation:
            return None
    return -result if negative_parentheses else result


def date_span(start: date, end: date) -> int:
    return (end - start).days + 1


def read_delimited(path: Path) -> tuple[str, list[list[Any]]]:
    payload = path.read_bytes()
    text = None
    for encoding in ("utf-8-sig", "utf-16", "gb18030"):
        try:
            text = payload.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError(f"无法识别文本编码: {path.name}")
    if path.suffix.casefold() == ".tsv":
        dialect = csv.excel_tab
    else:
        try:
            dialect = csv.Sniffer().sniff(text[:8192], delimiters=",\t;")
        except csv.Error:
            dialect = csv.excel
    rows = [list(row) for row in csv.reader(text.splitlines(), dialect)]
    return "CSV", rows


def read_xlsx(path: Path) -> list[tuple[str, list[list[Any]]]]:
    workbook = load_workbook(path, read_only=True, data_only=False)
    candidates: list[tuple[str, list[list[Any]]]] = []
    try:
        for worksheet in workbook.worksheets:
            rows = [list(row) for row in worksheet.iter_rows(values_only=True)]
            candidates.append((worksheet.title, rows))
    finally:
        workbook.close()
    return candidates


def alias_sets(config: dict[str, Any]) -> dict[str, set[str]]:
    return {
        field: {normalize_header(alias) for alias in aliases}
        for field, aliases in config["column_aliases"].items()
    }


def desired_fields(config: dict[str, Any], report_id: str) -> list[str]:
    spec = config["report_requirements"][report_id]
    fields = list(spec.get("required", [])) + list(spec.get("optional", []))
    for choices in spec.get("one_of", []):
        fields.extend(choices)
    return list(dict.fromkeys(fields))


def resolve_columns(
    headers: list[Any],
    fields: list[str],
    aliases: dict[str, set[str]],
) -> tuple[dict[str, int], list[str]]:
    normalized = [normalize_header(item) for item in headers]
    mapping: dict[str, int] = {}
    ambiguous: list[str] = []
    for field in fields:
        candidates = [index for index, header in enumerate(normalized) if header in aliases[field]]
        if len(candidates) == 1:
            mapping[field] = candidates[0]
        elif len(candidates) > 1:
            ambiguous.append(field)
    reused: dict[int, list[str]] = {}
    for field, index in mapping.items():
        reused.setdefault(index, []).append(field)
    for fields_at_index in reused.values():
        if len(fields_at_index) > 1:
            ambiguous.extend(fields_at_index)
            for field in fields_at_index:
                mapping.pop(field, None)
    return mapping, sorted(set(ambiguous))


def choose_sheet_and_header(
    path: Path,
    report_id: str,
    config: dict[str, Any],
) -> tuple[str, list[list[Any]], int, dict[str, int], list[str]]:
    if path.suffix.casefold() in {".csv", ".tsv"}:
        worksheet, rows = read_delimited(path)
        candidates = [(worksheet, rows)]
    elif path.suffix.casefold() == ".xlsx":
        candidates = read_xlsx(path)
    else:
        raise ValueError(f"不支持的文件格式: {path.suffix}")

    aliases = alias_sets(config)
    fields = desired_fields(config, report_id)
    required = set(config["report_requirements"][report_id].get("required", []))
    best: tuple[int, int, str, list[list[Any]], int, dict[str, int], list[str]] | None = None
    best_locations: list[tuple[str, int]] = []
    for worksheet, rows in candidates:
        for row_index, row in enumerate(rows[:20]):
            mapping, ambiguous = resolve_columns(row, fields, aliases)
            required_matches = len(required & set(mapping))
            total_matches = len(mapping)
            score = (required_matches, total_matches)
            candidate = (
                score[0],
                score[1],
                worksheet,
                rows,
                row_index,
                mapping,
                ambiguous,
            )
            if best is None or score > (best[0], best[1]):
                best = candidate
                best_locations = [(worksheet, row_index)]
            elif best is not None and score == (best[0], best[1]) and score[0] > 0:
                best_locations.append((worksheet, row_index))
    if best is None:
        raise ValueError(f"报表没有可读取的工作表或行: {path.name}")
    if len(best_locations) > 1:
        locations = ", ".join(f"{sheet}!row{row + 1}" for sheet, row in best_locations[:8])
        raise ValueError(f"存在多个同分表头候选，不能自动选择: {locations}")
    return best[2], best[3], best[4], best[5], best[6]


def validate_config(config: dict[str, Any]) -> None:
    required_ids = config.get("required_report_ids", [])
    if set(required_ids) != set(REPORT_TYPE_BY_ID):
        raise ValueError("required_report_ids 必须与 V2.0 六类完整模式报表一致")
    if config.get("allowed_category") != "rug":
        raise ValueError("聚合工具的 allowed_category 必须固定为 rug")
    if config.get("data_mode") != "FULL":
        raise ValueError("当前六表聚合工具的 data_mode 必须固定为 FULL")
    for report_id in required_ids:
        if report_id not in config.get("report_requirements", {}):
            raise ValueError(f"缺少报表字段合同: {report_id}")
    for field in set().union(
        *(set(desired_fields(config, report_id)) for report_id in required_ids)
    ):
        if field not in config.get("column_aliases", {}):
            raise ValueError(f"缺少字段别名: {field}")


def validate_context(context: dict[str, Any]) -> tuple[date, date, ZoneInfo]:
    required = (
        "schema_version",
        "category",
        "marketplace",
        "account_id",
        "link_id",
        "timezone",
        "currency",
        "attribution_window_days",
        "period_start",
        "period_end",
    )
    missing = [field for field in required if clean_text(context.get(field)) == ""]
    if missing:
        raise ValueError("上下文缺少字段: " + ", ".join(missing))
    if context["category"] != "rug":
        raise ValueError(
            "类目越界：陆遥广告智能体只允许 category=rug；其他类目请切换到有它广告智能体"
        )
    for field in ("account_id", "link_id"):
        if "请填写" in clean_text(context[field]):
            raise ValueError(f"上下文 {field} 仍是模板占位值")
    start = parse_date(context["period_start"])
    end = parse_date(context["period_end"])
    if start is None or end is None or end < start:
        raise ValueError("period_start / period_end 必须是有效且顺序正确的日期")
    currency = clean_text(context["currency"]).upper()
    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise ValueError("currency 必须是三位大写 ISO 货币代码")
    context["currency"] = currency
    try:
        timezone = ZoneInfo(clean_text(context["timezone"]))
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"无效时区: {context['timezone']}") from exc
    try:
        attribution = int(context["attribution_window_days"])
    except (TypeError, ValueError) as exc:
        raise ValueError("attribution_window_days 必须是非负整数") from exc
    if attribution < 0:
        raise ValueError("attribution_window_days 必须是非负整数")
    context["attribution_window_days"] = attribution
    return start, end, timezone


def discover_reports(
    source_dir: Path,
    config: dict[str, Any],
    report_map_path: Path | None,
    issues: IssueCollector,
) -> tuple[dict[str, Path], list[Path]]:
    extensions = {item.casefold() for item in config["input_extensions"]}
    if report_map_path:
        raw_map = load_json(report_map_path)
        mapped: dict[str, Path] = {}
        mapped_paths: dict[Path, str] = {}
        for report_id, value in raw_map.items():
            if report_id not in REPORT_TYPE_BY_ID:
                issues.add(
                    "UNKNOWN_REPORT_MAP_ID",
                    f"人工映射包含未知 report_id: {report_id}",
                    blocking=True,
                )
                continue
            candidate = Path(value).expanduser()
            if not candidate.is_absolute():
                candidate = source_dir / candidate
            candidate = candidate.resolve()
            try:
                candidate.relative_to(source_dir.resolve())
            except ValueError:
                issues.add(
                    "REPORT_MAP_OUTSIDE_SOURCE_DIR",
                    f"人工映射越过输入目录: {candidate}",
                    blocking=True,
                )
                continue
            if not candidate.is_file():
                issues.add(
                    "REPORT_MAP_FILE_NOT_FOUND",
                    f"人工映射文件不存在: {candidate}",
                    blocking=True,
                )
                continue
            if candidate.suffix.casefold() not in {
                item.casefold() for item in config["input_extensions"]
            }:
                issues.add(
                    "REPORT_MAP_EXTENSION_UNSUPPORTED",
                    f"人工映射文件格式不支持: {candidate.name}",
                    blocking=True,
                )
                continue
            if candidate in mapped_paths:
                issues.add(
                    "REPORT_MAP_FILE_REUSED",
                    f"同一文件不能映射为两类报表: {mapped_paths[candidate]} / {report_id} -> {candidate.name}",
                    blocking=True,
                )
                continue
            mapped[report_id] = candidate
            mapped_paths[candidate] = report_id
        return mapped, []

    candidates = [
        path
        for path in sorted(source_dir.rglob("*"))
        if path.is_file()
        and path.suffix.casefold() in extensions
        and not path.name.startswith(("~$", "._"))
    ]
    grouped: dict[str, list[Path]] = {}
    unclassified: list[Path] = []
    for path in candidates:
        match = classify_file(path)
        if match is None or match["id"] not in REPORT_TYPE_BY_ID:
            unclassified.append(path)
            continue
        grouped.setdefault(match["id"], []).append(path)

    resolved: dict[str, Path] = {}
    for report_id, paths in grouped.items():
        if len(paths) == 1:
            resolved[report_id] = paths[0]
        else:
            issues.add(
                "DUPLICATE_REPORT_TYPE",
                f"同一标准报表识别到多个文件，必须用 --report-map 明确选择: {report_id} -> "
                + "; ".join(path.name for path in paths),
                blocking=True,
            )
    return resolved, unclassified


def canonicalize_rows(
    report_id: str,
    path: Path,
    worksheet: str,
    matrix: list[list[Any]],
    header_row: int,
    mapping: dict[str, int],
    config: dict[str, Any],
    issues: IssueCollector,
) -> list[dict[str, Any]]:
    spec = config["report_requirements"][report_id]
    required = list(spec.get("required", []))
    missing_columns = [field for field in required if field not in mapping]
    missing_one_of = [
        choices for choices in spec.get("one_of", []) if not any(field in mapping for field in choices)
    ]
    if missing_columns:
        issues.add(
            "REQUIRED_COLUMN_MISSING",
            f"{path.name}/{worksheet} 缺少列: {', '.join(missing_columns)}",
            blocking=True,
        )
    for choices in missing_one_of:
        issues.add(
            "REQUIRED_ONE_OF_COLUMN_MISSING",
            f"{path.name}/{worksheet} 至少需要一列: {' / '.join(choices)}",
            blocking=True,
        )
    if missing_columns or missing_one_of:
        return []

    rows: list[dict[str, Any]] = []
    for source_row_number, raw_row in enumerate(matrix[header_row + 1 :], start=header_row + 2):
        if not any(clean_text(value) for value in raw_row):
            continue
        record: dict[str, Any] = {}
        row_errors: list[str] = []
        for field, index in mapping.items():
            raw_value = raw_row[index] if index < len(raw_row) else None
            if field in DATE_FIELDS:
                value = parse_date(raw_value)
                if raw_value not in (None, "") and value is None:
                    row_errors.append(f"{field}=无法解析日期({clean_text(raw_value)})")
            elif field in COUNT_FIELDS | MONEY_FIELDS:
                value = parse_decimal(raw_value)
                if raw_value not in (None, "") and value is None:
                    row_errors.append(f"{field}=无法解析数值({clean_text(raw_value)})")
            elif field in TEXT_FIELDS:
                value = clean_text(raw_value)
                if field == "currency":
                    value = value.upper()
            else:
                value = raw_value
            record[field] = value

        blanks = [field for field in required if record.get(field) in (None, "")]
        if blanks:
            row_errors.append("必填值为空(" + ", ".join(blanks) + ")")
        for choices in spec.get("one_of", []):
            if not any(record.get(field) not in (None, "") for field in choices):
                row_errors.append("至少填写一项(" + " / ".join(choices) + ")")

        for field in COUNT_FIELDS | MONEY_FIELDS:
            value = record.get(field)
            if value is not None and value < 0:
                row_errors.append(f"{field}=负数")
        for field in ("impressions", "clicks", "orders"):
            value = record.get(field)
            if value is not None and value != value.to_integral_value():
                row_errors.append(f"{field}=非整数")
        if record.get("clicks") is not None and record.get("impressions") is not None:
            if record["clicks"] > record["impressions"]:
                row_errors.append("clicks 大于 impressions")
        if record.get("orders") is not None and record.get("clicks") is not None:
            if record["orders"] > record["clicks"]:
                row_errors.append("orders 大于 clicks")

        if row_errors:
            issues.add(
                "SOURCE_ROW_REJECTED",
                f"{path.name}/{worksheet} 第{source_row_number}行: " + "; ".join(row_errors),
                blocking=True,
            )
            continue
        for field in ("impressions", "clicks"):
            if field in record and record[field] is not None:
                record[field] = int(record[field])
        rows.append(record)
    return rows


def infer_report_period(
    report_id: str,
    rows: list[dict[str, Any]],
    context_start: date,
    context_end: date,
    path: Path,
    issues: IssueCollector,
) -> tuple[date, date]:
    if report_id == "sp_search_terms_daily":
        dates = sorted({row["date"] for row in rows if row.get("date")})
        if not dates:
            return context_start, context_end
        actual_start, actual_end = dates[0], dates[-1]
    else:
        starts = {row["period_start"] for row in rows if row.get("period_start")}
        ends = {row["period_end"] for row in rows if row.get("period_end")}
        if len(starts) > 1 or len(ends) > 1:
            issues.add(
                "REPORT_PERIOD_INCONSISTENT",
                f"{path.name} 内存在多个开始或结束日期",
                blocking=True,
            )
        actual_start = min(starts) if starts else context_start
        actual_end = max(ends) if ends else context_end
    if actual_start != context_start or actual_end != context_end:
        issues.add(
            "REPORT_SNAPSHOT_PERIOD_MISMATCH",
            f"{path.name} 周期 {actual_start}..{actual_end} 与上下文 {context_start}..{context_end} 不一致",
            blocking=True,
        )
    return actual_start, actual_end


def load_report(
    report_id: str,
    path: Path,
    config: dict[str, Any],
    context: dict[str, Any],
    context_start: date,
    context_end: date,
    issues: IssueCollector,
) -> LoadedReport:
    worksheet, matrix, header_row, mapping, ambiguous = choose_sheet_and_header(
        path, report_id, config
    )
    if ambiguous:
        issues.add(
            "AMBIGUOUS_HEADER_MAPPING",
            f"{path.name}/{worksheet} 列名无法唯一映射: {', '.join(ambiguous)}",
            blocking=True,
        )
    rows = canonicalize_rows(
        report_id,
        path,
        worksheet,
        matrix,
        header_row,
        mapping,
        config,
        issues,
    )
    headers = matrix[header_row] if matrix else []
    column_mapping = {field: clean_text(headers[index]) for field, index in mapping.items()}
    for field in ("orders", "sales"):
        source_header = column_mapping.get(field, "")
        attribution_match = re.search(r"\b(7|14)\s*day\b|(?<!\d)(7|14)\s*天", source_header, re.I)
        if attribution_match:
            source_days = int(attribution_match.group(1) or attribution_match.group(2))
            if source_days != context["attribution_window_days"]:
                issues.add(
                    "REPORT_ATTRIBUTION_WINDOW_MISMATCH",
                    f"{path.name} 字段 {source_header} 表示 {source_days} 天归因，与上下文 "
                    f"{context['attribution_window_days']} 天不一致",
                    blocking=True,
                )
    for row in rows:
        currency = clean_text(row.get("currency")).upper()
        marketplace = clean_text(row.get("marketplace")).upper()
        if currency and currency != context["currency"]:
            issues.add(
                "REPORT_CURRENCY_MISMATCH",
                f"{path.name} 币种 {currency} 与上下文 {context['currency']} 不一致",
                blocking=True,
            )
        if marketplace and marketplace != clean_text(context["marketplace"]).upper():
            issues.add(
                "REPORT_MARKETPLACE_MISMATCH",
                f"{path.name} 站点 {marketplace} 与上下文 {context['marketplace']} 不一致",
                blocking=True,
            )
    period_start, period_end = infer_report_period(
        report_id, rows, context_start, context_end, path, issues
    )
    if not rows:
        issues.add(
            "MANDATORY_REPORT_EMPTY",
            f"标准报表没有有效数据行: {report_id}/{path.name}",
            blocking=True,
        )
    return LoadedReport(
        report_id=report_id,
        path=path,
        worksheet=worksheet,
        rows=rows,
        raw_row_count=sum(1 for row in matrix[header_row + 1 :] if any(clean_text(v) for v in row)),
        header_row=header_row + 1,
        column_mapping=column_mapping,
        period_start=period_start,
        period_end=period_end,
    )


def consistent_unique(
    rows: Iterable[dict[str, Any]],
    id_field: str,
    fields: tuple[str, ...],
    label: str,
    issues: IssueCollector,
) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        object_id = clean_text(row.get(id_field))
        if not object_id:
            continue
        candidate = {field: row.get(field) for field in fields}
        previous = by_id.get(object_id)
        if previous is None:
            by_id[object_id] = candidate
        elif previous != candidate:
            issues.add(
                "IMMUTABLE_ID_CONFLICT",
                f"同一 {label} ID 对应不同字段值: {object_id}",
                blocking=True,
                object_id=object_id,
            )
    return [{id_field: object_id, **values} for object_id, values in sorted(by_id.items())]


def build_facts(
    reports: dict[str, LoadedReport],
    issues: IssueCollector,
) -> tuple[
    list[CampaignFact],
    list[AdGroupFact],
    list[TargetFact],
    list[SearchTermFact],
    dict[tuple[str, str, str, str], str],
]:
    settings = reports.get("campaign_ad_group_settings")
    settings_rows = settings.rows if settings else []
    campaign_rows = consistent_unique(
        settings_rows,
        "campaign_id",
        ("campaign_name", "daily_budget", "campaign_status"),
        "Campaign",
        issues,
    )
    campaigns = [
        CampaignFact(
            campaign_id=row["campaign_id"],
            campaign_name=clean_text(row["campaign_name"]),
            daily_budget=row["daily_budget"],
            status=clean_text(row["campaign_status"]),
        )
        for row in campaign_rows
    ]

    ad_group_rows = consistent_unique(
        settings_rows,
        "ad_group_id",
        ("campaign_id", "ad_group_name", "default_bid", "ad_group_status"),
        "Ad Group",
        issues,
    )
    ad_groups = [
        AdGroupFact(
            ad_group_id=row["ad_group_id"],
            campaign_id=clean_text(row["campaign_id"]),
            ad_group_name=clean_text(row["ad_group_name"]),
            default_bid=row["default_bid"],
            status=clean_text(row["ad_group_status"]),
        )
        for row in ad_group_rows
    ]

    targeting = reports.get("sp_targeting")
    target_rows = consistent_unique(
        targeting.rows if targeting else [],
        "target_id",
        (
            "campaign_id",
            "ad_group_id",
            "target_text",
            "match_type",
            "bid",
            "target_status",
        ),
        "Target",
        issues,
    )
    targets = [
        TargetFact(
            target_id=row["target_id"],
            campaign_id=clean_text(row["campaign_id"]),
            ad_group_id=clean_text(row["ad_group_id"]),
            target_text=clean_text(row["target_text"]),
            match_type=clean_text(row["match_type"]),
            bid=row["bid"],
            status=clean_text(row["target_status"]),
        )
        for row in target_rows
    ]

    search_source_rows: list[dict[str, Any]] = []
    for report_id in ("sp_search_terms_daily", "sp_search_terms_summary"):
        report = reports.get(report_id)
        if report:
            search_source_rows.extend(report.rows)
    search_keys: dict[tuple[str, str, str, str], str] = {}
    search_terms: list[SearchTermFact] = []
    for row in search_source_rows:
        natural_key = (
            clean_text(row.get("campaign_id")),
            clean_text(row.get("ad_group_id")),
            clean_text(row.get("target_id")),
            clean_text(row.get("search_term")).casefold(),
        )
        if natural_key in search_keys:
            continue
        digest = hashlib.sha256("\x1f".join(natural_key).encode("utf-8")).hexdigest()[:20]
        search_key = f"ST-{digest}"
        search_keys[natural_key] = search_key
        search_terms.append(
            SearchTermFact(
                search_term_key=search_key,
                campaign_id=natural_key[0],
                ad_group_id=natural_key[1],
                target_id=natural_key[2] or None,
                search_term=clean_text(row.get("search_term")),
            )
        )
    search_terms.sort(key=lambda item: item.search_term_key)
    return campaigns, ad_groups, targets, search_terms, search_keys


def natural_search_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        clean_text(row.get("campaign_id")),
        clean_text(row.get("ad_group_id")),
        clean_text(row.get("target_id")),
        clean_text(row.get("search_term")).casefold(),
    )


def sum_metrics(rows: Iterable[dict[str, Any]]) -> dict[str, Decimal | int]:
    totals: dict[str, Decimal | int] = {
        "impressions": 0,
        "clicks": 0,
        "orders": Decimal("0"),
        "spend": Decimal("0"),
        "sales": Decimal("0"),
    }
    for row in rows:
        totals["impressions"] = int(totals["impressions"]) + int(row.get("impressions") or 0)
        totals["clicks"] = int(totals["clicks"]) + int(row.get("clicks") or 0)
        for field in ("orders", "spend", "sales"):
            totals[field] = Decimal(totals[field]) + Decimal(row.get(field) or 0)
    return totals


def reconcile_search_terms(
    reports: dict[str, LoadedReport],
    config: dict[str, Any],
    issues: IssueCollector,
) -> tuple[ReconciliationStatus, list[dict[str, Any]]]:
    daily = reports.get("sp_search_terms_daily")
    summary = reports.get("sp_search_terms_summary")
    if not daily or not summary or not daily.rows or not summary.rows:
        return ReconciliationStatus.NOT_CONFIGURED, []

    grouped_daily: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    grouped_summary: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    daily_grain_seen: set[tuple[date, str, str, str, str]] = set()
    for row in daily.rows:
        key = natural_search_key(row)
        grain = (row["date"], *key)
        if grain in daily_grain_seen:
            issues.add(
                "DUPLICATE_DAILY_GRAIN",
                f"每日搜索词报表存在重复粒度: {grain}",
                blocking=True,
            )
        daily_grain_seen.add(grain)
        grouped_daily.setdefault(key, []).append(row)
    summary_grain_seen: set[tuple[str, str, str, str]] = set()
    for row in summary.rows:
        key = natural_search_key(row)
        if key in summary_grain_seen:
            issues.add(
                "DUPLICATE_SUMMARY_GRAIN",
                f"搜索词汇总报表存在重复粒度: {key}",
                blocking=True,
            )
        summary_grain_seen.add(key)
        grouped_summary.setdefault(key, []).append(row)

    tolerance = config["technical_reconciliation_tolerance"]
    count_tolerance = Decimal(tolerance["count_absolute"])
    money_tolerance = Decimal(tolerance["money_absolute"])
    rows: list[dict[str, Any]] = []
    blocked = False
    for key in sorted(set(grouped_daily) | set(grouped_summary)):
        daily_totals = sum_metrics(grouped_daily.get(key, []))
        summary_totals = sum_metrics(grouped_summary.get(key, []))
        for metric in METRIC_FIELDS:
            left = Decimal(daily_totals[metric])
            right = Decimal(summary_totals[metric])
            difference = left - right
            allowed = count_tolerance if metric in COUNT_FIELDS else money_tolerance
            status = "PASS" if abs(difference) <= allowed else "BLOCKED"
            if status == "BLOCKED":
                blocked = True
            rows.append(
                {
                    "campaign_id": key[0],
                    "ad_group_id": key[1],
                    "target_id": key[2],
                    "search_term": key[3],
                    "metric": metric,
                    "daily_value": left,
                    "summary_value": right,
                    "difference": difference,
                    "tolerance": allowed,
                    "status": status,
                }
            )
    if blocked:
        issues.add(
            "SEARCH_TERM_RECONCILIATION_MISMATCH",
            "搜索词每日明细与搜索词汇总在同粒度对账不一致",
            blocking=True,
        )
        return ReconciliationStatus.BLOCKED, rows
    return ReconciliationStatus.PASS, rows


def aggregate_daily_metrics(
    daily_rows: list[dict[str, Any]],
    context_start: date,
    context_end: date,
    search_keys: dict[tuple[str, str, str, str], str],
    issues: IssueCollector,
) -> tuple[list[ObjectMetricFact], list[dict[str, Any]]]:
    valid_rows = []
    for row in daily_rows:
        if row["date"] < context_start or row["date"] > context_end:
            issues.add(
                "DAILY_ROW_OUTSIDE_SNAPSHOT",
                f"每日搜索词数据日期超出快照周期: {row['date']}",
                blocking=True,
            )
            continue
        valid_rows.append(row)

    if date_span(context_start, context_end) < 30:
        issues.add(
            "SNAPSHOT_SHORTER_THAN_D30",
            f"完整模式快照不足30个自然日: {context_start}..{context_end}",
            blocking=True,
        )

    grouped: dict[tuple[ObjectType, str], list[dict[str, Any]]] = {}
    for row in valid_rows:
        object_pairs = [
            (ObjectType.CAMPAIGN, clean_text(row["campaign_id"])),
            (ObjectType.AD_GROUP, clean_text(row["ad_group_id"])),
            (ObjectType.TARGET, clean_text(row["target_id"])),
            (ObjectType.SEARCH_TERM, search_keys[natural_search_key(row)]),
        ]
        for pair in object_pairs:
            grouped.setdefault(pair, []).append(row)

    windows = (
        (MetricWindow.D3, 3),
        (MetricWindow.D7, 7),
        (MetricWindow.D14, 14),
        (MetricWindow.D30, 30),
    )
    metric_facts: list[ObjectMetricFact] = []
    for (object_type, object_id), rows in sorted(grouped.items(), key=lambda item: (item[0][0].value, item[0][1])):
        samples: list[MetricSample] = []
        for window, days in windows:
            window_start = context_end - timedelta(days=days - 1)
            if window_start < context_start:
                continue
            totals = sum_metrics(row for row in rows if window_start <= row["date"] <= context_end)
            samples.append(
                MetricSample(
                    window=window,
                    period_start=window_start,
                    period_end=context_end,
                    impressions=int(totals["impressions"]),
                    clicks=int(totals["clicks"]),
                    orders=Decimal(totals["orders"]),
                    spend=Decimal(totals["spend"]),
                    sales=Decimal(totals["sales"]),
                )
            )
        metric_facts.append(
            ObjectMetricFact(object_type=object_type, object_id=object_id, samples=samples)
        )

    daily_totals: list[dict[str, Any]] = []
    current = context_start
    while current <= context_end:
        totals = sum_metrics(row for row in valid_rows if row["date"] == current)
        daily_totals.append({"date": current, **totals})
        current += timedelta(days=1)
    return metric_facts, daily_totals


def aggregate_custom_metrics(
    reports: dict[str, LoadedReport],
    context_start: date,
    context_end: date,
) -> tuple[list[ObjectMetricFact], dict[str, str]]:
    metric_facts: list[ObjectMetricFact] = []
    labels: dict[str, str] = {}
    specs = (
        ("sp_placement", ObjectType.PLACEMENT, ("campaign_id", "placement")),
        ("sp_advertised_product", ObjectType.ADVERTISED_PRODUCT, ("campaign_id", "ad_group_id", "sku", "asin")),
    )
    for report_id, object_type, key_fields in specs:
        report = reports.get(report_id)
        if not report:
            continue
        grouped: dict[tuple[str, ...], list[dict[str, Any]]] = {}
        for row in report.rows:
            key = tuple(clean_text(row.get(field)) for field in key_fields)
            grouped.setdefault(key, []).append(row)
        for key, rows in sorted(grouped.items()):
            digest = hashlib.sha256("\x1f".join(key).encode("utf-8")).hexdigest()[:20]
            prefix = "PLC" if object_type == ObjectType.PLACEMENT else "PRD"
            object_id = f"{prefix}-{digest}"
            labels[f"{object_type.value}/{object_id}"] = " | ".join(item for item in key if item)
            totals = sum_metrics(rows)
            metric_facts.append(
                ObjectMetricFact(
                    object_type=object_type,
                    object_id=object_id,
                    samples=[
                        MetricSample(
                            window=MetricWindow.CUSTOM,
                            period_start=context_start,
                            period_end=context_end,
                            impressions=int(totals["impressions"]),
                            clicks=int(totals["clicks"]),
                            orders=Decimal(totals["orders"]),
                            spend=Decimal(totals["spend"]),
                            sales=Decimal(totals["sales"]),
                        )
                    ],
                )
            )
    return metric_facts, labels


def report_sources(
    reports: dict[str, LoadedReport],
    imported_at: datetime,
) -> list[ReportSource]:
    return [
        ReportSource(
            report_type=REPORT_TYPE_BY_ID[report_id],
            file_name=report.path.name,
            sha256=sha256_file(report.path),
            imported_at=imported_at,
            period_start=report.period_start,
            period_end=report.period_end,
            row_count=len(report.rows),
            worksheet=report.worksheet,
        )
        for report_id, report in sorted(reports.items())
    ]


def snapshot_id(
    context: dict[str, Any],
    sources: list[ReportSource],
) -> str:
    material = {
        "category": context["category"],
        "marketplace": context["marketplace"],
        "account_id": context["account_id"],
        "link_id": context["link_id"],
        "period_start": context["period_start"],
        "period_end": context["period_end"],
        "sources": [(item.report_type.value, item.sha256) for item in sources],
    }
    digest = hashlib.sha256(
        json.dumps(material, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:20]
    return f"ADS-{digest}"


def json_ready(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    return value


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(json_ready(payload), ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def workbook_rows(
    packet: AdDecisionPacket,
    labels: dict[str, str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for fact in packet.metrics:
        label = labels.get(f"{fact.object_type.value}/{fact.object_id}", "")
        for sample in fact.samples:
            rows.append(
                {
                    "data_snapshot_id": packet.metadata.data_snapshot_id,
                    "object_type": fact.object_type.value,
                    "object_id": fact.object_id,
                    "object_label": label,
                    "window": sample.window.value,
                    "period_start": sample.period_start,
                    "period_end": sample.period_end,
                    "impressions": sample.impressions,
                    "clicks": sample.clicks,
                    "orders": sample.orders,
                    "spend": sample.spend,
                    "sales": sample.sales,
                }
            )
    return rows


def locate_node_runtime() -> tuple[Path, Path]:
    node_override = os.environ.get("AD_REPORT_NODE_BIN")
    modules_override = os.environ.get("ARTIFACT_TOOL_NODE_MODULES")
    node_candidates = [
        Path(node_override).expanduser() if node_override else None,
        Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node",
        Path(shutil.which("node")) if shutil.which("node") else None,
    ]
    module_candidates = [
        Path(modules_override).expanduser() if modules_override else None,
        Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules",
    ]
    node = next((path for path in node_candidates if path and path.is_file()), None)
    modules = next(
        (
            path
            for path in module_candidates
            if path and (path / "@oai" / "artifact-tool").exists()
        ),
        None,
    )
    if node is None or modules is None:
        raise RuntimeError(
            "未找到 Codex 工作簿运行时。可设置 AD_REPORT_NODE_BIN 和 ARTIFACT_TOOL_NODE_MODULES。"
        )
    return node, modules


def build_workbook(
    payload: dict[str, Any],
    output_path: Path,
    preview_dir: Path | None,
) -> None:
    node, node_modules = locate_node_runtime()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", encoding="utf-8", delete=False, dir=output_path.parent
    ) as handle:
        json.dump(json_ready(payload), handle, ensure_ascii=False)
        payload_path = Path(handle.name)
    env = os.environ.copy()
    env["NODE_PATH"] = str(node_modules)
    command = [str(node), str(WORKBOOK_BUILDER), str(payload_path), str(output_path)]
    if preview_dir:
        command.append(str(preview_dir))
    try:
        subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=env,
            check=True,
            text=True,
        )
    finally:
        payload_path.unlink(missing_ok=True)


def build_packet(
    source_dir: Path,
    context: dict[str, Any],
    config: dict[str, Any],
    report_map_path: Path | None = None,
) -> tuple[AdDecisionPacket, dict[str, Any]]:
    validate_config(config)
    context_start, context_end, timezone = validate_context(context)
    issues = IssueCollector()
    if config.get("data_mode") == "FULL" and date_span(context_start, context_end) < 30:
        issues.add(
            "SNAPSHOT_SHORTER_THAN_D30",
            "完整模式至少需要覆盖30个完整自然日",
            blocking=True,
        )

    discovered, unclassified = discover_reports(
        source_dir, config, report_map_path, issues
    )
    for path in unclassified:
        issues.add(
            "UNCLASSIFIED_INPUT_FILE",
            f"输入目录存在未分类表格，请人工确认是否应纳入: {path.name}",
            blocking=False,
        )
    reports: dict[str, LoadedReport] = {}
    for report_id in config["required_report_ids"]:
        path = discovered.get(report_id)
        if path is None:
            issues.add(
                "MANDATORY_REPORT_MISSING",
                f"缺少标准报表: {report_id}",
                blocking=True,
            )
            continue
        try:
            reports[report_id] = load_report(
                report_id,
                path,
                config,
                context,
                context_start,
                context_end,
                issues,
            )
        except Exception as exc:
            issues.add(
                "REPORT_READ_FAILED",
                f"{report_id}/{path.name} 读取失败: {exc}",
                blocking=True,
            )

    campaigns, ad_groups, targets, search_terms, search_keys = build_facts(reports, issues)
    reconciliation_status, reconciliation_rows = reconcile_search_terms(
        reports, config, issues
    )
    daily_report = reports.get("sp_search_terms_daily")
    metric_facts, daily_totals = aggregate_daily_metrics(
        daily_report.rows if daily_report else [],
        context_start,
        context_end,
        search_keys,
        issues,
    )
    custom_metrics, labels = aggregate_custom_metrics(
        reports, context_start, context_end
    )
    labels.update(
        {f"CAMPAIGN/{item.campaign_id}": item.campaign_name for item in campaigns}
    )
    labels.update(
        {f"AD_GROUP/{item.ad_group_id}": item.ad_group_name for item in ad_groups}
    )
    labels.update(
        {f"TARGET/{item.target_id}": item.target_text for item in targets}
    )
    labels.update(
        {
            f"SEARCH_TERM/{item.search_term_key}": item.search_term
            for item in search_terms
        }
    )
    metric_facts.extend(custom_metrics)

    generated_at = datetime.now(timezone)
    sources = report_sources(reports, generated_at)
    packet = AdDecisionPacket(
        metadata=SnapshotMetadata(
            schema_version="1.0",
            data_snapshot_id=snapshot_id(context, sources),
            generated_at=generated_at,
            period_start=context_start,
            period_end=context_end,
            marketplace=clean_text(context["marketplace"]),
            timezone=clean_text(context["timezone"]),
            currency=context["currency"],
            attribution_window_days=context["attribution_window_days"],
            data_mode=DataMode(config.get("data_mode", "FULL")),
            reconciliation_status=reconciliation_status,
        ),
        report_sources=sources,
        campaigns=campaigns,
        ad_groups=ad_groups,
        targets=targets,
        search_terms=search_terms,
        metrics=metric_facts,
        imported_issues=issues.finalize(),
    )
    dq_report = assess_data_quality(packet)
    support = {
        "context": context,
        "loaded_reports": {
            report_id: {
                "path": report.path,
                "worksheet": report.worksheet,
                "raw_row_count": report.raw_row_count,
                "valid_row_count": len(report.rows),
                "header_row": report.header_row,
                "column_mapping": report.column_mapping,
                "period_start": report.period_start,
                "period_end": report.period_end,
            }
            for report_id, report in sorted(reports.items())
        },
        "unclassified_files": unclassified,
        "reconciliation_rows": reconciliation_rows,
        "daily_totals": daily_totals,
        "object_labels": labels,
        "agent_input_rows": workbook_rows(packet, labels),
        "dq_report": dq_report,
    }
    return packet, support


def write_outputs(
    packet: AdDecisionPacket,
    support: dict[str, Any],
    output_dir: Path,
    *,
    workbook: bool,
    render_previews: bool,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    packet_path = output_dir / "ad_decision_packet.json"
    dq_path = output_dir / "data_quality_report.json"
    manifest_path = output_dir / "aggregation_manifest.json"
    workbook_path = output_dir / "ad_decision_packet.xlsx"
    write_json(packet_path, packet.model_dump(mode="json"))
    write_json(dq_path, support["dq_report"].model_dump(mode="json"))
    manifest = {
        "tool": "ad_report_aggregator",
        "tool_version": "V2.0",
        "data_snapshot_id": packet.metadata.data_snapshot_id,
        "data_quality_status": support["dq_report"].status.value,
        "reconciliation_status": packet.metadata.reconciliation_status.value,
        "human_execution_only": True,
        "amazon_action_execution_enabled": False,
        "context": support["context"],
        "loaded_reports": support["loaded_reports"],
        "unclassified_files": support["unclassified_files"],
        "outputs": {
            "packet_json": packet_path,
            "data_quality_json": dq_path,
            "workbook": workbook_path if workbook else None,
        },
    }
    write_json(manifest_path, manifest)
    if workbook:
        preview_dir = output_dir / "previews" if render_previews else None
        payload = {
            "packet": packet.model_dump(mode="json"),
            "dq_report": support["dq_report"].model_dump(mode="json"),
            "reconciliation_rows": support["reconciliation_rows"],
            "daily_totals": support["daily_totals"],
            "agent_input_rows": support["agent_input_rows"],
            "context": support["context"],
            "loaded_reports": support["loaded_reports"],
        }
        build_workbook(payload, workbook_path, preview_dir)
    return {
        "packet": packet_path,
        "dq": dq_path,
        "manifest": manifest_path,
        "workbook": workbook_path,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="将六类 Amazon SP 广告报表确定性聚合为 V2.0 AdDecisionPacket。"
    )
    parser.add_argument("--source-dir", required=True, help="六类报表所在目录。")
    parser.add_argument("--context", required=True, help="本批次上下文 JSON。")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="输出目录；会写入 JSON、XLSX、对账和数据质量结果。",
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="字段映射和技术配置。")
    parser.add_argument(
        "--report-map",
        help="可选人工文件映射 JSON；文件名无法唯一识别时必须提供。",
    )
    parser.add_argument(
        "--no-workbook",
        action="store_true",
        help="只生成 JSON；用于快速测试，不建议作为人工交付。",
    )
    parser.add_argument(
        "--render-previews",
        action="store_true",
        help="渲染全部工作表 PNG；用于发布验收和视觉检查。",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source_dir = Path(args.source_dir).expanduser().resolve()
    context_path = Path(args.context).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    config_path = Path(args.config).expanduser().resolve()
    report_map_path = Path(args.report_map).expanduser().resolve() if args.report_map else None
    if not source_dir.is_dir():
        raise FileNotFoundError(f"输入目录不存在: {source_dir}")
    context = load_json(context_path)
    config = load_json(config_path)
    packet, support = build_packet(
        source_dir,
        context,
        config,
        report_map_path=report_map_path,
    )
    outputs = write_outputs(
        packet,
        support,
        output_dir,
        workbook=not args.no_workbook,
        render_previews=args.render_previews,
    )
    status = support["dq_report"].status.value
    print(f"Data Snapshot: {packet.metadata.data_snapshot_id}")
    print(f"Data Quality: {status}")
    print(f"Reconciliation: {packet.metadata.reconciliation_status.value}")
    print(f"Agent JSON: {outputs['packet']}")
    if not args.no_workbook:
        print(f"Human workbook: {outputs['workbook']}")
    print(f"Manifest: {outputs['manifest']}")
    print("Amazon action execution: OFF (HUMAN_EXECUTION_ONLY)")
    return 0 if status == "DQ_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
