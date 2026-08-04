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
    cold_start_config = rules.strategy_rules.get("aba_cold_start", {}) or {}
    cold_start_enabled = cold_start_config.get("status") == "CANDIDATE_ONLY"
    historical_rows: list[HistoricalKeyword] = []
    for row in historical_keywords:
        if row.evidence_grain != "ABA_COLD_START":
            historical_rows.append(row)
            continue
        candidate = CandidateKeyword.model_validate(row.model_dump())
        if not _aba_type_matches(candidate.aba_rug_types, rug_type):
            continue
        reasons: list[str] = []
        if not cold_start_enabled:
            reasons.append("ABA冷启动能力未启用")
        if candidate.aba_conflict:
            reasons.append("同一关键词在多个 ABA 文件中的类型、层级、相关度或合规字段存在冲突")
        if candidate.compliance_status and candidate.compliance_status != "安全":
            reasons.append(f"ABA 合规状态为 {candidate.compliance_status}，不得进入常规广告候选池")
        if candidate.ad_status and candidate.ad_status != "可投":
            reasons.append(f"ABA 广告状态为 {candidate.ad_status}，需要隔离复核")
        if reasons:
            candidate.pool_status = "冷启动阻断"
            candidate.pool_reasons = reasons
            candidate.needs_review = True
            blocked.append(
                BlockedItem(
                    item_type="keyword",
                    identifier=row.search_term,
                    source_step="candidate_pool",
                    reason="; ".join(reasons),
                    data={"evidence_grain": row.evidence_grain},
                )
            )
        else:
            candidate.pool_status = "进入候选池"
            candidate.pool_reasons = ["ABA冷启动候选：无当前ASIN历史绩效，仅限人工确认"]
            candidate.needs_review = True
        candidates.append(candidate)

    if missing and historical_rows:
        blocked.append(
            BlockedItem(
                item_type="rule_package",
                identifier=rug_type,
                source_step="candidate_pool",
                reason=(
                    "; ".join(f"规则缺失：{field}" for field in missing)
                    + f"；{len(historical_rows)} 个历史效果词未进入历史辅助候选池"
                ),
                data={"missing_fields": missing, "historical_keyword_count": len(historical_rows)},
            )
        )
        for row in historical_rows:
            candidate = CandidateKeyword.model_validate(row.model_dump())
            candidate.pool_status = "待人工确认"
            candidate.needs_review = True
            candidate.pool_reasons = [f"规则缺失：{field}" for field in missing]
            candidates.append(candidate)
        return candidates, blocked

    min_dates = rules.candidate_pool_thresholds.min_independent_order_dates
    for row in historical_rows:
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


def _aba_type_matches(values: list[str], rug_type: str) -> bool:
    aliases = {
        "area_rug": {"area_rug", "area rug", "区域", "小区域", "大区域"},
        "runner": {"runner", "长条"},
        "doormat": {"doormat", "door mat", "门垫"},
        "round": {"round", "圆形"},
    }
    expected = {item.strip().lower().replace(" ", "_") for item in aliases.get(rug_type, {rug_type})}
    actual = {str(item).strip().lower().replace(" ", "_") for item in values}
    return bool(expected.intersection(actual))
