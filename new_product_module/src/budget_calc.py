from __future__ import annotations

from .schemas import CategoryRules, ProductInfo


def target_cpa(avg_order_value: float, target_acos: float) -> float:
    return avg_order_value * target_acos


def daily_budget(order_target: float, target_cpa_value: float, product_coefficient: float) -> float:
    return order_target * target_cpa_value * product_coefficient


def suggested_daily_budget(product: ProductInfo, rules: CategoryRules) -> tuple[float | None, list[str]]:
    reasons: list[str] = []
    profile = product.analysis_threshold_profile or product.rug_type
    threshold = rules.rug_analysis_thresholds.get(profile or "", {})
    cpa_normal_upper = threshold.get("cpa_normal_upper") if isinstance(threshold, dict) else None
    if cpa_normal_upper is None:
        reasons.append(f"规则缺失：rug_analysis_thresholds.{profile}.cpa_normal_upper")
        return None, reasons

    if product.ad_group_order_target is None:
        order_target = 1.0
        reasons.append("未提供单广告组目标订单数，按 1 单的标准最低日预算计算")
    elif product.ad_group_order_target <= 0:
        reasons.append("单广告组目标订单数必须大于 0")
        return None, reasons
    else:
        order_target = product.ad_group_order_target
    return round(float(cpa_normal_upper) * order_target, 2), reasons
