# 合同：数据输入

## AdContext

至少包含：

- `schema_version`；
- `ad_context_version`；
- `valid_until`；
- Marketplace、Account ID、Link ID、Category；
- AdProductType、StrategyProfile、BusinessMode；
- 唯一 Primary Objective；
- promotion、price、inventory 状态；
- budget cap、margin floor、protected entities。

BusinessMode 只允许 `NORMAL / EVENT / ANOMALY`。库存假设必须显式记录，不能静默假设充足。

## Data Snapshot

至少包含：

- Data Snapshot ID；
- 周期、站点、时区、币种、归因窗口；
- 报表来源文件、sheet、行数和 SHA-256；
- Campaign、Ad Group、Target、搜索词和商品不可变 ID；
- 当前预算、Bid、Placement 和状态；
- 原始样本数及确定性派生指标；
- 数据质量问题和对账状态。
- Bid、预算、Placement 或状态的设置变更点：`setting_change_point_id`、对象 ID、带时区生效时间、变更字段和来源证据。

共享数据包不能提前写入 ACTIVE 阈值命中或广告动作建议。

缺设置变更历史时可以做当前横截面分析，但跨变更期趋势只能标记 `INCONCLUSIVE`，不得生成趋势动作。

完整模式还必须满足：

- 六类必需报表的周期与 Data Snapshot 周期完全一致，且 `row_count>0`；
- Campaign、Ad Group、Target、搜索词和指标解析结果均非空；
- 搜索词、Target、Ad Group、Campaign 必须属于同一父级链；
- `D3 / D7 / D14 / D30` 分别覆盖 3 / 7 / 14 / 30 个完整自然日；
- 点击不得大于曝光，订单不得大于点击，订单必须是整数；
- 所有 `datetime` 字段必须包含明确时区。

任一条件不满足时为 `DQ_BLOCKED`，不得用报表文件存在、文件名正确或空表壳替代有效数据。

## 老品标准输入报表

必须：

1. `SP搜索词-按词-每日明细`；
2. `SP搜索词-按词-汇总`；
3. `SP投放对象 / 关键词 / 商品投放报告`；
4. `SP广告位报告`；
5. `SP广告商品报告`；
6. `Campaign / Ad Group 设置表`。

建议：

1. `SP广告位-每日明细`；
2. `SP关键词-每日明细`；
3. `小时预算 / 小时花费报告`；
4. `商品业务数据 / 订单目标 / 利润信息`；
5. `SPV / SB / SBV 素材与账户条件表`。

输入文件名不同时先显示映射到上述哪个标准报表。无法映射时标记待人工确认，不按文件名猜测口径。
