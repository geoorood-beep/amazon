import itertools

from ai_ads.contracts import DataQualityStatus
from ai_ads.decision_logic import (
    LowSampleInput,
    LowSamplePermission,
    MetricDirection,
    OverallState,
    OverallStateInput,
    TrendInput,
    TrendState,
    determine_overall_state,
    determine_trend_state,
    evaluate_low_sample_permission,
    placement_diagnostic_allowed,
)


def test_o_zero_complete_stop_exception_requires_approval() -> None:
    result = evaluate_low_sample_permission(
        LowSampleInput(
            orders=0,
            attribution_mature=True,
            category_stop_line_hit=True,
            target_mapping_complete=True,
            data_quality=DataQualityStatus.DQ_PASS,
        )
    )
    assert result == LowSamplePermission.APPROVAL_REQUIRED_CANDIDATE


def test_o_one_remains_observation_only() -> None:
    result = evaluate_low_sample_permission(
        LowSampleInput(
            orders=1,
            attribution_mature=True,
            category_stop_line_hit=True,
            target_mapping_complete=True,
            data_quality=DataQualityStatus.DQ_PASS,
        )
    )
    assert result == LowSamplePermission.OBSERVE_ONLY


def test_o_two_uses_normal_rules() -> None:
    result = evaluate_low_sample_permission(
        LowSampleInput(
            orders=2,
            attribution_mature=False,
            category_stop_line_hit=False,
            target_mapping_complete=False,
            data_quality=DataQualityStatus.DQ_WARNING,
        )
    )
    assert result == LowSamplePermission.NORMAL_RULES


def test_overall_state_truth_table_always_returns_one_state() -> None:
    for values in itertools.product([False, True], repeat=6):
        state = determine_overall_state(
            OverallStateInput(
                data_quality=DataQualityStatus.DQ_PASS,
                sample_sufficient=values[0],
                target_category_risk_conflict=values[1],
                category_high_risk=values[2],
                objective_met=values[3],
                volume_target_met=values[4],
                winner_spend_share_met=values[5],
            )
        )
        assert isinstance(state, OverallState)


def test_target_category_conflict_precedes_high_risk_action_state() -> None:
    state = determine_overall_state(
        OverallStateInput(
            data_quality=DataQualityStatus.DQ_PASS,
            sample_sufficient=True,
            target_category_risk_conflict=True,
            category_high_risk=True,
            objective_met=True,
            volume_target_met=True,
            winner_spend_share_met=True,
        )
    )
    assert state == OverallState.TARGET_CATEGORY_RISK_CONFLICT


def test_efficient_at_target_skips_placement_quality_analysis() -> None:
    assert not placement_diagnostic_allowed(OverallState.EFFICIENT_AT_TARGET)
    assert placement_diagnostic_allowed(OverallState.EFFICIENT_UNDERSCALE)


def test_primary_and_auxiliary_improvement_is_recovery() -> None:
    result = determine_trend_state(
        TrendInput(
            primary_direction=MetricDirection.IMPROVING,
            auxiliary_directions=[
                MetricDirection.IMPROVING,
                MetricDirection.STABLE,
            ],
        )
    )
    assert result == TrendState.RECOVERY


def test_mixed_metric_directions_only_observe() -> None:
    result = determine_trend_state(
        TrendInput(
            primary_direction=MetricDirection.IMPROVING,
            auxiliary_directions=[
                MetricDirection.WORSENING,
                MetricDirection.IMPROVING,
            ],
        )
    )
    assert result == TrendState.MIXED_SIGNAL
