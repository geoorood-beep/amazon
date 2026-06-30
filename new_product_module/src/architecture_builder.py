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

    group_index = 1
    for (traffic_entry, ad_type), items in sorted(grouped.items(), key=lambda item: item[0]):
        items = sorted(items, key=lambda item: (item[0].aba_rank, item[0].search_term))
        for chunk in _chunks(items, 5):
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
                ad_group_name=f"{asin}-{ad_type}-{traffic_entry}-{group_index:02d}",
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
            group_index += 1

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
