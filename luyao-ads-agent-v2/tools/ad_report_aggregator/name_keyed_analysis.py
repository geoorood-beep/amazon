from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from openpyxl import load_workbook

from .aggregator import json_ready, locate_node_runtime, sha256_file, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKBOOK_BUILDER = Path(__file__).with_name("name_keyed_workbook_builder.mjs")
METRIC_FIELDS = ("impressions", "clicks", "orders", "spend", "sales")
COUNT_FIELDS = {"impressions", "clicks", "orders"}

REPORT_FAMILIES = {
    "SP搜索词-按词": "SEARCH_TERM",
    "SP投放对象报告": "TARGET",
    "SP广告位报告": "PLACEMENT",
    "SP广告商品报告": "ADVERTISED_PRODUCT",
}

ALIASES = {
    "date": ("日期",),
    "period_start": ("开始日期",),
    "period_end": ("结束日期",),
    "portfolio": ("广告组合名称", "广告组合"),
    "currency": ("货币",),
    "marketplace": ("国家/地区", "国家"),
    "campaign": ("广告活动名称", "广告活动"),
    "ad_group": ("广告组名称", "广告组"),
    "target": ("投放", "关键词"),
    "keyword": ("关键词",),
    "match_type": ("匹配类型", "匹配方式"),
    "search_term": ("客户搜索词", "用户搜索词"),
    "placement": ("放置", "广告位"),
    "sku": ("广告SKU", "MSKU"),
    "asin": ("广告ASIN", "ASIN"),
    "impressions": ("展示量", "曝光量", "曝光"),
    "clicks": ("点击量", "点击"),
    "orders": ("7天总订单数(#)", "广告订单"),
    "spend": ("花费", "花费-本币"),
    "sales": ("7天总销售额", "广告销售额-本币", "广告销售额"),
    "store_orders": ("店铺订单",),
    "store_sales": ("店铺销售额",),
    "campaign_status": ("状态",),
    "daily_budget": ("预算",),
    "targeting_type": ("定位类型",),
    "bidding_strategy": ("竞价策略",),
    "default_bid": ("默认竞价-本币", "Bid"),
}


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return re.sub(r"\s+", " ", str(value)).strip()


def parse_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    text = clean_text(value)
    if text in {"", "--", "-"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()").replace(",", "")
    text = re.sub(r"[$¥€£\s]", "", text)
    if text.endswith("%"):
        text = text[:-1]
        divisor = Decimal("100")
    else:
        divisor = Decimal("1")
    try:
        result = Decimal(text) / divisor
    except InvalidOperation:
        return None
    return -result if negative else result


def parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = clean_text(value)
    if not text:
        return None
    for fmt in (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%b %d, %Y",
        "%m/%d/%Y",
        "%Y年%m月%d日",
    ):
        try:
            return datetime.strptime(text[:20], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def local_id(prefix: str, *parts: str) -> str:
    material = "\x1f".join(clean_text(item).casefold() for item in parts)
    return f"LOCAL-{prefix}-{hashlib.sha256(material.encode('utf-8')).hexdigest()[:20]}"


def header_index(headers: list[str], field: str) -> int | None:
    for alias in ALIASES[field]:
        if alias in headers:
            return headers.index(alias)
    return None


def _row_record(headers: list[str], row: tuple[Any, ...]) -> dict[str, Any]:
    record: dict[str, Any] = {}
    for field in ALIASES:
        index = header_index(headers, field)
        record[field] = row[index] if index is not None and index < len(row) else None
    return record


def read_xlsx_records(path: Path, worksheet_name: str | None = None) -> tuple[str, list[str], list[dict[str, Any]]]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        worksheet = (
            workbook[worksheet_name]
            if worksheet_name is not None
            else workbook.worksheets[0]
        )
        worksheet.reset_dimensions()
        iterator = worksheet.iter_rows(values_only=True)
        header_values = next(iterator, ())
        headers = [clean_text(value) for value in header_values]
        rows: list[dict[str, Any]] = []
        for row in iterator:
            if not any(clean_text(value) for value in row):
                continue
            rows.append(_row_record(headers, row))
        return worksheet.title, headers, rows
    finally:
        workbook.close()


def read_csv_records(path: Path) -> tuple[str, list[str], list[dict[str, Any]]]:
    payload = path.read_bytes()
    text = None
    for encoding in ("utf-8-sig", "utf-16", "gb18030"):
        try:
            text = payload.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError(f"无法识别CSV编码: {path.name}")
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",\t;")
    except csv.Error:
        dialect = csv.excel
    iterator = csv.reader(text.splitlines(), dialect)
    headers = [clean_text(value) for value in next(iterator, [])]
    rows = [
        _row_record(headers, tuple(row))
        for row in iterator
        if any(clean_text(value) for value in row)
    ]
    return "CSV", headers, rows


def read_records(path: Path, worksheet_name: str | None = None) -> tuple[str, list[str], list[dict[str, Any]]]:
    if path.suffix.casefold() == ".csv":
        return read_csv_records(path)
    return read_xlsx_records(path, worksheet_name)


def normalized_metrics(record: dict[str, Any]) -> dict[str, Decimal | int]:
    values: dict[str, Decimal | int] = {}
    for field in METRIC_FIELDS:
        parsed = parse_decimal(record.get(field)) or Decimal("0")
        if field in COUNT_FIELDS:
            values[field] = int(parsed)
        else:
            values[field] = parsed
    return values


def total_metrics(rows: Iterable[dict[str, Any]]) -> dict[str, Decimal | int]:
    total: dict[str, Decimal | int] = {
        "impressions": 0,
        "clicks": 0,
        "orders": 0,
        "spend": Decimal("0"),
        "sales": Decimal("0"),
    }
    for row in rows:
        metrics = normalized_metrics(row)
        for field in METRIC_FIELDS:
            total[field] += metrics[field]
    return total


def source_period(rows: list[dict[str, Any]]) -> tuple[date | None, date | None]:
    dates: list[date] = []
    for row in rows:
        for field in ("date", "period_start", "period_end"):
            value = parse_date(row.get(field))
            if value is not None:
                dates.append(value)
    if not dates:
        return None, None
    return min(dates), max(dates)


def discover_window_reports(source_dir: Path) -> dict[tuple[str, str, int], Path]:
    reports: dict[tuple[str, str, int], Path] = {}
    pattern = re.compile(r"^(?P<family>.+?)-(?P<grain>每日明细|汇总)-近(?P<days>7|14|30)天\.xlsx$")
    for path in sorted(source_dir.glob("*.xlsx")):
        match = pattern.match(path.name)
        if not match:
            continue
        family_name = match.group("family")
        if family_name not in REPORT_FAMILIES:
            continue
        key = (
            REPORT_FAMILIES[family_name],
            "DAILY" if match.group("grain") == "每日明细" else "SUMMARY",
            int(match.group("days")),
        )
        if key in reports:
            raise ValueError(f"重复窗口报表: {key}")
        reports[key] = path
    expected = {
        (family, grain, days)
        for family in REPORT_FAMILIES.values()
        for grain in ("DAILY", "SUMMARY")
        for days in (7, 14, 30)
    }
    missing = sorted(expected - set(reports))
    if missing:
        raise ValueError("缺少窗口报表: " + ", ".join(map(str, missing)))
    return reports


def normalize_daily_row(family: str, row: dict[str, Any]) -> dict[str, Any]:
    metrics = normalized_metrics(row)
    return {
        "date": parse_date(row.get("date")),
        "portfolio": clean_text(row.get("portfolio")),
        "currency": clean_text(row.get("currency")).upper(),
        "marketplace": clean_text(row.get("marketplace")),
        "campaign": clean_text(row.get("campaign")),
        "ad_group": clean_text(row.get("ad_group")),
        "target": clean_text(row.get("target")),
        "match_type": clean_text(row.get("match_type")),
        "search_term": clean_text(row.get("search_term")),
        "placement": clean_text(row.get("placement")),
        "sku": clean_text(row.get("sku")),
        "asin": clean_text(row.get("asin")).upper(),
        **metrics,
        "family": family,
    }


def comparison_row(
    family: str,
    check: str,
    provided: dict[str, Decimal | int],
    canonical: dict[str, Decimal | int],
) -> dict[str, Any]:
    differences = {
        field: Decimal(provided[field]) - Decimal(canonical[field])
        for field in METRIC_FIELDS
    }
    status = "PASS" if all(value == 0 for value in differences.values()) else "WARNING"
    return {
        "family": family,
        "check": check,
        "canonical_usage": "VALIDATION_ONLY" if check != "D30_DAILY_CANONICAL" else "CANONICAL_FACT_SOURCE",
        "status": status,
        **{f"provided_{field}": provided[field] for field in METRIC_FIELDS},
        **{f"canonical_{field}": canonical[field] for field in METRIC_FIELDS},
        **{f"difference_{field}": differences[field] for field in METRIC_FIELDS},
    }


def window_checks(
    loaded: dict[tuple[str, str, int], list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for family in REPORT_FAMILIES.values():
        daily_30 = loaded[(family, "DAILY", 30)]
        end = max(parse_date(row.get("date")) for row in daily_30 if parse_date(row.get("date")))
        totals_30 = total_metrics(daily_30)
        checks.append(comparison_row(family, "D30_DAILY_CANONICAL", totals_30, totals_30))
        for days in (7, 14):
            start = end - timedelta(days=days - 1)
            canonical_slice = [
                row for row in daily_30
                if (value := parse_date(row.get("date"))) is not None and start <= value <= end
            ]
            checks.append(
                comparison_row(
                    family,
                    f"D{days}_DAILY_VS_D30_SLICE",
                    total_metrics(loaded[(family, "DAILY", days)]),
                    total_metrics(canonical_slice),
                )
            )
        checks.append(
            comparison_row(
                family,
                "D30_SUMMARY_VS_D30_DAILY",
                total_metrics(loaded[(family, "SUMMARY", 30)]),
                totals_30,
            )
        )
    return checks


def aggregate_windows(
    rows: list[dict[str, Any]],
    *,
    key_fields: tuple[str, ...],
    period_label: str,
    end_date: date,
    windows: tuple[tuple[str, int], ...],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for window_name, days in windows:
        start_date = end_date - timedelta(days=days - 1)
        grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            row_date = row.get("date")
            if row_date is None or not start_date <= row_date <= end_date:
                continue
            key = tuple(clean_text(row.get(field)) for field in key_fields)
            grouped[key].append(row)
        for key, members in sorted(grouped.items()):
            totals = total_metrics(members)
            values = dict(zip(key_fields, key))
            family = clean_text(members[0].get("family"))
            if family == "SEARCH_TERM":
                object_type = "SEARCH_TERM"
                label = values.get("search_term", "")
                identifier = local_id("ST", *(values.get(field, "") for field in key_fields))
            elif family == "TARGET":
                object_type = "TARGET"
                label = values.get("target", "")
                identifier = local_id("T", *(values.get(field, "") for field in key_fields))
            elif family == "PLACEMENT":
                object_type = "PLACEMENT"
                label = values.get("placement", "")
                identifier = local_id("P", *(values.get(field, "") for field in key_fields))
            else:
                object_type = "ADVERTISED_PRODUCT"
                label = " | ".join(item for item in (values.get("asin", ""), values.get("sku", "")) if item)
                identifier = local_id("SKU", *(values.get(field, "") for field in key_fields))
            result.append(
                {
                    "period_label": period_label,
                    "object_type": object_type,
                    "local_object_id": identifier,
                    "campaign": values.get("campaign", ""),
                    "ad_group": values.get("ad_group", ""),
                    "object_label": label,
                    "window": window_name,
                    "period_start": start_date,
                    "period_end": end_date,
                    **totals,
                    "identity_quality": "DERIVED_NAME_KEY_ANALYSIS_ONLY",
                }
            )
    return result


def campaign_metrics_from_rows(
    rows: list[dict[str, Any]],
    *,
    period_label: str,
    end_date: date,
    windows: tuple[tuple[str, int], ...],
) -> list[dict[str, Any]]:
    campaign_rows = [dict(row, family="CAMPAIGN") for row in rows]
    result: list[dict[str, Any]] = []
    for window_name, days in windows:
        start_date = end_date - timedelta(days=days - 1)
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in campaign_rows:
            if row.get("date") is None or not start_date <= row["date"] <= end_date:
                continue
            grouped[(clean_text(row.get("campaign")), clean_text(row.get("ad_group")))].append(row)
        for (campaign, ad_group), members in sorted(grouped.items()):
            result.append(
                {
                    "period_label": period_label,
                    "object_type": "CAMPAIGN",
                    "local_object_id": local_id("C", campaign),
                    "campaign": campaign,
                    "ad_group": ad_group,
                    "object_label": campaign,
                    "window": window_name,
                    "period_start": start_date,
                    "period_end": end_date,
                    **total_metrics(members),
                    "identity_quality": "DERIVED_NAME_KEY_ANALYSIS_ONLY",
                }
            )
    return result


def aggregate_current_store_metrics(
    rows: list[dict[str, Any]],
    *,
    period_start: date,
    period_end: date,
) -> list[dict[str, Any]]:
    """Keep store-order metrics separate from Amazon Ads attribution metrics."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        row_date = row.get("date")
        if row_date is None or not period_start <= row_date <= period_end:
            continue
        grouped[(clean_text(row.get("asin")), clean_text(row.get("sku")))].append(row)
    result: list[dict[str, Any]] = []
    for (asin, sku), members in sorted(grouped.items()):
        result.append(
            {
                "asin": asin,
                "sku": sku,
                "period_start": period_start,
                "period_end": period_end,
                "store_orders": sum(
                    (Decimal(row.get("store_orders", 0)) for row in members),
                    Decimal("0"),
                ),
                "store_sales": sum(
                    (Decimal(row.get("store_sales", 0)) for row in members),
                    Decimal("0"),
                ),
                "source_grain": "ADVERTISED_PRODUCT_DAILY_STORE_METRICS",
            }
        )
    return result


def load_old_product_workbook(path: Path) -> dict[str, Any]:
    sheet_names = {
        "settings": "新广告设置表",
        "search": "搜索词报告",
        "placement": "广告位报告",
        "product": "广告商品报告",
        "keyword": "关键词报告",
    }
    loaded: dict[str, Any] = {}
    for key, worksheet in sheet_names.items():
        title, headers, rows = read_records(path, worksheet)
        loaded[key] = {"worksheet": title, "headers": headers, "rows": rows}
    return loaded


def normalize_old_daily(kind: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        target = clean_text(row.get("target"))
        if kind == "SEARCH_TERM" and target in {"", "--", "-"}:
            target = clean_text(row.get("keyword"))
        normalized.append(
            {
                "date": parse_date(row.get("date")),
                "portfolio": clean_text(row.get("portfolio")),
                "currency": "USD",
                "marketplace": clean_text(row.get("marketplace")),
                "campaign": clean_text(row.get("campaign")),
                "ad_group": clean_text(row.get("ad_group")),
                "target": target,
                "match_type": clean_text(row.get("match_type")),
                "search_term": clean_text(row.get("search_term")),
                "placement": clean_text(row.get("placement")),
                "sku": clean_text(row.get("sku")),
                "asin": clean_text(row.get("asin")).upper(),
                **normalized_metrics(row),
                "store_orders": parse_decimal(row.get("store_orders")) or Decimal("0"),
                "store_sales": parse_decimal(row.get("store_sales")) or Decimal("0"),
                "family": kind,
            }
        )
    return normalized


def settings_rows_from_sources(
    settings_path: Path,
    selected_campaigns: set[str],
    old_workbook: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    _, _, historical = read_records(settings_path)
    rows: list[dict[str, Any]] = []
    for row in historical:
        campaign = clean_text(row.get("campaign"))
        if campaign not in selected_campaigns:
            continue
        rows.append(
            {
                "period_label": "HISTORICAL_30D",
                "campaign": campaign,
                "ad_group": "",
                "local_campaign_id": local_id("C", campaign),
                "status": clean_text(row.get("campaign_status")),
                "daily_budget": parse_decimal(row.get("daily_budget")),
                "default_bid": None,
                "targeting_type": clean_text(row.get("targeting_type")),
                "bidding_strategy": clean_text(row.get("bidding_strategy")),
                "identity_quality": "DERIVED_NAME_KEY_ANALYSIS_ONLY",
            }
        )
    if old_workbook is None:
        return rows
    for row in old_workbook["settings"]["rows"]:
        ad_group = clean_text(row.get("ad_group"))
        if not ad_group:
            continue
        rows.append(
            {
                "period_label": "CURRENT_SHORT_PERIOD",
                "campaign": ad_group,
                "ad_group": ad_group,
                "local_campaign_id": local_id("C", ad_group),
                "status": "SOURCE_NOT_PROVIDED",
                "daily_budget": parse_decimal(row.get("daily_budget")),
                "default_bid": parse_decimal(row.get("default_bid")),
                "targeting_type": clean_text(row.get("match_type")),
                "bidding_strategy": "SOURCE_NOT_PROVIDED",
                "identity_quality": "DERIVED_NAME_KEY_ANALYSIS_ONLY",
            }
        )
    return rows


def evidence_row(path: Path, role: str, worksheet: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    start, end = source_period(rows)
    return {
        "role": role,
        "file_name": path.name,
        "worksheet": worksheet,
        "row_count": len(rows),
        "period_start": start,
        "period_end": end,
        "sha256": sha256_file(path),
        "source_path": str(path),
    }


def build_name_keyed_analysis(
    source_dir: Path,
    old_product_path: Path | None,
    primary_asin: str,
    *,
    timezone_name: str = "America/Los_Angeles",
) -> dict[str, Any]:
    primary_asin = primary_asin.upper()
    report_paths = discover_window_reports(source_dir)
    loaded_rows: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    evidence: list[dict[str, Any]] = []
    for key, path in sorted(report_paths.items()):
        worksheet, _, rows = read_records(path)
        loaded_rows[key] = rows
        evidence.append(evidence_row(path, "/".join(map(str, key)), worksheet, rows))

    checks = window_checks(loaded_rows)
    canonical: dict[str, list[dict[str, Any]]] = {
        family: [normalize_daily_row(family, row) for row in loaded_rows[(family, "DAILY", 30)]]
        for family in REPORT_FAMILIES.values()
    }
    historical_end = max(row["date"] for row in canonical["ADVERTISED_PRODUCT"] if row["date"])
    historical_start = historical_end - timedelta(days=29)
    product_rows = [row for row in canonical["ADVERTISED_PRODUCT"] if row["asin"] == primary_asin]
    if not product_rows:
        raise ValueError(f"30天广告商品明细中未找到ASIN: {primary_asin}")
    selected_pairs = {(row["campaign"], row["ad_group"]) for row in product_rows}
    selected_campaigns = {item[0] for item in selected_pairs}

    filtered = {
        "SEARCH_TERM": [
            row for row in canonical["SEARCH_TERM"]
            if (row["campaign"], row["ad_group"]) in selected_pairs
        ],
        "TARGET": [
            row for row in canonical["TARGET"]
            if (row["campaign"], row["ad_group"]) in selected_pairs
        ],
        "PLACEMENT": [
            row for row in canonical["PLACEMENT"]
            if row["campaign"] in selected_campaigns
        ],
        "ADVERTISED_PRODUCT": product_rows,
    }
    historical_windows = (("D3", 3), ("D7", 7), ("D14", 14), ("D30", 30))
    historical_metrics = {
        "campaign": campaign_metrics_from_rows(
            filtered["SEARCH_TERM"],
            period_label="HISTORICAL_30D",
            end_date=historical_end,
            windows=historical_windows,
        ),
        "target": aggregate_windows(
            filtered["TARGET"],
            key_fields=("campaign", "ad_group", "target", "match_type"),
            period_label="HISTORICAL_30D",
            end_date=historical_end,
            windows=historical_windows,
        ),
        "search_term": aggregate_windows(
            filtered["SEARCH_TERM"],
            key_fields=("campaign", "ad_group", "target", "match_type", "search_term"),
            period_label="HISTORICAL_30D",
            end_date=historical_end,
            windows=historical_windows,
        ),
        "placement": aggregate_windows(
            filtered["PLACEMENT"],
            key_fields=("campaign", "placement"),
            period_label="HISTORICAL_30D",
            end_date=historical_end,
            windows=historical_windows,
        ),
        "product": aggregate_windows(
            filtered["ADVERTISED_PRODUCT"],
            key_fields=("campaign", "ad_group", "sku", "asin"),
            period_label="HISTORICAL_30D",
            end_date=historical_end,
            windows=historical_windows,
        ),
    }

    old_workbook: dict[str, Any] | None = None
    if old_product_path is not None:
        old_workbook = load_old_product_workbook(old_product_path)
        evidence.append(
            {
                "role": "CURRENT_OLD_PRODUCT_WORKBOOK",
                "file_name": old_product_path.name,
                "worksheet": "多工作表",
                "row_count": sum(len(item["rows"]) for item in old_workbook.values()),
                "period_start": None,
                "period_end": None,
                "sha256": sha256_file(old_product_path),
                "source_path": str(old_product_path),
            }
        )
        current_normalized = {
            "SEARCH_TERM": normalize_old_daily("SEARCH_TERM", old_workbook["search"]["rows"]),
            "PLACEMENT": normalize_old_daily("PLACEMENT", old_workbook["placement"]["rows"]),
            "ADVERTISED_PRODUCT": normalize_old_daily("ADVERTISED_PRODUCT", old_workbook["product"]["rows"]),
        }
        current_dates = sorted(
            row["date"]
            for family_rows in current_normalized.values()
            for row in family_rows
            if row["date"] is not None
        )
        if not current_dates:
            raise ValueError("老品工作簿没有可解析的每日日期")
        current_start, current_end = current_dates[0], current_dates[-1]
        current_days = (current_end - current_start).days + 1
        current_window = ((f"CURRENT_{current_days}D", current_days),)
        current_period_label = "CURRENT_SHORT_PERIOD"
        current_target_rows = current_normalized["SEARCH_TERM"]
        current_product_keys = ("asin", "sku")
    else:
        current_end = historical_end
        current_start = historical_end - timedelta(days=6)
        current_days = 7
        current_window = (("LATEST_D7", 7),)
        current_period_label = "LATEST_REPORT_WINDOW"
        current_normalized = filtered
        current_target_rows = current_normalized["TARGET"]
        current_product_keys = ("campaign", "ad_group", "sku", "asin")

    current_metrics = {
        "campaign": campaign_metrics_from_rows(
            current_normalized["SEARCH_TERM"],
            period_label=current_period_label,
            end_date=current_end,
            windows=current_window,
        ),
        "target": aggregate_windows(
            current_target_rows,
            key_fields=("campaign", "ad_group", "target", "match_type"),
            period_label=current_period_label,
            end_date=current_end,
            windows=current_window,
        ),
        "search_term": aggregate_windows(
            current_normalized["SEARCH_TERM"],
            key_fields=("campaign", "ad_group", "target", "match_type", "search_term"),
            period_label=current_period_label,
            end_date=current_end,
            windows=current_window,
        ),
        "placement": aggregate_windows(
            current_normalized["PLACEMENT"],
            key_fields=("campaign", "placement"),
            period_label=current_period_label,
            end_date=current_end,
            windows=current_window,
        ),
        "product": aggregate_windows(
            current_normalized["ADVERTISED_PRODUCT"],
            key_fields=current_product_keys,
            period_label=current_period_label,
            end_date=current_end,
            windows=current_window,
        ),
    }
    current_store_metrics = (
        aggregate_current_store_metrics(
            current_normalized["ADVERTISED_PRODUCT"],
            period_start=current_start,
            period_end=current_end,
        )
        if old_workbook is not None
        else []
    )

    settings_path = source_dir / "Campaign___Ad_Group_设置表-汇总-近30天.csv"
    if not settings_path.is_file():
        raise FileNotFoundError(settings_path)
    settings_sheet, _, settings_source_rows = read_records(settings_path)
    evidence.append(evidence_row(settings_path, "CAMPAIGN_SETTINGS_30D", settings_sheet, settings_source_rows))
    hourly_path = source_dir / "小时预算___小时花费报告-汇总-近30天.xlsx"
    if not hourly_path.is_file():
        raise FileNotFoundError(hourly_path)
    hourly_sheet, hourly_headers, hourly_rows = read_records(hourly_path)
    evidence.append(evidence_row(hourly_path, "ACCOUNT_TOTAL_NOT_HOURLY", hourly_sheet, hourly_rows))
    settings = settings_rows_from_sources(settings_path, selected_campaigns, old_workbook)

    gap_days = (current_start - historical_end).days - 1 if old_workbook is not None else 0
    issues = [
        {
            "level": "BLOCK_EXECUTION",
            "code": "IMMUTABLE_AMAZON_IDS_MISSING",
            "message": "源报表只有名称，没有Campaign/Ad Group/Target不可变ID；本包仅供分析，禁止生成后台执行动作。",
        },
    ]
    if old_workbook is not None:
        issues.extend(
            [
                {
                    "level": "WARNING",
                    "code": "CURRENT_PERIOD_SHORT",
                    "message": f"老品当前数据只有{current_days}个自然日（{current_start}..{current_end}），不得当作成熟D7/D14/D30样本。",
                },
                {
                    "level": "WARNING",
                    "code": "NON_CONTIGUOUS_PERIODS",
                    "message": f"历史数据结束于{historical_end}，当前数据开始于{current_start}，中间空缺{gap_days}天；两个周期独立保存。",
                },
            ]
        )
    else:
        issues.append(
            {
                "level": "WARNING",
                "code": "LATEST_D7_DERIVED_FROM_30D_REPORT",
                "message": f"未提供额外当前快照；当前窗口固定取30天每日事实源的最后7天（{current_start}..{current_end}），不得重复累加7/14天导出。",
            }
        )
    if "小时" not in hourly_headers and "Hour" not in hourly_headers:
        issues.append(
            {
                "level": "BLOCK_RULE_CALIBRATION",
                "code": "HOURLY_GRAIN_MISSING",
                "message": "小时预算/花费文件只有30天汇总，没有小时字段和预算字段，不能校准分时花费曲线。",
            }
        )
    for check in checks:
        if check["status"] != "PASS":
            issues.append(
                {
                    "level": "WARNING",
                    "code": "OVERLAPPING_EXPORT_DIFFERENCE",
                    "message": f"{check['family']} {check['check']} 与30天事实源存在差异；未叠加，只用于校验。",
                }
            )

    payload_material = {
        "primary_asin": primary_asin,
        "historical_start": historical_start.isoformat(),
        "historical_end": historical_end.isoformat(),
        "current_start": current_start.isoformat(),
        "current_end": current_end.isoformat(),
        "source_hashes": [(item["file_name"], item["sha256"]) for item in evidence],
    }
    snapshot_id = "NAMEKEY-" + hashlib.sha256(
        json.dumps(payload_material, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:20]
    generated_at = datetime.now(ZoneInfo(timezone_name))
    return {
        "schema_version": "1.0",
        "profile": "NAME_KEYED_ANALYSIS_ONLY",
        "data_snapshot_id": snapshot_id,
        "generated_at": generated_at,
        "category": "rug",
        "marketplace": "US",
        "currency": "USD",
        "timezone": timezone_name,
        "attribution_window_days": 7,
        "primary_asin": primary_asin,
        "analysis_status": "READY_WITH_WARNINGS",
        "execution_status": "BLOCKED_MISSING_IMMUTABLE_IDS",
        "deduplication_rule": "30天每日明细为唯一事实源；7天/14天及汇总表只校验，不参与重复求和。",
        "periods": {
            "historical": {"start": historical_start, "end": historical_end, "days": 30},
            "current": {"start": current_start, "end": current_end, "days": current_days},
            "gap_days": gap_days,
        },
        "selected_historical_campaigns": sorted(selected_campaigns),
        "window_checks": checks,
        "historical_metrics": historical_metrics,
        "current_metrics": current_metrics,
        "current_store_metrics": current_store_metrics,
        "settings": settings,
        "issues": issues,
        "evidence": evidence,
    }


def build_workbook(payload_path: Path, output_path: Path, preview_dir: Path | None) -> None:
    node, node_modules = locate_node_runtime()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_dir = Path(tempfile.mkdtemp(prefix="ad-namekey-node-"))
    try:
        (runtime_dir / "node_modules").symlink_to(node_modules, target_is_directory=True)
        command = [str(node), str(WORKBOOK_BUILDER), str(payload_path), str(output_path)]
        if preview_dir is not None:
            command.append(str(preview_dir))
        env = os.environ.copy()
        env["NODE_PATH"] = str(node_modules)
        subprocess.run(command, cwd=runtime_dir, env=env, check=True, text=True)
    finally:
        for child in runtime_dir.iterdir():
            if child.is_symlink():
                child.unlink()
        runtime_dir.rmdir()


def write_outputs(payload: dict[str, Any], output_dir: Path, *, render_previews: bool) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    packet_path = output_dir / "ad_analysis_packet.json"
    workbook_path = output_dir / "ad_analysis_packet.xlsx"
    dq_path = output_dir / "data_quality_report.json"
    manifest_path = output_dir / "aggregation_manifest.json"
    write_json(packet_path, payload)
    write_json(
        dq_path,
        {
            "data_snapshot_id": payload["data_snapshot_id"],
            "analysis_status": payload["analysis_status"],
            "execution_status": payload["execution_status"],
            "issues": payload["issues"],
        },
    )
    write_json(
        manifest_path,
        {
            "tool": "ad_report_aggregator/name_keyed_analysis",
            "tool_version": "V2.0",
            "data_snapshot_id": payload["data_snapshot_id"],
            "deduplication_rule": payload["deduplication_rule"],
            "execution_enabled": False,
            "evidence": payload["evidence"],
            "outputs": {
                "packet": packet_path,
                "workbook": workbook_path,
                "data_quality": dq_path,
            },
        },
    )
    preview_dir = output_dir / "previews" if render_previews else None
    build_workbook(packet_path, workbook_path, preview_dir)
    return {
        "packet": packet_path,
        "workbook": workbook_path,
        "data_quality": dq_path,
        "manifest": manifest_path,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="聚合7/14/30天重叠广告报表，并把无Amazon ID的数据限制为名称键分析包。"
    )
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--old-product-workbook")
    parser.add_argument("--primary-asin", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--render-previews", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_name_keyed_analysis(
        Path(args.source_dir).expanduser().resolve(),
        Path(args.old_product_workbook).expanduser().resolve() if args.old_product_workbook else None,
        args.primary_asin,
    )
    outputs = write_outputs(
        payload,
        Path(args.output_dir).expanduser().resolve(),
        render_previews=args.render_previews,
    )
    print(f"Data Snapshot: {payload['data_snapshot_id']}")
    print(f"Analysis status: {payload['analysis_status']}")
    print(f"Execution status: {payload['execution_status']}")
    print(f"Workbook: {outputs['workbook']}")
    print(f"Agent JSON: {outputs['packet']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
