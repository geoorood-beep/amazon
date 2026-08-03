from __future__ import annotations

from collections import defaultdict
from typing import Any

from .budget_calc import suggested_daily_budget
from .schemas import AdArchitectureRow, BlockedItem, CategoryRules, KeywordScore, ProductInfo
from .strategy_mapper import map_strategy


def build_ad_architecture(
    keyword_scores: list[KeywordScore],
    product: ProductInfo,
    rules: CategoryRules,
) -> tuple[list[AdArchitectureRow], list[BlockedItem]]:
    blocked: list[BlockedItem] = []
    eligible: list[tuple[KeywordScore, dict[str, Any]]] = []

    for score in keyword_scores:
        if score.conclusion == "建议投放":
            pass
        elif score.conclusion in {"受限测试", "ABA超出阶段范围，受限测试"}:
            if not rules.strategy_rules.get("allow_restricted_test_architecture", False):
                blocked.append(
                    BlockedItem(
                        item_type="keyword",
                        identifier=score.search_term,
                        source_step="architecture_builder",
                        reason="受限测试需要低预算、低Bid和测试上限配置后再生成广告架构",
                        data=score.model_dump(),
                    )
                )
                continue
        else:
            continue
        strategy = map_strategy(score, product, rules)
        if not strategy.get("supported", False):
            blocked.append(
                BlockedItem(
                    item_type="strategy",
                    identifier=product.business_goal,
                    source_step="strategy_mapper",
                    reason=strategy["reason"],
                    data=score.model_dump(),
                )
            )
            continue
        if not strategy.get("eligible", False):
            blocked.append(
                BlockedItem(
                    item_type="keyword",
                    identifier=score.search_term,
                    source_step="strategy_mapper",
                    reason=strategy["reason"],
                    data=score.model_dump(),
                )
            )
            continue
        eligible.append((score, strategy))

    grouped: dict[tuple[str, str], list[tuple[KeywordScore, dict[str, Any]]]] = defaultdict(list)
    for score, strategy in eligible:
        grouped[(strategy["traffic_entry"], strategy["ad_type"])].append((score, strategy))

    budget, budget_reasons = suggested_daily_budget(product, rules)
    rows: list[AdArchitectureRow] = []
    asin = product.asin or product.sku

    for (traffic_entry, ad_type), items in sorted(grouped.items(), key=lambda item: item[0]):
        items = sorted(items, key=lambda item: (item[0].aba_rank, item[0].search_term))
        rank_groups, grouping_error = _rank_aware_groups(items, rules)
        if grouping_error:
            blocked.append(
                BlockedItem(
                    item_type="strategy",
                    identifier=f"{traffic_entry}/{ad_type}",
                    source_step="architecture_builder",
                    reason=grouping_error,
                )
            )
            continue
        for chunk in rank_groups:
            terms = [score.search_term for score, _ in chunk]
            row_reasons = list(budget_reasons)
            bid = _default_bid(ad_type, rules)
            if bid is None:
                row_reasons.append(f"规则缺失：bid_defaults.{ad_type}")
            placement = _default_placement(ad_type, rules)
            if placement is None:
                row_reasons.append(f"规则缺失：placement_defaults.{ad_type}")

            needs_review = bool(row_reasons) or any(score.needs_review for score, _ in chunk)
            row_reasons.extend(reason for score, _ in chunk for reason in score.reasons)
            row = AdArchitectureRow(
                ad_group_name=_ad_group_name(product, ad_type, traffic_entry, chunk),
                asin=asin,
                ad_type=ad_type,
                budget=budget,
                bid=bid,
                strategy=chunk[0][1]["strategy"],
                placement=placement,
                keyword="、".join(terms),
                rationale=_rationale(chunk, traffic_entry),
                needs_review=needs_review,
                reasons=sorted(set(row_reasons)),
            )
            rows.append(row)

    for row in rows:
        if row.ad_type == "精准":
            row.needs_review = True
            row.reasons.append("地毯类目新品阶段禁止精准关键词广告")
            blocked.append(
                BlockedItem(
                    item_type="ad_architecture",
                    identifier=row.ad_group_name,
                    source_step="architecture_builder",
                    reason="地毯类目新品阶段禁止精准关键词广告",
                    data=row.model_dump(),
                )
            )

    return rows, blocked


def _chunks(items: list[tuple[KeywordScore, dict[str, Any]]], size: int) -> list[list[tuple[KeywordScore, dict[str, Any]]]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _rank_aware_groups(
    items: list[tuple[KeywordScore, dict[str, Any]]],
    rules: CategoryRules,
) -> tuple[list[list[tuple[KeywordScore, dict[str, Any]]]], str | None]:
    """Apply the fixed Rug grouping bands without mixing traffic levels."""

    config = rules.strategy_rules.get("ad_group_rank_bands", {}) or {}
    single_max = config.get("single_keyword_max_rank")
    multi_max = config.get("multi_keyword_max_rank")
    group_size = config.get("max_keywords_per_group")
    if any(value is None for value in (single_max, multi_max, group_size)):
        return [], "规则缺失：strategy_rules.ad_group_rank_bands"
    single_max = int(single_max)
    multi_max = int(multi_max)
    group_size = int(group_size)
    if single_max <= 0 or multi_max <= single_max or group_size <= 0:
        return [], "规则错误：ad_group_rank_bands 必须满足 0<单词线<多词线，且组词数>0"

    high_traffic = [item for item in items if item[0].aba_rank <= single_max]
    middle = [item for item in items if single_max < item[0].aba_rank <= multi_max]
    long_tail = [item for item in items if item[0].aba_rank > multi_max]
    groups = [[item] for item in high_traffic]
    groups.extend(_chunks(middle, group_size))
    groups.extend(_chunks(long_tail, group_size))
    return groups, None


def _ad_group_name(
    product: ProductInfo,
    ad_type: str,
    traffic_entry: str,
    chunk: list[tuple[KeywordScore, dict[str, Any]]],
) -> str:
    spu = product.spu or product.sku or "SPU待补"
    size = product.size_spec or "尺寸待补"
    operator = product.operator_name or "lulu"
    scene = product.scene_tags[0] if product.scene_tags else _rug_type_label(product.rug_type)
    if len(chunk) == 1:
        score = chunk[0][0]
        targeting = f"{score.search_term}({_format_aba_rank(score.aba_rank)})"
    else:
        targeting = f"{traffic_entry}多词"
    components = [spu, "SP", targeting, ad_type, scene, size, operator]
    return "-".join(_clean_name_component(value) for value in components)


def _rug_type_label(value: str | None) -> str:
    return {
        "runner": "长条",
        "doormat": "门垫",
        "area_rug": "区域",
        "round": "圆形",
    }.get(value or "", value or "场景待补")


def _format_aba_rank(rank: int) -> str:
    if rank >= 10_000:
        value = round(rank / 10_000, 1)
        return f"{value:g}w"
    value = round(rank / 1_000, 1)
    return f"{value:g}k"


def _clean_name_component(value: Any) -> str:
    return " ".join(str(value).replace("-", " ").split())


def _default_bid(ad_type: str, rules: CategoryRules) -> float | None:
    value = rules.bid_defaults.get(ad_type)
    if value is None:
        value = rules.bid_defaults.get("default")
    return None if value is None else float(value)


def _default_placement(ad_type: str, rules: CategoryRules) -> str | None:
    value = rules.placement_defaults.get(ad_type)
    if value is None:
        value = rules.placement_defaults.get("default")
    return None if value is None else str(value)


def _rationale(chunk: list[tuple[KeywordScore, dict[str, Any]]], traffic_entry: str) -> str:
    scores = [score for score, _ in chunk]
    terms = "、".join(score.search_term for score in scores)
    conclusions = "；".join(f"{score.search_term}: {score.conclusion}, 总分{score.total_match_score}" for score in scores)
    return f"{traffic_entry}入口；投放词：{terms}；{conclusions}。"
