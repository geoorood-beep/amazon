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
            "ad_types": [],
        }

    config = rules.strategy_rules.get("match_type_routing")
    error = _validate_routing_config(config)
    if error:
        return {"supported": False, "reason": error}

    if keyword_score.relevance_evidence_status != "READY":
        return {
            "supported": False,
            "reason": "相关性表未覆盖当前ASIN与搜索词，不判定Phrase/Broad",
        }
    allowed_levels = {str(item).upper() for item in config["eligible_relevance_levels"]}
    relevance_level = str(keyword_score.relevance_level or "").upper()
    if relevance_level not in allowed_levels:
        return {
            "supported": True,
            "eligible": False,
            "reason": f"相关性等级 {relevance_level or '未知'} 未通过投放资格门",
            "traffic_entry": _traffic_entry(keyword_score.search_term, product),
            "ad_type": None,
            "ad_types": [],
        }

    if keyword_score.match_type_evidence_status != "READY":
        return {
            "supported": False,
            "reason": "词根月搜索量或词根分布未覆盖当前候选，不得用ABA排名代替",
        }

    root_volume = keyword_score.root_monthly_search_volume
    top3_share = keyword_score.root_top3_volume_share
    query_count = keyword_score.root_distinct_query_count
    if root_volume is None or top3_share is None or query_count is None:
        return {
            "supported": False,
            "reason": "Phrase/Broad判定缺少词根月搜索量、Top3占比或有效查询数",
        }

    bands = config["root_monthly_volume_bands"]
    no_standalone_lt = float(bands["no_standalone_lt"])
    if root_volume < no_standalone_lt:
        return {
            "supported": True,
            "eligible": False,
            "reason": (
                f"词根月搜索量 {root_volume:g} 低于独立投放门 {no_standalone_lt:g}；"
                "仅保留候选，不新建广告组"
            ),
            "traffic_entry": _traffic_entry(keyword_score.search_term, product),
            "ad_type": None,
            "ad_types": [],
        }

    concentration = config["root_concentration"]
    specific_points = _semantic_specificity_points(keyword_score.search_term, product)
    sparse_limit = int(concentration["sparse_query_phrase_max"])
    phrase_share = float(concentration["phrase_top3_share_gte"])
    mixed_share = float(concentration["mixed_top3_share_gte"])

    if specific_points:
        ad_types = ["词组"]
        routing_reason = f"明确属性长尾优先Phrase：{'、'.join(specific_points)}"
    elif query_count <= sparse_limit:
        ad_types = ["词组"]
        routing_reason = f"词根仅 {query_count} 个有效查询，语序可控，优先Phrase"
    elif top3_share >= phrase_share:
        ad_types = ["词组"]
        routing_reason = f"词根Top3搜索量占比 {top3_share:.1%}，流量集中，优先Phrase"
    elif top3_share >= mixed_share:
        ad_types = ["词组", "广泛"]
        routing_reason = (
            f"词根Top3搜索量占比 {top3_share:.1%}，为中度分散；"
            "Phrase承接、Broad探索必须分组"
        )
    else:
        ad_types = ["广泛"]
        routing_reason = f"词根Top3搜索量占比 {top3_share:.1%}，流量分散，使用Broad探索"

    demand_tier = _demand_tier(root_volume, bands)
    strategy_by_type = {
        "词组": f"{demand_tier}：Phrase承接测试",
        "广泛": f"{demand_tier}：Broad低预算拓词",
    }
    observed_months = len(keyword_score.search_volume_months)
    preferred_months = int(config.get("preferred_complete_months", 3))
    window_reason = (
        f"；当前仅 {observed_months} 个完整月，少于优选 {preferred_months} 个月"
        if observed_months < preferred_months
        else ""
    )
    return {
        "supported": True,
        "eligible": True,
        "traffic_entry": _traffic_entry(keyword_score.search_term, product),
        "ad_type": ad_types[0],
        "ad_types": ad_types,
        "strategy": strategy_by_type[ad_types[0]],
        "strategy_by_type": strategy_by_type,
        "demand_tier": demand_tier,
        "needs_review": (
            root_volume < float(bands["conditional_group_lt"])
            or len(ad_types) > 1
            or observed_months < preferred_months
        ),
        "reason": f"{routing_reason}；词根月搜索量 {root_volume:g}（{demand_tier}）{window_reason}",
    }


def map_strategy(keyword_score: KeywordScore, product: ProductInfo, rules: CategoryRules) -> dict[str, Any]:
    return map_new_product_strategy(keyword_score, product, rules)


def _validate_routing_config(config: Any) -> str | None:
    if not isinstance(config, dict):
        return "规则缺失：strategy_rules.match_type_routing"
    required = {"eligible_relevance_levels", "root_monthly_volume_bands", "root_concentration"}
    if not required.issubset(config):
        return "规则缺失：match_type_routing相关性、月搜索量或集中度配置"
    try:
        bands = config["root_monthly_volume_bands"]
        volume_values = [
            float(bands["no_standalone_lt"]),
            float(bands["conditional_group_lt"]),
            float(bands["broad_test_lt"]),
            float(bands["phrase_priority_lt"]),
        ]
        concentration = config["root_concentration"]
        mixed = float(concentration["mixed_top3_share_gte"])
        phrase = float(concentration["phrase_top3_share_gte"])
        sparse = int(concentration["sparse_query_phrase_max"])
    except (KeyError, TypeError, ValueError):
        return "规则错误：match_type_routing配置不完整"
    if volume_values != sorted(volume_values) or volume_values[0] <= 0:
        return "规则错误：词根月搜索量分层必须严格递增且大于0"
    if len(set(volume_values)) != len(volume_values):
        return "规则错误：词根月搜索量分层不得重叠"
    if not 0 < mixed < phrase <= 1 or sparse < 1:
        return "规则错误：词根集中度门槛无效"
    return None


def _demand_tier(root_volume: float, bands: dict[str, Any]) -> str:
    if root_volume < float(bands["conditional_group_lt"]):
        return "低量条件测试"
    if root_volume < float(bands["broad_test_lt"]):
        return "可投测试层"
    if root_volume < float(bands["phrase_priority_lt"]):
        return "中高量主力层"
    return "高量核心层"


def _semantic_specificity_points(search_term: str, product: ProductInfo) -> list[str]:
    term = _normalize(search_term)
    points: list[str] = []
    if _normalized_size(product.size_spec) and _normalized_size(product.size_spec) in _normalized_size(term):
        points.append("明确尺寸")
    if any(_contains_phrase(term, tag) for tag in product.scene_tags if tag):
        points.append("明确场景")
    for label, value in (
        ("材质", product.material),
        ("风格", product.style),
        ("颜色", product.color),
        ("形状", product.shape),
    ):
        if value and _contains_phrase(term, value):
            points.append(f"明确{label}")
    return list(dict.fromkeys(points))


def _traffic_entry(search_term: str, product: ProductInfo) -> str:
    term = _normalize(search_term)
    if re.search(r"\b\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?\b", term):
        return "尺寸词"
    if product.size_spec and _normalize(product.size_spec) in term:
        return "尺寸词"
    if any(_normalize(tag) in term for tag in product.scene_tags):
        return "场景词"
    return "长尾词/场景词"


def _contains_phrase(term: str, value: str) -> bool:
    phrase = _normalize(value)
    if not phrase:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", term) is not None


def _normalized_size(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^0-9.x]", "", _normalize(value).replace("×", "x"))


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower().replace("-", " "))
