# 待运营配置清单

来源：`config/category_rules.example.yaml`

当前文件状态为 `HUMAN_EXECUTION_ONLY + TEST_ONLY`。已确认的 Rug CVR / ACOS / CPA 连续区间已同步到 `rug_analysis_thresholds` 摘要，但以下字段没有得到独立确认，继续保持 `null`，不得由程序推算。

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

历史辅助模式会优先读取各地毯类型下的 `min_click_sample` / `min_order_sample`；两处都缺失时，历史效果词进入 `待人工确认`。这两个缺口不再清空 `ABA_COLD_START` 候选；冷启动按类型、次级属性、阶段、合规和广告状态门独立判断，且始终需要人工批准。

## 属性匹配评分

- `attribute_scoring.region.partial_match_score`
- `attribute_scoring.spec.partial_match_score`
- `attribute_scoring.style.partial_match_score`
- `attribute_scoring.color.partial_match_score`
- `attribute_scoring.color.neutral_score`

## Phrase / Broad 证据与回放

- `reference/rug-relevance/` 尚未放入实际 ASIN 相关性表；
- `reference/rug-search-volume/` 尚未放入实际搜索词月搜索量表；
- `3,000 / 10,000 / 30,000 / 100,000` 词根月搜索量分层和 `35% / 60%` Top3 占比是用户已确认的临时候选逻辑，但还没有用 Rug 数据回放校准；
- 数据补齐前机器状态保持 `MATCH_TYPE_DATA_PENDING / TEST_ONLY`，不得回退到 ABA 排名分界。

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

## 强收缩停止线

- Rug 点击 / 花费 O<2 停止线在 Markdown 中仍保留人工锚点，但确认原件未给出可执行 Threshold ID。
- 机器状态固定为 `BLOCKED_PENDING_THRESHOLD_ID`；补齐来源、Threshold ID、适用对象和 Validator 用例前，不得形成执行动作。
