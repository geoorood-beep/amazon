# 第 08 层：Autonomous Loop 受控闭环

## 当前状态

```text
HUMAN_EXECUTION_ONLY
ai_ads = TEST_ONLY
SP_COLD_START = CANDIDATE_ONLY
Amazon API 自动执行 = OFF
```

## 允许的闭环

```text
人工提供数据
→ Python 生成确定性证据与工具回执
→ Codex 按八层 AGENTS 上下文生成候选方案
→ Validator 独立重建上下文并核对回执
→ 人工审批与执行
→ 人工登记实际结果
→ 复盘形成证据
→ 生成 CANDIDATE
→ 人工批准后才可能升级
```

## 生产启用门

必须全部满足：

1. 单一机器规则源确定；
2. 规则文件和阈值文件形成同版本完整包；
3. 所有引用的 Threshold ID 存在且状态有效；
4. 真实报表预处理、对账和对象映射通过；
5. 历史回放和小范围试运行通过；
6. 回滚、执行确认和复盘链完整；
7. 人工明确批准生产能力。

任一条件未满足，不得通过改文档状态文字绕过阻断。
