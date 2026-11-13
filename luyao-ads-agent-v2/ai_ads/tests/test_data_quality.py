from datetime import date
from decimal import Decimal

from ai_ads.contracts import (
    AdGroupFact,
    CampaignFact,
    DataMode,
    DataQualityStatus,
    MetricWindow,
    ReconciliationStatus,
    SearchTermFact,
    TargetFact,
)
from ai_ads.data_quality import assess_data_quality
from ai_ads.tests.factories import packet


def test_complete_consistent_packet_passes() -> None:
    report = assess_data_quality(packet())
    assert report.status == DataQualityStatus.DQ_PASS
    assert report.findings == []


def test_one_campaign_two_ad_groups_blocks() -> None:
    source = packet()
    source.ad_groups.append(
        AdGroupFact(
            ad_group_id="G-002",
            campaign_id="C-001",
            ad_group_name="second",
            status="ENABLED",
        )
    )
    report = assess_data_quality(source)
    assert report.status == DataQualityStatus.DQ_BLOCKED
    assert any(
        item.code == "CAMPAIGN_AD_GROUP_CARDINALITY"
        for item in report.findings
    )


def test_unmapped_search_term_warns() -> None:
    source = packet()
    source.search_terms[0].target_id = None
    report = assess_data_quality(source)
    assert report.status == DataQualityStatus.DQ_WARNING
    assert any(item.code == "SEARCH_TERM_TARGET_UNMAPPED" for item in report.findings)


def test_full_packet_missing_required_reports_blocks() -> None:
    source = packet()
    source.report_sources = source.report_sources[:2]
    report = assess_data_quality(source)
    assert report.status == DataQualityStatus.DQ_BLOCKED
    assert any(item.code == "MANDATORY_REPORTS_MISSING" for item in report.findings)


def test_limited_packet_without_reconciliation_only_warns() -> None:
    source = packet(
        data_mode=DataMode.LIMITED,
        reconciliation_status=ReconciliationStatus.NOT_CONFIGURED,
    )
    source.report_sources = []
    report = assess_data_quality(source)
    assert report.status == DataQualityStatus.DQ_WARNING


def test_empty_full_packet_and_zero_row_report_shells_block() -> None:
    source = packet()
    source.campaigns = []
    source.ad_groups = []
    source.targets = []
    source.search_terms = []
    source.metrics = []
    source.report_sources = [item.model_copy(update={"row_count": 0}) for item in source.report_sources]

    report = assess_data_quality(source)
    assert report.status == DataQualityStatus.DQ_BLOCKED
    codes = {item.code for item in report.findings}
    assert "MANDATORY_REPORT_EMPTY" in codes
    assert "FULL_PACKET_FACTS_EMPTY" in codes


def test_report_period_must_match_snapshot_period() -> None:
    source = packet()
    source.report_sources = [
        item.model_copy(
            update={
                "period_start": date(2025, 1, 1),
                "period_end": date(2025, 1, 30),
            }
        )
        for item in source.report_sources
    ]
    report = assess_data_quality(source)
    assert report.status == DataQualityStatus.DQ_BLOCKED
    assert any(item.code == "REPORT_SNAPSHOT_PERIOD_MISMATCH" for item in report.findings)


def test_search_term_target_must_share_the_same_parent_chain() -> None:
    source = packet()
    source.campaigns.append(
        CampaignFact(
            campaign_id="C-002",
            campaign_name="second",
            daily_budget=Decimal("50"),
            status="ENABLED",
        )
    )
    source.ad_groups.append(
        AdGroupFact(
            ad_group_id="G-002",
            campaign_id="C-002",
            ad_group_name="second",
            status="ENABLED",
        )
    )
    source.targets.append(
        TargetFact(
            target_id="T-002",
            campaign_id="C-002",
            ad_group_id="G-002",
            target_text="runner rug",
            match_type="EXACT",
            bid=Decimal("1"),
            status="ENABLED",
        )
    )
    source.search_terms[0] = SearchTermFact(
        search_term_key="S-001",
        campaign_id="C-001",
        ad_group_id="G-001",
        target_id="T-002",
        search_term="washable area rug",
    )
    report = assess_data_quality(source)
    assert report.status == DataQualityStatus.DQ_BLOCKED
    assert any(item.code == "SEARCH_TERM_TARGET_PARENT_MISMATCH" for item in report.findings)


def test_model_copy_cannot_bypass_metric_funnel_or_window_checks() -> None:
    source = packet()
    current = source.metrics[0].samples[0]
    invalid = current.model_copy(
        update={
            "window": MetricWindow.D3,
            "impressions": 100,
            "clicks": 200,
            "orders": Decimal("300"),
        }
    )
    source.metrics[0] = source.metrics[0].model_copy(update={"samples": [invalid]})
    report = assess_data_quality(source)
    assert report.status == DataQualityStatus.DQ_BLOCKED
    codes = {item.code for item in report.findings}
    assert "IMPOSSIBLE_METRIC_FUNNEL" in codes
    assert "METRIC_WINDOW_LENGTH_MISMATCH" in codes


def test_metric_object_without_samples_blocks_full_packet() -> None:
    source = packet()
    source.metrics[0] = source.metrics[0].model_copy(update={"samples": []})
    report = assess_data_quality(source)
    assert report.status == DataQualityStatus.DQ_BLOCKED
    assert any(item.code == "METRIC_SAMPLES_EMPTY" for item in report.findings)
