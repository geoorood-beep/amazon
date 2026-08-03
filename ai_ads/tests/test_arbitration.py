from decimal import Decimal

from ai_ads.arbitration import arbitrate_actions
from ai_ads.contracts import ActionType, PriorityTier
from ai_ads.tests.factories import action


def test_higher_priority_action_wins() -> None:
    risk_action = action(
        action_id="A-RISK",
        action_type=ActionType.DECREASE_BID,
        priority=PriorityTier.RISK_CONTROL,
        proposed_value=Decimal("0.80"),
    )
    exploration_action = action(
        action_id="A-EXPLORE",
        action_type=ActionType.INCREASE_BID,
        priority=PriorityTier.EXPLORATION,
    )
    result = arbitrate_actions("BATCH-001", [exploration_action, risk_action])
    assert [item.candidate_action_id for item in result.selected_actions] == ["A-RISK"]
    assert result.conflicts == []


def test_opposite_actions_same_priority_block_selection() -> None:
    increase = action(action_id="A-UP", action_type=ActionType.INCREASE_BID)
    decrease = action(
        action_id="A-DOWN",
        action_type=ActionType.DECREASE_BID,
        proposed_value=Decimal("0.90"),
    )
    result = arbitrate_actions("BATCH-001", [increase, decrease])
    assert result.selected_actions == []
    assert result.conflicts[0].code == "OPPOSITE_ACTIONS_SAME_PRIORITY"


def test_duplicate_action_is_removed() -> None:
    first = action(action_id="A-001")
    duplicate = action(action_id="A-002")
    result = arbitrate_actions("BATCH-001", [first, duplicate])
    assert len(result.selected_actions) == 1
    assert any(item.reason_code == "DUPLICATE_ACTION" for item in result.rejected_actions)


def test_pause_is_the_only_primary_action() -> None:
    pause = action(
        action_id="A-PAUSE",
        action_type=ActionType.PAUSE,
        priority=PriorityTier.EXPLORATION,
        current_value="ENABLED",
        proposed_value="PAUSED",
    )
    decrease = action(
        action_id="A-DOWN",
        action_type=ActionType.DECREASE_BID,
        proposed_value=Decimal("0.90"),
    )
    result = arbitrate_actions("BATCH-001", [decrease, pause])
    assert [item.candidate_action_id for item in result.selected_actions] == ["A-PAUSE"]


def test_supporting_opposite_action_creates_blocking_conflict() -> None:
    increase = action(action_id="A-UP", action_type=ActionType.INCREASE_BID)
    decrease = action(
        action_id="A-DOWN",
        action_type=ActionType.DECREASE_BID,
        proposed_value=Decimal("0.90"),
        is_primary=False,
    )
    decrease.dependencies = ["A-UP"]
    result = arbitrate_actions("BATCH-001", [increase, decrease])
    assert [item.candidate_action_id for item in result.selected_actions] == ["A-UP"]
    assert any(item.code == "SUPPORTING_ACTION_CONFLICT" for item in result.conflicts)


def test_duplicate_action_ids_block_all_duplicated_actions() -> None:
    first = action(action_id="A-DUP")
    second = action(
        action_id="A-DUP",
        action_type=ActionType.DECREASE_BID,
        proposed_value=Decimal("0.90"),
    )
    result = arbitrate_actions("BATCH-001", [first, second])
    assert result.selected_actions == []
    assert any(item.code == "DUPLICATE_ACTION_ID" for item in result.conflicts)
