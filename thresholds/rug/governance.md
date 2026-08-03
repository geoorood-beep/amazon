# Rug 治理阈值

## 归因成熟等待期

- Threshold ID：`THR-301`
- 状态：`CONFIRMED_HUMAN`
- 最低等待期：观察期结束后 `7 个完整自然日`。
- 如果来源报表声明更长窗口，使用更长窗口。
- 口径冲突或无法确认时不得标记 `DQ_PASS`。

## 趋势动作窗口

- 状态：`HUMAN_RULE_FIXED`
- 动作窗口：`D0-3`、`D4-7`、`D8-14`、`D15-30`，互不重叠。
- 滚动 `3/7/14/30` 天只描述水平，不直接触发动作。
- 机器 Threshold ID：`PENDING`。

## 小时预算压力监控

- 状态：`BLOCKED_PENDING_HOURLY_CALIBRATION / READ_ONLY_ONLY`
- 机器 Threshold ID：`PENDING`。
- 当前没有可用的 `marketplace + timezone + category + effective_period` 校准曲线，因此不定义“理想累计花费”、过快、过慢或正常阈值。
- 2026-08-03 提供的“小时预算/小时花费”文件只有 30 天账户汇总，没有小时字段和预算字段，不能用于分时校准。

有逐小时数据时，只允许输出以下实际事实：

- 本地时区、小时、累计花费和累计花费占比；
- Campaign 日预算、预算剩余比例和首次耗尽时间；
- 是否在当日结束前耗尽，以及数据缺失小时。

未维护校准曲线前，不得输出过快/过慢/正常标签，也不得据此生成预算、Bid 或广告位动作。新增曲线必须记录 Marketplace、时区、Rug 类目、样本周期、样本量、生成方法、`effective_from`、`expires_at` 和来源文件 SHA-256。
