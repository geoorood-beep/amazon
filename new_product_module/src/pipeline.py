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
from .rug_size_classifier import classify_rug_size, normalize_rug_type
from .stage_matching import determine_order_stage, match_stage


def run_new_product_pipeline(
    product_info: ProductInfo | dict,
    historical_keywords: list[HistoricalKeyword] | list[dict],
    rules: CategoryRules,
) -> PipelineResult:
    product = ProductInfo.model_validate(product_info)
    blocked_items: list[BlockedItem] = []
    if product.category.strip().lower() not in {"rug", "rugs"}:
        blocked_items.append(
            BlockedItem(
                item_type="product",
                identifier=product.category,
                source_step="scope_gate",
                reason="陆遥广告智能体只支持 Rug / 地毯，非 Rug 类目已阻断",
            )
        )
        return PipelineResult(
            product_profile=_build_product_profile(product, [], blocked_items),
            blocked_items=blocked_items,
        )

    keyword_rows = [row if isinstance(row, HistoricalKeyword) else HistoricalKeyword.model_validate(row) for row in historical_keywords]

    classification = classify_rug_size(
        product.size_spec,
        product.shape,
        rules.rug_size_type_mapping,
    )
    provided_rug_type = normalize_rug_type(product.rug_type)
    if classification.rug_type is None:
        blocked_items.append(
            BlockedItem(
                item_type="product",
                identifier=product.size_spec or "尺寸未提供",
                source_step="rug_size_classifier",
                reason=classification.reason,
            )
        )
        return PipelineResult(
            product_profile=_build_product_profile(product, [], blocked_items),
            blocked_items=blocked_items,
        )
    if provided_rug_type and provided_rug_type != classification.rug_type:
        blocked_items.append(
            BlockedItem(
                item_type="product",
                identifier=product.size_spec or "尺寸未提供",
                source_step="rug_size_classifier",
                reason=(
                    f"人工地毯类型 {provided_rug_type} 与尺寸自动识别类型 "
                    f"{classification.rug_type} 冲突；按尺寸识别结果执行"
                ),
            )
        )
    product.rug_type = classification.rug_type
    product.analysis_threshold_profile = classification.analysis_threshold_profile

    candidate_pool, candidate_blocked = build_candidate_pool(keyword_rows, rules, product.rug_type)
    blocked_items.extend(candidate_blocked)

    try:
        stage_rule = determine_order_stage(product.order_target_daily, rules)
    except ValueError as exc:
        blocked_items.append(
            BlockedItem(
                item_type="stage",
                identifier=str(product.order_target_daily),
                source_step="stage_matching",
                reason=str(exc),
            )
        )
        return PipelineResult(
            product_profile=_build_product_profile(product, [], blocked_items),
            blocked_items=blocked_items,
        )
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
    cold_start_scores = [
        row for row in keyword_scores if getattr(row, "evidence_grain", "") == "ABA_COLD_START"
    ]
    cold_start_candidates = [row for row in cold_start_scores if row.conclusion == "建议投放"]
    if cold_start_candidates:
        core_diagnosis = (
            f"没有要求当前ASIN历史点击；已按ABA、产品属性和阶段门生成"
            f" {len(cold_start_candidates)} 个冷启动人工候选。"
        )
        confidence = "中"
    elif blocked_items:
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
        overall_strategy=(
            "新品验证：先通过产品属性与ASIN相关性门，再按词根月搜索量、"
            "语义特异度和流量集中度生成Phrase/Broad人工候选；"
            "证据缺失时不新建；新品阶段不建立精准关键词广告。"
        ),
        data_confidence=confidence,
        rug_type=product.rug_type,
        analysis_threshold_profile=product.analysis_threshold_profile,
        target_size=product.size_spec,
    )


def _format_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)
