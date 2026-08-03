from __future__ import annotations

from collections import defaultdict

from .contracts import (
    ActionConflict,
    ActionType,
    ArbitrationResult,
    CandidateAction,
    RejectedAction,
)


OPPOSITE_ACTIONS = {
    frozenset({ActionType.INCREASE_BUDGET, ActionType.DECREASE_BUDGET}),
    frozenset({ActionType.INCREASE_BID, ActionType.DECREASE_BID}),
    frozenset({ActionType.PAUSE, ActionType.ENABLE}),
}


def _action_signature(action: CandidateAction) -> tuple[object, ...]:
    return (
        action.action_type,
        action.proposed_value,
        action.object_type,
        action.object_id,
    )


def _contains_opposites(actions: list[CandidateAction]) -> bool:
    action_types = {action.action_type for action in actions}
    return any(pair <= action_types for pair in OPPOSITE_ACTIONS)


def _supporting_conflicts_with_selected(
    action: CandidateAction,
    existing: CandidateAction,
) -> bool:
    if action.object_type != existing.object_type or action.object_id != existing.object_id:
        return False
    if _contains_opposites([action, existing]):
        return True
    if ActionType.PAUSE in {action.action_type, existing.action_type}:
        return action.action_type != ActionType.OBSERVE and existing.action_type != ActionType.OBSERVE
    return False


def arbitrate_actions(
    batch_id: str,
    actions: list[CandidateAction],
) -> ArbitrationResult:
    rejected: list[RejectedAction] = []
    conflicts: list[ActionConflict] = []
    selected: list[CandidateAction] = []

    actions_by_id: dict[str, list[CandidateAction]] = defaultdict(list)
    for action in actions:
        actions_by_id[action.candidate_action_id].append(action)
    duplicate_action_ids = {
        action_id for action_id, grouped_actions in actions_by_id.items()
        if len(grouped_actions) > 1
    }
    for action_id in sorted(duplicate_action_ids):
        duplicated = actions_by_id[action_id]
        first = duplicated[0]
        conflicts.append(
            ActionConflict(
                object_type=first.object_type,
                object_id=first.object_id,
                action_ids=[item.candidate_action_id for item in duplicated],
                code="DUPLICATE_ACTION_ID",
                message=f"candidate_action_id重复，无法唯一定位动作: {action_id}",
            )
        )
        for item in duplicated:
            rejected.append(
                RejectedAction(
                    candidate_action_id=item.candidate_action_id,
                    reason_code="DUPLICATE_ACTION_ID",
                    reason="动作ID必须在批次内唯一",
                )
            )

    unique_actions: list[CandidateAction] = []
    first_by_signature: dict[tuple[object, ...], CandidateAction] = {}
    for action in sorted(actions, key=lambda item: item.candidate_action_id):
        if action.candidate_action_id in duplicate_action_ids:
            continue
        signature = _action_signature(action)
        duplicate = first_by_signature.get(signature)
        if duplicate:
            rejected.append(
                RejectedAction(
                    candidate_action_id=action.candidate_action_id,
                    reason_code="DUPLICATE_ACTION",
                    reason=f"与{duplicate.candidate_action_id}动作及目标值相同",
                )
            )
        else:
            unique_actions.append(action)
            first_by_signature[signature] = action

    grouped: dict[tuple[str, str], list[CandidateAction]] = defaultdict(list)
    supporting: list[CandidateAction] = []
    for action in unique_actions:
        if action.batch_id != batch_id:
            rejected.append(
                RejectedAction(
                    candidate_action_id=action.candidate_action_id,
                    reason_code="BATCH_ID_MISMATCH",
                    reason=f"动作Batch ID为{action.batch_id}，期望{batch_id}",
                )
            )
        elif action.is_primary:
            grouped[(action.object_type.value, action.object_id)].append(action)
        else:
            supporting.append(action)

    for (_, _), object_actions in sorted(grouped.items()):
        object_actions.sort(
            key=lambda item: (item.priority_tier.value, item.candidate_action_id)
        )
        pause_actions = [
            item for item in object_actions if item.action_type == ActionType.PAUSE
        ]
        if len(pause_actions) == 1:
            winner = pause_actions[0]
            selected.append(winner)
            for item in object_actions:
                if item.candidate_action_id != winner.candidate_action_id:
                    rejected.append(
                        RejectedAction(
                            candidate_action_id=item.candidate_action_id,
                            reason_code="PAUSE_IS_PRIMARY",
                            reason=f"{winner.candidate_action_id}为该对象唯一暂停主动作",
                        )
                    )
            continue

        highest_priority = object_actions[0].priority_tier
        finalists = [
            item for item in object_actions if item.priority_tier == highest_priority
        ]

        if _contains_opposites(finalists):
            conflicts.append(
                ActionConflict(
                    object_type=finalists[0].object_type,
                    object_id=finalists[0].object_id,
                    action_ids=[item.candidate_action_id for item in finalists],
                    code="OPPOSITE_ACTIONS_SAME_PRIORITY",
                    message="同一对象同一优先级存在相反动作，无法安全仲裁",
                )
            )
            for item in object_actions:
                rejected.append(
                    RejectedAction(
                        candidate_action_id=item.candidate_action_id,
                        reason_code="UNRESOLVED_ACTION_CONFLICT",
                        reason="该对象未保留主动作",
                    )
                )
            continue

        if len(finalists) > 1:
            conflicts.append(
                ActionConflict(
                    object_type=finalists[0].object_type,
                    object_id=finalists[0].object_id,
                    action_ids=[item.candidate_action_id for item in finalists],
                    code="MULTIPLE_PRIMARY_ACTIONS_SAME_PRIORITY",
                    message="同一对象同一优先级存在多个不同主动作",
                )
            )
            for item in object_actions:
                rejected.append(
                    RejectedAction(
                        candidate_action_id=item.candidate_action_id,
                        reason_code="UNRESOLVED_ACTION_CONFLICT",
                        reason="该对象未保留主动作",
                    )
                )
            continue

        winner = finalists[0]
        selected.append(winner)
        for item in object_actions:
            if item.candidate_action_id != winner.candidate_action_id:
                rejected.append(
                    RejectedAction(
                        candidate_action_id=item.candidate_action_id,
                        reason_code="LOWER_PRIORITY_ACTION",
                        reason=f"优先级低于{winner.candidate_action_id}",
                    )
                )

    selected_ids = {item.candidate_action_id for item in selected}
    for action in supporting:
        missing_dependencies = [
            dependency
            for dependency in action.dependencies
            if dependency not in selected_ids
        ]
        if missing_dependencies:
            rejected.append(
                RejectedAction(
                    candidate_action_id=action.candidate_action_id,
                    reason_code="DEPENDENCY_NOT_SELECTED",
                    reason="依赖动作未选中: " + ", ".join(missing_dependencies),
                )
            )
        else:
            conflicting = next(
                (
                    existing
                    for existing in selected
                    if _supporting_conflicts_with_selected(action, existing)
                ),
                None,
            )
            if conflicting is not None:
                conflicts.append(
                    ActionConflict(
                        object_type=action.object_type,
                        object_id=action.object_id,
                        action_ids=[
                            conflicting.candidate_action_id,
                            action.candidate_action_id,
                        ],
                        code="SUPPORTING_ACTION_CONFLICT",
                        message="辅助动作与已选动作相反或与暂停动作冲突",
                    )
                )
                rejected.append(
                    RejectedAction(
                        candidate_action_id=action.candidate_action_id,
                        reason_code="SUPPORTING_ACTION_CONFLICT",
                        reason=f"与已选动作{conflicting.candidate_action_id}冲突",
                    )
                )
                continue
            selected.append(action)
            selected_ids.add(action.candidate_action_id)

    return ArbitrationResult(
        batch_id=batch_id,
        selected_actions=selected,
        rejected_actions=rejected,
        conflicts=conflicts,
    )
