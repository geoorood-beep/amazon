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
    asin: str | None = None
    sku: str | None = None
    category: str
    rug_type: str
    scene_tags: list[str] = Field(default_factory=list)
    order_target_daily: float
    region_tags: list[str] = Field(default_factory=list)
    size_spec: str | None = None
    material: str | None = None
    style: str | None = None
    color: str | None = None
    avg_order_value: float | None = None
    target_acos: float | None = None
    target_cpa: float | None = None
    business_goal: str = "新品验证"
    product_stage: str = "new_test"

    @field_validator("order_target_daily", "avg_order_value", "target_acos", "target_cpa", mode="before")
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

    @field_validator("clicks", "orders", "aba_rank", mode="before")
    @classmethod
    def _parse_int_fields(cls, value: Any) -> int:
        parsed = parse_int(value)
        if parsed is None:
            raise ValueError("integer value is required")
        return parsed

    @field_validator("cvr", "cpa", mode="before")
    @classmethod
    def _parse_number_fields(cls, value: Any) -> float | None:
        return parse_number(value)

    @field_validator("order_dates", mode="before")
    @classmethod
    def _parse_dates_field(cls, value: Any) -> list[str]:
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
    aba_stage_ok: bool = False


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
