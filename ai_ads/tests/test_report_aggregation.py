from __future__ import annotations

import json

import pytest

from tools.ad_report_aggregator.aggregator import (
    DEFAULT_CONFIG,
    build_packet,
    load_json,
    write_outputs,
)
from tools.ad_report_aggregator.synthetic import REPORT_FILES, create_synthetic_reports


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
