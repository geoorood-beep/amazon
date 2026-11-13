# 第 04 层：Reflective Validator 与复盘

## 独立 Validator

Validator 只检查，不新增、不修改动作。它检查：

- 服务端可信意图路由与请求路由完全一致；
- `agents_context.json` 可从当前文件重新构建且摘要一致，八层必须 8/8；
- 规则、阈值、知识、配置、工具、合同、本次证据的 SHA-256；
- Python 工具回执的输入、配置、程序和输出摘要；
- Codex 运行回执、原始 JSON、上下文摘要、完整 `sources_read` 和输出摘要；
- 数据质量和对象映射；
- 类目、广告产品和 StrategyProfile 能力；
- 规则包版本与两个文件 SHA-256；
- 阈值空档、重叠和多重命中；
- 重复、相反、暂停与其他主动作冲突；
- 当前值、目标值、回滚值和有效期；
- 单动作及批次累计风险。

输出只能是 `AUTO_PASS / APPROVAL_REQUIRED / BLOCKED`。

Validator 不信任网页、Python、Codex 或结果 JSON 自报的“已读取/已通过”。任一来源未登记、文件内容被替换、回执不一致或最终工作簿被篡改，固定阻断。聚合数据包可以使用 `DETERMINISTIC_TOOL_ONLY`；广告架构和 SP 优化结论必须使用 `CODEX_AGENTS`。

## 复盘

复盘必须读取冻结方案、实际执行、前后快照、当时的 AdContext 和规则包快照。未满足观察期、归因成熟或执行记录要求时固定为 `NOT_READY`。

复盘只能生成证据和 `CANDIDATE`，不能覆盖 `ACTIVE`。当前项目尚未建立生产 `ACTIVE` 机器规则包。

规则入口：`rules/core/action-arbitration-validator.md`。合同入口：`contracts/review.md`。
