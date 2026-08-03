# 合同：小白运营入口任务

状态：`V2.0 / HUMAN_EXECUTION_ONLY`。

网页只提交业务意图和输入，不保存业务规则或阈值。允许意图固定为：

- `NEW_PRODUCT_PROMOTION`；
- `OLD_PRODUCT_OPTIMIZATION`；
- `AGGREGATE_REPORTS`；
- `WEEKLY_REVIEW`。

每个任务必须保存 `job_id`、意图、`category=rug`、创建时间、输入字段、输入文件引用、AGENTS/规则/阈值版本、预处理状态、Codex结果和 Validator结果。

固定状态：

```text
QUEUED
→ PREPROCESSING
→ ANALYZING
→ VALIDATING
→ COMPLETED / BLOCKED / FAILED
```

网页和 Codex Worker 均不得输出已执行状态。所有建议固定为 `CANDIDATE_ONLY`，最后只能“确认并导出执行表、重新分析、拒绝方案”。Amazon 后台连接和自动执行保持关闭。

任务运行目录位于 `runtime/operator-jobs/<job_id>/`，不纳入 V2.0 规则包或 Git。网页路由只读 [operator_intents.json](../config/operator_intents.json)，具体规则、阈值和输出字段仍从其单一真源读取。
