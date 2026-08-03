from datetime import datetime
from decimal import Decimal

from ai_ads.contracts import (
    ActionType,
    DataMode,
    RiskLevel,
    RuleSourceStatus,
    RunMode,
    ValidationOutcome,
)
from ai_ads.tests.factories import NOW, action, context, package, packet, plan
from ai_ads.validator import validate_plan


def test_production_blocks_undecided_rule_and_threshold_sources() -> None:
    current_action = action()
    candidate, arbitration = plan([current_action])
    report = validate_plan(
        packet=packet(),
        context=context(),
        package=package(
            rule_status=RuleSourceStatus.UNDECIDED,
            threshold_status=RuleSourceStatus.UNDECIDED,
        ),
        arbitration=arbitration,
        plan=candidate,
        run_mode=RunMode.PRODUCTION,
        now=NOW,
    )
    assert report.outcome == ValidationOutcome.BLOCKED
    codes = {item.code for item in report.findings}
    assert "RULE_SOURCE_NOT_ACTIVE" in codes
    assert "THRESHOLD_SOURCE_NOT_ACTIVE" in codes


def test_production_remains_disabled_even_when_caller_claims_sources_are_active() -> None:
    current_action = action()
    candidate, arbitration = plan([current_action])
    report = validate_plan(
        packet=packet(),
        context=context(),
        package=package(
            rule_status=RuleSourceStatus.ACTIVE,
            threshold_status=RuleSourceStatus.ACTIVE,
        ),
        arbitration=arbitration,
        plan=candidate,
        run_mode=RunMode.PRODUCTION,
        now=NOW,
    )
    assert report.outcome == ValidationOutcome.BLOCKED
    assert any(item.code == "PRODUCTION_EXECUTION_DISABLED" for item in report.findings)


def test_structurally_valid_test_plan_auto_passes() -> None:
    current_action = action()
    candidate, arbitration = plan([current_action])
    report = validate_plan(
        packet=packet(),
        context=context(),
        package=package(),
        arbitration=arbitration,
        plan=candidate,
        run_mode=RunMode.TEST_ONLY,
        now=NOW,
    )
    assert report.outcome == ValidationOutcome.AUTO_PASS


def test_non_rug_context_is_blocked() -> None:
    current_action = action()
    candidate, arbitration = plan([current_action])
    current_context = context()
    current_context.category = "office_chair"
    report = validate_plan(
        packet=packet(),
        context=current_context,
        package=package(),
        arbitration=arbitration,
        plan=candidate,
        run_mode=RunMode.TEST_ONLY,
        now=NOW,
    )
    assert report.outcome == ValidationOutcome.BLOCKED
    assert any(item.code == "UNSUPPORTED_CATEGORY" for item in report.findings)


def test_missing_rule_file_checksums_blocks_plan() -> None:
    current_action = action()
    candidate, arbitration = plan([current_action])
    current_package = package()
    current_package.rule_file_sha256 = None
    report = validate_plan(
        packet=packet(),
        context=context(),
        package=current_package,
        arbitration=arbitration,
        plan=candidate,
        run_mode=RunMode.TEST_ONLY,
        now=NOW,
    )
    assert report.outcome == ValidationOutcome.BLOCKED
    assert any(item.code == "RULE_PACKAGE_FILE_CHECKSUM_MISSING" for item in report.findings)


def test_high_risk_action_requires_approval() -> None:
    current_action = action(risk=RiskLevel.HIGH)
    candidate, arbitration = plan([current_action])
    report = validate_plan(
        packet=packet(),
        context=context(),
        package=package(),
        arbitration=arbitration,
        plan=candidate,
        run_mode=RunMode.TEST_ONLY,
        now=NOW,
    )
    assert report.outcome == ValidationOutcome.APPROVAL_REQUIRED
    assert any(item.code == "HIGH_IMPACT_ACTION" for item in report.findings)


def test_limited_data_cannot_emit_executable_action() -> None:
    current_action = action()
    candidate, arbitration = plan([current_action])
    report = validate_plan(
        packet=packet(data_mode=DataMode.LIMITED),
        context=context(),
        package=package(),
        arbitration=arbitration,
        plan=candidate,
        run_mode=RunMode.TEST_ONLY,
        now=NOW,
    )
    assert report.outcome == ValidationOutcome.BLOCKED
    assert any(
        item.code == "LIMITED_DATA_EXECUTION_FORBIDDEN"
        for item in report.findings
    )


def test_protected_entity_cannot_be_paused() -> None:
    pause = action(
        action_type=ActionType.PAUSE,
        current_value="ENABLED",
        proposed_value="PAUSED",
        risk=RiskLevel.HIGH,
    )
    candidate, arbitration = plan([pause])
    report = validate_plan(
        packet=packet(),
        context=context(protected_entities=["T-001"]),
        package=package(),
        arbitration=arbitration,
        plan=candidate,
        run_mode=RunMode.TEST_ONLY,
        now=NOW,
    )
    assert report.outcome == ValidationOutcome.BLOCKED
    assert any(item.code == "PROTECTED_ENTITY_ACTION" for item in report.findings)


def test_batch_budget_cap_blocks_aggregate_increase() -> None:
    increase = action(
        action_type=ActionType.INCREASE_BUDGET,
        object_type="CAMPAIGN",
        object_id="C-001",
        current_value=Decimal("100"),
        proposed_value=Decimal("130"),
    )
    candidate, arbitration = plan([increase])
    current_context = context()
    current_context.batch_budget_change_cap = Decimal("20")
    report = validate_plan(
        packet=packet(),
        context=current_context,
        package=package(),
        arbitration=arbitration,
        plan=candidate,
        run_mode=RunMode.TEST_ONLY,
        now=NOW,
    )
    assert report.outcome == ValidationOutcome.BLOCKED
    assert any(item.code == "BATCH_BUDGET_CAP_EXCEEDED" for item in report.findings)


def test_missing_rollback_value_blocks_execution() -> None:
    current_action = action()
    current_action.rollback_value = None
    candidate, arbitration = plan([current_action])
    report = validate_plan(
        packet=packet(),
        context=context(),
        package=package(),
        arbitration=arbitration,
        plan=candidate,
        run_mode=RunMode.TEST_ONLY,
        now=NOW,
    )
    assert report.outcome == ValidationOutcome.BLOCKED
    assert any(item.code == "EXECUTION_FIELDS_MISSING" for item in report.findings)


def test_pause_cannot_be_misclassified_as_low_risk() -> None:
    pause = action(
        action_type=ActionType.PAUSE,
        current_value="ENABLED",
        proposed_value="PAUSED",
        risk=RiskLevel.LOW,
    )
    candidate, arbitration = plan([pause])
    report = validate_plan(
        packet=packet(),
        context=context(),
        package=package(),
        arbitration=arbitration,
        plan=candidate,
        run_mode=RunMode.TEST_ONLY,
        now=NOW,
    )
    assert report.outcome == ValidationOutcome.BLOCKED
    assert any(
        item.code == "HIGH_IMPACT_RISK_MISCLASSIFIED"
        for item in report.findings
    )


def test_unresolved_opposite_actions_block_plan() -> None:
    increase = action(action_id="A-UP", action_type=ActionType.INCREASE_BID)
    decrease = action(
        action_id="A-DOWN",
        action_type=ActionType.DECREASE_BID,
        proposed_value=Decimal("0.90"),
    )
    candidate, arbitration = plan([increase, decrease])
    report = validate_plan(
        packet=packet(),
        context=context(),
        package=package(),
        arbitration=arbitration,
        plan=candidate,
        run_mode=RunMode.TEST_ONLY,
        now=NOW,
    )
    assert report.outcome == ValidationOutcome.BLOCKED
    assert any(
        item.code == "OPPOSITE_ACTIONS_SAME_PRIORITY"
        for item in report.findings
    )


def test_wrong_direction_budget_increase_is_blocked() -> None:
    invalid = action(
        action_type=ActionType.INCREASE_BUDGET,
        object_type="CAMPAIGN",
        object_id="C-001",
        current_value=Decimal("100"),
        proposed_value=Decimal("10"),
    )
    candidate, arbitration = plan([invalid])
    report = validate_plan(
        packet=packet(),
        context=context(),
        package=package(),
        arbitration=arbitration,
        plan=candidate,
        run_mode=RunMode.TEST_ONLY,
        now=NOW,
    )
    assert report.outcome == ValidationOutcome.BLOCKED
    assert any(item.code == "ACTION_DIRECTION_INVALID" for item in report.findings)


def test_nonnumeric_bid_values_are_blocked() -> None:
    invalid = action(current_value="not-a-number", proposed_value=True)
    candidate, arbitration = plan([invalid])
    report = validate_plan(
        packet=packet(),
        context=context(),
        package=package(),
        arbitration=arbitration,
        plan=candidate,
        run_mode=RunMode.TEST_ONLY,
        now=NOW,
    )
    assert report.outcome == ValidationOutcome.BLOCKED
    assert any(item.code == "NUMERIC_ACTION_VALUE_INVALID" for item in report.findings)


def test_unknown_placement_object_is_blocked() -> None:
    invalid = action(
        action_type=ActionType.SET_PLACEMENT,
        object_type="PLACEMENT",
        object_id="PLACEMENT-DOES-NOT-EXIST",
        current_value=Decimal("0"),
        proposed_value=Decimal("50"),
    )
    candidate, arbitration = plan([invalid])
    report = validate_plan(
        packet=packet(),
        context=context(),
        package=package(),
        arbitration=arbitration,
        plan=candidate,
        run_mode=RunMode.TEST_ONLY,
        now=NOW,
    )
    assert report.outcome == ValidationOutcome.BLOCKED
    assert any(item.code == "ACTION_OBJECT_NOT_FOUND" for item in report.findings)


def test_naive_datetime_is_blocked_without_crashing_validator() -> None:
    invalid_context = context().model_copy(
        update={"valid_until": datetime(2026, 8, 6, 12, 0, 0)}
    )
    current_action = action()
    candidate, arbitration = plan([current_action])
    report = validate_plan(
        packet=packet(),
        context=invalid_context,
        package=package(),
        arbitration=arbitration,
        plan=candidate,
        run_mode=RunMode.TEST_ONLY,
        now=NOW,
    )
    assert report.outcome == ValidationOutcome.BLOCKED
    assert any(item.code == "AD_CONTEXT_TIMEZONE_MISSING" for item in report.findings)
