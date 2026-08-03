from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from ai_ads.arbitration import arbitrate_actions
from ai_ads.contracts import (
    ActionType,
    AdContext,
    AdDecisionPacket,
    AdGroupFact,
    AdPlanCandidate,
    AdProductType,
    BusinessMode,
    BudgetType,
    CampaignFact,
    CandidateAction,
    DecisionConfidence,
    DataMode,
    InventoryState,
    PlanMetadata,
    PrimaryObjective,
    PriorityTier,
    ReconciliationStatus,
    ReportSource,
    ReportType,
    RiskLevel,
    RulePackageReference,
    RuleSourceStatus,
    SearchTermFact,
    SnapshotMetadata,
    StrategyProfile,
    TargetFact,
    MetricSample,
    MetricWindow,
    ObjectMetricFact,
    ObjectType,
)


NOW = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def report_sources() -> list[ReportSource]:
    required = [
        ReportType.SEARCH_TERM_DAILY,
        ReportType.SEARCH_TERM_SUMMARY,
        ReportType.TARGETING,
        ReportType.PLACEMENT,
        ReportType.ADVERTISED_PRODUCT,
        ReportType.CAMPAIGN_SETTINGS,
    ]
    return [
        ReportSource(
            report_type=report_type,
            file_name=f"{report_type.value}.xlsx",
            sha256=_hash(report_type.value),
            imported_at=NOW,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 30),
            row_count=10,
        )
        for report_type in required
    ]


def packet(
    *,
    data_mode: DataMode = DataMode.FULL,
    reconciliation_status: ReconciliationStatus = ReconciliationStatus.PASS,
) -> AdDecisionPacket:
    return AdDecisionPacket(
        metadata=SnapshotMetadata(
            schema_version="1.0",
            data_snapshot_id="SNAP-001",
            generated_at=NOW,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 30),
            marketplace="US",
            timezone="America/Los_Angeles",
            currency="USD",
            attribution_window_days=7,
            data_mode=data_mode,
            reconciliation_status=reconciliation_status,
        ),
        report_sources=report_sources(),
        campaigns=[
            CampaignFact(
                campaign_id="C-001",
                campaign_name="campaign",
                daily_budget=Decimal("100"),
                status="ENABLED",
            )
        ],
        ad_groups=[
            AdGroupFact(
                ad_group_id="G-001",
                campaign_id="C-001",
                ad_group_name="group",
                default_bid=Decimal("1.00"),
                status="ENABLED",
            )
        ],
        targets=[
            TargetFact(
                target_id="T-001",
                campaign_id="C-001",
                ad_group_id="G-001",
                target_text="washable area rug",
                match_type="EXACT",
                bid=Decimal("1.00"),
                status="ENABLED",
            )
        ],
        search_terms=[
            SearchTermFact(
                search_term_key="S-001",
                campaign_id="C-001",
                ad_group_id="G-001",
                target_id="T-001",
                search_term="washable area rug",
            )
        ],
        metrics=[
            ObjectMetricFact(
                object_type=ObjectType.TARGET,
                object_id="T-001",
                samples=[
                    MetricSample(
                        window=MetricWindow.D30,
                        period_start=date(2026, 7, 1),
                        period_end=date(2026, 7, 30),
                        impressions=1000,
                        clicks=100,
                        orders=Decimal("10"),
                        spend=Decimal("100"),
                        sales=Decimal("500"),
                    )
                ],
            )
        ],
    )


def context(*, protected_entities: list[str] | None = None) -> AdContext:
    return AdContext(
        schema_version="1.0",
        ad_context_version="CTX-001",
        valid_until=NOW + timedelta(days=7),
        marketplace="US",
        account_id="ACCOUNT-001",
        link_id="ASIN-001",
        category="rug",
        ad_product_type=AdProductType.SP,
        strategy_profile=StrategyProfile.SP_STANDARD_OPTIMIZATION,
        business_mode=BusinessMode.NORMAL,
        primary_objective=PrimaryObjective.ACOS,
        inventory_state=InventoryState.ASSUMED_SUFFICIENT,
        protected_entities=protected_entities or [],
    )


def package(
    *,
    rule_status: RuleSourceStatus = RuleSourceStatus.PROVIDED_FOR_TEST,
    threshold_status: RuleSourceStatus = RuleSourceStatus.PROVIDED_FOR_TEST,
) -> RulePackageReference:
    return RulePackageReference(
        rule_package_version="TEST-0.1",
        rule_package_checksum="0" * 64,
        rule_file_sha256="1" * 64,
        threshold_file_sha256="2" * 64,
        rule_source_status=rule_status,
        threshold_source_status=threshold_status,
        source_descriptor="synthetic test fixture",
    )


def action(
    *,
    action_id: str = "A-001",
    action_type: ActionType = ActionType.INCREASE_BID,
    object_type: ObjectType = ObjectType.TARGET,
    object_id: str = "T-001",
    priority: PriorityTier = PriorityTier.PRIMARY_OBJECTIVE,
    risk: RiskLevel = RiskLevel.LOW,
    current_value: Decimal | str | bool | None = Decimal("1.00"),
    proposed_value: Decimal | str | bool | None = Decimal("1.10"),
    is_primary: bool = True,
) -> CandidateAction:
    return CandidateAction(
        candidate_action_id=action_id,
        batch_id="BATCH-001",
        ad_product_type=AdProductType.SP,
        strategy_profile=StrategyProfile.SP_STANDARD_OPTIMIZATION,
        object_type=object_type,
        object_id=object_id,
        action_level="TARGET",
        action_type=action_type,
        priority_tier=priority,
        current_value=current_value,
        proposed_value=proposed_value,
        expected_current_value=current_value,
        unit="USD",
        source_module="synthetic_test",
        rule_id="RULE-TEST",
        threshold_id="THRESHOLD-TEST",
        evidence_refs=["SNAP-001/T-001"],
        confidence=DecisionConfidence.HIGH,
        budget_type=(
            BudgetType.EXPANSION
            if action_type in {ActionType.INCREASE_BUDGET, ActionType.DECREASE_BUDGET}
            else None
        ),
        calculation_basis=(
            "synthetic test basis"
            if action_type in {ActionType.INCREASE_BUDGET, ActionType.DECREASE_BUDGET}
            else None
        ),
        target_orders_per_day=(
            Decimal("1")
            if action_type in {ActionType.INCREASE_BUDGET, ActionType.DECREASE_BUDGET}
            else None
        ),
        budget_purpose=(
            "synthetic validation"
            if action_type in {ActionType.INCREASE_BUDGET, ActionType.DECREASE_BUDGET}
            else None
        ),
        expected_impact="test",
        risk_level=risk,
        reversible=True,
        rollback_value=current_value,
        valid_until=NOW + timedelta(days=1),
        review_metrics=["ACOS"],
        observation_days=7,
        is_primary=is_primary,
    )


def plan(actions: list[CandidateAction]) -> tuple[AdPlanCandidate, object]:
    arbitration = arbitrate_actions("BATCH-001", actions)
    candidate = AdPlanCandidate(
        metadata=PlanMetadata(
            schema_version="1.0",
            plan_id="PLAN-001",
            batch_id="BATCH-001",
            data_snapshot_id="SNAP-001",
            ad_context_version="CTX-001",
            ad_product_type=AdProductType.SP,
            strategy_profile=StrategyProfile.SP_STANDARD_OPTIMIZATION,
            rule_package_version="TEST-0.1",
            rule_package_checksum="0" * 64,
            model_version="DETERMINISTIC-TEST",
            prompt_version="NOT_APPLICABLE",
            generated_at=NOW,
            valid_until=NOW + timedelta(days=1),
        ),
        actions=arbitration.selected_actions,
        rejected_actions=arbitration.rejected_actions,
    )
    return candidate, arbitration
