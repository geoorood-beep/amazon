from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def parse_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    if text.endswith("%"):
        return float(text[:-1]) / 100
    return float(text)


def parse_int(value: Any) -> int | None:
    parsed = parse_number(value)
    if parsed is None:
        return None
    return int(parsed)


def parse_dates(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    for separator in [";", "，", "|"]:
        text = text.replace(separator, ",")
    return [part.strip() for part in text.split(",") if part.strip()]


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FlexibleBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class ProductInfo(FlexibleBaseModel):
    spu: str | None = None
    asin: str | None = None
    sku: str | None = None
    category: str
    rug_type: str | None = None
    analysis_threshold_profile: str | None = None
    scene_tags: list[str] = Field(default_factory=list)
    order_target_daily: float = Field(gt=0)
    ad_group_order_target: float | None = Field(default=None, gt=0)
    region_tags: list[str] = Field(default_factory=list)
    size_spec: str | None = None
    material: str | None = None
    style: str | None = None
    color: str | None = None
    shape: str | None = None
    animal_pattern: str | None = None
    avg_order_value: float | None = Field(default=None, gt=0)
    target_acos: float | None = Field(default=None, gt=0)
    target_cpa: float | None = Field(default=None, gt=0)
    business_goal: str = "新品验证"
    product_stage: str = "new_test"
    operator_name: str = "lulu"

    @field_validator(
        "order_target_daily",
        "ad_group_order_target",
        "avg_order_value",
        "target_acos",
        "target_cpa",
        mode="before",
    )
    @classmethod
    def _parse_optional_number(cls, value: Any) -> float | None:
        return parse_number(value)


class HistoricalKeyword(FlexibleBaseModel):
    search_term: str
    clicks: int
    orders: int
    order_dates: list[str] = Field(default_factory=list)
    cvr: float
    aba_rank: int
    cpa: float | None = None
    evidence_grain: str = "CUSTOMER_SEARCH_TERM"
    source_report_type: str | None = None
    source_files: list[str] = Field(default_factory=list)
    aba_sources: list[str] = Field(default_factory=list)
    aba_conflict: bool = False
    compliance_status: str | None = None
    ad_status: str | None = None
    recommendation_tier: str | None = None
    normalized_root: str | None = None
    category_judgment: str | None = None
    detailed_category: str | None = None
    comprehensive_priority: str | None = None
    advertising_use: str | None = None
    aba_tags: list[str] = Field(default_factory=list)
    aba_rug_types: list[str] = Field(default_factory=list)
    aba_relevance_levels: list[str] = Field(default_factory=list)
    aba_judgment_reason: str | None = None
    relevance_evidence_status: str = "PENDING_SOURCE"
    relevance_level: str | None = None
    relevance_score: float | None = None
    relevance_reason: str | None = None
    relevance_source_files: list[str] = Field(default_factory=list)
    monthly_search_volume: float | None = None
    root_monthly_search_volume: float | None = None
    root_top3_volume_share: float | None = None
    root_distinct_query_count: int | None = None
    search_volume_months: list[str] = Field(default_factory=list)
    search_volume_source_files: list[str] = Field(default_factory=list)
    match_type_evidence_status: str = "PENDING_SOURCE"

    @field_validator("clicks", "orders", "aba_rank", mode="before")
    @classmethod
    def _parse_int_fields(cls, value: Any) -> int:
        parsed = parse_int(value)
        if parsed is None:
            raise ValueError("integer value is required")
        return parsed

    @field_validator(
        "cvr",
        "cpa",
        "relevance_score",
        "monthly_search_volume",
        "root_monthly_search_volume",
        "root_top3_volume_share",
        mode="before",
    )
    @classmethod
    def _parse_number_fields(cls, value: Any) -> float | None:
        return parse_number(value)

    @field_validator("order_dates", mode="before")
    @classmethod
    def _parse_dates_field(cls, value: Any) -> list[str]:
        return parse_dates(value)

    @field_validator("root_distinct_query_count", mode="before")
    @classmethod
    def _parse_optional_int_fields(cls, value: Any) -> int | None:
        return parse_int(value)

    @field_validator(
        "source_files",
        "aba_sources",
        "aba_tags",
        "aba_rug_types",
        "aba_relevance_levels",
        "relevance_source_files",
        "search_volume_months",
        "search_volume_source_files",
        mode="before",
    )
    @classmethod
    def _parse_string_lists(cls, value: Any) -> list[str]:
        return parse_dates(value)


class CandidateKeyword(HistoricalKeyword):
    pool_status: str = ""
    pool_reasons: list[str] = Field(default_factory=list)
    needs_review: bool = False


class StageMatchedKeyword(CandidateKeyword):
    order_stage: str
    aba_stage_ok: bool = False
    aba_stage_status: str = ""
    stage_min_match_score: float | None = None
    stage_max_keyword_count: int | None = None
    keyword_types: list[str] = Field(default_factory=list)


class KeywordScore(FlexibleBaseModel):
    asin: str | None = None
    order_stage: str
    search_term: str
    clicks: int
    orders: int
    cvr: float
    aba_rank: int
    transaction_data_score: float | None = None
    region_score: float | None = None
    spec_score: float | None = None
    style_score: float | None = None
    color_score: float | None = None
    total_match_score: float | None = None
    conclusion: str
    reasons: list[str] = Field(default_factory=list)
    needs_review: bool = False
    hard_conflict: bool = False
    attribute_conflicts: list[str] = Field(default_factory=list)
    aba_stage_ok: bool = False
    evidence_grain: str = "CUSTOMER_SEARCH_TERM"
    source_report_type: str | None = None
    source_files: list[str] = Field(default_factory=list)
    aba_sources: list[str] = Field(default_factory=list)
    compliance_status: str | None = None
    ad_status: str | None = None
    recommendation_tier: str | None = None
    normalized_root: str | None = None
    category_judgment: str | None = None
    detailed_category: str | None = None
    comprehensive_priority: str | None = None
    advertising_use: str | None = None
    aba_tags: list[str] = Field(default_factory=list)
    aba_rug_types: list[str] = Field(default_factory=list)
    aba_relevance_levels: list[str] = Field(default_factory=list)
    aba_judgment_reason: str | None = None
    relevance_evidence_status: str = "PENDING_SOURCE"
    relevance_level: str | None = None
    relevance_score: float | None = None
    relevance_reason: str | None = None
    relevance_source_files: list[str] = Field(default_factory=list)
    monthly_search_volume: float | None = None
    root_monthly_search_volume: float | None = None
    root_top3_volume_share: float | None = None
    root_distinct_query_count: int | None = None
    search_volume_months: list[str] = Field(default_factory=list)
    search_volume_source_files: list[str] = Field(default_factory=list)
    match_type_evidence_status: str = "PENDING_SOURCE"


class AdArchitectureRow(FlexibleBaseModel):
    ad_group_name: str
    asin: str | None = None
    ad_type: str
    budget: float | None = None
    bid: float | None = None
    strategy: str
    placement: str | None = None
    keyword: str
    rationale: str
    needs_review: bool = False
    reasons: list[str] = Field(default_factory=list)


class BlockedItem(FlexibleBaseModel):
    item_type: str
    identifier: str
    source_step: str
    reason: str
    data: dict[str, Any] = Field(default_factory=dict)


class ProductProfile(FlexibleBaseModel):
    asin_sku: str
    current_order_target: str
    core_diagnosis: str
    overall_strategy: str
    data_confidence: str
    rug_type: str | None = None
    analysis_threshold_profile: str | None = None
    target_size: str | None = None


class PipelineResult(FlexibleBaseModel):
    product_profile: ProductProfile
    keyword_scoring_table: list[KeywordScore] = Field(default_factory=list)
    ad_architecture: list[AdArchitectureRow] = Field(default_factory=list)
    blocked_items: list[BlockedItem] = Field(default_factory=list)


class RugTypeBaseline(FlexibleBaseModel):
    ctr_baseline: float | None = None
    cvr_baseline: float | None = None
    cpa_normal_line: float | None = None
    cpa_high_risk_line: float | None = None
    acos_target: float | None = None
    min_click_sample: int | None = None
    min_order_sample: int | None = None

    @field_validator(
        "ctr_baseline",
        "cvr_baseline",
        "cpa_normal_line",
        "cpa_high_risk_line",
        "acos_target",
        mode="before",
    )
    @classmethod
    def _parse_optional_float(cls, value: Any) -> float | None:
        return parse_number(value)

    @field_validator("min_click_sample", "min_order_sample", mode="before")
    @classmethod
    def _parse_optional_int(cls, value: Any) -> int | None:
        return parse_int(value)


class CandidatePoolThresholds(FlexibleBaseModel):
    min_independent_order_dates: int = 3
    min_click_sample: int | None = None
    min_order_sample: int | None = None


class ScoringWeights(FlexibleBaseModel):
    transaction_data: float = 0.60
    region_match: float = 0.15
    spec_match: float = 0.15
    style_match: float = 0.05
    color_match: float = 0.05
    cvr_score_multiplier: float = 2


class BudgetFormula(FlexibleBaseModel):
    product_coefficient_by_stage: dict[str, float | None] = Field(default_factory=dict)


class RiskConstraints(FlexibleBaseModel):
    inventory_redline: float | None = None
    profit_redline: float | None = None
    max_test_spend: float | None = None


class StageRule(FlexibleBaseModel):
    stage: str
    keyword_types: list[str] = Field(default_factory=list)
    min_match_score: float | None = None
    min_match_score_upper: float | None = None
    max_keyword_count: int | None = None
    min_daily_orders: float | None = None
    max_daily_orders: float | None = None

    def aba_range_for(self, rug_type: str) -> list[int] | None:
        key = f"{rug_type}_aba_range"
        value = getattr(self, key, None)
        if value is None and self.model_extra:
            value = self.model_extra.get(key)
        if value is None:
            return None
        return [int(value[0]), int(value[1])]


class CategoryRules(FlexibleBaseModel):
    version: str
    site: str
    category: str
    effective_date: str
    owner: str
    rug_type_baselines: dict[str, RugTypeBaseline]
    rug_size_type_mapping: dict[str, Any] = Field(default_factory=dict)
    rug_analysis_thresholds: dict[str, Any] = Field(default_factory=dict)
    global_ctr_baseline: float | None = None
    order_stage_aba_table: list[StageRule]
    candidate_pool_thresholds: CandidatePoolThresholds
    scoring_weights: ScoringWeights
    budget_formula: BudgetFormula
    risk_constraints: RiskConstraints
    attribute_scoring: dict[str, Any] = Field(default_factory=dict)
    strategy_rules: dict[str, Any] = Field(default_factory=dict)
    bid_defaults: dict[str, Any] = Field(default_factory=dict)
    placement_defaults: dict[str, Any] = Field(default_factory=dict)
