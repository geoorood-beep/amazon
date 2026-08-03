from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from openpyxl import Workbook

from tools.ad_report_aggregator.aggregator import (
    DEFAULT_CONFIG,
    build_packet,
    load_json,
    read_xlsx,
    write_outputs,
)
from tools.ad_report_aggregator.synthetic import REPORT_FILES, create_synthetic_reports
from tools.ad_report_aggregator.name_keyed_analysis import (
    REPORT_FAMILIES,
    aggregate_current_store_metrics,
    window_checks,
)


def test_valid_six_report_bundle_builds_dq_pass(tmp_path):
    source_dir, context_path = create_synthetic_reports(tmp_path / "source")
    packet, support = build_packet(
        source_dir,
        load_json(context_path),
        load_json(DEFAULT_CONFIG),
    )

    assert support["dq_report"].status.value == "DQ_PASS"
    assert packet.metadata.reconciliation_status.value == "PASS"
    assert len(packet.report_sources) == 6
    assert len(packet.campaigns) == 1
    assert len(packet.ad_groups) == 1
    assert len(packet.targets) == 1
    assert len(packet.search_terms) == 1
    assert any(row["object_label"] == "washable area rug 1" for row in support["agent_input_rows"])
    assert {sample.window.value for fact in packet.metrics for sample in fact.samples} >= {
        "D3",
        "D7",
        "D14",
        "D30",
        "CUSTOM",
    }


def test_reconciliation_mismatch_is_blocked(tmp_path):
    source_dir, context_path = create_synthetic_reports(
        tmp_path / "source", summary_spend_delta=1
    )
    packet, support = build_packet(
        source_dir,
        load_json(context_path),
        load_json(DEFAULT_CONFIG),
    )

    assert packet.metadata.reconciliation_status.value == "BLOCKED"
    assert support["dq_report"].status.value == "DQ_BLOCKED"
    assert any(
        finding.code == "SEARCH_TERM_RECONCILIATION_MISMATCH"
        for finding in support["dq_report"].findings
    )


def test_wrong_category_stops_before_report_analysis(tmp_path):
    source_dir, context_path = create_synthetic_reports(tmp_path / "source")
    context = load_json(context_path)
    context["category"] = "office_chair"

    with pytest.raises(ValueError, match="类目越界"):
        build_packet(source_dir, context, load_json(DEFAULT_CONFIG))


def test_missing_report_is_blocked_and_still_exports_json(tmp_path):
    source_dir, context_path = create_synthetic_reports(tmp_path / "source")
    (source_dir / REPORT_FILES["sp_placement"]).unlink()
    packet, support = build_packet(
        source_dir,
        load_json(context_path),
        load_json(DEFAULT_CONFIG),
    )
    output_dir = tmp_path / "output"
    outputs = write_outputs(packet, support, output_dir, workbook=False, render_previews=False)

    assert support["dq_report"].status.value == "DQ_BLOCKED"
    payload = json.loads(outputs["packet"].read_text(encoding="utf-8"))
    assert payload["metadata"]["data_mode"] == "FULL"
    assert any(issue["code"] == "MANDATORY_REPORT_MISSING" for issue in payload["imported_issues"])


def test_duplicate_daily_grain_and_multi_ad_group_are_blocked(tmp_path):
    source_dir, context_path = create_synthetic_reports(
        tmp_path / "source",
        duplicate_daily_row=True,
        extra_ad_group=True,
    )
    _, support = build_packet(
        source_dir,
        load_json(context_path),
        load_json(DEFAULT_CONFIG),
    )
    codes = {finding.code for finding in support["dq_report"].findings}
    assert support["dq_report"].status.value == "DQ_BLOCKED"
    assert "DUPLICATE_DAILY_GRAIN" in codes
    assert "CAMPAIGN_AD_GROUP_CARDINALITY" in codes


def test_non_numeric_metric_is_rejected(tmp_path):
    source_dir, context_path = create_synthetic_reports(
        tmp_path / "source", malformed_clicks=True
    )
    _, support = build_packet(
        source_dir,
        load_json(context_path),
        load_json(DEFAULT_CONFIG),
    )
    assert support["dq_report"].status.value == "DQ_BLOCKED"
    assert any(
        finding.code == "SOURCE_ROW_REJECTED" for finding in support["dq_report"].findings
    )


def test_attribution_window_header_mismatch_is_blocked(tmp_path):
    source_dir, context_path = create_synthetic_reports(tmp_path / "source")
    context = load_json(context_path)
    context["attribution_window_days"] = 14
    _, support = build_packet(source_dir, context, load_json(DEFAULT_CONFIG))

    assert support["dq_report"].status.value == "DQ_BLOCKED"
    assert any(
        finding.code == "REPORT_ATTRIBUTION_WINDOW_MISMATCH"
        for finding in support["dq_report"].findings
    )


def test_xlsx_reader_ignores_broken_a1_dimension_metadata(tmp_path):
    original = tmp_path / "original.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["Date", "Campaign ID", "Spend"])
    worksheet.append(["2026-07-01", "C-001", 1])
    worksheet.append(["2026-07-02", "C-001", 2])
    workbook.save(original)
    broken = tmp_path / "broken_dimension.xlsx"
    with ZipFile(original, "r") as source, ZipFile(broken, "w", ZIP_DEFLATED) as target:
        for info in source.infolist():
            payload = source.read(info.filename)
            if info.filename == "xl/worksheets/sheet1.xml":
                payload = payload.replace(
                    b'<dimension ref="A1:C3"/>',
                    b'<dimension ref="A1"/>',
                )
            target.writestr(info, payload)

    sheets = read_xlsx(broken)

    assert len(sheets) == 1
    assert len(sheets[0][1]) == 3
    assert sheets[0][1][0][0] == "Date"


def test_overlapping_windows_are_validation_only_and_use_d30_daily_slices():
    end = date(2026, 6, 29)
    daily_30 = [
        {
            "date": end - timedelta(days=offset),
            "impressions": 10,
            "clicks": 2,
            "orders": 1,
            "spend": Decimal("1.00"),
            "sales": Decimal("5.00"),
        }
        for offset in range(30)
    ]
    loaded = {}
    for family in REPORT_FAMILIES.values():
        loaded[(family, "DAILY", 30)] = list(daily_30)
        loaded[(family, "DAILY", 14)] = daily_30[:14]
        loaded[(family, "DAILY", 7)] = daily_30[:7]
        loaded[(family, "SUMMARY", 30)] = list(daily_30)

    checks = window_checks(loaded)

    assert len(checks) == 16
    assert all(row["canonical_usage"] in {"CANONICAL_FACT_SOURCE", "VALIDATION_ONLY"} for row in checks)
    assert all(row["status"] == "PASS" for row in checks)


def test_store_metrics_remain_separate_from_ad_attribution_metrics():
    rows = [
        {
            "date": date(2026, 7, 6),
            "asin": "B0H3642LQD",
            "sku": "SKU-1",
            "store_orders": Decimal("2"),
            "store_sales": Decimal("100.00"),
        },
        {
            "date": date(2026, 7, 7),
            "asin": "B0H3642LQD",
            "sku": "SKU-1",
            "store_orders": Decimal("3"),
            "store_sales": Decimal("259.95"),
        },
    ]

    result = aggregate_current_store_metrics(
        rows,
        period_start=date(2026, 7, 6),
        period_end=date(2026, 7, 9),
    )

    assert result == [
        {
            "asin": "B0H3642LQD",
            "sku": "SKU-1",
            "period_start": date(2026, 7, 6),
            "period_end": date(2026, 7, 9),
            "store_orders": Decimal("5"),
            "store_sales": Decimal("359.95"),
            "source_grain": "ADVERTISED_PRODUCT_DAILY_STORE_METRICS",
        }
    ]
