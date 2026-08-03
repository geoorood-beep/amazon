from __future__ import annotations

from .schemas import BlockedItem, CandidateKeyword, CategoryRules, HistoricalKeyword


def build_candidate_pool(
    historical_keywords: list[HistoricalKeyword],
    rules: CategoryRules,
    rug_type: str,
) -> tuple[list[CandidateKeyword], list[BlockedItem]]:
    baseline = rules.rug_type_baselines.get(rug_type)
    blocked: list[BlockedItem] = []
    if baseline is None:
        return [], [
            BlockedItem(
                item_type="product",
                identifier=rug_type,
                source_step="candidate_pool",
                reason="规则缺失：产品地毯类型未在 rug_type_baselines 中配置",
            )
        ]

    min_click_sample = baseline.min_click_sample
    if min_click_sample is None:
        min_click_sample = rules.candidate_pool_thresholds.min_click_sample

    min_order_sample = baseline.min_order_sample
    if min_order_sample is None:
        min_order_sample = rules.candidate_pool_thresholds.min_order_sample

    missing = []
    if min_click_sample is None:
        missing.append("min_click_sample")
    if min_order_sample is None:
        missing.append("min_order_sample")

    candidates: list[CandidateKeyword] = []
    if missing:
        for row in historical_keywords:
            candidate = CandidateKeyword.model_validate(row.model_dump())
            candidate.pool_status = "待人工确认"
            candidate.needs_review = True
            candidate.pool_reasons = [f"规则缺失：{field}" for field in missing]
            blocked.append(
                BlockedItem(
                    item_type="keyword",
                    identifier=row.search_term,
                    source_step="candidate_pool",
                    reason="; ".join(candidate.pool_reasons),
                    data=row.model_dump(),
                )
            )
        return candidates, blocked

    min_dates = rules.candidate_pool_thresholds.min_independent_order_dates
    for row in historical_keywords:
        candidate = CandidateKeyword.model_validate(row.model_dump())
        reasons: list[str] = []
        independent_dates = len(set(candidate.order_dates))

        if candidate.aba_conflict:
            reasons.append("同一关键词在多个 ABA 文件中的类型、层级、相关度或合规字段存在冲突")
        if candidate.compliance_status and candidate.compliance_status != "安全":
            reasons.append(f"ABA 合规状态为 {candidate.compliance_status}，不得进入常规广告候选池")
        if candidate.ad_status and candidate.ad_status != "可投":
            reasons.append(f"ABA 广告状态为 {candidate.ad_status}，需要隔离复核")

        if candidate.clicks < min_click_sample:
            reasons.append(f"历史点击 {candidate.clicks} 低于最低点击样本 {min_click_sample}")
        if candidate.orders < min_order_sample:
            reasons.append(f"历史订单 {candidate.orders} 低于最低重复订单 {min_order_sample}")
        if independent_dates < min_dates:
            reasons.append(f"独立成交日期 {independent_dates} 低于最低要求 {min_dates}")

        if not reasons:
            candidate.pool_status = "进入候选池"
        else:
            candidate.pool_status = "偶然成交候选" if candidate.orders < min_order_sample else "继续观察"
            candidate.pool_reasons = reasons
            candidate.needs_review = True
            blocked.append(
                BlockedItem(
                    item_type="keyword",
                    identifier=candidate.search_term,
                    source_step="candidate_pool",
                    reason="; ".join(reasons),
                    data={
                        "pool_status": candidate.pool_status,
                        "clicks": candidate.clicks,
                        "orders": candidate.orders,
                        "independent_order_dates": independent_dates,
                    },
                )
            )
        candidates.append(candidate)
    return candidates, blocked
