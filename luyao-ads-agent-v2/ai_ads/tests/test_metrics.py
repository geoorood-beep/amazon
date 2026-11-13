from datetime import date
from decimal import Decimal

import pytest

from ai_ads.contracts import MetricSample, MetricWindow
from ai_ads.metrics import derive_metrics


def test_derive_metrics_from_raw_facts() -> None:
    sample = MetricSample(
        window=MetricWindow.D30,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 30),
        impressions=100,
        clicks=10,
        orders=Decimal("2"),
        spend=Decimal("20"),
        sales=Decimal("100"),
    )
    result = derive_metrics(sample)
    assert result.ctr == Decimal("0.100000")
    assert result.cvr == Decimal("0.200000")
    assert result.cpc == Decimal("2.000000")
    assert result.cpa == Decimal("10.000000")
    assert result.acos == Decimal("0.200000")


def test_zero_denominator_returns_none() -> None:
    sample = MetricSample(
        window=MetricWindow.D3,
        period_start=date(2026, 7, 28),
        period_end=date(2026, 7, 30),
    )
    result = derive_metrics(sample)
    assert result.ctr is None
    assert result.cvr is None
    assert result.cpc is None
    assert result.cpa is None
    assert result.acos is None


def test_impossible_metric_funnel_is_rejected() -> None:
    with pytest.raises(ValueError, match="clicks cannot exceed impressions"):
        MetricSample(
            window=MetricWindow.D3,
            period_start=date(2026, 7, 28),
            period_end=date(2026, 7, 30),
            impressions=100,
            clicks=101,
            orders=Decimal("1"),
        )


def test_named_metric_window_must_have_exact_length() -> None:
    with pytest.raises(ValueError, match="D3 must cover exactly 3"):
        MetricSample(
            window=MetricWindow.D3,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 30),
            impressions=100,
            clicks=10,
            orders=Decimal("1"),
        )
