from __future__ import annotations

import csv
from datetime import date, timedelta
import json
from pathlib import Path
from typing import Any


REPORT_FILES = {
    "sp_search_terms_daily": "SP搜索词-按词-每日明细.csv",
    "sp_search_terms_summary": "SP搜索词-按词-汇总.csv",
    "sp_targeting": "SP投放对象报告.csv",
    "sp_placement": "SP广告位报告.csv",
    "sp_advertised_product": "SP广告商品报告.csv",
    "campaign_ad_group_settings": "Campaign Ad Group 设置表.csv",
}


def write_csv(path: Path, headers: list[str], rows: list[list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def create_synthetic_reports(
    source_dir: Path,
    *,
    period_start: date = date(2026, 7, 1),
    days: int = 30,
    term_count: int = 1,
    attribution_window_days: int = 7,
    summary_spend_delta: float = 0,
    currency: str = "USD",
    duplicate_daily_row: bool = False,
    malformed_clicks: bool = False,
    extra_ad_group: bool = False,
) -> tuple[Path, Path]:
    source_dir.mkdir(parents=True, exist_ok=True)
    period_end = period_start + timedelta(days=days - 1)
    context = {
        "schema_version": "1.0",
        "category": "rug",
        "marketplace": "US",
        "account_id": "ACCOUNT-SYNTHETIC",
        "link_id": "ASIN-SYNTHETIC",
        "timezone": "America/Los_Angeles",
        "currency": "USD",
        "attribution_window_days": attribution_window_days,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "notes": "synthetic regression fixture",
    }
    context_path = source_dir / "context.json"
    context_path.write_text(json.dumps(context, indent=2), encoding="utf-8")

    daily_headers = [
        "Date",
        "Campaign ID",
        "Ad Group ID",
        "Target ID",
        "Customer Search Term",
        "Impressions",
        "Clicks",
        "7 Day Total Orders (#)",
        "Spend",
        "7 Day Total Sales",
        "Currency",
        "Marketplace",
    ]
    daily_rows: list[list[Any]] = []
    for offset in range(days):
        current = period_start + timedelta(days=offset)
        for index in range(term_count):
            clicks: Any = 10
            if malformed_clicks and offset == 0 and index == 0:
                clicks = "not-a-number"
            daily_rows.append(
                [
                    current.isoformat(),
                    "C-001",
                    "G-001",
                    "T-001",
                    f"washable area rug {index + 1}",
                    100,
                    clicks,
                    1,
                    "10.00",
                    "50.00",
                    currency,
                    "US",
                ]
            )
    if duplicate_daily_row and daily_rows:
        daily_rows.append(list(daily_rows[0]))
    write_csv(source_dir / REPORT_FILES["sp_search_terms_daily"], daily_headers, daily_rows)

    summary_headers = [
        "Start Date",
        "End Date",
        "Campaign ID",
        "Ad Group ID",
        "Target ID",
        "Customer Search Term",
        "Impressions",
        "Clicks",
        "7 Day Total Orders (#)",
        "Spend",
        "7 Day Total Sales",
        "Currency",
        "Marketplace",
    ]
    summary_rows = []
    for index in range(term_count):
        spend = days * 10 + (summary_spend_delta if index == 0 else 0)
        summary_rows.append(
            [
                period_start.isoformat(),
                period_end.isoformat(),
                "C-001",
                "G-001",
                "T-001",
                f"washable area rug {index + 1}",
                days * 100,
                days * 10,
                days,
                f"{spend:.2f}",
                f"{days * 50:.2f}",
                currency,
                "US",
            ]
        )
    write_csv(source_dir / REPORT_FILES["sp_search_terms_summary"], summary_headers, summary_rows)

    write_csv(
        source_dir / REPORT_FILES["sp_targeting"],
        [
            "Start Date",
            "End Date",
            "Campaign ID",
            "Ad Group ID",
            "Target ID",
            "Targeting",
            "Match Type",
            "Bid",
            "Target Status",
            "Currency",
            "Marketplace",
        ],
        [
            [
                period_start.isoformat(),
                period_end.isoformat(),
                "C-001",
                "G-001",
                "T-001",
                "washable area rug",
                "EXACT",
                "1.00",
                "ENABLED",
                currency,
                "US",
            ]
        ],
    )

    write_csv(
        source_dir / REPORT_FILES["sp_placement"],
        [
            "Start Date",
            "End Date",
            "Campaign ID",
            "Placement",
            "Impressions",
            "Clicks",
            "7 Day Total Orders (#)",
            "Spend",
            "7 Day Total Sales",
            "Currency",
            "Marketplace",
        ],
        [
            [
                period_start.isoformat(),
                period_end.isoformat(),
                "C-001",
                "Top of Search",
                days * term_count * 100,
                days * term_count * 10,
                days * term_count,
                f"{days * term_count * 10:.2f}",
                f"{days * term_count * 50:.2f}",
                currency,
                "US",
            ]
        ],
    )

    write_csv(
        source_dir / REPORT_FILES["sp_advertised_product"],
        [
            "Start Date",
            "End Date",
            "Campaign ID",
            "Ad Group ID",
            "Advertised SKU",
            "Advertised ASIN",
            "Impressions",
            "Clicks",
            "7 Day Total Orders (#)",
            "Spend",
            "7 Day Total Sales",
            "Currency",
            "Marketplace",
        ],
        [
            [
                period_start.isoformat(),
                period_end.isoformat(),
                "C-001",
                "G-001",
                "RUG-SKU-001",
                "B0RUGSYN001",
                days * term_count * 100,
                days * term_count * 10,
                days * term_count,
                f"{days * term_count * 10:.2f}",
                f"{days * term_count * 50:.2f}",
                currency,
                "US",
            ]
        ],
    )

    settings_rows = [
        [
            period_start.isoformat(),
            period_end.isoformat(),
            "C-001",
            "Rug Campaign",
            "ENABLED",
            "100.00",
            "G-001",
            "Rug Ad Group",
            "ENABLED",
            "1.00",
            currency,
            "US",
        ]
    ]
    if extra_ad_group:
        settings_rows.append(
            [
                period_start.isoformat(),
                period_end.isoformat(),
                "C-001",
                "Rug Campaign",
                "ENABLED",
                "100.00",
                "G-002",
                "Second Ad Group",
                "ENABLED",
                "1.00",
                currency,
                "US",
            ]
        )
    write_csv(
        source_dir / REPORT_FILES["campaign_ad_group_settings"],
        [
            "Start Date",
            "End Date",
            "Campaign ID",
            "Campaign Name",
            "Campaign Status",
            "Daily Budget",
            "Ad Group ID",
            "Ad Group Name",
            "Ad Group Status",
            "Default Bid",
            "Currency",
            "Marketplace",
        ],
        settings_rows,
    )
    return source_dir, context_path
