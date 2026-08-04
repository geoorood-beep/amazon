from __future__ import annotations

from .schemas import BlockedItem, CandidateKeyword, CategoryRules, StageMatchedKeyword, StageRule


def determine_order_stage(order_target_daily: float, rules: CategoryRules) -> StageRule:
    for stage in rules.order_stage_aba_table:
        if stage.min_daily_orders is None and stage.max_daily_orders is None:
            continue
        lower_ok = stage.min_daily_orders is None or order_target_daily >= stage.min_daily_orders
        upper_ok = stage.max_daily_orders is None or order_target_daily < stage.max_daily_orders
        if lower_ok and upper_ok:
            return stage
    if not rules.order_stage_aba_table:
        raise ValueError("order_stage_aba_table is empty")
    raise ValueError(
        f"订单目标 {order_target_daily} 未唯一命中 order_stage_aba_table；"
        "禁止回退到首个阶段"
    )


def match_stage(
    candidates: list[CandidateKeyword],
    rules: CategoryRules,
    rug_type: str,
    stage: str,
) -> tuple[list[StageMatchedKeyword], list[BlockedItem]]:
    stage_rule = next((item for item in rules.order_stage_aba_table if item.stage == stage), None)
    if stage_rule is None:
        return [], [
            BlockedItem(
                item_type="stage",
                identifier=stage,
                source_step="stage_matching",
                reason="规则缺失：order_stage_aba_table 中不存在该订单阶段",
            )
        ]

    aba_range = stage_rule.aba_range_for(rug_type)
    if aba_range is None:
        blocked = [
            BlockedItem(
                item_type="keyword",
                identifier=candidate.search_term,
                source_step="stage_matching",
                reason=f"规则缺失：{stage} 未配置 {rug_type}_aba_range",
                data=candidate.model_dump(),
            )
            for candidate in candidates
            if candidate.pool_status == "进入候选池"
        ]
        return [], blocked

    matched: list[StageMatchedKeyword] = []
    for candidate in candidates:
        if candidate.pool_status != "进入候选池":
            continue
        row = StageMatchedKeyword.model_validate(
            {
                **candidate.model_dump(),
                "order_stage": stage_rule.stage,
                "stage_min_match_score": stage_rule.min_match_score,
                "stage_max_keyword_count": stage_rule.max_keyword_count,
                "keyword_types": stage_rule.keyword_types,
            }
        )
        if aba_range[0] <= row.aba_rank <= aba_range[1]:
            row.aba_stage_ok = True
            row.aba_stage_status = "ABA阶段适配"
        else:
            row.aba_stage_ok = False
            row.aba_stage_status = "ABA超出阶段范围"
            row.needs_review = True
            row.pool_reasons.append(
                f"ABA排名 {row.aba_rank} 不在当前阶段区间 {aba_range[0]}-{aba_range[1]} 内"
            )
        matched.append(row)

    # Attribute conflicts are evaluated after the ABA stage gate.  Limiting here
    # would let high-ranked but wrong-attribute terms consume the whole quota.
    # The architecture builder applies max_keyword_count after hard conflicts.
    return matched, []


def _apply_stage_keyword_limit(rows: list[StageMatchedKeyword], stage_rule: StageRule) -> list[StageMatchedKeyword]:
    if stage_rule.max_keyword_count is None:
        return rows
    sorted_rows = sorted(rows, key=lambda row: (not row.aba_stage_ok, row.aba_rank, row.search_term))
    allowed_terms = {row.search_term for row in sorted_rows[: stage_rule.max_keyword_count]}
    for row in rows:
        if row.search_term not in allowed_terms:
            row.needs_review = True
            row.aba_stage_status = "超过阶段最大选词数"
            row.pool_reasons.append(f"当前阶段最多选择 {stage_rule.max_keyword_count} 个关键词")
    return rows
