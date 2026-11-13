from __future__ import annotations

from .contracts import (
    EvidenceClassification,
    ReviewEligibility,
    ReviewEligibilityResult,
    ReviewInput,
)


def assess_review_eligibility(review: ReviewInput) -> ReviewEligibilityResult:
    reasons: list[str] = []
    if review.execution_confirmation is None:
        reasons.append("缺少实际执行确认")
    elif review.execution_confirmation.batch_id != review.batch_id:
        reasons.append("执行确认Batch ID不一致")
    elif review.execution_confirmation.plan_id != review.plan_id:
        reasons.append("执行确认Plan ID不一致")

    if not review.before_snapshot_id or not review.after_snapshot_id:
        reasons.append("缺少执行前或执行后数据快照")
    if review.observed_at < review.attribution_complete_at:
        reasons.append("最低观察周期或归因窗口尚未结束")
    if not review.metrics_comparable:
        reasons.append("执行前后指标口径不一致")
    if not review.secondary_adjustments_marked:
        reasons.append("二次调整尚未完整标记")
    if review.overlapping_action_ids:
        reasons.append("存在尚未拆分的重叠动作")

    if reasons:
        return ReviewEligibilityResult(
            plan_id=review.plan_id,
            batch_id=review.batch_id,
            eligibility=ReviewEligibility.NOT_READY,
            reasons=reasons,
        )

    unisolated_events = [
        item for item in review.external_events if not item.isolated
    ]
    return ReviewEligibilityResult(
        plan_id=review.plan_id,
        batch_id=review.batch_id,
        eligibility=ReviewEligibility.READY,
        reasons=(
            ["存在无法隔离的外部事件，证据只能标记为INCONCLUSIVE"]
            if unisolated_events
            else []
        ),
        evidence_classification=(
            EvidenceClassification.INCONCLUSIVE if unisolated_events else None
        ),
    )
