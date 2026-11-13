from __future__ import annotations

from .architecture_builder import build_ad_architecture
from .candidate_pool import build_candidate_pool
from .conflict_check import run_conflict_checks
from .keyword_scoring import score_keywords
from .schemas import (
    BlockedItem,
    CategoryRules,
    HistoricalKeyword,
    PipelineResult,
    ProductInfo,
    ProductProfile,
)
from .stage_matching import determine_order_stage, match_stage


def run_new_product_pipeline(
    product_info: ProductInfo | dict,
    historical_keywords: list[HistoricalKeyword] | list[dict],
    rules: CategoryRules,
) -> PipelineResult:
    product = ProductInfo.model_validate(product_info)
    keyword_rows = [row if isinstance(row, HistoricalKeyword) else HistoricalKeyword.model_validate(row) for row in historical_keywords]

    blocked_items: list[BlockedItem] = []
    candidate_pool, candidate_blocked = build_candidate_pool(keyword_rows, rules, product.rug_type)
    blocked_items.extend(candidate_blocked)

    stage_rule = determine_order_stage(product.order_target_daily, rules)
    stage_rows, stage_blocked = match_stage(candidate_pool, rules, product.rug_type, stage_rule.stage)
    blocked_items.extend(stage_blocked)

    keyword_scores, scoring_blocked = score_keywords(stage_rows, product, rules)
    blocked_items.extend(scoring_blocked)

    ad_architecture, architecture_blocked = build_ad_architecture(keyword_scores, product, rules)
    blocked_items.extend(architecture_blocked)

    ad_architecture, conflict_blocked = run_conflict_checks(ad_architecture, keyword_scores, rules)
    blocked_items.extend(conflict_blocked)

    return PipelineResult(
        product_profile=_build_product_profile(product, keyword_scores, blocked_items),
        keyword_scoring_table=keyword_scores,
        ad_architecture=ad_architecture,
        blocked_items=blocked_items,
    )


def _build_product_profile(
    product: ProductInfo,
    keyword_scores: list,
    blocked_items: list[BlockedItem],
) -> ProductProfile:
    asin_sku = product.asin or product.sku or "未提供"
    current_order_target = f"父体目标日订单{_format_number(product.order_target_daily)}单"
    if blocked_items:
        core_diagnosis = "存在规则缺失、样本不足或冲突项，已进入待人工确认清单。"
        confidence = "中" if keyword_scores else "低"
    elif keyword_scores:
        core_diagnosis = "历史成交证据、ABA阶段适配和属性匹配已完成，生成新品验证建议。"
        confidence = "高"
    else:
        core_diagnosis = "没有关键词通过历史成交候选池。"
        confidence = "低"
    return ProductProfile(
        asin_sku=asin_sku,
        current_order_target=current_order_target,
        core_diagnosis=core_diagnosis,
        overall_strategy="新品验证：尺寸词、长尾词/场景词；词组小预算测试；地毯类目新品阶段不建立精准关键词广告。",
        data_confidence=confidence,
    )


def _format_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)
