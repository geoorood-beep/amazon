from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .contracts import DerivedMetrics, MetricSample


METRIC_QUANT = Decimal("0.000001")


def _divide(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    if denominator == 0:
        return None
    return (numerator / denominator).quantize(METRIC_QUANT, rounding=ROUND_HALF_UP)


def derive_metrics(sample: MetricSample) -> DerivedMetrics:
    impressions = Decimal(sample.impressions)
    clicks = Decimal(sample.clicks)
    return DerivedMetrics(
        ctr=_divide(clicks, impressions),
        cvr=_divide(sample.orders, clicks),
        cpc=_divide(sample.spend, clicks),
        cpa=_divide(sample.spend, sample.orders),
        acos=_divide(sample.spend, sample.sales),
    )
