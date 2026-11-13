from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from itertools import combinations
import random
from typing import Any


METRICS = {
    "cvr": "higher_is_better",
    "cpa": "lower_is_better",
    "acos": "lower_is_better",
}


def _ratio(numerator: Decimal | int, denominator: Decimal | int) -> Decimal | None:
    denominator = Decimal(denominator)
    return None if denominator == 0 else Decimal(numerator) / denominator


def _totals(rows: list[dict[str, Any]]) -> dict[str, Decimal | int]:
    return {
        "impressions": sum(int(row["impressions"]) for row in rows),
        "clicks": sum(int(row["clicks"]) for row in rows),
        "orders": sum(int(row["orders"]) for row in rows),
        "spend": sum((Decimal(row["spend"]) for row in rows), Decimal("0")),
        "sales": sum((Decimal(row["sales"]) for row in rows), Decimal("0")),
    }


def _metrics(totals: dict[str, Decimal | int]) -> dict[str, Decimal | None]:
    return {
        "cvr": _ratio(totals["orders"], totals["clicks"]),
        "cpa": _ratio(totals["spend"], totals["orders"]),
        "acos": _ratio(totals["spend"], totals["sales"]),
    }


def _quantile(values: list[Decimal], q: Decimal) -> Decimal:
    ordered = sorted(values)
    position = q * Decimal(len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - Decimal(lower)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _candidate_boundaries(values: list[Decimal], direction: str) -> dict[str, Any]:
    p25 = _quantile(values, Decimal("0.25"))
    p50 = _quantile(values, Decimal("0.50"))
    p75 = _quantile(values, Decimal("0.75"))
    if direction == "higher_is_better":
        boundaries = {"excellent": p75, "normal": p50, "warning": p25}
    else:
        boundaries = {"excellent": p25, "normal": p50, "warning": p75}
    return {
        "direction": direction,
        **boundaries,
        "train_object_count": len(values),
        "source": "TRAIN_OBJECT_DISTRIBUTION_P25_P50_P75",
    }


def _tier(value: Decimal, thresholds: dict[str, Any], *, candidate: bool) -> int:
    direction = thresholds["direction"]
    excellent = Decimal(str(thresholds["excellent"]))
    normal = Decimal(str(thresholds["normal"]))
    warning = Decimal(str(thresholds["warning"]))
    if direction == "higher_is_better":
        if value >= excellent:
            return 0
        if value >= normal:
            return 1
        if value >= warning:
            return 2
        return 3
    if value <= excellent:
        return 0
    normal_hit = value <= normal if candidate else value < normal
    warning_hit = value <= warning if candidate else value < warning
    if normal_hit:
        return 1
    if warning_hit:
        return 2
    return 3


def _quality(value: Decimal, direction: str) -> Decimal:
    return value if direction == "higher_is_better" else -value


def _concordance(records: list[dict[str, Any]]) -> tuple[Decimal, Decimal, int]:
    current_score = Decimal("0")
    candidate_score = Decimal("0")
    pair_count = 0
    for left, right in combinations(records, 2):
        if left["object_id"] == right["object_id"]:
            continue
        current_differs = left["current_tier"] != right["current_tier"]
        candidate_differs = left["candidate_tier"] != right["candidate_tier"]
        if not current_differs and not candidate_differs:
            continue
        pair_count += 1
        actual = (left["holdout_quality"] > right["holdout_quality"]) - (
            left["holdout_quality"] < right["holdout_quality"]
        )
        for key, differs in (
            ("current", current_differs),
            ("candidate", candidate_differs),
        ):
            if not differs or actual == 0:
                score = Decimal("0.5")
            else:
                predicted = -1 if left[f"{key}_tier"] < right[f"{key}_tier"] else 1
                score = Decimal("1") if predicted == -actual else Decimal("0")
            if key == "current":
                current_score += score
            else:
                candidate_score += score
    if pair_count == 0:
        return Decimal("0.5"), Decimal("0.5"), 0
    denominator = Decimal(pair_count)
    return current_score / denominator, candidate_score / denominator, pair_count


def _percentile(values: list[Decimal], q: Decimal) -> Decimal:
    return _quantile(values, q)


def _metric_proof(
    metric: str,
    objects: dict[str, dict[str, Any]],
    current: dict[str, Any],
    candidate: dict[str, Any] | None,
    standard: dict[str, Any],
) -> dict[str, Any]:
    if candidate is None:
        return {"status": "INCONCLUSIVE_NO_CANDIDATE_BOUNDARIES"}
    records = []
    for object_id, item in objects.items():
        train = item["train"]
        holdout = item["holdout"]
        train_value = item["train_metrics"][metric]
        holdout_value = item["holdout_metrics"][metric]
        if train_value is None or holdout_value is None:
            continue
        if (
            int(train["clicks"]) < standard["minimum_train_clicks_per_object"]
            or int(holdout["clicks"]) < standard["minimum_holdout_clicks_per_object"]
        ):
            continue
        if metric == "cpa" and (
            int(train["orders"]) < standard["minimum_train_orders_for_cpa"]
            or int(holdout["orders"]) < standard["minimum_holdout_orders_for_cpa"]
        ):
            continue
        records.append(
            {
                "object_id": object_id,
                "current_tier": _tier(train_value, current, candidate=False),
                "candidate_tier": _tier(train_value, candidate, candidate=True),
                "holdout_quality": _quality(holdout_value, METRICS[metric]),
            }
        )
    minimum_objects = standard["minimum_evaluable_objects"]
    if len(records) < minimum_objects:
        return {
            "status": "INCONCLUSIVE_INSUFFICIENT_OBJECTS",
            "evaluable_objects": len(records),
            "minimum_evaluable_objects": minimum_objects,
        }
    current_score, candidate_score, pairs = _concordance(records)
    if pairs < standard["minimum_comparable_pairs"]:
        return {
            "status": "INCONCLUSIVE_INSUFFICIENT_PAIRS",
            "evaluable_objects": len(records),
            "comparable_pairs": pairs,
            "minimum_comparable_pairs": standard["minimum_comparable_pairs"],
        }
    improvement = candidate_score - current_score
    rng = random.Random(standard["bootstrap_seed"] + sum(ord(char) for char in metric))
    bootstrapped: list[Decimal] = []
    for _ in range(standard["bootstrap_iterations"]):
        sample = [rng.choice(records) for _ in records]
        current_sample, candidate_sample, sample_pairs = _concordance(sample)
        if sample_pairs:
            bootstrapped.append(candidate_sample - current_sample)
    lower = _percentile(bootstrapped, Decimal("0.025"))
    upper = _percentile(bootstrapped, Decimal("0.975"))
    margin = Decimal(str(standard["minimum_concordance_improvement"]))
    if lower > 0 and improvement >= margin:
        status = "BETTER"
    elif upper < 0 and improvement <= -margin:
        status = "WORSE"
    else:
        status = "INCONCLUSIVE"
    return {
        "status": status,
        "evaluable_objects": len(records),
        "comparable_pairs": pairs,
        "current_holdout_concordance": current_score,
        "candidate_holdout_concordance": candidate_score,
        "concordance_improvement": improvement,
        "improvement_95_bootstrap_interval": {"lower": lower, "upper": upper},
        "minimum_required_improvement": margin,
        "bootstrap_iterations": len(bootstrapped),
    }


def build_historical_better_proof(
    rows: list[dict[str, Any]], size_profile: str, object_grain: str, config: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    standard = config["historical_better_proof"]
    base = {
        "method": "CHRONOLOGICAL_OBJECT_LEVEL_HOLDOUT_CONCORDANCE",
        "current_threshold_source": standard["current_threshold_source"],
        "applicable_grain": standard["applicable_grain"],
        "proves_future_superiority": False,
    }
    if object_grain != standard["applicable_grain"]:
        return {}, {
            **base,
            "overall_status": "INCONCLUSIVE_GRAIN_MISMATCH",
            "actual_grain": object_grain,
        }
    current_profile = standard["current_profiles"].get(size_profile)
    if current_profile is None:
        return {}, {
            **base,
            "overall_status": "INCONCLUSIVE_PROFILE_UNSUPPORTED",
            "size_profile": size_profile,
        }
    settings = config["candidate_generation"]["historical_validation"]
    days = sorted({row["date"] for row in rows})
    holdout_min = settings["minimum_holdout_days"]
    split_index = int(len(days) * Decimal(str(settings["train_fraction"])))
    split_index = max(1, min(split_index, len(days) - holdout_min))
    train_days = set(days[:split_index])
    holdout_days = set(days[split_index:])
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: {"train": [], "holdout": []}
    )
    for row in rows:
        period = "train" if row["date"] in train_days else "holdout"
        grouped[row["object_id"]][period].append(row)
    objects: dict[str, dict[str, Any]] = {}
    for object_id, periods in grouped.items():
        if not periods["train"] or not periods["holdout"]:
            continue
        train = _totals(periods["train"])
        holdout = _totals(periods["holdout"])
        objects[object_id] = {
            "train": train,
            "holdout": holdout,
            "train_metrics": _metrics(train),
            "holdout_metrics": _metrics(holdout),
        }
    candidate_thresholds: dict[str, Any] = {}
    for metric, direction in METRICS.items():
        values = []
        for item in objects.values():
            value = item["train_metrics"][metric]
            if value is None:
                continue
            if int(item["train"]["clicks"]) < standard["minimum_train_clicks_per_object"]:
                continue
            if metric == "cpa" and int(item["train"]["orders"]) < standard["minimum_train_orders_for_cpa"]:
                continue
            values.append(value)
        if len(values) >= standard["minimum_candidate_objects"]:
            candidate_thresholds[metric] = _candidate_boundaries(values, direction)
    metric_results = {
        metric: _metric_proof(
            metric,
            objects,
            current_profile[metric],
            candidate_thresholds.get(metric),
            standard,
        )
        for metric in METRICS
    }
    better = sum(item["status"] == "BETTER" for item in metric_results.values())
    worse = sum(item["status"] == "WORSE" for item in metric_results.values())
    if better >= standard["minimum_better_metrics"] and not (
        standard["reject_if_any_metric_worse"] and worse
    ):
        overall = "HISTORICALLY_BETTER_CANDIDATE"
    elif worse:
        overall = "NOT_BETTER"
    else:
        overall = "INCONCLUSIVE"
    return candidate_thresholds, {
        **base,
        "overall_status": overall,
        "size_profile": size_profile,
        "train_period": {"start": min(train_days), "end": max(train_days)},
        "holdout_period": {"start": min(holdout_days), "end": max(holdout_days)},
        "train_days": len(train_days),
        "holdout_days": len(holdout_days),
        "independent_objects": len(objects),
        "metric_results": metric_results,
        "decision_rule": {
            "minimum_better_metrics": standard["minimum_better_metrics"],
            "reject_if_any_metric_worse": standard["reject_if_any_metric_worse"],
        },
        "interpretation": (
            "BETTER仅表示候选阈值在未参与拟合的历史留出期中，"
            "对对象未来表现的分层一致性显著优于当前阈值；仍不是未来因果保证。"
        ),
    }
