# 合同：候选动作、方案与执行

## 候选动作字段

至少包含：

- Candidate Action ID、Batch ID；
- AdProductType、StrategyProfile；
- object type、不可变 object ID；
- action type、action level、priority；
- current value、proposed value、expected current value、unit；
- source module、Rule ID、Threshold ID；
- evidence refs、sample status；
- `confidence`；
- `traffic_role`、`overlap_intent`（结构动作）；
- `expansion_execution_object`（拓量动作）；
- `budget_type`、`calculation_basis`、`target_orders_per_day`、`budget_purpose`（预算动作）；
- `setting_change_point_id`、`strategy_stage`（趋势动作）；
- `migration_state`、`migrated_winner_object_ids`（关闭旧流量前）；
- expected impact、risk、reversible；
- rollback value、valid until；
- preconditions、dependencies；
- review metrics、observation period；
- Action Pack ID（如适用）。

动作字段不变量：

- Candidate Action ID 在批次内必须唯一；
- 预算、Bid 和广告位动作的当前值、目标值、预期当前值及回滚值必须是非负数值；
- `INCREASE_*` 的目标值必须大于当前值，`DECREASE_*` 必须小于当前值；
- 预算动作只能定位 Campaign，Bid 动作只能定位 Ad Group / Target，广告位动作必须定位快照中真实存在的 Placement；
- `valid_until` 必须包含时区；
- 主动作、辅助动作和依赖动作一起参与相反动作及暂停冲突检查。
- 低置信度不得生成执行动作；中置信度只能进入人工审批。
- `CREATE_STRUCTURE` 必须声明流量角色和重叠意图；Phrase 承接与 Broad 拓词只有角色明确不同才可视为有意重叠。
- 拓量默认只允许已验证完整搜索词或真实 Target；词根聚合只有订单集中度门通过后才可作为执行对象。
- 预算动作必须区分标准最低、观察、拓量、复制验证和风险上限，不得只输出一个无语义的金额。
- 趋势动作必须按设置变更点切段；跨 Bid、预算或状态变化的数据不得当作同一策略阶段。
- 关闭 Broad、Phrase、Target、Ad Group 或 Campaign 旧流量前，迁移状态必须到 `LEGACY_REMAINDER_READY_TO_CLOSE`，且保存已迁移赢家的真实对象 ID；否则 Validator 阻断。

## 最终方案头部

- Plan ID；
- Batch ID；
- Data Snapshot ID；
- AdContext Version；
- AdProductType、StrategyProfile；
- Rule Package Version；
- Rule file SHA-256；
- Threshold file SHA-256；
- Rule Package Checksum；
- Model Version、Prompt Version、Schema Version。

## 方案正文

1. 方案摘要；
2. 最终动作表；
3. 被淘汰动作及原因；
4. Validator 结果。

## 人工执行确认

批次完全按计划执行时可记录批次级确认。未执行、实际值不同、时间不同或部分执行时必须逐条登记。执行状态只允许 `EXECUTED / SKIPPED / PARTIAL / FAILED`。

V2.0 固定启用独立生产保险。即使调用方把规则源和阈值源声明为 `ACTIVE`，只要项目仍为 `HUMAN_EXECUTION_ONLY`，生产模式必须返回 `PRODUCTION_EXECUTION_DISABLED`。
