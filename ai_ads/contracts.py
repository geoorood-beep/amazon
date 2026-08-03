from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _require_timezone_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include timezone information")


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class AdProductType(str, Enum):
    SP = "SP"
    SB = "SB"
    SD = "SD"


class StrategyProfile(str, Enum):
    SP_STANDARD_OPTIMIZATION = "SP_STANDARD_OPTIMIZATION"
    SP_COLD_START = "SP_COLD_START"


class BusinessMode(str, Enum):
    NORMAL = "NORMAL"
    EVENT = "EVENT"
    ANOMALY = "ANOMALY"


class InventoryState(str, Enum):
    ASSUMED_SUFFICIENT = "ASSUMED_SUFFICIENT"
    KNOWN_SUFFICIENT = "KNOWN_SUFFICIENT"
    RISK = "RISK"
    UNKNOWN = "UNKNOWN"


class DataMode(str, Enum):
    FULL = "FULL"
    LIMITED = "LIMITED"


class ReconciliationStatus(str, Enum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    PASS = "PASS"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class DataQualityStatus(str, Enum):
    DQ_PASS = "DQ_PASS"
    DQ_WARNING = "DQ_WARNING"
    DQ_BLOCKED = "DQ_BLOCKED"


class ReportType(str, Enum):
    SEARCH_TERM_DAILY = "SEARCH_TERM_DAILY"
    SEARCH_TERM_SUMMARY = "SEARCH_TERM_SUMMARY"
    TARGETING = "TARGETING"
    PLACEMENT = "PLACEMENT"
    ADVERTISED_PRODUCT = "ADVERTISED_PRODUCT"
    CAMPAIGN_SETTINGS = "CAMPAIGN_SETTINGS"
    PLACEMENT_DAILY = "PLACEMENT_DAILY"
    KEYWORD_DAILY = "KEYWORD_DAILY"
    HOURLY_SPEND = "HOURLY_SPEND"
    BUSINESS_TARGET = "BUSINESS_TARGET"


class MetricWindow(str, Enum):
    D3 = "D3"
    D7 = "D7"
    D14 = "D14"
    D30 = "D30"
    CUSTOM = "CUSTOM"


class ObjectType(str, Enum):
    CAMPAIGN = "CAMPAIGN"
    AD_GROUP = "AD_GROUP"
    TARGET = "TARGET"
    SEARCH_TERM = "SEARCH_TERM"
    PLACEMENT = "PLACEMENT"
    ADVERTISED_PRODUCT = "ADVERTISED_PRODUCT"
    STRUCTURE = "STRUCTURE"


class ActionType(str, Enum):
    INCREASE_BUDGET = "INCREASE_BUDGET"
    DECREASE_BUDGET = "DECREASE_BUDGET"
    INCREASE_BID = "INCREASE_BID"
    DECREASE_BID = "DECREASE_BID"
    SET_PLACEMENT = "SET_PLACEMENT"
    PAUSE = "PAUSE"
    ENABLE = "ENABLE"
    NEGATIVE_EXACT = "NEGATIVE_EXACT"
    CREATE_STRUCTURE = "CREATE_STRUCTURE"
    OBSERVE = "OBSERVE"


class PriorityTier(int, Enum):
    DATA_AND_MAPPING = 1
    CONTEXT_HARD_CONSTRAINT = 2
    RISK_CONTROL = 3
    PRIMARY_OBJECTIVE = 4
    CAMPAIGN_DIAGNOSIS = 5
    LOCAL_DIAGNOSIS = 6
    EXPLORATION = 7


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ValidationOutcome(str, Enum):
    AUTO_PASS = "AUTO_PASS"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    BLOCKED = "BLOCKED"


class FindingLevel(str, Enum):
    INFO = "INFO"
    APPROVAL = "APPROVAL"
    BLOCK = "BLOCK"


class RuleSourceStatus(str, Enum):
    UNDECIDED = "UNDECIDED"
    PROVIDED_FOR_TEST = "PROVIDED_FOR_TEST"
    ACTIVE = "ACTIVE"


class RunMode(str, Enum):
    TEST_ONLY = "TEST_ONLY"
    PRODUCTION = "PRODUCTION"


class ExecutionStatus(str, Enum):
    EXECUTED = "EXECUTED"
    SKIPPED = "SKIPPED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class ReviewEligibility(str, Enum):
    READY = "READY"
    NOT_READY = "NOT_READY"


class EvidenceClassification(str, Enum):
    SUPPORT = "SUPPORT"
    OPPOSE = "OPPOSE"
    INCONCLUSIVE = "INCONCLUSIVE"
    SCOPE_LIMITED = "SCOPE_LIMITED"
    CONFLICT = "CONFLICT"
    UNSTABLE = "UNSTABLE"


class PrimaryObjective(str, Enum):
    ACOS = "ACOS"
    CPA = "CPA"
    ORDERS = "ORDERS"
    PROFIT = "PROFIT"
    STRUCTURE = "STRUCTURE"


class SnapshotMetadata(StrictModel):
    schema_version: str
    data_snapshot_id: str
    generated_at: datetime
    period_start: date
    period_end: date
    marketplace: str
    timezone: str
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    attribution_window_days: int = Field(ge=0)
    data_mode: DataMode
    reconciliation_status: ReconciliationStatus

    @model_validator(mode="after")
    def validate_period(self) -> "SnapshotMetadata":
        _require_timezone_aware(self.generated_at, "generated_at")
        if self.period_end < self.period_start:
            raise ValueError("period_end cannot be earlier than period_start")
        return self


class ReportSource(StrictModel):
    report_type: ReportType
    file_name: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    imported_at: datetime
    period_start: date
    period_end: date
    row_count: int = Field(ge=0)
    worksheet: str | None = None

    @model_validator(mode="after")
    def validate_period(self) -> "ReportSource":
        _require_timezone_aware(self.imported_at, "imported_at")
        if self.period_end < self.period_start:
            raise ValueError("report period_end cannot be earlier than period_start")
        return self


class MetricSample(StrictModel):
    window: MetricWindow
    period_start: date
    period_end: date
    impressions: int = Field(default=0, ge=0)
    clicks: int = Field(default=0, ge=0)
    orders: Decimal = Field(default=Decimal("0"), ge=0)
    spend: Decimal = Field(default=Decimal("0"), ge=0)
    sales: Decimal = Field(default=Decimal("0"), ge=0)

    @model_validator(mode="after")
    def validate_period(self) -> "MetricSample":
        if self.period_end < self.period_start:
            raise ValueError("metric period_end cannot be earlier than period_start")
        if self.clicks > self.impressions:
            raise ValueError("clicks cannot exceed impressions")
        if self.orders > self.clicks:
            raise ValueError("orders cannot exceed clicks")
        if self.orders != self.orders.to_integral_value():
            raise ValueError("orders must be an integer count")
        expected_days = {
            MetricWindow.D3: 3,
            MetricWindow.D7: 7,
            MetricWindow.D14: 14,
            MetricWindow.D30: 30,
        }.get(self.window)
        actual_days = (self.period_end - self.period_start).days + 1
        if expected_days is not None and actual_days != expected_days:
            raise ValueError(
                f"{self.window.value} must cover exactly {expected_days} inclusive days"
            )
        return self


class DerivedMetrics(StrictModel):
    ctr: Decimal | None = None
    cvr: Decimal | None = None
    cpc: Decimal | None = None
    cpa: Decimal | None = None
    acos: Decimal | None = None


class CampaignFact(StrictModel):
    campaign_id: str
    campaign_name: str
    daily_budget: Decimal = Field(ge=0)
    status: str


class AdGroupFact(StrictModel):
    ad_group_id: str
    campaign_id: str
    ad_group_name: str
    default_bid: Decimal | None = Field(default=None, ge=0)
    status: str


class TargetFact(StrictModel):
    target_id: str
    campaign_id: str
    ad_group_id: str
    target_text: str
    match_type: str
    bid: Decimal = Field(ge=0)
    status: str


class SearchTermFact(StrictModel):
    search_term_key: str
    campaign_id: str
    ad_group_id: str
    target_id: str | None = None
    search_term: str


class ObjectMetricFact(StrictModel):
    object_type: ObjectType
    object_id: str
    samples: list[MetricSample] = Field(default_factory=list)


class ImportedDataIssue(StrictModel):
    code: str
    message: str
    object_type: ObjectType | None = None
    object_id: str | None = None
    blocking: bool = False


class AdDecisionPacket(StrictModel):
    metadata: SnapshotMetadata
    report_sources: list[ReportSource] = Field(default_factory=list)
    campaigns: list[CampaignFact] = Field(default_factory=list)
    ad_groups: list[AdGroupFact] = Field(default_factory=list)
    targets: list[TargetFact] = Field(default_factory=list)
    search_terms: list[SearchTermFact] = Field(default_factory=list)
    metrics: list[ObjectMetricFact] = Field(default_factory=list)
    imported_issues: list[ImportedDataIssue] = Field(default_factory=list)


class AdContext(StrictModel):
    schema_version: str
    ad_context_version: str
    valid_until: datetime
    marketplace: str
    account_id: str
    link_id: str
    category: str
    ad_product_type: AdProductType
    strategy_profile: StrategyProfile
    business_mode: BusinessMode = BusinessMode.NORMAL
    primary_objective: PrimaryObjective
    promotion_state: dict[str, Any] = Field(default_factory=dict)
    price_state: dict[str, Any] = Field(default_factory=dict)
    inventory_state: InventoryState
    budget_cap: Decimal | None = Field(default=None, ge=0)
    batch_budget_change_cap: Decimal | None = Field(default=None, ge=0)
    margin_floor: Decimal | None = None
    protected_entities: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_datetime(self) -> "AdContext":
        _require_timezone_aware(self.valid_until, "valid_until")
        return self


class RulePackageReference(StrictModel):
    rule_package_version: str
    rule_package_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    rule_file_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    threshold_file_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    rule_source_status: RuleSourceStatus
    threshold_source_status: RuleSourceStatus
    source_descriptor: str | None = None
    resolution_trace: list[str] = Field(default_factory=list)


ActionValue = Decimal | str | bool


class CandidateAction(StrictModel):
    candidate_action_id: str
    batch_id: str
    ad_product_type: AdProductType
    strategy_profile: StrategyProfile
    object_type: ObjectType
    object_id: str
    action_level: str
    action_type: ActionType
    priority_tier: PriorityTier
    current_value: ActionValue | None = None
    proposed_value: ActionValue | None = None
    expected_current_value: ActionValue | None = None
    unit: str | None = None
    source_module: str
    rule_id: str
    threshold_id: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    expected_impact: str
    risk_level: RiskLevel
    reversible: bool
    rollback_value: ActionValue | None = None
    valid_until: datetime
    preconditions: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)
    review_metrics: list[str] = Field(default_factory=list)
    observation_days: int = Field(ge=0)
    is_primary: bool = True
    action_pack_id: str | None = None

    @model_validator(mode="after")
    def validate_datetime(self) -> "CandidateAction":
        _require_timezone_aware(self.valid_until, "valid_until")
        return self


class RejectedAction(StrictModel):
    candidate_action_id: str
    reason_code: str
    reason: str


class ActionConflict(StrictModel):
    object_type: ObjectType
    object_id: str
    action_ids: list[str]
    code: str
    message: str


class ArbitrationResult(StrictModel):
    batch_id: str
    selected_actions: list[CandidateAction] = Field(default_factory=list)
    rejected_actions: list[RejectedAction] = Field(default_factory=list)
    conflicts: list[ActionConflict] = Field(default_factory=list)


class PlanMetadata(StrictModel):
    schema_version: str
    plan_id: str
    batch_id: str
    data_snapshot_id: str
    ad_context_version: str
    ad_product_type: AdProductType
    strategy_profile: StrategyProfile
    rule_package_version: str
    rule_package_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_version: str
    prompt_version: str
    generated_at: datetime
    valid_until: datetime

    @model_validator(mode="after")
    def validate_datetimes(self) -> "PlanMetadata":
        _require_timezone_aware(self.generated_at, "generated_at")
        _require_timezone_aware(self.valid_until, "valid_until")
        return self


class AdPlanCandidate(StrictModel):
    metadata: PlanMetadata
    actions: list[CandidateAction] = Field(default_factory=list)
    rejected_actions: list[RejectedAction] = Field(default_factory=list)


class ValidationFinding(StrictModel):
    code: str
    level: FindingLevel
    message: str
    action_id: str | None = None
    object_id: str | None = None


class ValidationReport(StrictModel):
    plan_id: str
    batch_id: str
    outcome: ValidationOutcome
    findings: list[ValidationFinding] = Field(default_factory=list)


class ActionExecutionRecord(StrictModel):
    action_id: str
    status: ExecutionStatus
    planned_value: ActionValue | None = None
    actual_value: ActionValue | None = None
    executed_at: datetime | None = None
    note: str | None = None


class ExecutionConfirmation(StrictModel):
    plan_id: str
    batch_id: str
    executed_as_planned: bool
    executed_at: datetime | None = None
    operator: str | None = None
    action_records: list[ActionExecutionRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_deviations(self) -> "ExecutionConfirmation":
        if self.executed_as_planned:
            if self.executed_at is None or not self.operator:
                raise ValueError("batch confirmation requires executed_at and operator")
        elif not self.action_records:
            raise ValueError("deviated execution requires action_records")
        return self


class ExternalEvent(StrictModel):
    event_type: str
    occurred_at: datetime
    description: str
    isolated: bool


class ReviewInput(StrictModel):
    plan_id: str
    batch_id: str
    execution_confirmation: ExecutionConfirmation | None
    before_snapshot_id: str | None
    after_snapshot_id: str | None
    observed_at: datetime
    attribution_complete_at: datetime
    metrics_comparable: bool
    secondary_adjustments_marked: bool
    overlapping_action_ids: list[str] = Field(default_factory=list)
    external_events: list[ExternalEvent] = Field(default_factory=list)


class ReviewEligibilityResult(StrictModel):
    plan_id: str
    batch_id: str
    eligibility: ReviewEligibility
    reasons: list[str] = Field(default_factory=list)
    evidence_classification: EvidenceClassification | None = None


class AdReviewSignal(StrictModel):
    schema_version: str
    plan_id: str
    batch_id: str
    action_id: str | None = None
    action_pack_id: str | None = None
    rule_id: str
    threshold_id: str | None = None
    classification: EvidenceClassification
    expected_direction: str
    actual_direction: str
    metric_changes: dict[str, Decimal | None] = Field(default_factory=dict)
    external_event_notes: list[str] = Field(default_factory=list)
    candidate_version: str | None = None
    continue_observing: list[str] = Field(default_factory=list)
