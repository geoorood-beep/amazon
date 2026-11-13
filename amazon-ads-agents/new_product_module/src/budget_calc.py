from __future__ import annotations

from .schemas import CategoryRules, ProductInfo


def target_cpa(avg_order_value: float, target_acos: float) -> float:
    return avg_order_value * target_acos


def daily_budget(order_target: float, target_cpa_value: float, product_coefficient: float) -> float:
    return order_target * target_cpa_value * product_coefficient


def suggested_daily_budget(product: ProductInfo, rules: CategoryRules) -> tuple[float | None, list[str]]:
    reasons: list[str] = []
    if product.target_cpa is not None:
        cpa = product.target_cpa
    elif product.avg_order_value is not None and product.target_acos is not None:
        cpa = target_cpa(product.avg_order_value, product.target_acos)
    else:
        reasons.append("规则/输入缺失：target_cpa 或 avg_order_value + target_acos")
        cpa = None

    coefficient = rules.budget_formula.product_coefficient_by_stage.get(product.product_stage)
    if coefficient is None:
        coefficient = rules.budget_formula.product_coefficient_by_stage.get("default")
    if coefficient is None:
        reasons.append(f"规则缺失：budget_formula.product_coefficient_by_stage.{product.product_stage}")

    if cpa is None or coefficient is None:
        return None, reasons
    return round(daily_budget(product.order_target_daily, cpa, coefficient), 2), reasons
