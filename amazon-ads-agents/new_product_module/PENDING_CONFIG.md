# 待运营配置清单

来源：`config/category_rules.example.yaml`

## 地毯类型基准

以下字段在 `area_rug`、`runner`、`doormat`、`round` 四个地毯类型下均为 `null`：

- `ctr_baseline`
- `cvr_baseline`
- `cpa_normal_line`
- `cpa_high_risk_line`
- `acos_target`
- `min_click_sample`
- `min_order_sample`

另有全局字段：

- `global_ctr_baseline`

## ABA 阶段表

以下阶段缺少 `doormat_aba_range` 和 `round_aba_range`：

- `0-15单/日`
- `15-30单/日`
- `30-50单/日`
- `50单+/日`
- `100单+/日`

以下阶段未配置 `min_match_score_upper`，当前只在 `100单+/日` 阶段按 SOP 记录了 `65-70` 的上限字段：

- `0-15单/日`
- `15-30单/日`
- `30-50单/日`
- `50单+/日`

说明：`100单+/日.max_daily_orders: null` 是无上限阶段，不属于待运营补数。

## 候选池门槛

- `candidate_pool_thresholds.min_click_sample`
- `candidate_pool_thresholds.min_order_sample`

实际执行时会优先读取各地毯类型下的 `min_click_sample` / `min_order_sample`；两处都缺失时，关键词进入 `待人工确认`。

## 属性匹配评分

- `attribute_scoring.region.partial_match_score`
- `attribute_scoring.spec.partial_match_score`
- `attribute_scoring.style.partial_match_score`
- `attribute_scoring.color.partial_match_score`
- `attribute_scoring.color.neutral_score`

## 预算、Bid、广告位和风险

- `bid_defaults.词组`
- `bid_defaults.广泛`
- `bid_defaults.自动`
- `bid_defaults.商品投放`
- `bid_defaults.default`
- `placement_defaults.词组`
- `placement_defaults.广泛`
- `placement_defaults.自动`
- `placement_defaults.商品投放`
- `placement_defaults.default`
- `risk_constraints.inventory_redline`
- `risk_constraints.profit_redline`
- `risk_constraints.max_test_spend`
