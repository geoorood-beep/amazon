from __future__ import annotations

from collections import Counter, defaultdict

from pydantic import Field

from .contracts import (
    AdDecisionPacket,
    DataMode,
    DataQualityStatus,
    FindingLevel,
    MetricWindow,
    ObjectType,
    ReconciliationStatus,
    ReportType,
    StrictModel,
    ValidationFinding,
)


MANDATORY_FULL_REPORTS = {
    ReportType.SEARCH_TERM_DAILY,
    ReportType.SEARCH_TERM_SUMMARY,
    ReportType.TARGETING,
    ReportType.PLACEMENT,
    ReportType.ADVERTISED_PRODUCT,
    ReportType.CAMPAIGN_SETTINGS,
}


class DataQualityReport(StrictModel):
    data_snapshot_id: str
    status: DataQualityStatus
    findings: list[ValidationFinding] = Field(default_factory=list)


def _duplicates(values: list[str]) -> set[str]:
    counts = Counter(values)
    return {value for value, count in counts.items() if count > 1}


def assess_data_quality(packet: AdDecisionPacket) -> DataQualityReport:
    findings: list[ValidationFinding] = []

    for label, values in (
        ("Campaign", [item.campaign_id for item in packet.campaigns]),
        ("Ad Group", [item.ad_group_id for item in packet.ad_groups]),
        ("Target", [item.target_id for item in packet.targets]),
        ("Search Term", [item.search_term_key for item in packet.search_terms]),
    ):
        for duplicate in sorted(_duplicates(values)):
            findings.append(
                ValidationFinding(
                    code="DUPLICATE_IMMUTABLE_ID",
                    level=FindingLevel.BLOCK,
                    message=f"{label} ID重复: {duplicate}",
                    object_id=duplicate,
                )
            )

    campaign_ids = {item.campaign_id for item in packet.campaigns}
    ad_group_ids = {item.ad_group_id for item in packet.ad_groups}
    target_ids = {item.target_id for item in packet.targets}

    campaign_ad_groups: dict[str, list[str]] = defaultdict(list)
    for ad_group in packet.ad_groups:
        campaign_ad_groups[ad_group.campaign_id].append(ad_group.ad_group_id)
        if ad_group.campaign_id not in campaign_ids:
            findings.append(
                ValidationFinding(
                    code="AD_GROUP_CAMPAIGN_NOT_FOUND",
                    level=FindingLevel.BLOCK,
                    message=f"Ad Group映射到不存在的Campaign: {ad_group.ad_group_id}",
                    object_id=ad_group.ad_group_id,
                )
            )

    for campaign_id in sorted(campaign_ids):
        mapped = campaign_ad_groups.get(campaign_id, [])
        if len(mapped) != 1:
            findings.append(
                ValidationFinding(
                    code="CAMPAIGN_AD_GROUP_CARDINALITY",
                    level=FindingLevel.BLOCK,
                    message=(
                        f"Campaign必须恰好对应1个Ad Group: {campaign_id}，"
                        f"当前={len(mapped)}"
                    ),
                    object_id=campaign_id,
                )
            )

    target_by_id = {item.target_id: item for item in packet.targets}
    ad_group_by_id = {item.ad_group_id: item for item in packet.ad_groups}
    for target in packet.targets:
        ad_group = ad_group_by_id.get(target.ad_group_id)
        if ad_group is None:
            findings.append(
                ValidationFinding(
                    code="TARGET_AD_GROUP_NOT_FOUND",
                    level=FindingLevel.BLOCK,
                    message=f"Target映射到不存在的Ad Group: {target.target_id}",
                    object_id=target.target_id,
                )
            )
        elif ad_group.campaign_id != target.campaign_id:
            findings.append(
                ValidationFinding(
                    code="TARGET_CAMPAIGN_MISMATCH",
                    level=FindingLevel.BLOCK,
                    message=f"Target的Campaign与Ad Group所属Campaign不一致: {target.target_id}",
                    object_id=target.target_id,
                )
            )

    for term in packet.search_terms:
        ad_group = ad_group_by_id.get(term.ad_group_id)
        target = target_by_id.get(term.target_id) if term.target_id is not None else None
        if term.campaign_id not in campaign_ids or ad_group is None:
            findings.append(
                ValidationFinding(
                    code="SEARCH_TERM_PARENT_NOT_FOUND",
                    level=FindingLevel.BLOCK,
                    message=f"搜索词父级对象不存在: {term.search_term_key}",
                    object_id=term.search_term_key,
                )
            )
        elif ad_group.campaign_id != term.campaign_id:
            findings.append(
                ValidationFinding(
                    code="SEARCH_TERM_CAMPAIGN_MISMATCH",
                    level=FindingLevel.BLOCK,
                    message=f"搜索词的Campaign与Ad Group所属Campaign不一致: {term.search_term_key}",
                    object_id=term.search_term_key,
                )
            )
        if term.target_id is None:
            findings.append(
                ValidationFinding(
                    code="SEARCH_TERM_TARGET_UNMAPPED",
                    level=FindingLevel.APPROVAL,
                    message=f"搜索词未映射Target: {term.search_term_key}",
                    object_id=term.search_term_key,
                )
            )
        elif term.target_id not in target_ids:
            findings.append(
                ValidationFinding(
                    code="SEARCH_TERM_TARGET_NOT_FOUND",
                    level=FindingLevel.BLOCK,
                    message=f"搜索词映射到不存在的Target: {term.search_term_key}",
                    object_id=term.search_term_key,
                )
            )
        elif target is not None and (
            target.campaign_id != term.campaign_id
            or target.ad_group_id != term.ad_group_id
        ):
            findings.append(
                ValidationFinding(
                    code="SEARCH_TERM_TARGET_PARENT_MISMATCH",
                    level=FindingLevel.BLOCK,
                    message=f"搜索词映射Target与搜索词父级链不一致: {term.search_term_key}",
                    object_id=term.search_term_key,
                )
            )

    known_ids = {
        ObjectType.CAMPAIGN: campaign_ids,
        ObjectType.AD_GROUP: ad_group_ids,
        ObjectType.TARGET: target_ids,
        ObjectType.SEARCH_TERM: {
            item.search_term_key for item in packet.search_terms
        },
    }
    seen_metric_keys: set[tuple[ObjectType, str, str]] = set()
    for metric in packet.metrics:
        if metric.object_type in known_ids and metric.object_id not in known_ids[metric.object_type]:
            findings.append(
                ValidationFinding(
                    code="METRIC_OBJECT_NOT_FOUND",
                    level=FindingLevel.BLOCK,
                    message=f"指标映射对象不存在: {metric.object_type.value}/{metric.object_id}",
                    object_id=metric.object_id,
                )
            )
        if not metric.samples:
            findings.append(
                ValidationFinding(
                    code="METRIC_SAMPLES_EMPTY",
                    level=FindingLevel.BLOCK,
                    message=f"指标对象没有任何窗口样本: {metric.object_type.value}/{metric.object_id}",
                    object_id=metric.object_id,
                )
            )
        for sample in metric.samples:
            key = (metric.object_type, metric.object_id, sample.window.value)
            if key in seen_metric_keys:
                findings.append(
                    ValidationFinding(
                        code="DUPLICATE_METRIC_WINDOW",
                        level=FindingLevel.BLOCK,
                        message=f"同一对象同一窗口指标重复: {key}",
                        object_id=metric.object_id,
                    )
                )
            seen_metric_keys.add(key)
            if sample.period_start < packet.metadata.period_start or sample.period_end > packet.metadata.period_end:
                findings.append(
                    ValidationFinding(
                        code="METRIC_PERIOD_OUTSIDE_SNAPSHOT",
                        level=FindingLevel.BLOCK,
                        message=f"指标窗口超出数据快照周期: {key}",
                        object_id=metric.object_id,
                    )
                )
            expected_days = {
                MetricWindow.D3: 3,
                MetricWindow.D7: 7,
                MetricWindow.D14: 14,
                MetricWindow.D30: 30,
            }.get(sample.window)
            actual_days = (sample.period_end - sample.period_start).days + 1
            if expected_days is not None and actual_days != expected_days:
                findings.append(
                    ValidationFinding(
                        code="METRIC_WINDOW_LENGTH_MISMATCH",
                        level=FindingLevel.BLOCK,
                        message=(
                            f"{sample.window.value}窗口应为{expected_days}个完整自然日，"
                            f"实际为{actual_days}日"
                        ),
                        object_id=metric.object_id,
                    )
                )
            if sample.clicks > sample.impressions or sample.orders > sample.clicks:
                findings.append(
                    ValidationFinding(
                        code="IMPOSSIBLE_METRIC_FUNNEL",
                        level=FindingLevel.BLOCK,
                        message="指标漏斗不成立：点击不得大于曝光，订单不得大于点击",
                        object_id=metric.object_id,
                    )
                )

    available_reports = {item.report_type for item in packet.report_sources}
    report_type_counts = Counter(item.report_type for item in packet.report_sources)
    for report_type, count in sorted(report_type_counts.items(), key=lambda item: item[0].value):
        if count > 1:
            findings.append(
                ValidationFinding(
                    code="DUPLICATE_REPORT_TYPE",
                    level=FindingLevel.BLOCK,
                    message=f"同一快照包含重复报表类型: {report_type.value}，数量={count}",
                )
            )
    for source in packet.report_sources:
        if (
            source.period_start != packet.metadata.period_start
            or source.period_end != packet.metadata.period_end
        ):
            findings.append(
                ValidationFinding(
                    code="REPORT_SNAPSHOT_PERIOD_MISMATCH",
                    level=FindingLevel.BLOCK,
                    message=(
                        f"报表周期与快照周期不一致: {source.report_type.value} "
                        f"{source.period_start}..{source.period_end}"
                    ),
                )
            )
        if (
            packet.metadata.data_mode == DataMode.FULL
            and source.report_type in MANDATORY_FULL_REPORTS
            and source.row_count == 0
        ):
            findings.append(
                ValidationFinding(
                    code="MANDATORY_REPORT_EMPTY",
                    level=FindingLevel.BLOCK,
                    message=f"完整模式必需报表为空: {source.report_type.value}",
                )
            )
    missing_reports = sorted(
        MANDATORY_FULL_REPORTS - available_reports,
        key=lambda item: item.value,
    )
    if missing_reports:
        level = (
            FindingLevel.BLOCK
            if packet.metadata.data_mode == DataMode.FULL
            else FindingLevel.APPROVAL
        )
        findings.append(
            ValidationFinding(
                code="MANDATORY_REPORTS_MISSING",
                level=level,
                message="缺少报表: " + ", ".join(item.value for item in missing_reports),
            )
        )

    if packet.metadata.data_mode == DataMode.FULL:
        required_facts = {
            "campaigns": packet.campaigns,
            "ad_groups": packet.ad_groups,
            "targets": packet.targets,
            "search_terms": packet.search_terms,
            "metrics": packet.metrics,
        }
        for fact_name, facts in required_facts.items():
            if not facts:
                findings.append(
                    ValidationFinding(
                        code="FULL_PACKET_FACTS_EMPTY",
                        level=FindingLevel.BLOCK,
                        message=f"完整模式解析结果为空: {fact_name}",
                    )
                )
    if packet.metadata.reconciliation_status == ReconciliationStatus.NOT_CONFIGURED:
        findings.append(
            ValidationFinding(
                code="RECONCILIATION_NOT_CONFIGURED",
                level=FindingLevel.APPROVAL,
                message="跨报表对账口径尚未配置，不能形成自动通过的执行方案",
            )
        )
    elif packet.metadata.reconciliation_status == ReconciliationStatus.WARNING:
        findings.append(
            ValidationFinding(
                code="RECONCILIATION_WARNING",
                level=FindingLevel.APPROVAL,
                message="跨报表对账存在允许范围内差异，需要人工复核",
            )
        )
    elif packet.metadata.reconciliation_status == ReconciliationStatus.BLOCKED:
        findings.append(
            ValidationFinding(
                code="RECONCILIATION_BLOCKED",
                level=FindingLevel.BLOCK,
                message="跨报表对账失败",
            )
        )

    for issue in packet.imported_issues:
        findings.append(
            ValidationFinding(
                code=issue.code,
                level=FindingLevel.BLOCK if issue.blocking else FindingLevel.APPROVAL,
                message=issue.message,
                object_id=issue.object_id,
            )
        )

    if any(item.level == FindingLevel.BLOCK for item in findings):
        status = DataQualityStatus.DQ_BLOCKED
    elif findings:
        status = DataQualityStatus.DQ_WARNING
    else:
        status = DataQualityStatus.DQ_PASS

    return DataQualityReport(
        data_snapshot_id=packet.metadata.data_snapshot_id,
        status=status,
        findings=findings,
    )
