from __future__ import annotations

import re
from typing import Any

from .schemas import BlockedItem, CategoryRules, KeywordScore, ProductInfo, StageMatchedKeyword


def score_keywords(
    rows: list[StageMatchedKeyword],
    product: ProductInfo,
    rules: CategoryRules,
) -> tuple[list[KeywordScore], list[BlockedItem]]:
    blocked: list[BlockedItem] = []
    scores: list[KeywordScore] = []
    baseline = rules.rug_type_baselines.get(product.rug_type)

    if baseline is None:
        return [], [
            BlockedItem(
                item_type="product",
                identifier=product.rug_type,
                source_step="keyword_scoring",
                reason="规则缺失：产品地毯类型未在 rug_type_baselines 中配置",
            )
        ]

    for row in rows:
        score, missing = _score_one_keyword(row, product, rules, baseline.cvr_baseline)
        scores.append(score)
        if missing:
            blocked.append(
                BlockedItem(
                    item_type="keyword",
                    identifier=row.search_term,
                    source_step="keyword_scoring",
                    reason="; ".join(missing),
                    data=score.model_dump(),
                )
            )
    return scores, blocked


def _score_one_keyword(
    row: StageMatchedKeyword,
    product: ProductInfo,
    rules: CategoryRules,
    target_cvr: float | None,
) -> tuple[KeywordScore, list[str]]:
    missing: list[str] = []
    override = _keyword_override(row.search_term, rules)

    transaction_score = override.get("transaction_data_score")
    if transaction_score is None:
        if target_cvr is None:
            missing.append("规则缺失：cvr_baseline")
        elif target_cvr <= 0:
            missing.append("规则错误：cvr_baseline 必须大于 0")
        else:
            multiplier = rules.scoring_weights.cvr_score_multiplier
            transaction_score = min(row.cvr / target_cvr / multiplier, 1) * 100

    region_score, region_missing, region_hard_conflict = _attribute_score(
        "region", row.search_term, product.region_tags, rules, override
    )
    spec_score, spec_missing, spec_hard_conflict = _attribute_score(
        "spec", row.search_term, [product.size_spec, product.material], rules, override
    )
    style_score, style_missing, style_hard_conflict = _attribute_score(
        "style", row.search_term, [product.style], rules, override
    )
    color_score, color_missing, color_hard_conflict = _attribute_score(
        "color", row.search_term, [product.color], rules, override
    )
    missing.extend(region_missing + spec_missing + style_missing + color_missing)
    hard_conflict = any([region_hard_conflict, spec_hard_conflict, style_hard_conflict, color_hard_conflict])

    components = [transaction_score, region_score, spec_score, style_score, color_score]
    total_score = override.get("total_match_score")
    if total_score is None and all(component is not None for component in components):
        weights = rules.scoring_weights
        total_score = (
            float(transaction_score) * weights.transaction_data
            + float(region_score) * weights.region_match
            + float(spec_score) * weights.spec_match
            + float(style_score) * weights.style_match
            + float(color_score) * weights.color_match
        )

    if row.stage_min_match_score is None:
        missing.append("规则缺失：stage.min_match_score")

    conclusion = "待人工确认"
    reasons = list(row.pool_reasons)
    needs_review = bool(row.needs_review)
    if missing:
        needs_review = True
        reasons.extend(missing)
    elif hard_conflict:
        conclusion = "不建议投放"
        reasons.append("产品属性硬冲突")
    elif not row.aba_stage_ok:
        conclusion = "ABA超出阶段范围，受限测试"
        needs_review = True
        reasons.append(row.aba_stage_status)
    elif float(total_score) >= float(row.stage_min_match_score):
        conclusion = "建议投放"
    else:
        conclusion = "受限测试"
        needs_review = True
        reasons.append("总匹配度未达到当前阶段最低匹配度")

    score = KeywordScore(
        asin=product.asin or product.sku,
        order_stage=row.order_stage,
        search_term=row.search_term,
        clicks=row.clicks,
        orders=row.orders,
        cvr=row.cvr,
        aba_rank=row.aba_rank,
        transaction_data_score=_round_score(transaction_score),
        region_score=_round_score(region_score),
        spec_score=_round_score(spec_score),
        style_score=_round_score(style_score),
        color_score=_round_score(color_score),
        total_match_score=_round_score(total_score),
        conclusion=conclusion,
        reasons=reasons,
        needs_review=needs_review,
        hard_conflict=hard_conflict,
        aba_stage_ok=row.aba_stage_ok,
    )
    return score, missing


def _keyword_override(search_term: str, rules: CategoryRules) -> dict[str, Any]:
    overrides = rules.attribute_scoring.get("keyword_score_overrides", {})
    return overrides.get(_normalize_term(search_term), overrides.get(search_term, {})) or {}


def _attribute_score(
    name: str,
    search_term: str,
    product_values: list[str | None] | list[str],
    rules: CategoryRules,
    override: dict[str, Any],
) -> tuple[float | None, list[str], bool]:
    override_key = f"{name}_score"
    if override_key in override:
        return float(override[override_key]), [], False

    config = rules.attribute_scoring.get(name, {})
    term = _normalize_term(search_term)
    hard_conflict_terms = [_normalize_term(item) for item in config.get("hard_conflict_terms", [])]
    if any(term_part in term for term_part in hard_conflict_terms):
        return 0, [], True

    candidates = [_normalize_term(value) for value in product_values if value]
    if any(candidate and candidate in term for candidate in candidates):
        return 100, [], False

    neutral_score = config.get("neutral_score")
    if neutral_score is not None and not _contains_any_known_attribute(term, config):
        return float(neutral_score), [], False

    partial_score = config.get("partial_match_score")
    if partial_score is not None:
        return float(partial_score), [], False

    return None, [f"规则缺失：attribute_scoring.{name}.partial_match_score"], False


def _contains_any_known_attribute(term: str, config: dict[str, Any]) -> bool:
    known_terms = [_normalize_term(item) for item in config.get("known_terms", [])]
    return any(item and item in term for item in known_terms)


def _normalize_term(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower().replace("-", " "))


def _round_score(value: Any) -> float | None:
    if value is None:
        return None
    rounded = round(float(value), 2)
    if rounded.is_integer():
        return int(rounded)
    return rounded
