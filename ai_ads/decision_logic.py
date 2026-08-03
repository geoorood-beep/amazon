from __future__ import annotations

from enum import Enum

from pydantic import Field

from .contracts import DataQualityStatus, StrictModel


class LowSamplePermission(str, Enum):
    NORMAL_RULES = "NORMAL_RULES"
    OBSERVE_ONLY = "OBSERVE_ONLY"
    APPROVAL_REQUIRED_CANDIDATE = "APPROVAL_REQUIRED_CANDIDATE"


class OverallState(str, Enum):
    DATA_BLOCKED = "DATA_BLOCKED"
    DATA_INSUFFICIENT = "DATA_INSUFFICIENT"
    TARGET_CATEGORY_RISK_CONFLICT = "TARGET_CATEGORY_RISK_CONFLICT"
    HIGH_RISK_WITH_VOLUME = "HIGH_RISK_WITH_VOLUME"
    HIGH_RISK_WITHOUT_VOLUME = "HIGH_RISK_WITHOUT_VOLUME"
    EFFICIENT_AT_TARGET = "EFFICIENT_AT_TARGET"
    EFFICIENT_STRUCTURE_RISK = "EFFICIENT_STRUCTURE_RISK"
    EFFICIENT_UNDERSCALE = "EFFICIENT_UNDERSCALE"
    VOLUME_ACHIEVED_COST_ABOVE_TARGET = "VOLUME_ACHIEVED_COST_ABOVE_TARGET"
    COST_ABOVE_TARGET_UNDERSCALE = "COST_ABOVE_TARGET_UNDERSCALE"
    INCONCLUSIVE = "INCONCLUSIVE"


class MetricDirection(str, Enum):
    IMPROVING = "IMPROVING"
    WORSENING = "WORSENING"
    STABLE = "STABLE"
    UNKNOWN = "UNKNOWN"


class TrendState(str, Enum):
    RECOVERY = "RECOVERY"
    DETERIORATION = "DETERIORATION"
    STABLE = "STABLE"
    MIXED_SIGNAL = "MIXED_SIGNAL"
    INCONCLUSIVE = "INCONCLUSIVE"


class LowSampleInput(StrictModel):
    orders: int = Field(ge=0)
    attribution_mature: bool
    category_stop_line_hit: bool
    target_mapping_complete: bool
    data_quality: DataQualityStatus


class OverallStateInput(StrictModel):
    data_quality: DataQualityStatus
    sample_sufficient: bool
    target_category_risk_conflict: bool
    category_high_risk: bool
    objective_met: bool
    volume_target_met: bool
    winner_spend_share_met: bool


class TrendInput(StrictModel):
    primary_direction: MetricDirection
    auxiliary_directions: list[MetricDirection] = Field(default_factory=list)


def evaluate_low_sample_permission(data: LowSampleInput) -> LowSamplePermission:
    if data.orders >= 2:
        return LowSamplePermission.NORMAL_RULES
    if (
        data.orders == 0
        and data.attribution_mature
        and data.category_stop_line_hit
        and data.target_mapping_complete
        and data.data_quality == DataQualityStatus.DQ_PASS
    ):
        return LowSamplePermission.APPROVAL_REQUIRED_CANDIDATE
    return LowSamplePermission.OBSERVE_ONLY


def determine_overall_state(data: OverallStateInput) -> OverallState:
    if data.data_quality == DataQualityStatus.DQ_BLOCKED:
        return OverallState.DATA_BLOCKED
    if not data.sample_sufficient:
        return OverallState.DATA_INSUFFICIENT
    if data.target_category_risk_conflict:
        return OverallState.TARGET_CATEGORY_RISK_CONFLICT
    if data.category_high_risk:
        return (
            OverallState.HIGH_RISK_WITH_VOLUME
            if data.volume_target_met
            else OverallState.HIGH_RISK_WITHOUT_VOLUME
        )
    if data.objective_met:
        if not data.volume_target_met:
            return OverallState.EFFICIENT_UNDERSCALE
        if not data.winner_spend_share_met:
            return OverallState.EFFICIENT_STRUCTURE_RISK
        return OverallState.EFFICIENT_AT_TARGET
    if data.volume_target_met:
        return OverallState.VOLUME_ACHIEVED_COST_ABOVE_TARGET
    return OverallState.COST_ABOVE_TARGET_UNDERSCALE


PLACEMENT_ROUTE = {
    OverallState.DATA_BLOCKED: False,
    OverallState.DATA_INSUFFICIENT: False,
    OverallState.TARGET_CATEGORY_RISK_CONFLICT: False,
    OverallState.HIGH_RISK_WITH_VOLUME: True,
    OverallState.HIGH_RISK_WITHOUT_VOLUME: True,
    OverallState.EFFICIENT_AT_TARGET: False,
    OverallState.EFFICIENT_STRUCTURE_RISK: False,
    OverallState.EFFICIENT_UNDERSCALE: True,
    OverallState.VOLUME_ACHIEVED_COST_ABOVE_TARGET: True,
    OverallState.COST_ABOVE_TARGET_UNDERSCALE: True,
    OverallState.INCONCLUSIVE: False,
}


def placement_diagnostic_allowed(state: OverallState) -> bool:
    return PLACEMENT_ROUTE[state]


def determine_trend_state(data: TrendInput) -> TrendState:
    directions = [
        item
        for item in data.auxiliary_directions
        if item not in {MetricDirection.UNKNOWN, MetricDirection.STABLE}
    ]
    opposite = {
        MetricDirection.IMPROVING: MetricDirection.WORSENING,
        MetricDirection.WORSENING: MetricDirection.IMPROVING,
    }

    if data.primary_direction in opposite:
        if opposite[data.primary_direction] in directions:
            return TrendState.MIXED_SIGNAL
        if data.primary_direction not in directions:
            return TrendState.INCONCLUSIVE
        return (
            TrendState.RECOVERY
            if data.primary_direction == MetricDirection.IMPROVING
            else TrendState.DETERIORATION
        )

    if (
        MetricDirection.IMPROVING in directions
        and MetricDirection.WORSENING in directions
    ):
        return TrendState.MIXED_SIGNAL
    if data.primary_direction == MetricDirection.STABLE and not directions:
        return TrendState.STABLE
    return TrendState.INCONCLUSIVE
