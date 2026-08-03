# 第 04 层：Reflective Validator 与复盘

## 独立 Validator

Validator 只检查，不新增、不修改动作。它检查：

- 数据质量和对象映射；
- 类目、广告产品和 StrategyProfile 能力；
- 规则包版本与两个文件 SHA-256；
- 阈值空档、重叠和多重命中；
- 重复、相反、暂停与其他主动作冲突；
- 当前值、目标值、回滚值和有效期；
- 单动作及批次累计风险。

输出只能是 `AUTO_PASS / APPROVAL_REQUIRED / BLOCKED`。

## 复盘

复盘必须读取冻结方案、实际执行、前后快照、当时的 AdContext 和规则包快照。未满足观察期、归因成熟或执行记录要求时固定为 `NOT_READY`。

复盘只能生成证据和 `CANDIDATE`，不能覆盖 `ACTIVE`。当前项目尚未建立生产 `ACTIVE` 机器规则包。

规则入口：`rules/core/action-arbitration-validator.md`。合同入口：`contracts/review.md`。
