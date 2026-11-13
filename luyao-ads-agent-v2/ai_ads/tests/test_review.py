from datetime import timedelta

from ai_ads.contracts import (
    EvidenceClassification,
    ExecutionConfirmation,
    ExternalEvent,
    ReviewEligibility,
    ReviewInput,
)
from ai_ads.review import assess_review_eligibility
from ai_ads.tests.factories import NOW


def confirmation() -> ExecutionConfirmation:
    return ExecutionConfirmation(
        plan_id="PLAN-001",
        batch_id="BATCH-001",
        executed_as_planned=True,
        executed_at=NOW,
        operator="lulu",
    )


def review_input() -> ReviewInput:
    return ReviewInput(
        plan_id="PLAN-001",
        batch_id="BATCH-001",
        execution_confirmation=confirmation(),
        before_snapshot_id="SNAP-BEFORE",
        after_snapshot_id="SNAP-AFTER",
        observed_at=NOW + timedelta(days=8),
        attribution_complete_at=NOW + timedelta(days=7),
        metrics_comparable=True,
        secondary_adjustments_marked=True,
    )


def test_missing_execution_confirmation_is_not_ready() -> None:
    current = review_input()
    current.execution_confirmation = None
    result = assess_review_eligibility(current)
    assert result.eligibility == ReviewEligibility.NOT_READY
    assert "缺少实际执行确认" in result.reasons


def test_complete_review_input_is_ready() -> None:
    result = assess_review_eligibility(review_input())
    assert result.eligibility == ReviewEligibility.READY
    assert result.evidence_classification is None


def test_unisolated_external_event_limits_evidence() -> None:
    current = review_input()
    current.external_events.append(
        ExternalEvent(
            event_type="PRICE_CHANGE",
            occurred_at=NOW + timedelta(days=2),
            description="价格发生变化",
            isolated=False,
        )
    )
    result = assess_review_eligibility(current)
    assert result.eligibility == ReviewEligibility.READY
    assert result.evidence_classification == EvidenceClassification.INCONCLUSIVE
