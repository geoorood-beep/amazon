#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "reference" / "category-history" / "rug" / "raw"
NORMALIZED_DIR = PROJECT_DIR / "reference" / "category-history" / "rug" / "normalized"
INGEST_DATE = "20260707"
REPORT_YEAR = 2026

SOURCES = [
    Path("/Users/leo/Downloads/亚马逊-冬豚-US-US-关键词分析-0408-0706-汇总-932758699202043904.xlsx"),
    Path("/Users/leo/Downloads/亚马逊-岚风-US-US-关键词分析-0106-0706-汇总-932759690372714496.xlsx"),
]


def parse_date_range(name: str) -> tuple[str, str, str]:
    match = re.search(r"-(\d{4})-(\d{4})-汇总", name)
    if not match:
        return "", "", ""
    start_raw, end_raw = match.groups()
    start = f"{REPORT_YEAR}-{start_raw[:2]}-{start_raw[2:]}"
    end = f"{REPORT_YEAR}-{end_raw[:2]}-{end_raw[2:]}"
    return start, end, f"{start_raw}-{end_raw}"


def parse_source_product(name: str) -> str:
    parts = name.split("-")
    if len(parts) >= 2:
        return parts[1]
    return ""


def to_number(value) -> float | None:
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip().replace(",", "")
        if value in {"", "--", "有花费无订单", "有花费无销售额"}:
            return None
        if value.endswith("%"):
            try:
                return float(value[:-1]) / 100
            except ValueError:
                return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def infer_subcategory(term: str) -> str:
    t = term.lower()
    if any(x in t for x in ["runner", "hallway", "stair runner"]):
        return "runner rug"
    if any(x in t for x in ["kitchen", "anti fatigue"]):
        return "kitchen rug"
    if any(x in t for x in ["bath", "bathroom", "shower"]):
        return "bathroom rug"
    if any(x in t for x in ["doormat", "door mat", "entryway", "front door", "welcome mat"]):
        return "doormat"
    if any(x in t for x in ["round", "circle", "circular", "oval"]):
        return "round rug"
    if any(x in t for x in ["area rug", "living room", "bedroom", "rug"]):
        return "area rug"
    return "rug"


def clean_keyword(term: str) -> str:
    return re.sub(r"\s+", " ", str(term).replace("+", " ").strip()).strip().lower()


def load_source(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=0)
    source_product = parse_source_product(path.name)
    date_start, date_end, raw_range = parse_date_range(path.name)

    rows = []
    for _, row in df.iterrows():
        term = row.get("关键词")
        if pd.isna(term) or not str(term).strip():
            continue
        ad_orders = to_number(row.get("广告订单")) or 0
        if ad_orders <= 0:
            continue
        clicks = to_number(row.get("点击"))
        spend = to_number(row.get("花费"))
        sales = to_number(row.get("广告销售额"))
        cpa = to_number(row.get("CPA"))
        cvr = to_number(row.get("CVR"))
        acos = to_number(row.get("ACoS"))
        if cpa is None and spend is not None and ad_orders:
            cpa = spend / ad_orders
        if cvr is None and clicks:
            cvr = ad_orders / clicks
        if acos is None and spend is not None and sales:
            acos = spend / sales

        cleaned = clean_keyword(term)
        rows.append(
            {
                "category": "rug",
                "subcategory": infer_subcategory(cleaned),
                "source_product": source_product,
                "source_asin": "",
                "source_sku": "",
                "date_start": date_start,
                "date_end": date_end,
                "search_term": cleaned,
                "original_keyword": str(term).strip(),
                "translation": row.get("中文翻译") if not pd.isna(row.get("中文翻译")) else "",
                "campaign": "",
                "ad_group": "",
                "match_type": "",
                "targeting": cleaned,
                "campaign_count": to_number(row.get("广告活动投放")),
                "impressions": to_number(row.get("曝光量")),
                "clicks": clicks,
                "spend": spend,
                "ad_orders": ad_orders,
                "direct_orders": to_number(row.get("直接订单")),
                "indirect_orders": to_number(row.get("间接订单")),
                "sales": sales,
                "direct_sales": to_number(row.get("直接销售额")),
                "indirect_sales": to_number(row.get("间接销售额")),
                "acos": acos,
                "cvr": cvr,
                "cpa": cpa,
                "cpc": to_number(row.get("CPC")),
                "ctr": to_number(row.get("CTR")),
                "currency": "USD",
                "source_file": path.name,
                "source_report_type": "keyword_analysis_summary",
                "source_date_range_raw": raw_range,
                "data_confidence": "中",
                "notes": "关键词分析汇总表；缺 Campaign / Ad Group 明细，可作 Rug 历史出单词和效果词参考，不替代当前链接真实报表。",
            }
        )
    return pd.DataFrame(rows)


def join_unique(values) -> str:
    unique = []
    for value in values:
        if pd.isna(value) or value == "":
            continue
        text = str(value)
        if text not in unique:
            unique.append(text)
    return "; ".join(unique)


def build_summary(detail: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        detail.groupby("search_term", as_index=False)
        .agg(
            subcategory=("subcategory", lambda x: join_unique(x)),
            source_products=("source_product", lambda x: join_unique(x)),
            source_files=("source_file", lambda x: join_unique(x)),
            source_count=("source_product", "nunique"),
            clicks=("clicks", "sum"),
            spend=("spend", "sum"),
            ad_orders=("ad_orders", "sum"),
            direct_orders=("direct_orders", "sum"),
            indirect_orders=("indirect_orders", "sum"),
            sales=("sales", "sum"),
            impressions=("impressions", "sum"),
        )
    )
    grouped["cpa"] = grouped["spend"] / grouped["ad_orders"]
    grouped["cvr"] = grouped["ad_orders"] / grouped["clicks"]
    grouped["acos"] = grouped["spend"] / grouped["sales"]
    grouped["currency"] = "USD"
    grouped["data_confidence"] = "中"
    grouped["notes"] = "按 search_term 聚合；用于 Rug 新品选词历史参考。"
    return grouped.sort_values(["ad_orders", "sales", "clicks"], ascending=[False, False, False])


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)

    details = []
    raw_targets = []
    for source in SOURCES:
        if not source.exists():
            raise FileNotFoundError(source)
        source_product = parse_source_product(source.name)
        _, _, raw_range = parse_date_range(source.name)
        raw_target = RAW_DIR / f"{INGEST_DATE}_rug_{source_product}_US_keyword_analysis_{raw_range}.xlsx"
        shutil.copy2(source, raw_target)
        raw_targets.append(raw_target)
        details.append(load_source(source))

    detail = pd.concat(details, ignore_index=True)
    summary = build_summary(detail)

    output = NORMALIZED_DIR / f"{INGEST_DATE}_rug_historical_search_terms_normalized.xlsx"
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        detail.to_excel(writer, sheet_name="historical_order_terms", index=False)
        summary.to_excel(writer, sheet_name="term_summary", index=False)

    print(f"normalized={output}")
    for raw in raw_targets:
        print(f"raw={raw}")
    print(f"detail_rows={len(detail)}")
    print(f"unique_terms={detail['search_term'].nunique()}")
    print(f"total_orders={int(detail['ad_orders'].sum())}")
    print(f"total_clicks={int(detail['clicks'].sum())}")
    print(f"total_spend={detail['spend'].sum():.2f}")
    print(f"total_sales={detail['sales'].sum():.2f}")
    print("by_source_product")
    print(detail.groupby("source_product").agg(rows=("search_term", "count"), unique_terms=("search_term", "nunique"), orders=("ad_orders", "sum"), clicks=("clicks", "sum"), spend=("spend", "sum"), sales=("sales", "sum")).to_string())


if __name__ == "__main__":
    main()
