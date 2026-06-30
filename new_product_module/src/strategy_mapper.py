from __future__ import annotations

import re
from typing import Any

from .schemas import CategoryRules, KeywordScore, ProductInfo


def map_new_product_strategy(
    keyword_score: KeywordScore,
    product: ProductInfo,
    rules: CategoryRules,
) -> dict[str, Any]:
    if product.business_goal != "新品验证":
        return {
            "supported": False,
            "reason": f"经营目标「{product.business_goal}」待支持",
        }

    term = _normalize(keyword_score.search_term)
    big_word_terms = [_normalize(item) for item in rules.strategy_rules.get("category_big_word_terms", [])]
    if term in big_word_terms:
        return {
            "supported": True,
            "eligible": False,
            "reason": "新品验证场景类目大词不投",
            "traffic_entry": "类目大词",
            "ad_type": None,
        }

    threshold = int(rules.strategy_rules.get("phrase_priority_aba_rank", 50000))
    ad_type = "词组" if keyword_score.aba_rank <= threshold else "广泛"
    return {
        "supported": True,
        "eligible": True,
        "traffic_entry": _traffic_entry(keyword_score.search_term, product),
        "ad_type": ad_type,
        "strategy": "词组小预算测试" if ad_type == "词组" else "广泛低预算测试",
        "reason": "新品验证：尺寸词、长尾词/场景词；新品阶段不建立精准关键词广告",
    }


def map_strategy(keyword_score: KeywordScore, product: ProductInfo, rules: CategoryRules) -> dict[str, Any]:
    return map_new_product_strategy(keyword_score, product, rules)


def _traffic_entry(search_term: str, product: ProductInfo) -> str:
    term = _normalize(search_term)
    if re.search(r"\b\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?\b", term):
        return "尺寸词"
    if product.size_spec and _normalize(product.size_spec) in term:
        return "尺寸词"
    if any(_normalize(tag) in term for tag in product.scene_tags):
        return "场景词"
    return "长尾词/场景词"


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower().replace("-", " "))
