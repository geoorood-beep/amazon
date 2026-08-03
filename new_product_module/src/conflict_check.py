from __future__ import annotations

from collections import defaultdict

from .schemas import AdArchitectureRow, BlockedItem, CategoryRules, KeywordScore


def run_conflict_checks(
    ad_rows: list[AdArchitectureRow],
    keyword_scores: list[KeywordScore],
    rules: CategoryRules,
) -> tuple[list[AdArchitectureRow], list[BlockedItem]]:
    blocked: list[BlockedItem] = []
    keyword_to_groups: dict[str, list[str]] = defaultdict(list)
    for row in ad_rows:
        for keyword in _split_keywords(row.keyword):
            keyword_to_groups[keyword].append(row.ad_group_name)

    duplicate_keywords = {keyword: groups for keyword, groups in keyword_to_groups.items() if len(groups) > 1}
    if duplicate_keywords:
        for row in ad_rows:
            duplicated = [keyword for keyword in _split_keywords(row.keyword) if keyword in duplicate_keywords]
            if duplicated:
                row.needs_review = True
                reason = f"重复投放关键词：{'、'.join(duplicated)}"
                row.reasons.append(reason)
                blocked.append(
                    BlockedItem(
                        item_type="ad_architecture",
                        identifier=row.ad_group_name,
                        source_step="conflict_check",
                        reason=reason,
                        data=row.model_dump(),
                    )
                )

    max_test_spend = rules.risk_constraints.max_test_spend
    if max_test_spend is not None:
        total_budget = sum(row.budget or 0 for row in ad_rows)
        if total_budget > max_test_spend:
            reason = f"预算总和 {total_budget} 超过最大测试花费 {max_test_spend}"
            for row in ad_rows:
                row.needs_review = True
                row.reasons.append(reason)
            blocked.append(
                BlockedItem(
                    item_type="ad_architecture",
                    identifier="budget_total",
                    source_step="conflict_check",
                    reason=reason,
                    data={"total_budget": total_budget, "max_test_spend": max_test_spend},
                )
            )

    cpa_flagged = [score for score in keyword_scores if "CPA超标" in "；".join(score.reasons) and score.conclusion == "建议投放"]
    for score in cpa_flagged:
        blocked.append(
            BlockedItem(
                item_type="keyword",
                identifier=score.search_term,
                source_step="conflict_check",
                reason="CPA超标但仍为建议投放，需人工复核",
                data=score.model_dump(),
            )
        )
    return ad_rows, blocked


def _split_keywords(value: str) -> list[str]:
    return [part.strip() for part in value.replace(",", "、").split("、") if part.strip()]
