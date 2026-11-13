import pytest
from pydantic import ValidationError

from ai_ads.contracts import ExecutionConfirmation
from ai_ads.tests.factories import NOW


def test_batch_confirmation_requires_operator_and_time() -> None:
    with pytest.raises(ValidationError):
        ExecutionConfirmation(
            plan_id="PLAN-001",
            batch_id="BATCH-001",
            executed_as_planned=True,
        )


def test_deviated_execution_requires_action_records() -> None:
    with pytest.raises(ValidationError):
        ExecutionConfirmation(
            plan_id="PLAN-001",
            batch_id="BATCH-001",
            executed_as_planned=False,
            executed_at=NOW,
            operator="lulu",
        )
